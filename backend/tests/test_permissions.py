from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import SessionLocal, engine
from app.documents import create_document
from app.models import AuditLog, SharingPermission
from app.audit import verify_audit_chain
from app.permissions import (
    get_viewer_document_access,
    list_shared_documents,
    record_viewer_document_access,
    revoke_share,
    share_document,
)
from app.security import Role


def make_document(owner):
    return create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 1024
    )


def make_share(document, viewer, **options):
    return share_document(
        document_id=document["id"],
        owner_id=document["owner_id"],
        recipient_name=viewer["name"],
        recipient_email=viewer["email"],
        expires_at=options.pop(
            "expires_at", datetime.now(timezone.utc) + timedelta(days=1)
        ),
        **options,
    )


def test_owner_can_share_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)

    share = make_share(document, viewer)

    assert share["viewer_id"] == viewer["id"]
    assert share["can_view"] is True
    assert share["can_download"] is False
    assert share["expires_at"] is not None
    with SessionLocal() as db:
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "document_shared")
        ) is not None


def test_owner_can_share_with_another_owner_for_one_time_access(
    create_account,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    recipient = create_account(
        "Recipient Owner", "recipient@example.com", Role.OWNER
    )
    document = make_document(owner)

    share = share_document(
        document_id=document["id"],
        owner_id=owner["id"],
        recipient_name=recipient["name"],
        recipient_email=recipient["email"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        can_download=True,
    )

    authorized = get_viewer_document_access(
        document["id"],
        recipient["id"],
        require_download=True,
    )
    record_viewer_document_access(
        document["id"],
        recipient["id"],
        require_download=True,
    )

    assert share["viewer_id"] == recipient["id"]
    assert authorized["id"] == document["id"]
    with SessionLocal() as db:
        stored = db.get(SharingPermission, share["id"])
        assert stored.viewed_at is not None


def test_other_owner_cannot_share_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other = create_account("Other", "other@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)

    with pytest.raises(HTTPException) as error:
        share_document(
            document["id"],
            other["id"],
            viewer["name"],
            viewer["email"],
            datetime.now(timezone.utc) + timedelta(days=1),
        )

    assert error.value.status_code == 404


def test_share_requires_active_viewer(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    inactive = create_account(
        "Inactive", "inactive@example.com", active=False
    )
    document = make_document(owner)

    with pytest.raises(HTTPException) as error:
        make_share(document, inactive)

    assert error.value.status_code == 400


def test_viewer_sees_shared_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    make_share(document, viewer)

    result = list_shared_documents(viewer["id"])

    assert len(result) == 1
    assert result[0]["document_id"] == document["id"]
    assert result[0]["viewed"] is False


def test_revoked_share_disappears_from_viewer_list(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    share = make_share(document, viewer)

    revoke_share(share["id"], owner["id"])

    assert list_shared_documents(viewer["id"]) == []
    with SessionLocal() as db:
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "document_share_revoked"
            )
        ) is not None
    assert verify_audit_chain() is True


def test_another_owner_cannot_revoke_share(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other = create_account("Other", "other@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    share = make_share(make_document(owner), viewer)

    with pytest.raises(HTTPException) as error:
        revoke_share(share["id"], other["id"])

    assert error.value.status_code == 404


def test_expired_permission_is_rejected(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    share = make_share(document, viewer)
    with SessionLocal.begin() as db:
        db.get(SharingPermission, share["id"]).expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        )

    with pytest.raises(HTTPException) as error:
        get_viewer_document_access(document["id"], viewer["id"])

    assert error.value.status_code == 403


def test_revoked_permission_is_rejected(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    share = make_share(document, viewer)
    revoke_share(share["id"], owner["id"])

    with pytest.raises(HTTPException) as error:
        get_viewer_document_access(document["id"], viewer["id"])

    assert error.value.status_code == 403


def test_one_successful_access_consumes_share_and_is_audited(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    share = make_share(document, viewer)

    allowed = get_viewer_document_access(document["id"], viewer["id"])
    assert allowed["id"] == document["id"]

    record_viewer_document_access(document["id"], viewer["id"])

    with pytest.raises(HTTPException) as error:
        get_viewer_document_access(document["id"], viewer["id"])
    assert error.value.status_code == 403

    with SessionLocal() as db:
        stored_share = db.get(SharingPermission, share["id"])
        events = db.scalars(
            select(AuditLog).where(AuditLog.action == "document_viewed")
        ).all()
        assert stored_share.viewed_at is not None
        assert len(events) == 1


def test_download_requires_permission_and_consumes_same_allowance(
    create_account,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    make_share(document, viewer, can_download=True)

    record_viewer_document_access(
        document["id"], viewer["id"], require_download=True
    )

    with pytest.raises(HTTPException) as error:
        get_viewer_document_access(document["id"], viewer["id"])
    assert error.value.status_code == 403


def test_invalid_expiration_and_name_are_rejected(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)

    with pytest.raises(HTTPException) as error:
        make_share(
            document,
            viewer,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
    assert error.value.status_code == 400

    with pytest.raises(HTTPException) as error:
        share_document(
            document["id"],
            owner["id"],
            " ",
            viewer["email"],
            datetime.now(timezone.utc) + timedelta(days=1),
        )
    assert error.value.status_code == 400


@pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="SQLite cannot exercise PostgreSQL row-lock concurrency.",
)
def test_concurrent_requests_grant_only_one_successful_access(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = make_document(owner)
    make_share(document, viewer)
    barrier = Barrier(2)

    def access():
        barrier.wait()
        try:
            record_viewer_document_access(document["id"], viewer["id"])
            return "granted"
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: access(), range(2)))

    assert results.count("granted") == 1
    assert results.count(403) == 1
