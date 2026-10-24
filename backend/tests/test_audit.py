import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.audit import (
    log_event,
    list_audit_logs,
    list_owner_audit_logs,
    verify_audit_chain,
)
from app.database import SessionLocal
from app.documents import create_document
from app.models import AuditLog
from app.security import Role


def test_event_is_recorded(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)

    event = log_event(owner["id"], "document_uploaded", "doc1")

    assert event["actor_id"] == owner["id"]
    assert event["action"] == "document_uploaded"


def test_admin_can_view_audit_logs(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    log_event(owner["id"], "document_uploaded", "doc1")

    assert len(list_audit_logs(Role.ADMIN)) == 1


def test_viewer_cannot_view_audit_logs():
    with pytest.raises(HTTPException) as error:
        list_audit_logs(Role.VIEWER)

    assert error.value.status_code == 403


def test_owner_audit_log_includes_activity_on_owned_documents_only(
    create_account,
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other_owner = create_account(
        "Other owner", "other-owner@example.com", Role.OWNER
    )
    viewer = create_account("Viewer", "viewer@example.com")
    owned_document = create_document(
        owner["id"], Role.OWNER, "owned.pdf", "application/pdf", 10
    )
    unrelated_document = create_document(
        other_owner["id"], Role.OWNER, "private.pdf", "application/pdf", 10
    )

    log_event(
        viewer["id"],
        "document_viewed",
        owned_document["id"],
        {"filename": "owned.pdf"},
    )
    log_event(
        other_owner["id"],
        "document_viewed",
        unrelated_document["id"],
        {"filename": "private.pdf"},
    )
    log_event(owner["id"], "profile_name_updated", details={"field": "name"})

    events = list_owner_audit_logs(owner["id"])

    assert {event["action"] for event in events} == {
        "document_viewed",
        "profile_name_updated",
    }
    assert all(
        event["document_id"] != unrelated_document["id"]
        for event in events
    )
    assert all("previous_hash" in event and "event_hash" in event for event in events)


def test_audit_chain_remains_valid_after_account_deactivation(
    create_account,
):
    from app.admin import set_user_active

    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    log_event(owner["id"], "document_uploaded", "doc1")

    set_user_active(admin["id"], owner["id"], False)

    assert verify_audit_chain() is True
    assert [
        event["action"] for event in list_audit_logs(Role.ADMIN)
    ] == ["document_uploaded", "user_account_deactivated"]


def test_tampering_is_detected(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    log_event(owner["id"], "document_uploaded", "doc1")

    with SessionLocal.begin() as db:
        event = db.scalar(select(AuditLog))
        event.action = "document_deleted"

    assert verify_audit_chain() is False
