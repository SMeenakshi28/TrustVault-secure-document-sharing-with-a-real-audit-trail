from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.admin import change_user_role, delete_user_account, set_user_active
from app.database import SessionLocal
from app.documents import create_document
from app.models import (
    AuditLog,
    Document,
    SharingPermission,
    User,
    UserIdentity,
)
from app.permissions import share_document
from app.security import Role


def test_admin_cannot_deactivate_self(create_account):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    with pytest.raises(HTTPException) as error:
        set_user_active(admin["id"], admin["id"], False)

    assert error.value.status_code == 400


def test_last_active_admin_cannot_be_deactivated_or_demoted(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    second = create_account("Second", "second@example.com", Role.ADMIN)

    set_user_active(admin["id"], second["id"], False)
    with pytest.raises(HTTPException) as error:
        set_user_active(admin["id"], admin["id"], False)
    assert error.value.status_code == 400

    with pytest.raises(HTTPException) as error:
        change_user_role(admin["id"], admin["id"], Role.VIEWER)
    assert error.value.status_code == 400


def test_deactivation_revokes_shares_but_preserves_records(create_account):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    viewer = create_account("Viewer", "viewer@example.com")
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )
    share = share_document(
        document["id"],
        owner["id"],
        viewer["name"],
        viewer["email"],
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    set_user_active(admin["id"], viewer["id"], False)

    with SessionLocal() as db:
        stored_user = db.get(User, viewer["id"])
        stored_document = db.get(Document, document["id"])
        stored_share = db.get(SharingPermission, share["id"])

        assert stored_user.active is False
        assert stored_document is not None
        assert stored_document.is_deleted is False
        assert stored_share.revoked is True
        assert stored_share.revoked_at is not None


def test_inactive_admin_cannot_manage_accounts(create_account):
    inactive = create_account(
        "Inactive Admin", "inactive@example.com", Role.ADMIN, active=False
    )
    viewer = create_account("Viewer", "viewer@example.com")

    with pytest.raises(HTTPException) as error:
        set_user_active(inactive["id"], viewer["id"], False)

    assert error.value.status_code == 403


def test_delete_account_removes_login_and_preserves_history(
    create_account,
):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 100
    )

    result = delete_user_account(admin["id"], owner["id"])

    assert result["user_id"] == owner["id"]
    with SessionLocal() as db:
        assert db.get(User, owner["id"]) is None
        identity = db.get(UserIdentity, owner["id"])
        assert identity is not None
        assert identity.email == owner["email"]
        assert identity.deleted_at is not None
        assert db.scalar(
            select(Document).where(Document.owner_id == owner["id"])
        ) is not None
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "user_account_deleted"
            )
        ) is not None


def test_admin_account_cannot_be_permanently_deleted(create_account):
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)
    another_admin = create_account(
        "Another Admin", "another-admin@example.com", Role.ADMIN
    )

    with pytest.raises(HTTPException) as error:
        delete_user_account(admin["id"], another_admin["id"])

    assert error.value.status_code == 400
    with SessionLocal() as db:
        assert db.get(User, another_admin["id"]) is not None
