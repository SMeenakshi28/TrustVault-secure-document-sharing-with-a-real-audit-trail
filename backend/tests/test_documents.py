import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.documents import (
    create_document,
    delete_document,
    get_document,
    list_owner_documents,
)
from app.models import Document
from app.security import Role


def test_owner_can_create_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    document = create_document(
        owner["id"], Role.OWNER, "report.pdf", "application/pdf", 1024
    )

    assert document["filename"] == "report.pdf"
    assert document["owner_id"] == owner["id"]


def test_viewer_cannot_create_document(create_account):
    viewer = create_account("Viewer", "viewer@example.com")

    with pytest.raises(HTTPException) as error:
        create_document(
            viewer["id"], Role.VIEWER, "report.pdf", "application/pdf", 1024
        )

    assert error.value.status_code == 403


def test_owner_only_sees_own_documents(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other = create_account("Other", "other@example.com", Role.OWNER)
    create_document(owner["id"], Role.OWNER, "a.pdf", "application/pdf", 100)
    create_document(other["id"], Role.OWNER, "b.pdf", "application/pdf", 200)

    result = list_owner_documents(owner["id"])

    assert [document["filename"] for document in result] == ["a.pdf"]


def test_owner_cannot_access_another_owners_document(create_account):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    other = create_account("Other", "other@example.com", Role.OWNER)
    document = create_document(
        owner["id"], Role.OWNER, "private.pdf", "application/pdf", 100
    )

    with pytest.raises(HTTPException) as error:
        get_document(document["id"], other["id"])

    assert error.value.status_code == 404


def test_delete_soft_deletes_metadata_and_preserves_history(
    create_account, monkeypatch
):
    owner = create_account("Owner", "owner@example.com", Role.OWNER)
    document = create_document(
        owner["id"], Role.OWNER, "remove.pdf", "application/pdf", 100
    )
    monkeypatch.setattr("app.storage.delete_object", lambda _path: None)

    delete_document(document["id"], owner["id"])

    with SessionLocal() as db:
        stored = db.scalar(
            select(Document).where(Document.id == document["id"])
        )
        assert stored is not None
        assert stored.is_deleted is True

    assert list_owner_documents(owner["id"]) == []
