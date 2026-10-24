import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.audit import log_event
from app.database import SessionLocal
from app.models import User, UserIdentity, SharingPermission
from app.security import Role

ADMIN_ROLE_LOCK_KEY = 742891105
logger = logging.getLogger(__name__)


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at else None
        ),
    }


def list_users() -> list[dict]:
    with SessionLocal() as db:
        users = db.scalars(
            select(User).order_by(User.created_at.desc())
        ).all()
        return [_user_dict(user) for user in users]


def change_user_role(
    actor_id: str,
    target_user_id: str,
    new_role: Role,
) -> dict:
    with SessionLocal() as db:
        with db.begin():
            if db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": ADMIN_ROLE_LOCK_KEY},
                )

            actor = db.get(User, actor_id)
            target = db.scalar(
                select(User)
                .where(User.id == target_user_id)
                .with_for_update()
            )

            if (
                not actor
                or not actor.active
                or actor.role != Role.ADMIN.value
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Admin access required.",
                )

            if not target:
                raise HTTPException(
                    status_code=404,
                    detail="User account not found.",
                )

            if target.id == actor_id:
                raise HTTPException(
                    status_code=400,
                    detail="You cannot change your own role.",
                )

            old_role = target.role

            if (
                old_role == Role.ADMIN.value
                and new_role.value != Role.ADMIN.value
                and target.active
            ):
                count = db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(
                        User.role == Role.ADMIN.value,
                        User.active.is_(True),
                    )
                ) or 0

                if count <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="The last active Admin cannot be demoted.",
                    )

            target.role = new_role.value
            db.flush()
            result = _user_dict(target)
            if old_role != target.role:
                log_event(
                    actor_id=actor_id,
                    action="user_role_changed",
                    details={
                        "target_user_id": target.id,
                        "target_email": target.email,
                        "old_role": old_role,
                        "new_role": target.role,
                    },
                    db=db,
                )

        return {"user": result, "old_role": old_role}


def set_user_active(
    actor_id: str,
    target_user_id: str,
    active: bool,
) -> dict:
    with SessionLocal() as db:
        with db.begin():
            if db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": ADMIN_ROLE_LOCK_KEY},
                )

            actor = db.get(User, actor_id)
            target = db.scalar(
                select(User)
                .where(User.id == target_user_id)
                .with_for_update()
            )

            if (
                not actor
                or not actor.active
                or actor.role != Role.ADMIN.value
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Admin access required.",
                )

            if not target:
                raise HTTPException(
                    status_code=404,
                    detail="User account not found.",
                )

            if target.id == actor_id and not active:
                raise HTTPException(
                    status_code=400,
                    detail="You cannot deactivate your own Admin account.",
                )

            if (
                target.role == Role.ADMIN.value
                and target.active
                and not active
            ):
                count = db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(
                        User.role == Role.ADMIN.value,
                        User.active.is_(True),
                    )
                ) or 0

                if count <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="The last active Admin cannot be deactivated.",
                    )

            was_active = target.active
            target.active = active

            if was_active and not active:
                now = datetime.now(timezone.utc)
                shares = db.scalars(
                    select(SharingPermission)
                    .where(
                        (
                            (SharingPermission.owner_id == target_user_id)
                            | (SharingPermission.viewer_id == target_user_id)
                        ),
                        SharingPermission.revoked.is_(False),
                    )
                    .with_for_update()
                ).all()

                for share in shares:
                    share.revoked = True
                    share.revoked_at = now

            if was_active != active:
                log_event(
                    actor_id=actor_id,
                    action=(
                        "user_account_activated"
                        if active
                        else "user_account_deactivated"
                    ),
                    details={
                        "target_user_id": target.id,
                        "target_email": target.email,
                    },
                    db=db,
                )

            db.flush()
            result = _user_dict(target)

        return result

def delete_user_account(actor_id: str, target_user_id: str) -> dict:
    try:
        with SessionLocal() as db:
            with db.begin():
                if db.bind.dialect.name == "postgresql":
                    db.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"),
                        {"lock_key": ADMIN_ROLE_LOCK_KEY},
                    )

                actor = db.get(User, actor_id)
                if (
                    not actor
                    or not actor.active
                    or actor.role != Role.ADMIN.value
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="Admin access required.",
                    )

                target = db.scalar(
                    select(User)
                    .where(User.id == target_user_id)
                    .with_for_update()
                )
                if not target:
                    raise HTTPException(
                        status_code=404,
                        detail="User account not found.",
                    )
                if target.role == Role.ADMIN.value:
                    raise HTTPException(
                        status_code=400,
                        detail="Admin accounts cannot be deleted.",
                    )

                identity = db.get(UserIdentity, target.id)
                if not identity:
                    identity = UserIdentity(
                        id=target.id,
                        name=target.name,
                        email=target.email,
                        created_at=target.created_at,
                    )
                    db.add(identity)
                    db.flush()
                identity.deleted_at = datetime.now(timezone.utc)

                now = datetime.now(timezone.utc)
                shares = db.scalars(
                    select(SharingPermission)
                    .where(
                        (
                            (SharingPermission.owner_id == target_user_id)
                            | (SharingPermission.viewer_id == target_user_id)
                        ),
                        SharingPermission.revoked.is_(False),
                    )
                    .with_for_update()
                ).all()
                for share in shares:
                    share.revoked = True
                    share.revoked_at = now

                log_event(
                    actor_id=actor_id,
                    action="user_account_deleted",
                    details={
                        "target_user_id": target.id,
                        "target_name": target.name,
                        "target_email": target.email,
                        "target_role": target.role,
                        "deleted_at": now.isoformat(),
                    },
                    db=db,
                )
                db.delete(target)
                db.flush()
                result = {
                    "message": (
                        "User account was permanently removed. "
                        "Documents and audit history were preserved; "
                        "sharing access was revoked."
                    ),
                    "user_id": target_user_id,
                    "email": target.email,
                }

        return result
    except IntegrityError as error:
        logger.exception("Database relationship prevented account deletion.")
        raise HTTPException(
            status_code=409,
            detail=(
                "The account could not be deleted because a database "
                "relationship still depends on it. Apply the account "
                "identity retention migration and retry."
            ),
        ) from error