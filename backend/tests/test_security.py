
from fastapi import HTTPException
from app.security import (
    Role,
    require_role,
    require_document_access,
)

# Test 1: Admin can manage users.
require_role(Role.ADMIN, {Role.ADMIN})

# Test 2: Viewer cannot manage users.
try:
    require_role(Role.VIEWER, {Role.ADMIN})
    print("FAIL: Viewer was incorrectly authorized.")
except HTTPException as error:
    assert error.status_code == 403
    print("PASS: Viewer cannot manage users.")

# Test 3: Viewer with view permission can open a shared file.
require_document_access(
    user_id="viewer1",
    user_role=Role.VIEWER,
    owner_id="owner1",
    shared_user_ids={"viewer1"},
    action="view",
    can_view=True,
    can_download=False,
)
print("PASS: Viewer can open an authorized document.")

# Test 4: Viewer cannot download without permission.
try:
    require_document_access(
        user_id="viewer1",
        user_role=Role.VIEWER,
        owner_id="owner1",
        shared_user_ids={"viewer1"},
        action="download",
        can_view=True,
        can_download=False,
    )
    print("FAIL: Download restriction did not work.")
except HTTPException as error:
    assert error.status_code == 403
    print("PASS: Unauthorized download is blocked.")

print("Security tests completed.")
