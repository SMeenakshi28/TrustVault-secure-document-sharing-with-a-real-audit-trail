from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from typing import Literal

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
    count_active_documents,
    get_document,
    delete_document,
)
from app.audit import (
    log_event,
    list_audit_logs,
    list_owner_audit_logs,
)

from pydantic import BaseModel, EmailStr, Field

from app.access_requests import (
    create_owner_access_request,
    get_latest_owner_access_request,
    list_pending_owner_access_requests,
    review_owner_access_request,
)

from app.permissions import (
    share_document,
    list_shared_documents,
    list_owner_shares,
    revoke_share,
    get_viewer_document_access,
    record_viewer_document_access,
)
from app.storage import download_object

from app.admin import (
    list_users,
    change_user_role,
    set_user_active,
    delete_user_account,
)

from fastapi.responses import Response
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User, UserIdentity, SharingPermission

router = APIRouter()
bearer_scheme = HTTPBearer()

class RoleUpdateRequest(BaseModel):
    role: Role


class ActiveUpdateRequest(BaseModel):
    active: bool


class OwnerAccessReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]


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

def require_admin(user: dict):
    if user["role"] != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

class ShareRequest(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=100)
    recipient_email: EmailStr
    expires_at: datetime
    can_download: bool = False

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


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.patch("/auth/profile")
def update_own_profile(
    data: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
):
    new_name = data.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    with SessionLocal() as db:
        with db.begin():
            account = db.scalar(
                select(User).where(User.id == user["id"]).with_for_update()
            )
            identity = db.get(UserIdentity, user["id"])
            if not account or not account.active:
                raise HTTPException(status_code=401, detail="Account is unavailable.")
            account.name = new_name
            if identity:
                identity.name = new_name
            log_event(
                actor_id=user["id"],
                action="profile_name_updated",
                details={"field": "name"},
                db=db,
            )
        return {"id": account.id, "name": account.name, "email": account.email}


@router.delete("/auth/account")
def delete_own_account(user: dict = Depends(get_current_user)):
    """Remove login access while retaining identity references required by audit history."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        with db.begin():
            account = db.scalar(
                select(User).where(User.id == user["id"]).with_for_update()
            )
            if not account:
                raise HTTPException(status_code=404, detail="Account not found.")
            if account.role == Role.ADMIN.value:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Admin accounts cannot be self-deleted. "
                        "Ask another authorized Admin to manage this account."
                    ),
                )

            identity = db.get(UserIdentity, account.id)
            if not identity:
                identity = UserIdentity(
                    id=account.id,
                    name=account.name,
                    email=account.email,
                    created_at=account.created_at,
                )
                db.add(identity)
                db.flush()
            identity.deleted_at = now

            shares = db.scalars(
                select(SharingPermission).where(
                    (
                        (SharingPermission.owner_id == account.id)
                        | (SharingPermission.viewer_id == account.id)
                    ),
                    SharingPermission.revoked.is_(False),
                ).with_for_update()
            ).all()
            for share in shares:
                share.revoked = True
                share.revoked_at = now

            log_event(
                actor_id=account.id,
                action="user_self_account_deleted",
                details={
                    "deleted_at": now.isoformat(),
                    "account_role": account.role,
                    "retention_note": "Identity reference retained for audit integrity.",
                },
                db=db,
            )
            db.delete(account)
            db.flush()

    return {
        "message": "Account sign-in has been removed and active shares revoked. Historical identity and document records are retained where required for audit integrity."
    }


@router.get("/auth/owner-access-request")
def get_my_owner_access_request(user: dict = Depends(get_current_user)):
    if user["role"] not in {Role.VIEWER, Role.OWNER}:
        raise HTTPException(
            status_code=403,
            detail="Owner access request status is unavailable for this account.",
        )
    return get_latest_owner_access_request(user["id"])


@router.post("/auth/owner-access-request", status_code=201)
def request_owner_access(user: dict = Depends(get_current_user)):
    if user["role"] != Role.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Only Viewer accounts can request Owner access.",
        )
    return create_owner_access_request(user["id"])


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
    # Owners can access their own documents or a valid share from another Owner.
    if user["role"] == Role.OWNER:
        try:
            return get_document(
                document_id=document_id,
                owner_id=user["id"],
            )
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return get_viewer_document_access(
                document_id=document_id,
                viewer_id=user["id"],
                require_download=require_download,
            )

    # Other users must have an active, valid share.
    return get_viewer_document_access(
        document_id=document_id,
        viewer_id=user["id"],
        require_download=require_download,
    )


def log_denied_document_access(
    document_id: str,
    user: dict,
    action: str,
    error: HTTPException,
) -> None:
    log_event(
        actor_id=user["id"],
        action="document_access_denied",
        document_id=document_id,
        details={
            "attempted_action": action,
            "reason": error.detail,
        },
    )


@router.get("/documents/{document_id}/file")
def view_document_file(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    try:
        document = get_authorized_document(
            document_id=document_id,
            user=user,
            require_download=False,
        )
    except HTTPException as error:
        if user["role"] == Role.VIEWER:
            log_denied_document_access(document_id, user, "view", error)
        raise

    contents = download_object(document["storage_path"])

    if user["role"] == Role.VIEWER or document.get("owner_id") != user["id"]:
        try:
            record_viewer_document_access(document_id, user["id"])
        except HTTPException as error:
            log_denied_document_access(document_id, user, "view", error)
            raise
    else:
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
    try:
        document = get_authorized_document(
            document_id=document_id,
            user=user,
            require_download=True,
        )
    except HTTPException as error:
        if user["role"] in {Role.VIEWER, Role.OWNER}:
            log_denied_document_access(document_id, user, "download", error)
        raise

    contents = download_object(document["storage_path"])

    if user["role"] == Role.VIEWER or document.get("owner_id") != user["id"]:
        try:
            record_viewer_document_access(
                document_id,
                user["id"],
                require_download=True,
            )
        except HTTPException as error:
            log_denied_document_access(document_id, user, "download", error)
            raise
    else:
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
        recipient_name=data.recipient_name,
        recipient_email=str(data.recipient_email),
        expires_at=data.expires_at,
        can_download=data.can_download,
    )

    return share


@router.get("/shared-with-me")
def get_shared_documents(
    user: dict = Depends(get_current_user),
):
    return list_shared_documents(user["id"])


@router.get("/owner/shares")
def get_owner_shares(user: dict = Depends(get_current_user)):
    require_owner(user)
    return list_owner_shares(user["id"])


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

    return result

# ---------- AUDIT LOGS ----------

@router.get("/owner/audit-logs")
def get_owner_audit_logs(user: dict = Depends(get_current_user)):
    require_owner(user)
    return list_owner_audit_logs(user["id"])


# ---------- ADMIN USER MANAGEMENT ----------

@router.get("/admin/users")
def get_admin_users(
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    return list_users()


@router.patch("/admin/users/{target_user_id}/role")
def update_user_role(
    target_user_id: str,
    data: RoleUpdateRequest,
    user: dict = Depends(get_current_user),
):
    require_admin(user)

    result = change_user_role(
        actor_id=user["id"],
        target_user_id=target_user_id,
        new_role=data.role,
    )

    target = result["user"]

    return {
        "message": "User role updated successfully.",
        "user": target,
    }


@router.patch("/admin/users/{target_user_id}/active")
def update_user_active(
    target_user_id: str,
    data: ActiveUpdateRequest,
    user: dict = Depends(get_current_user),
):
    require_admin(user)

    target = set_user_active(
        actor_id=user["id"],
        target_user_id=target_user_id,
        active=data.active,
    )

    return {
        "message": "User account status updated successfully.",
        "user": target,
    }


@router.get("/admin/audit-logs")
def get_audit_logs(
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    return list_audit_logs(user["role"])


@router.get("/admin/document-count")
def get_admin_document_count(
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    return {"count": count_active_documents()}


@router.get("/admin/owner-access-requests")
def get_owner_access_requests(
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    return list_pending_owner_access_requests()


@router.patch("/admin/owner-access-requests/{request_id}")
def review_owner_access_request_route(
    request_id: str,
    data: OwnerAccessReviewRequest,
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    return review_owner_access_request(
        admin_id=user["id"],
        request_id=request_id,
        decision=data.decision,
    )


@router.delete("/admin/users/{target_user_id}")
def delete_admin_user(
    target_user_id: str,
    user: dict = Depends(get_current_user),
):
    require_admin(user)

    result = delete_user_account(
        actor_id=user["id"],
        target_user_id=target_user_id,
    )

    return {
        "message": result["message"],
        "user_id": result["user_id"],
        "email": result["email"],
    }
