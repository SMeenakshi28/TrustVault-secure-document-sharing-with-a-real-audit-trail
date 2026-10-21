
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr

from app.security import Role

# DEVELOPMENT ONLY: replace with an environment variable before deployment.
SECRET_KEY = "development-only-change-this-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

# Temporary in-memory user storage.
# All accounts will disappear when the server restarts.
users = {}


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_user(name: str, email: str, password: str):
    email = email.lower()

    if email in users:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    user = {
        "id": str(uuid4()),
        "name": name,
        "email": email,
        "password_hash": password_hash.hash(password),
        "role": Role.VIEWER,
        "active": True,
    }

    users[email] = user
    return user

def create_development_owner(name: str, email: str, password: str):
    user = create_user(name, email, password)
    user["role"] = Role.OWNER
    return user


def authenticate_user(email: str, password: str):
    user = users.get(email.lower())

    if not user or not password_hash.verify(
        password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )

    return user


def create_access_token(user: dict):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user["id"],
        "role": user["role"].value,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_from_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")

        user = next(
            (u for u in users.values() if u["id"] == user_id),
            None,
        )

        if not user or not user["active"]:
            raise HTTPException(
                status_code=401,
                detail="User not found or account disabled.",
            )

        return user

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
        )
