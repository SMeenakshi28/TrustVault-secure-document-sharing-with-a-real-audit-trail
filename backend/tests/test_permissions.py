
import pytest
from fastapi import HTTPException

from app.documents import documents, create_document
from app.permissions import shares, share_document, list_shared_documents, revoke_share
from app.security import Role


@pytest.fixture(autouse=True)
def clear_data():
    documents.clear()
    shares.clear()
    yield
    documents.clear()
    shares.clear()


def make_document():
    return create_document(
        "owner1", Role.OWNER, "report.pdf", "application/pdf", 1024
    )


def test_owner_can_share_document():
    document = make_document()
    share = share_document(document["id"], "owner1", "viewer1")
    assert share["viewer_id"] == "viewer1"
    assert share["can_view"] is True
    assert share["can_download"] is False


def test_other_owner_cannot_share_document():
    document = make_document()
    with pytest.raises(HTTPException) as error:
        share_document(document["id"], "owner2", "viewer1")
    assert error.value.status_code == 404


def test_viewer_sees_shared_document():
    document = make_document()
    share_document(document["id"], "owner1", "viewer1")
    result = list_shared_documents("viewer1")
    assert len(result) == 1
    assert result[0]["id"] == document["id"]


def test_revoked_share_disappears_from_viewer_list():
    document = make_document()
    share = share_document(document["id"], "owner1", "viewer1")
    revoke_share(share["id"], "owner1")
    assert list_shared_documents("viewer1") == []


def test_another_owner_cannot_revoke_share():
    document = make_document()
    share = share_document(document["id"], "owner1", "viewer1")
    with pytest.raises(HTTPException) as error:
        revoke_share(share["id"], "owner2")
    assert error.value.status_code == 404


def test_invalid_expiry_is_rejected():
    document = make_document()
    with pytest.raises(HTTPException) as error:
        share_document(
            document["id"], "owner1", "viewer1", expires_in_days=0
        )
    assert error.value.status_code == 400
