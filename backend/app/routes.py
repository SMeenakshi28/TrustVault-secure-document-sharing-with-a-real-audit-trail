from uuid import uuid4
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
    get_document,
    delete_document,
)
from app.audit import log_event, list_audit_logs

from pydantic import BaseModel, Field

from app.permissions import (
    share_document,
    list_shared_documents,
    revoke_share,
    get_viewer_document_access,
)
from app.storage import download_object

from fastapi.responses import Response

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


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/documents/upload", status_code=201)
async def upload_document_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    require_owner(user)

    filename = Path(file.filename or "upload.bin").name
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    content_type = file.content_type or "application/octet-stream"
    contents = await file.read(MAX_UPLOAD_BYTES + 1)

    if not contents:
        raise HTTPException(status_code=400, detail="The file is empty.")

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 20 MB upload limit.",
        )

    storage_path = f"{user['id']}/{uuid4()}/{filename}"

    # Upload the actual file to private Supabase Storage first.
    from app.storage import upload_object, delete_object

    upload_object(storage_path, contents, content_type)

    try:
        document = create_document(
            owner_id=user["id"],
            user_role=user["role"],
            filename=filename,
            content_type=content_type,
            size_bytes=len(contents),
            storage_path=storage_path,
        )
    except Exception:
        # Avoid leaving an orphaned file if the database insert fails.
        try:
            delete_object(storage_path)
        except Exception:
            pass
        raise

    log_event(
        actor_id=user["id"],
        action="document_uploaded",
        document_id=document["id"],
        details={
            "filename": filename,
            "size_bytes": len(contents),
        },
    )

    return document

@router.get("/documents")
def get_my_documents(user: dict = Depends(get_current_user)):
    require_owner(user)
    return list_owner_documents(user["id"])


def get_authorized_document(
    document_id: str,
    user: dict,
    require_download: bool = False,
) -> dict:
    # Owners can access only their own documents.
    if user["role"] == Role.OWNER:
        return get_document(
            document_id=document_id,
            owner_id=user["id"],
        )

    # Other users must have an active, valid share.
    return get_viewer_document_access(
        document_id=document_id,
        viewer_id=user["id"],
        require_download=require_download,
    )


@router.get("/documents/{document_id}/file")
def view_document_file(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    document = get_authorized_document(
        document_id=document_id,
        user=user,
        require_download=False,
    )

    contents = download_object(document["storage_path"])

    log_event(
        actor_id=user["id"],
        action="document_viewed",
        document_id=document_id,
        details={"filename": document["filename"]},
    )

    return Response(
        content=contents,
        media_type=document["content_type"],
        headers={
            "Content-Disposition": (
                f"inline; filename*=UTF-8''{quote(document['filename'])}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/download")
def download_document_file(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    document = get_authorized_document(
        document_id=document_id,
        user=user,
        require_download=True,
    )

    contents = download_object(document["storage_path"])

    log_event(
        actor_id=user["id"],
        action="document_downloaded",
        document_id=document_id,
        details={"filename": document["filename"]},
    )

    return Response(
        content=contents,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(document['filename'])}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.delete("/documents/{document_id}")
def remove_document(document_id: str, user: dict = Depends(get_current_user)):
    require_owner(user)

    result = delete_document(document_id=document_id, owner_id=user["id"])
    log_event(actor_id=user["id"], action="document_deleted", document_id=document_id)
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

