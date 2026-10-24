from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select, update

from app.audit import log_event
from app.database import SessionLocal
from app.models import Document, SharingPermission, User, UserIdentity
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
    recipient_name: str,
    recipient_email: str,
    expires_at: datetime,
    can_download: bool = False,
):
    now = datetime.now(timezone.utc)
    recipient_name = recipient_name.strip()
    recipient_email = recipient_email.strip().lower()

    if not recipient_name or len(recipient_name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid recipient name.",
        )

    if expires_at.tzinfo is None or expires_at <= now:
        raise HTTPException(
            status_code=400,
            detail="The access expiration must be a future date and time.",
        )

    with SessionLocal() as db:
        with db.begin():
            document = db.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.owner_id == owner_id,
                    Document.is_deleted.is_(False),
                )
            )

            if not document:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found for this owner.",
                )

            recipient = db.scalar(
                select(User).where(User.email == recipient_email)
            )

            if (
                not recipient
                or not recipient.active
                or recipient.role not in {
                    Role.VIEWER.value,
                    Role.OWNER.value,
                }
            ):
                raise HTTPException(
                    status_code=400,
                    detail="The recipient must be an active Viewer or Owner account.",
                )

            if recipient.id == owner_id:
                raise HTTPException(
                    status_code=400,
                    detail="You cannot share a document with yourself.",
                )

            existing_share = db.scalar(
                select(SharingPermission).where(
                    SharingPermission.document_id == document_id,
                    SharingPermission.viewer_id == recipient.id,
                    SharingPermission.revoked.is_(False),
                )
            )

            if existing_share:
                raise HTTPException(
                    status_code=409,
                    detail="An active share already exists for this viewer.",
                )

            share = SharingPermission(
                id=str(uuid4()),
                document_id=document_id,
                owner_id=owner_id,
                viewer_id=recipient.id,
                can_view=True,
                can_download=can_download,
                expires_at=expires_at.astimezone(timezone.utc),
                revoked=False,
                created_at=now,
            )

            db.add(share)
            db.flush()
            log_event(
                actor_id=owner_id,
                action="document_shared",
                document_id=document_id,
                details={
                    "share_id": share.id,
                    "viewer_id": recipient.id,
                    "recipient_name": recipient_name,
                    "recipient_email": recipient_email,
                    "can_view": True,
                    "can_download": can_download,
                    "expires_at": expires_at.isoformat(),
                },
                db=db,
            )
            result = _share_dict(share)
            result["viewer_name"] = recipient.name
            result["viewer_email"] = recipient.email

        return result


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
                Document.is_deleted.is_(False),
            )
            .order_by(SharingPermission.created_at.desc())
        ).all()

        results = []

        for share, document in rows:
            # Ignore shares that have expired.
            if share.expires_at:
                expiry = share.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= now:
                    continue

            results.append({
                **_share_dict(share),
                "filename": document.filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "viewed_at": (
                    share.viewed_at.isoformat()
                    if share.viewed_at else None
                ),
                "viewed": share.viewed_at is not None,
            })

        return results


def list_owner_shares(owner_id: str):
    with SessionLocal() as db:
        rows = db.execute(
            select(SharingPermission, Document, UserIdentity)
            .join(
                Document,
                SharingPermission.document_id == Document.id,
            )
            .join(
                UserIdentity,
                SharingPermission.viewer_id == UserIdentity.id,
            )
            .where(
                SharingPermission.owner_id == owner_id,
                Document.owner_id == owner_id,
            )
            .order_by(SharingPermission.created_at.desc())
        ).all()

        return [
            {
                **_share_dict(share),
                "filename": document.filename,
                "recipient_name": recipient.name,
                "recipient_email": recipient.email,
                "viewed_at": (
                    share.viewed_at.isoformat()
                    if share.viewed_at else None
                ),
            }
            for share, document, recipient in rows
        ]


def revoke_share(share_id: str, owner_id: str):
    with SessionLocal() as db:
        with db.begin():
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
                log_event(
                    actor_id=owner_id,
                    action="document_share_revoked",
                    document_id=share.document_id,
                    details={"share_id": share_id},
                    db=db,
                )
            result = _share_dict(share)

        return {
            "message": "Document sharing revoked successfully.",
            "share": result,
        }
        

def get_viewer_document_access(
    document_id: str,
    viewer_id: str,
    require_download: bool = False,
) -> dict:
    """Return document details only when the viewer has valid permission."""

    with SessionLocal() as db:
        recipient = db.scalar(
            select(User).where(
                User.id == viewer_id,
                User.active.is_(True),
                User.role.in_([Role.VIEWER.value, Role.OWNER.value]),
            )
        )
        if not recipient:
            raise HTTPException(
                status_code=403,
                detail="An active Viewer or Owner account is required.",
            )

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

        if share.viewed_at:
            raise HTTPException(
                status_code=403,
                detail="This share has already been viewed.",
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
            select(Document).where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
                Document.owner_id == share.owner_id,
            )
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


def record_viewer_document_access(
    document_id: str,
    viewer_id: str,
    require_download: bool = False,
) -> None:
    """Atomically consume the share after the stored object was retrieved."""
    with SessionLocal() as db:
        with db.begin():
            recipient = db.scalar(
                select(User)
                .where(
                    User.id == viewer_id,
                    User.active.is_(True),
                    User.role.in_([Role.VIEWER.value, Role.OWNER.value]),
                )
                .with_for_update()
            )
            if not recipient:
                raise HTTPException(
                    status_code=403,
                    detail="An active Viewer or Owner account is required.",
                )

            share = db.scalar(
                select(SharingPermission)
                .where(
                    SharingPermission.document_id == document_id,
                    SharingPermission.viewer_id == viewer_id,
                )
                .with_for_update()
            )

            if not share or share.revoked or not share.can_view:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to view this document.",
                )

            if share.viewed_at:
                raise HTTPException(
                    status_code=403,
                    detail="This share has already been viewed.",
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
                select(Document).where(
                    Document.id == document_id,
                    Document.owner_id == share.owner_id,
                    Document.is_deleted.is_(False),
                )
            )
            if not document:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found.",
                )

            accessed_at = datetime.now(timezone.utc)
            share.viewed_at = accessed_at
            consumed = db.execute(
                update(SharingPermission)
                .where(
                    SharingPermission.id == share.id,
                    SharingPermission.viewer_id == viewer_id,
                    SharingPermission.document_id == document_id,
                    SharingPermission.revoked.is_(False),
                    SharingPermission.can_view.is_(True),
                    SharingPermission.viewed_at.is_(None),
                    or_(
                        SharingPermission.expires_at.is_(None),
                        SharingPermission.expires_at > accessed_at,
                    ),
                    *(
                        [SharingPermission.can_download.is_(True)]
                        if require_download else []
                    ),
                )
                .values(viewed_at=accessed_at)
            )
            if consumed.rowcount != 1:
                raise HTTPException(
                    status_code=403,
                    detail="This share is no longer available.",
                )

            log_event(
                actor_id=viewer_id,
                action=(
                    "document_downloaded"
                    if require_download
                    else "document_viewed"
                ),
                document_id=document_id,
                details={
                    "filename": document.filename,
                    "share_id": share.id,
                },
                db=db,
            )
