
from enum import Enum
from fastapi import HTTPException, status


class Role(str, Enum):
    ADMIN = "admin"
    OWNER = "owner"
    VIEWER = "viewer"


def require_role(
    user_role: Role,
    allowed_roles: set[Role],
) -> None:
    """Allow an operation only for an approved role."""

    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )


def require_document_access(
    user_id: str,
    user_role: Role,
    owner_id: str,
    shared_user_ids: set[str],
    action: str,
    can_view: bool,
    can_download: bool,
    is_expired: bool = False,
    is_revoked: bool = False,
) -> None:
    """Check document ownership or sharing permissions."""

    # Owners can access their own documents.
    if user_role == Role.OWNER and user_id == owner_id:
        return

    # Only viewers with an active share can access shared files.
    if user_role != Role.VIEWER or user_id not in shared_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document.",
        )

    if is_expired or is_revoked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This document share has expired or been revoked.",
        )

    if action == "view" and not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="View permission has not been granted.",
        )

    if action == "download" and not can_download:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download permission has not been granted.",
        )

    if action not in {"view", "download"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported document action.",
        )
