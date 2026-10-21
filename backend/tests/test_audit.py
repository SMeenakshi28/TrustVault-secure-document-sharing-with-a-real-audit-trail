
import pytest
from fastapi import HTTPException

from app.audit import (
    audit_logs,
    log_event,
    list_audit_logs,
    verify_audit_chain,
)
from app.security import Role


@pytest.fixture(autouse=True)
def clear_audit_logs():
    audit_logs.clear()
    yield
    audit_logs.clear()


def test_event_is_recorded():
    event = log_event("owner1", "document_uploaded", "doc1")
    assert event["actor_id"] == "owner1"
    assert event["action"] == "document_uploaded"


def test_admin_can_view_audit_logs():
    log_event("owner1", "document_uploaded", "doc1")
    assert len(list_audit_logs(Role.ADMIN)) == 1


def test_viewer_cannot_view_audit_logs():
    with pytest.raises(HTTPException) as error:
        list_audit_logs(Role.VIEWER)
    assert error.value.status_code == 403


def test_audit_chain_is_valid():
    log_event("owner1", "document_uploaded", "doc1")
    log_event("owner1", "document_shared", "doc1")
    assert verify_audit_chain() is True


def test_tampering_is_detected():
    log_event("owner1", "document_uploaded", "doc1")
    audit_logs[0]["action"] = "document_deleted"
    assert verify_audit_chain() is False
