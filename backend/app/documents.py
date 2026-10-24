from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Document, SharingPermission
from app.security import Role


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = "application/octet-stream"
    size_bytes: int = Field(ge=0)


def _document_dict(document: Document) -> dict:
    return {
        "id": document.id,
        "owner_id": document.owner_id,
        "filename": document.filename,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "storage_path": document.storage_path,
        "created_at": (
            document.created_at.isoformat()
            if document.created_at else None
        ),
    }


def create_document(
    owner_id: str,
    user_role,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str | None = None,
):
    role = (
        user_role.value
        if isinstance(user_role, Role)
        else user_role
    )

    if role != Role.OWNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only document owners can create documents.",
        )

    document_id = str(uuid4())

    with SessionLocal() as db:
        document = Document(
            id=document_id,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path or f"{owner_id}/{document_id}",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return _document_dict(document)


def list_owner_documents(owner_id: str):
    with SessionLocal() as db:
        documents = db.scalars(
            select(Document)
            .where(
                Document.owner_id == owner_id,
                Document.is_deleted.is_(False),
            )
            .order_by(Document.created_at.desc())
        ).all()

        return [_document_dict(doc) for doc in documents]


def count_active_documents() -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.is_deleted.is_(False))
        ) or 0


def get_document(document_id: str, owner_id: str):
    with SessionLocal() as db:
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
                detail="Document not found.",
            )

        return _document_dict(document)


def delete_document(document_id: str, owner_id: str):
    """Remove a document from active use while preserving audit history."""
    from app.storage import delete_object

    with SessionLocal() as db:
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
                detail="Document not found.",
            )

        # Delete the actual file from private storage first.
        if document.storage_path:
            delete_object(document.storage_path)

        now = datetime.now(timezone.utc)
        document.is_deleted = True

        # Revoke active shares; keep the rows for history.
        shares = db.scalars(
            select(SharingPermission).where(
                SharingPermission.document_id == document_id,
                SharingPermission.revoked.is_(False),
            )
        ).all()

        for share in shares:
            share.revoked = True
            share.revoked_at = now

        db.commit()

        return {
            "message": (
                "Document deleted from active use; audit history preserved."
            ),
            "document_id": document_id,
        }