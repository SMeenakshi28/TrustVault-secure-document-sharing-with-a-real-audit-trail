
import pytest
from fastapi import HTTPException

from app.auth import (
    users,
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user_from_token,
)


@pytest.fixture(autouse=True)
def reset_users():
    users.clear()
    yield
    users.clear()


def test_signup_hashes_password():
    user = create_user(
        "Meenakshi",
        "meenakshi@example.com",
        "StrongPass123",
    )

    assert user["password_hash"] != "StrongPass123"
    assert user["email"] == "meenakshi@example.com"


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
