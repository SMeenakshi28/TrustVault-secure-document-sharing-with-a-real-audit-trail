
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AuditLog, Document
from app.security import Role


GENESIS_HASH = "0" * 64
AUDIT_LOCK_KEY = 742891104


def _timestamp_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def _hash_event(event: dict) -> str:
    event_data = json.dumps(
        event, sort_keys=True, separators=(",", ":")
    )
    return sha256(event_data.encode("utf-8")).hexdigest()


def _row_to_event(row: AuditLog) -> dict:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "action": row.action,
        "document_id": row.document_id,
        "details": row.details or {},
        "timestamp": _timestamp_iso(row.timestamp),
        "previous_hash": row.previous_hash,
        "event_hash": row.event_hash,
    }


def log_event(
    actor_id: str,
    action: str,
    document_id: str | None = None,
    details: dict | None = None,
    db: Session | None = None,
):
    def append_event(session: Session) -> dict:
        if session.bind.dialect.name == "postgresql":
            # Serialize audit writes so concurrent requests do not
            # append events using the same previous hash.
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": AUDIT_LOCK_KEY},
            )

        last_event = (
            session.query(AuditLog)
            .order_by(
                AuditLog.timestamp.desc(),
                AuditLog.id.desc(),
            )
            .first()
        )

        timestamp = datetime.now(timezone.utc)
        if last_event:
            last_timestamp = last_event.timestamp
            if last_timestamp.tzinfo is None:
                last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
            if timestamp <= last_timestamp:
                timestamp = last_timestamp + timedelta(microseconds=1)

        event = {
            "id": str(uuid4()),
            "actor_id": actor_id,
            "action": action,
            "document_id": document_id,
            "details": details or {},
            "timestamp": timestamp.isoformat(),
            "previous_hash": (
                last_event.event_hash
                if last_event
                else GENESIS_HASH
            ),
        }

        event_hash = _hash_event(event)

        session.add(AuditLog(
            id=event["id"],
            actor_id=event["actor_id"],
            action=event["action"],
            document_id=event["document_id"],
            details=event["details"],
            timestamp=timestamp,
            previous_hash=event["previous_hash"],
            event_hash=event_hash,
        ))
        event["event_hash"] = event_hash
        return event

    if db is not None:
        return append_event(db)

    session = SessionLocal()
    try:
        with session.begin():
            event = append_event(session)
        return event
    finally:
        session.close()


def list_audit_logs(requester_role: Role):
    if requester_role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view the audit logs.",
        )

    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .all()
        )
        return [_row_to_event(row) for row in rows]
    finally:
        db.close()

def list_owner_audit_logs(owner_id: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                or_(
                    AuditLog.actor_id == owner_id,
                    AuditLog.document_id.in_(
                        select(Document.id).where(
                            Document.owner_id == owner_id
                        )
                    ),
                )
            )
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .all()
        )
        return [_row_to_event(row) for row in rows]
    finally:
        db.close()


def verify_audit_chain():
    db = SessionLocal()

    try:
        rows = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .all()
        )

        previous_hash = GENESIS_HASH

        for row in rows:
            event = _row_to_event(row)

            if event["previous_hash"] != previous_hash:
                return False

            event_without_hash = {
                key: value
                for key, value in event.items()
                if key != "event_hash"
            }

            if _hash_event(event_without_hash) != event["event_hash"]:
                return False

            previous_hash = event["event_hash"]

        return True

    finally:
        db.close()
