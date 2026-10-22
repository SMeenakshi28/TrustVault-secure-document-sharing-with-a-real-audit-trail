
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import User
from app.security import Role

load_dotenv()

SECRET_KEY = os.getenv("TRUSTVAULT_JWT_SECRET")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "TRUSTVAULT_JWT_SECRET is missing or too short. "
        "Set a long random secret in backend/.env."
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30
password_hash = PasswordHash.recommended()

# Temporary compatibility cache for modules not yet migrated to PostgreSQL.
# PostgreSQL is the source of truth for authentication.
users = {}


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "password_hash": user.password_hash,
        "role": Role(user.role),
        "active": user.active,
    }


def create_user(name: str, email: str, password: str):
    email = email.strip().lower()

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists.",
            )

        user = User(
            name=name.strip(),
            email=email,
            password_hash=password_hash.hash(password),
            role=Role.VIEWER.value,
            active=True,
        )
        db.add(user)

        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists.",
            )

        result = _user_to_dict(user)
        users[email] = result
        return result


def create_development_owner(name: str, email: str, password: str):
    email = email.strip().lower()

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))

        if existing:
            existing.role = Role.OWNER.value
            db.commit()
            db.refresh(existing)
            result = _user_to_dict(existing)
            users[email] = result
            return result

    user = create_user(name, email, password)

    with SessionLocal() as db:
        owner = db.get(User, user["id"])
        owner.role = Role.OWNER.value
        db.commit()
        db.refresh(owner)
        result = _user_to_dict(owner)
        users[email] = result
        return result


def authenticate_user(email: str, password: str):
    email = email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if not user or not password_hash.verify(
            password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )

        result = _user_to_dict(user)
        users[email] = result
        return result


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

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid access token.",
            )

        with SessionLocal() as db:
            user = db.get(User, user_id)

            if not user or not user.active:
                raise HTTPException(
                    status_code=401,
                    detail="User not found or account disabled.",
                )

            result = _user_to_dict(user)
            users[result["email"]] = result
            return result

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
        )
