from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from app.audit import log_event
from app.database import SessionLocal
from app.models import OwnerAccessRequest, User, UserIdentity
from app.security import Role


def _request_dict(request, identity=None, user=None):
    return {
        "id": request.id,
        "user_id": request.user_id,
        "user_name": identity.name if identity else None,
        "user_email": identity.email if identity else None,
        "user_active": bool(user and user.active),
        "status": request.status,
        "created_at": request.created_at.isoformat(),
        "reviewed_by": request.reviewed_by,
        "reviewed_at": (
            request.reviewed_at.isoformat() if request.reviewed_at else None
        ),
    }


def create_owner_access_request(user_id: str) -> dict:
    with SessionLocal() as db:
        with db.begin():
            user = db.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if not user or not user.active:
                raise HTTPException(status_code=401, detail="Account is unavailable.")
            if user.role != Role.VIEWER.value:
                raise HTTPException(
                    status_code=409,
                    detail="Only Viewer accounts can request Owner access.",
                )

            existing = db.scalar(
                select(OwnerAccessRequest)
                .where(
                    OwnerAccessRequest.user_id == user_id,
                    OwnerAccessRequest.status == "pending",
                )
                .with_for_update()
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="An Owner access request is already pending.",
                )

            request = OwnerAccessRequest(
                id=str(uuid4()),
                user_id=user_id,
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
            db.add(request)
            db.flush()
            log_event(
                actor_id=user_id,
                action="owner_access_requested",
                details={"request_id": request.id},
                db=db,
            )
            result = _request_dict(request, db.get(UserIdentity, user_id), user)

        return result


def get_latest_owner_access_request(user_id: str) -> dict | None:
    with SessionLocal() as db:
        row = db.execute(
            select(OwnerAccessRequest, UserIdentity, User)
            .join(UserIdentity, UserIdentity.id == OwnerAccessRequest.user_id)
            .outerjoin(User, User.id == OwnerAccessRequest.user_id)
            .where(OwnerAccessRequest.user_id == user_id)
            .order_by(
                OwnerAccessRequest.created_at.desc(),
                OwnerAccessRequest.id.desc(),
            )
            .limit(1)
        ).first()
        if not row:
            return None
        return _request_dict(*row)


def list_pending_owner_access_requests() -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            select(OwnerAccessRequest, UserIdentity, User)
            .join(UserIdentity, UserIdentity.id == OwnerAccessRequest.user_id)
            .outerjoin(User, User.id == OwnerAccessRequest.user_id)
            .where(OwnerAccessRequest.status == "pending")
            .order_by(OwnerAccessRequest.created_at.asc())
        ).all()
        return [_request_dict(*row) for row in rows]


def review_owner_access_request(
    admin_id: str,
    request_id: str,
    decision: str,
) -> dict:
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Invalid review decision.")

    with SessionLocal() as db:
        with db.begin():
            if db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": 742891105},
                )

            admin = db.get(User, admin_id)
            if not admin or not admin.active or admin.role != Role.ADMIN.value:
                raise HTTPException(status_code=403, detail="Admin access required.")

            request_snapshot = db.scalar(
                select(OwnerAccessRequest).where(
                    OwnerAccessRequest.id == request_id
                )
            )
            if not request_snapshot:
                raise HTTPException(
                    status_code=404,
                    detail="Owner access request not found.",
                )

            requester = db.scalar(
                select(User)
                .where(User.id == request_snapshot.user_id)
                .with_for_update()
            )
            request = db.scalar(
                select(OwnerAccessRequest)
                .where(OwnerAccessRequest.id == request_id)
                .with_for_update()
            )
            if not request:
                raise HTTPException(
                    status_code=404,
                    detail="Owner access request not found.",
                )
            if request.status != "pending":
                raise HTTPException(
                    status_code=409,
                    detail="This Owner access request has already been reviewed.",
                )

            if decision == "approve" and (
                not requester
                or not requester.active
                or requester.role != Role.VIEWER.value
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Only an active Viewer can be approved for Owner access.",
                )

            now = datetime.now(timezone.utc)
            request.status = "approved" if decision == "approve" else "rejected"
            request.reviewed_by = admin_id
            request.reviewed_at = now

            if decision == "approve":
                requester.role = Role.OWNER.value
                log_event(
                    actor_id=admin_id,
                    action="user_role_changed",
                    details={
                        "target_user_id": requester.id,
                        "target_email": requester.email,
                        "old_role": Role.VIEWER.value,
                        "new_role": Role.OWNER.value,
                        "request_id": request.id,
                        "request_status": "approved",
                    },
                    db=db,
                )
            else:
                log_event(
                    actor_id=admin_id,
                    action="owner_access_request_rejected",
                    details={
                        "request_id": request.id,
                        "target_user_id": request.user_id,
                    },
                    db=db,
                )
            db.flush()

            identity = db.get(UserIdentity, request.user_id)
            result = _request_dict(request, identity, requester)

        return result
