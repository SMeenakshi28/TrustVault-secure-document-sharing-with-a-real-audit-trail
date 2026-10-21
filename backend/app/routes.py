
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth import (
    SignupRequest,
    LoginRequest,
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user_from_token,
)
from app.security import Role
from app.documents import (
    DocumentCreate,
    create_document,
    list_owner_documents,
    delete_document,
)
from app.audit import log_event, list_audit_logs

from pydantic import BaseModel, Field

from app.permissions import (
    share_document,
    list_shared_documents,
    revoke_share,
)

router = APIRouter()
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    return get_current_user_from_token(credentials.credentials)


def require_owner(user: dict):
    if user["role"] != Role.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only document owners can perform this action.",
        )

class ShareRequest(BaseModel):
    viewer_id: str
    can_view: bool = True
    can_download: bool = False
    expires_in_days: int | None = Field(default=None, gt=0)


# ---------- AUTHENTICATION ----------

@router.post("/auth/signup", status_code=201)
def signup(data: SignupRequest):
    user = create_user(data.name, data.email, data.password)

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"].value,
    }


@router.post("/auth/login")
def login(data: LoginRequest):
    user = authenticate_user(data.email, data.password)

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"].value,
        },
    }


@router.get("/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"].value,
    }


# ---------- DOCUMENT MANAGEMENT ----------

@router.post("/documents", status_code=201)
def upload_document_metadata(
    data: DocumentCreate,
    user: dict = Depends(get_current_user),
):
    require_owner(user)

    document = create_document(
        owner_id=user["id"],
        user_role=user["role"],
        filename=data.filename,
        content_type=data.content_type,
        size_bytes=data.size_bytes,
    )

    log_event(
        actor_id=user["id"],
        action="document_metadata_created",
        document_id=document["id"],
        details={"filename": document["filename"]},
    )

    return document


@router.get("/documents")
def get_my_documents(user: dict = Depends(get_current_user)):
    require_owner(user)
    return list_owner_documents(user["id"])


@router.delete("/documents/{document_id}")
def remove_document(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    require_owner(user)

    result = delete_document(
        document_id=document_id,
        owner_id=user["id"],
    )

    log_event(
        actor_id=user["id"],
        action="document_metadata_deleted",
        document_id=document_id,
    )

    return result

# ---------- DOCUMENT SHARING ----------

@router.post("/documents/{document_id}/share", status_code=201)
def create_document_share(
    document_id: str,
    data: ShareRequest,
    user: dict = Depends(get_current_user),
):
    require_owner(user)

    share = share_document(
        document_id=document_id,
        owner_id=user["id"],
        viewer_id=data.viewer_id,
        can_view=data.can_view,
        can_download=data.can_download,
        expires_in_days=data.expires_in_days,
    )

    log_event(
        actor_id=user["id"],
        action="document_shared",
        document_id=document_id,
        details={
            "viewer_id": data.viewer_id,
            "can_view": data.can_view,
            "can_download": data.can_download,
        },
    )

    return share


@router.get("/shared-with-me")
def get_shared_documents(
    user: dict = Depends(get_current_user),
):
    return list_shared_documents(user["id"])


@router.delete("/shares/{share_id}")
def remove_document_share(
    share_id: str,
    user: dict = Depends(get_current_user),
):
    require_owner(user)

    result = revoke_share(
        share_id=share_id,
        owner_id=user["id"],
    )

    log_event(
        actor_id=user["id"],
        action="document_share_revoked",
        details={"share_id": share_id},
    )

    return result

# ---------- AUDIT LOGS ----------

@router.get("/admin/audit-logs")
def get_audit_logs(user: dict = Depends(get_current_user)):
    return list_audit_logs(user["role"])

