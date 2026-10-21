
import pytest
from fastapi import HTTPException

from app.documents import (
    documents,
    create_document,
    list_owner_documents,
    get_document,
    delete_document,
)
from app.security import Role


@pytest.fixture(autouse=True)
def clear_documents():
    documents.clear()
    yield
    documents.clear()


def test_owner_can_create_document():
    document = create_document(
        "owner1", Role.OWNER, "report.pdf", "application/pdf", 1024
    )

    assert document["filename"] == "report.pdf"
    assert document["owner_id"] == "owner1"


def test_viewer_cannot_create_document():
    with pytest.raises(HTTPException) as error:
        create_document(
            "viewer1", Role.VIEWER, "report.pdf", "application/pdf", 1024
        )

    assert error.value.status_code == 403


def test_owner_only_sees_own_documents():
    create_document("owner1", Role.OWNER, "a.pdf", "application/pdf", 100)
    create_document("owner2", Role.OWNER, "b.pdf", "application/pdf", 200)

    result = list_owner_documents("owner1")

    assert len(result) == 1
    assert result[0]["filename"] == "a.pdf"


def test_owner_cannot_access_another_owners_document():
    document = create_document(
        "owner1", Role.OWNER, "private.pdf", "application/pdf", 100
    )

    with pytest.raises(HTTPException) as error:
        get_document(document["id"], "owner2")

    assert error.value.status_code == 404


def test_owner_can_delete_own_document():
    document = create_document(
        "owner1", Role.OWNER, "remove.pdf", "application/pdf", 100
    )

    delete_document(document["id"], "owner1")

    assert document["id"] not in documents
