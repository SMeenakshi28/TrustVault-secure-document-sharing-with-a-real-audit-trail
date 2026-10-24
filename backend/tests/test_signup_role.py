from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models import User
from app.security import Role

client = TestClient(app)


def auth_headers(user):
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def stored_role(email):
    with SessionLocal() as db:
        return db.query(User).filter(User.email == email).one().role


def test_signup_creates_viewer():
    response = client.post(
        "/auth/signup",
        json={
            "name": "New User",
            "email": "new.user@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "viewer"
    assert stored_role("new.user@example.com") == "viewer"


def test_signup_ignores_client_supplied_role():
    for index, requested_role in enumerate(["admin", "owner", "ADMIN"]):
        email = f"sneaky{index}@example.com"
        response = client.post(
            "/auth/signup",
            json={
                "name": "Sneaky User",
                "email": email,
                "password": "StrongPass123",
                "role": requested_role,
            },
        )

        assert response.status_code == 201
        assert response.json()["role"] == "viewer"
        assert stored_role(email) == "viewer"


def test_login_after_signup_reports_viewer():
    client.post(
        "/auth/signup",
        json={
            "name": "Login User",
            "email": "login.user@example.com",
            "password": "StrongPass123",
            "role": "admin",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login.user@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "viewer"


def test_existing_roles_are_unchanged_by_new_signups(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    admin = create_account("Admin", "admin@example.com", Role.ADMIN)

    client.post(
        "/auth/signup",
        json={
            "name": "Another User",
            "email": "another@example.com",
            "password": "StrongPass123",
        },
    )

    assert stored_role("owner@example.com") == "owner"
    assert stored_role("admin@example.com") == "admin"
    assert owner["role"] == Role.OWNER
    assert admin["role"] == Role.ADMIN


def test_user_cannot_change_own_role_through_api(create_account):
    viewer = create_account("Viewer", "viewer@example.com")

    response = client.patch(
        f"/admin/users/{viewer['id']}/role",
        json={"role": "owner"},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403
    assert stored_role("viewer@example.com") == "viewer"


def test_profile_update_cannot_change_role(create_account):
    viewer = create_account("Viewer", "viewer@example.com")

    response = client.patch(
        "/auth/profile",
        json={"name": "Viewer Renamed", "role": "admin"},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 200
    assert stored_role("viewer@example.com") == "viewer"