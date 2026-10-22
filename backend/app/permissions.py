from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Document, SharingPermission, User
from app.security import Role


def _share_dict(share: SharingPermission) -> dict:
    return {
        "id": share.id,
        "document_id": share.document_id,
        "owner_id": share.owner_id,
        "viewer_id": share.viewer_id,
        "can_view": share.can_view,
        "can_download": share.can_download,
        "expires_at": (
            share.expires_at.isoformat()
            if share.expires_at else None
        ),
        "revoked": share.revoked,
        "revoked_at": (
            share.revoked_at.isoformat()
            if share.revoked_at else None
        ),
        "created_at": (
            share.created_at.isoformat()
            if share.created_at else None
        ),
    }


def share_document(
    document_id: str,
    owner_id: str,
    viewer_id: str,
    can_view: bool = True,
    can_download: bool = False,
    expires_in_days: int | None = None,
):
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        document = db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == owner_id,
            )
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found for this owner.",
            )

        viewer = db.get(User, viewer_id)

        if (
            not viewer
            or not viewer.active
            or viewer.role != Role.VIEWER.value
        ):
            raise HTTPException(
                status_code=400,
                detail="The recipient must be an active viewer account.",
            )

        existing_share = db.scalar(
            select(SharingPermission).where(
                SharingPermission.document_id == document_id,
                SharingPermission.viewer_id == viewer_id,
                SharingPermission.revoked.is_(False),
            )
        )

        if existing_share:
            raise HTTPException(
                status_code=409,
                detail="An active share already exists for this viewer.",
            )

        expires_at = (
            now + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        )

        share = SharingPermission(
            id=str(uuid4()),
            document_id=document_id,
            owner_id=owner_id,
            viewer_id=viewer_id,
            can_view=can_view,
            can_download=can_download,
            expires_at=expires_at,
            revoked=False,
            created_at=now,
        )

        db.add(share)
        db.commit()
        db.refresh(share)

        return _share_dict(share)


def list_shared_documents(viewer_id: str):
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        rows = db.execute(
            select(SharingPermission, Document)
            .join(
                Document,
                SharingPermission.document_id == Document.id,
            )
            .where(
                SharingPermission.viewer_id == viewer_id,
                SharingPermission.revoked.is_(False),
                SharingPermission.can_view.is_(True),
            )
            .order_by(SharingPermission.created_at.desc())
        ).all()

        results = []

        for share, document in rows:
            # Ignore shares that have expired.
            if share.expires_at and share.expires_at <= now:
                continue

            results.append({
                **_share_dict(share),
                "filename": document.filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
            })

        return results


def revoke_share(share_id: str, owner_id: str):
    with SessionLocal() as db:
        share = db.scalar(
            select(SharingPermission).where(
                SharingPermission.id == share_id,
                SharingPermission.owner_id == owner_id,
            )
        )

        if not share:
            raise HTTPException(
                status_code=404,
                detail="Share not found for this owner.",
            )

        if not share.revoked:
            share.revoked = True
            share.revoked_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(share)

        return {
            "message": "Document sharing revoked successfully.",
            "share": _share_dict(share),
        }
        

def get_viewer_document_access(
    document_id: str,
    viewer_id: str,
    require_download: bool = False,
) -> dict:
    """Return document details only when the viewer has valid permission."""

    with SessionLocal() as db:
        share = db.scalar(
            select(SharingPermission).where(
                SharingPermission.document_id == document_id,
                SharingPermission.viewer_id == viewer_id,
                SharingPermission.revoked.is_(False),
            )
        )

        if not share or not share.can_view:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this document.",
            )

        if share.expires_at:
            expiry = share.expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=403,
                    detail="This document share has expired.",
                )

        if require_download and not share.can_download:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to download this document.",
            )

        document = db.scalar(
            select(Document).where(Document.id == document_id)
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        return {
            "id": document.id,
            "owner_id": document.owner_id,
            "filename": document.filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
            "storage_path": document.storage_path,
        }
