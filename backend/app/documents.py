
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.security import Role


# Temporary in-memory document metadata.
documents = {}


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)


def create_document(
    owner_id: str,
    user_role: Role,
    filename: str,
    content_type: str,
    size_bytes: int,
):
    if user_role != Role.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only owners can upload documents.",
        )

    if not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="Filename cannot be empty.",
        )

    if size_bytes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Document size must be greater than zero.",
        )

    document = {
        "id": str(uuid4()),
        "owner_id": owner_id,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    documents[document["id"]] = document
    return document


def list_owner_documents(owner_id: str):
    return [
        document
        for document in documents.values()
        if document["owner_id"] == owner_id
    ]


def get_document(document_id: str, owner_id: str):
    document = documents.get(document_id)

    if not document or document["owner_id"] != owner_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return document


def delete_document(document_id: str, owner_id: str):
    document = get_document(document_id, owner_id)
    del documents[document_id]

    return {
        "message": "Document metadata deleted successfully.",
        "document_id": document["id"],
    }
