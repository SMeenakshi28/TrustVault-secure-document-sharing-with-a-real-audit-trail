
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.database import SessionLocal
from app.models import AuditLog
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
):
    db = SessionLocal()

    try:
        with db.begin():
            # Serialize audit writes so concurrent requests do not
            # append events using the same previous hash.
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": AUDIT_LOCK_KEY},
            )

            last_event = (
                db.query(AuditLog)
                .order_by(
                    AuditLog.timestamp.desc(),
                    AuditLog.id.desc(),
                )
                .first()
            )

            timestamp = datetime.now(timezone.utc)

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

            db.add(AuditLog(
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

    finally:
        db.close()


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
