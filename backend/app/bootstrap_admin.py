import os

from dotenv import load_dotenv
from sqlalchemy import select

from app.auth import password_hash
from app.database import SessionLocal
from app.models import User, UserIdentity
from app.security import Role

load_dotenv()


def main():
    name = os.getenv(
        "TRUSTVAULT_BOOTSTRAP_ADMIN_NAME",
        "TrustVault Admin",
    ).strip()

    email = os.getenv(
        "TRUSTVAULT_BOOTSTRAP_ADMIN_EMAIL",
        "",
    ).strip().lower()

    password = os.getenv(
        "TRUSTVAULT_BOOTSTRAP_ADMIN_PASSWORD",
        "",
    )

    if not email or not password:
        raise SystemExit(
            "Set TRUSTVAULT_BOOTSTRAP_ADMIN_EMAIL and "
            "TRUSTVAULT_BOOTSTRAP_ADMIN_PASSWORD in backend/.env."
        )

    if len(password) < 12:
        raise SystemExit(
            "Use an initial Admin password of at least 12 characters."
        )

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user:
            user.name = name or user.name
            user.password_hash = password_hash.hash(password)
            user.role = Role.ADMIN.value
            user.active = True
            action = "promoted existing account to Admin"
        else:
            user = User(
                name=name or "TrustVault Admin",
                email=email,
                password_hash=password_hash.hash(password),
                role=Role.ADMIN.value,
                active=True,
            )
            db.add(user)
            db.flush()
            action = "created Admin account"

        identity = db.get(UserIdentity, user.id)
        if not identity:
            db.add(UserIdentity(
                id=user.id,
                name=user.name,
                email=user.email,
                created_at=user.created_at,
            ))
        else:
            identity.name = user.name
            identity.email = user.email

        db.commit()

    print(f"Successfully {action}: {email}")
    print("Sign in using the normal TrustVault login page.")


if __name__ == "__main__":
    main()