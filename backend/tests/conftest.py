import os

os.environ["DATABASE_URL"] = (
    "sqlite+pysqlite:///file:trustvault_test?"
    "mode=memory&cache=shared&uri=true"
)
os.environ["TRUSTVAULT_JWT_SECRET"] = (
    "test-only-jwt-secret-that-is-not-for-use-outside-tests"
)
os.environ["TRUSTVAULT_CREATE_TEST_OWNER"] = "false"

import pytest
from sqlalchemy import event

from app.auth import password_hash
from app.database import Base, SessionLocal, engine
from app.models import User, UserIdentity
from app.security import Role


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def create_account():
    def create(name, email, role=Role.VIEWER, active=True):
        role_value = role.value if isinstance(role, Role) else role
        with SessionLocal.begin() as db:
            user = User(
                name=name,
                email=email.lower(),
                password_hash=password_hash.hash("StrongPass123"),
                role=role_value,
                active=active,
            )
            db.add(user)
            db.flush()
            db.add(UserIdentity(
                id=user.id,
                name=user.name,
                email=user.email,
                created_at=user.created_at,
            ))
            db.flush()
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": Role(user.role),
                "active": user.active,
            }

    return create
