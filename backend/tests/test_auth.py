
import pytest
from fastapi import HTTPException

from app.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user_from_token,
)
from app.admin import set_user_active
from app.database import SessionLocal
from app.models import User, UserIdentity


def test_signup_hashes_password():
    user = create_user(
        "Meenakshi",
        "meenakshi@example.com",
        "StrongPass123",
    )

    assert user["password_hash"] != "StrongPass123"
    assert user["email"] == "meenakshi@example.com"
    with SessionLocal() as db:
        identity = db.get(UserIdentity, user["id"])
        assert identity is not None
        assert identity.email == user["email"]


def test_duplicate_email_is_rejected():
    create_user("Meenakshi", "meenakshi@example.com", "StrongPass123")

    with pytest.raises(HTTPException) as error:
        create_user("Another User", "meenakshi@example.com", "StrongPass456")

    assert error.value.status_code == 400


def test_login_with_correct_password():
    create_user("Meenakshi", "meenakshi@example.com", "StrongPass123")

    user = authenticate_user("meenakshi@example.com", "StrongPass123")

    assert user["active"] is True


def test_wrong_password_is_rejected():
    create_user("Meenakshi", "meenakshi@example.com", "StrongPass123")

    with pytest.raises(HTTPException) as error:
        authenticate_user("meenakshi@example.com", "WrongPass123")

    assert error.value.status_code == 401


def test_valid_token_returns_user():
    user = create_user("Meenakshi", "meenakshi@example.com", "StrongPass123")
    token = create_access_token(user)

    result = get_current_user_from_token(token)

    assert result["id"] == user["id"]


def test_deactivated_user_cannot_login(create_account):
    user = create_account("Viewer", "viewer@example.com")
    with SessionLocal.begin() as db:
        db.get(User, user["id"]).active = False

    with pytest.raises(HTTPException) as error:
        authenticate_user("viewer@example.com", "StrongPass123")

    assert error.value.status_code == 403


def test_existing_token_is_rejected_after_deactivation(create_account):
    admin = create_account("Admin", "admin@example.com", "admin")
    viewer = create_account("Viewer", "viewer@example.com")
    token = create_access_token(viewer)

    set_user_active(admin["id"], viewer["id"], False)

    with pytest.raises(HTTPException) as error:
        get_current_user_from_token(token)

    assert error.value.status_code == 401
