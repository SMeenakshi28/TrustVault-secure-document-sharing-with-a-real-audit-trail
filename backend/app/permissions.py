
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.documents import documents
from app.security import Role
from app.auth import users

# Temporary in-memory storage; database comes later.
shares = {}


def share_document(
    document_id: str,
    owner_id: str,
    viewer_id: str,
    can_view: bool = True,
    can_download: bool = False,
    expires_in_days: int | None = None,
):
    document = documents.get(document_id)

    if not document or document["owner_id"] != owner_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if not viewer_id or viewer_id == owner_id:
        raise HTTPException(
            status_code=400,
            detail="Choose a valid viewer."
        )
    
    viewer = next(
    (u for u in users.values() if u["id"] == viewer_id),
    None,
    )
    
    if not viewer or viewer["role"] != Role.VIEWER or not viewer["active"]:
        raise HTTPException(
            status_code=400,
            detail="Recipient must be an active viewer account.",
        )

    if not can_view and not can_download:
        raise HTTPException(
            status_code=400,
            detail="Grant at least one permission."
        )

    if expires_in_days is not None and expires_in_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="Expiry must be at least one day."
        )

    # Reuse an existing share for the same document and viewer.
    existing = next(
        (
            share for share in shares.values()
            if share["document_id"] == document_id
            and share["viewer_id"] == viewer_id
        ),
        None,
    )

    now = datetime.now(timezone.utc)

    share = {
        "id": existing["id"] if existing else str(uuid4()),
        "document_id": document_id,
        "owner_id": owner_id,
        "viewer_id": viewer_id,
        "can_view": can_view,
        "can_download": can_download,
        "expires_at": (
            (now + timedelta(days=expires_in_days)).isoformat()
            if expires_in_days is not None
            else None
        ),
        "revoked": False,
        "created_at": now.isoformat(),
    }

    shares[share["id"]] = share
    return share


def list_shared_documents(viewer_id: str):
    now = datetime.now(timezone.utc)
    result = []

    for share in shares.values():
        if share["viewer_id"] != viewer_id or share["revoked"]:
            continue

        if share["expires_at"]:
            expiry = datetime.fromisoformat(share["expires_at"])
            if expiry <= now:
                continue

        document = documents.get(share["document_id"])
        if document:
            result.append({
                **document,
                "can_view": share["can_view"],
                "can_download": share["can_download"],
                "share_id": share["id"],
                "expires_at": share["expires_at"],
            })

    return result


def revoke_share(share_id: str, owner_id: str):
    share = shares.get(share_id)

    if not share or share["owner_id"] != owner_id:
        raise HTTPException(
            status_code=404,
            detail="Share not found."
        )

    if share["revoked"]:
        raise HTTPException(
            status_code=400,
            detail="This share has already been revoked."
        )

    share["revoked"] = True
    share["revoked_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "message": "Document access revoked successfully.",
        "share_id": share_id,
    }
