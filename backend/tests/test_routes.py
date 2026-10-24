from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.auth import create_access_token
from app.audit import verify_audit_chain
from app.database import SessionLocal
from app.documents import create_document
from app.main import app
from app.models import (
    AuditLog,
    Document,
    SharingPermission,
    User,
    UserIdentity,
)
from app.security import Role
from sqlalchemy import select


client = TestClient(app)


def auth_headers(user):
    return {
        "Authorization": f"Bearer {create_access_token(user)}",
    }


def test_owner_shares_owned_document_by_recipient_email(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    response = client.post(
        f"/documents/{document['id']}/share",
        headers=auth_headers(owner),
        json={
            "recipient_name": viewer["name"],
            "recipient_email": viewer["email"],
            "expires_at": expires_at.isoformat(),
            "can_download": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["viewer_id"] == viewer["id"]
    assert response.json()["can_download"] is True


def test_owner_shared_access_lists_only_owned_shares_and_revokes_them(
    create_account,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other_owner = create_account("Other Owner", "other@example.com", Role.OWNER)
    recipient = create_account("Recipient", "recipient@example.com", Role.VIEWER)
    owner_document = create_document(
        owner["id"], Role.OWNER, "owner-report.pdf", "application/pdf", 100
    )
    other_document = create_document(
        other_owner["id"], Role.OWNER, "other-report.pdf", "application/pdf", 100
    )
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    owner_share_response = client.post(
        f"/documents/{owner_document['id']}/share",
        headers=auth_headers(owner),
        json={
            "recipient_name": recipient["name"],
            "recipient_email": recipient["email"],
            "expires_at": expires_at,
            "can_download": True,
        },
    )
    other_share_response = client.post(
        f"/documents/{other_document['id']}/share",
        headers=auth_headers(other_owner),
        json={
            "recipient_name": recipient["name"],
            "recipient_email": recipient["email"],
            "expires_at": expires_at,
            "can_download": False,
        },
    )

    assert owner_share_response.status_code == 201
    assert other_share_response.status_code == 201
    owner_list_response = client.get(
        "/owner/shares",
        headers=auth_headers(owner),
    )
    assert owner_list_response.status_code == 200
    assert len(owner_list_response.json()) == 1
    owner_share = owner_list_response.json()[0]
    assert owner_share["id"] == owner_share_response.json()["id"]
    assert owner_share["filename"] == "owner-report.pdf"
    assert owner_share["recipient_email"] == recipient["email"]

    assert client.get(
        "/owner/shares",
        headers=auth_headers(recipient),
    ).status_code == 403
    assert client.get("/owner/shares").status_code == 401

    revoke_response = client.delete(
        f"/shares/{owner_share['id']}",
        headers=auth_headers(owner),
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["share"]["revoked"] is True


def test_owner_recipient_can_view_shared_document_once(
    create_account,
    monkeypatch,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    recipient = create_account(
        "Recipient Owner", "recipient@example.com", Role.OWNER
    )
    document = create_document(
        owner["id"], Role.OWNER, "owner-report.pdf", "application/pdf", 100
    )
    monkeypatch.setattr(
        "app.routes.download_object",
        lambda _path: b"shared owner document",
    )

    share_response = client.post(
        f"/documents/{document['id']}/share",
        headers=auth_headers(owner),
        json={
            "recipient_name": recipient["name"],
            "recipient_email": recipient["email"],
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
            "can_download": True,
        },
    )
    incoming_response = client.get(
        "/shared-with-me",
        headers=auth_headers(recipient),
    )
    access_response = client.get(
        f"/documents/{document['id']}/file",
        headers=auth_headers(recipient),
    )
    repeated_access = client.get(
        f"/documents/{document['id']}/file",
        headers=auth_headers(recipient),
    )

    assert share_response.status_code == 201
    assert incoming_response.status_code == 200
    assert incoming_response.json()[0]["document_id"] == document["id"]
    assert access_response.status_code == 200
    assert access_response.content == b"shared owner document"
    assert repeated_access.status_code == 403


def test_owner_cannot_share_another_owners_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other = create_account("Other", "other@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        other["id"], Role.OWNER, "private.pdf", "application/pdf", 100
    )

    response = client.post(
        f"/documents/{document['id']}/share",
        headers=auth_headers(owner),
        json={
            "recipient_name": viewer["name"],
            "recipient_email": viewer["email"],
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 404


def test_viewer_list_is_scoped_and_other_viewer_cannot_fetch_file(
    create_account, monkeypatch
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    recipient = create_account("Recipient", "recipient@example.com")
    other_viewer = create_account("Other", "other@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )

    from app.permissions import share_document

    share_document(
        document["id"],
        owner["id"],
        recipient["name"],
        recipient["email"],
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    recipient_list = client.get(
        "/shared-with-me", headers=auth_headers(recipient)
    )
    other_list = client.get(
        "/shared-with-me", headers=auth_headers(other_viewer)
    )
    unauthorized_file = client.get(
        f"/documents/{document['id']}/file",
        headers=auth_headers(other_viewer),
    )

    assert recipient_list.status_code == 200
    assert recipient_list.json()[0]["document_id"] == document["id"]
    assert recipient_list.json()[0]["id"] != document["id"]
    assert other_list.json() == []
    assert unauthorized_file.status_code == 403


def test_unauthorized_document_download_is_denied_without_server_error(
    create_account,
    monkeypatch,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other_owner = create_account(
        "Other Owner", "other-owner@example.com", Role.OWNER
    )
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "private.pdf", "application/pdf", 100
    )
    monkeypatch.setattr(
        "app.routes.download_object",
        lambda _path: pytest.fail("Unauthorized download reached storage."),
    )

    owner_response = client.get(
        f"/documents/{document['id']}/download",
        headers=auth_headers(other_owner),
    )
    viewer_response = client.get(
        f"/documents/{document['id']}/download",
        headers=auth_headers(viewer),
    )

    assert owner_response.status_code == 403
    assert viewer_response.status_code == 403


@pytest.mark.parametrize("recipient_role", [Role.VIEWER, Role.OWNER])
def test_shared_recipient_download_is_single_use(
    create_account,
    monkeypatch,
    recipient_role,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    recipient = create_account(
        "Recipient",
        f"{recipient_role.value}-recipient@example.com",
        recipient_role,
    )
    document = create_document(
        owner["id"], Role.OWNER, "shared.pdf", "application/pdf", 100
    )
    from app.permissions import share_document

    share_document(
        document_id=document["id"],
        owner_id=owner["id"],
        recipient_name=recipient["name"],
        recipient_email=recipient["email"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        can_download=True,
    )
    delivered_paths = []
    monkeypatch.setattr(
        "app.routes.download_object",
        lambda path: delivered_paths.append(path) or b"document bytes",
    )

    first = client.get(
        f"/documents/{document['id']}/download",
        headers=auth_headers(recipient),
    )
    second = client.get(
        f"/documents/{document['id']}/download",
        headers=auth_headers(recipient),
    )

    assert first.status_code == 200
    assert first.content == b"document bytes"
    assert second.status_code == 403
    assert len(delivered_paths) == 1


@pytest.mark.parametrize(
    "share_state",
    ["expired", "revoked"],
)
@pytest.mark.parametrize("recipient_role", [Role.VIEWER, Role.OWNER])
def test_expired_or_revoked_share_cannot_be_downloaded(
    create_account,
    monkeypatch,
    recipient_role,
    share_state,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    recipient = create_account(
        "Recipient",
        f"{recipient_role.value}-recipient@example.com",
        recipient_role,
    )
    document = create_document(
        owner["id"], Role.OWNER, "shared.pdf", "application/pdf", 100
    )
    from app.permissions import revoke_share, share_document

    share = share_document(
        document_id=document["id"],
        owner_id=owner["id"],
        recipient_name=recipient["name"],
        recipient_email=recipient["email"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        can_download=True,
    )
    if share_state == "expired":
        with SessionLocal.begin() as db:
            db.get(SharingPermission, share["id"]).expires_at = (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            )
    else:
        revoke_share(share["id"], owner["id"])

    monkeypatch.setattr(
        "app.routes.download_object",
        lambda _path: pytest.fail("Invalid share reached storage."),
    )
    response = client.get(
        f"/documents/{document['id']}/download",
        headers=auth_headers(recipient),
    )

    assert response.status_code == 403


def test_owner_upload_still_persists_document_metadata(
    create_account, monkeypatch
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    monkeypatch.setattr(
        "app.storage.upload_object", lambda _path, _contents, _type: None
    )

    response = client.post(
        "/documents/upload",
        headers=auth_headers(owner),
        files={"file": ("report.txt", b"document body", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "report.txt"
    assert response.json()["size_bytes"] == len(b"document body")


def test_viewer_can_request_owner_access_and_admin_approval_changes_role(
    create_account,
):
    viewer = create_account("Viewer", "viewer@example.com")
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    request_response = client.post(
        "/auth/owner-access-request",
        headers=auth_headers(viewer),
    )
    duplicate_response = client.post(
        "/auth/owner-access-request",
        headers=auth_headers(viewer),
    )
    admin_list = client.get(
        "/admin/owner-access-requests",
        headers=auth_headers(admin),
    )

    assert request_response.status_code == 201
    assert request_response.json()["status"] == "pending"
    assert duplicate_response.status_code == 409
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1

    approved = client.patch(
        f"/admin/owner-access-requests/{request_response.json()['id']}",
        headers=auth_headers(admin),
        json={"decision": "approve"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    with SessionLocal() as db:
        assert db.get(User, viewer["id"]).role == Role.OWNER.value
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user_role_changed",
                AuditLog.details["request_status"].as_string() == "approved",
            )
        ) is not None
    assert verify_audit_chain() is True


def test_only_admin_can_review_owner_access_request(create_account):
    viewer = create_account("Viewer", "viewer@example.com")
    other_viewer = create_account("Other", "other@example.com")
    request_response = client.post(
        "/auth/owner-access-request",
        headers=auth_headers(viewer),
    )

    response = client.patch(
        f"/admin/owner-access-requests/{request_response.json()['id']}",
        headers=auth_headers(other_viewer),
        json={"decision": "approve"},
    )

    assert response.status_code == 403
    with SessionLocal() as db:
        assert db.get(User, viewer["id"]).role == Role.VIEWER.value


def test_viewer_cannot_access_owner_request_admin_list(create_account):
    viewer = create_account("Viewer", "viewer@example.com")

    response = client.get(
        "/admin/owner-access-requests",
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403


def test_admin_can_reject_owner_access_request(create_account):
    viewer = create_account("Viewer", "viewer@example.com")
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    request_response = client.post(
        "/auth/owner-access-request",
        headers=auth_headers(viewer),
    )

    response = client.patch(
        f"/admin/owner-access-requests/{request_response.json()['id']}",
        headers=auth_headers(admin),
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    with SessionLocal() as db:
        assert db.get(User, viewer["id"]).role == Role.VIEWER.value


def test_only_active_admin_can_manage_accounts(create_account):
    viewer = create_account("Viewer", "viewer@example.com")
    inactive_admin = create_account(
        "Inactive Admin", "admin@example.com", Role.ADMIN, active=False
    )

    assert client.get(
        "/admin/users", headers=auth_headers(viewer)
    ).status_code == 403
    assert client.get(
        "/admin/users", headers=auth_headers(inactive_admin)
    ).status_code == 401


def test_owner_audit_endpoint_is_scoped_and_admin_endpoint_remains_protected(
    create_account,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    owner_response = client.get(
        "/owner/audit-logs", headers=auth_headers(owner)
    )
    owner_admin_logs_response = client.get(
        "/admin/audit-logs", headers=auth_headers(owner)
    )
    viewer_owner_logs_response = client.get(
        "/owner/audit-logs", headers=auth_headers(viewer)
    )
    admin_owner_logs_response = client.get(
        "/owner/audit-logs", headers=auth_headers(admin)
    )

    assert owner_response.status_code == 200
    assert owner_admin_logs_response.status_code == 403
    assert viewer_owner_logs_response.status_code == 403
    assert admin_owner_logs_response.status_code == 403


def test_admin_document_count_excludes_soft_deleted_and_requires_admin(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    active_document = create_document(
        owner["id"], Role.OWNER, "active.pdf", "application/pdf", 10
    )
    deleted_document = create_document(
        owner["id"], Role.OWNER, "deleted.pdf", "application/pdf", 10
    )
    with SessionLocal.begin() as db:
        db.get(Document, deleted_document["id"]).is_deleted = True

    response = client.get(
        "/admin/document-count", headers=auth_headers(admin)
    )
    owner_response = client.get(
        "/admin/document-count", headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json() == {"count": 1}
    assert active_document["id"] != deleted_document["id"]
    assert owner_response.status_code == 403


def test_admin_delete_removes_user_and_preserves_relations(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )

    from app.permissions import share_document

    share = share_document(
        document["id"],
        owner["id"],
        viewer["name"],
        viewer["email"],
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    response = client.delete(
        f"/admin/users/{owner['id']}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(User, owner["id"]) is None
        identity = db.get(UserIdentity, owner["id"])
        assert identity is not None
        assert identity.deleted_at is not None
        assert db.get(Document, document["id"]) is not None
        assert db.get(SharingPermission, share["id"]).revoked is True
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user_account_deleted"
            )
        ) is not None
    assert verify_audit_chain() is True


def test_non_admin_cannot_use_account_delete_route(create_account):
    viewer = create_account("Viewer", "viewer@example.com")
    target = create_account("Target", "target@example.com")

    response = client.delete(
        f"/admin/users/{target['id']}",
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403


def test_admin_cannot_bypass_admin_deletion_policy_with_self_delete(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    response = client.delete(
        "/auth/account",
        headers=auth_headers(admin),
    )

    assert response.status_code == 403
    with SessionLocal() as db:
        assert db.get(User, admin["id"]) is not None


def test_admin_cannot_delete_last_admin_through_admin_route(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    response = client.delete(
        f"/admin/users/{admin['id']}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 400
    with SessionLocal() as db:
        assert db.get(User, admin["id"]) is not None


@pytest.mark.parametrize(
    ("role", "email"),
    [
        (Role.VIEWER, "viewer@example.com"),
        (Role.OWNER, "owner@example.com"),
    ],
)
def test_viewer_and_owner_can_still_delete_own_accounts(
    create_account,
    role,
    email,
):
    account = create_account("Account", email, role)

    response = client.delete(
        "/auth/account",
        headers=auth_headers(account),
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(User, account["id"]) is None
        identity = db.get(UserIdentity, account["id"])
        assert identity is not None
        assert identity.deleted_at is not None


def test_failed_storage_delivery_does_not_consume_share(
    create_account, monkeypatch
):
    from app.permissions import share_document

    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )
    share_document(
        document["id"],
        owner["id"],
        viewer["name"],
        viewer["email"],
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    def storage_failure(_path):
        raise HTTPException(status_code=502, detail="Storage unavailable.")

    monkeypatch.setattr("app.routes.download_object", storage_failure)
    response = client.get(
        f"/documents/{document['id']}/file",
        headers=auth_headers(viewer),
    )
    assert response.status_code == 502
    with SessionLocal() as db:
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "document_viewed")
        ) is None

    def storage_success(_path):
        return b"verified document contents"

    monkeypatch.setattr("app.routes.download_object", storage_success)
    response = client.get(
        f"/documents/{document['id']}/file",
        headers=auth_headers(viewer),
    )

    assert response.status_code == 200
    assert response.content == b"verified document contents"
    assert verify_audit_chain() is True


def test_repeated_file_request_is_denied_and_audited(
    create_account, monkeypatch
):
    from app.permissions import share_document

    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )
    share_document(
        document["id"],
        owner["id"],
        viewer["name"],
        viewer["email"],
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    monkeypatch.setattr(
        "app.routes.download_object", lambda _path: b"contents"
    )
    headers = auth_headers(viewer)

    first = client.get(
        f"/documents/{document['id']}/file", headers=headers
    )
    second = client.get(
        f"/documents/{document['id']}/file", headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 403
    assert second.json()["detail"] == "This share has already been viewed."
    with SessionLocal() as db:
        actions = db.scalars(
            select(AuditLog.action)
            .where(
                AuditLog.action.in_(
                    ["document_viewed", "document_access_denied"]
                )
            )
        ).all()
    assert actions.count("document_viewed") == 1
    assert actions.count("document_access_denied") == 1
    assert verify_audit_chain() is True
