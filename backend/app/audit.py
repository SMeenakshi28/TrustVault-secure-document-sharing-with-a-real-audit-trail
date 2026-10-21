
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from fastapi import HTTPException

from app.security import Role


# Temporary storage. We will move this to the database later.
audit_logs = []

GENESIS_HASH = "0" * 64


def log_event(
    actor_id: str,
    action: str,
    document_id: str | None = None,
    details: dict | None = None,
):
    previous_hash = (
        audit_logs[-1]["event_hash"]
        if audit_logs
        else GENESIS_HASH
    )

    event = {
        "id": str(uuid4()),
        "actor_id": actor_id,
        "action": action,
        "document_id": document_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previous_hash": previous_hash,
    }

    # Hash the event together with the previous event's hash.
    event_data = json.dumps(
        event, sort_keys=True, separators=(",", ":")
    )
    event["event_hash"] = sha256(event_data.encode("utf-8")).hexdigest()

    audit_logs.append(event)
    return event


def list_audit_logs(requester_role: Role):
    if requester_role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view the audit logs.",
        )

    return audit_logs.copy()


def verify_audit_chain():
    previous_hash = GENESIS_HASH

    for event in audit_logs:
        if event["previous_hash"] != previous_hash:
            return False

        event_data = {
            key: value
            for key, value in event.items()
            if key != "event_hash"
        }

        serialized = json.dumps(
            event_data, sort_keys=True, separators=(",", ":")
        )
        expected_hash = sha256(
            serialized.encode("utf-8")
        ).hexdigest()

        if event["event_hash"] != expected_hash:
            return False

        previous_hash = event["event_hash"]

    return True
