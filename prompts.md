# TrustVault — AI-Assisted Development Prompts

## Day 1 — October 19, 2026

**Project:** TrustVault — Secure document sharing with a real audit trail

### Entry 1: Understanding the problem statement and user roles

**Prompt / request:**

Explain the TrustVault hackathon problem statement in simple terms. Describe the problem, the proposed solution, and the responsibilities of the admin, owner, and viewer.

**What AI produced:**

A simplified explanation of TrustVault as a secure document-sharing platform, where owners share documents with selected viewers and important document activities are recorded in an audit trail. It also explained the responsibilities of the three roles.

**What was wrong or incomplete:**

The distinction between the admin and document owner was initially unclear. I also needed clarification on whether each role required a separate application or separate screens.

**What I did instead:**

I clarified the role responsibilities and decided to use one application with separate dashboards for admin, owner, and viewer.

**Related commit:** No direct code commit — this entry documents problem-statement clarification and role planning.

### Entry 2: Selecting the technology stack and planning the project lifecycle

**Prompt / request:**

Help me choose a suitable technology stack for TrustVault and explain the project lifecycle from initialization through development, testing, deployment, and maintenance.

**What AI produced:**

A proposed architecture using React with Vite for the frontend, Python with FastAPI for the backend, Supabase PostgreSQL for the database, and private Supabase Storage for documents. It also outlined the major development stages.

**What was wrong or incomplete:**

The technology choices and lifecycle plan provided a starting point but did not constitute a working application. The integration, security, testing, deployment, and maintenance tasks still needed to be completed.

**What I did instead:**

I proceeded with the proposed architecture and planned to build the application in stages, starting with the frontend before integrating the backend and database.

**Related commit:** No direct code commit — this entry documents planning and technology selection.

### Entry 3: Exploring the UI design using Lovable

**Prompt / request:**

Provide a prompt for Lovable to generate a visual reference for the TrustVault interface, including the login screen and role-specific dashboards, so I could understand the design and build my own frontend.

**What AI produced:**

A prompt describing a secure document-sharing interface with role-based dashboards and document-management features.

**What was wrong or incomplete:**

The initial UI direction did not fully match the interface I wanted. I needed a clearer visual reference before continuing with the frontend implementation.

**What I did instead:**

I requested a Lovable prompt to explore the interface visually and use the generated design as a reference for building my own React frontend.

**Related commit:** No direct commit for the UI-reference prompt itself. Related frontend implementation

### Entry 4: Implementing the React frontend

**Prompt / request:**

Help me build the TrustVault frontend in React, starting with the login and sign-up screens and progressing toward role-specific dashboards. Explain the code and provide the relevant file paths.

**What AI produced:**

Frontend implementation guidance for the login and sign-up interfaces, form fields, password visibility, role selection in the prototype, navigation between screens, and role-based dashboard layouts.

**What was wrong or incomplete:**

The frontend was still a work in progress. Some screens and interactions were developed, but the application was not yet fully connected to backend authentication, document storage, or permission enforcement.

**What I did instead:**

I continued developing the frontend in stages and used the interface as a prototype, keeping the remaining integration and security work for subsequent development.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/eab71cd

### Entry 5: Implementing form validation and identifying security limitations

**Prompt / request:**

Help me implement sign-up form validation, including password-strength requirements, and explain which security features must be handled by the backend.

**What AI produced:**

Password validation requirements covering minimum length, uppercase and lowercase letters, a number, and a special character. It also explained the difference between frontend validation and server-side security enforcement.

**What was wrong or incomplete:**

Frontend validation improves the user experience but can be bypassed. Allowing public users to assign themselves the Admin role would also be unsafe in the finished application.

**What I did instead:**

I treated frontend validation and role selection as prototype functionality and identified backend authentication, trusted role assignment, and server-side authorization as necessary follow-up tasks.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/eab71cd


## Day 2 — October 20, 2026

**Project:** TrustVault — Secure document sharing with a real audit trail

### Entry 1: Building the backend authentication module and tests

**Prompt / request:**

Help me implement TrustVault backend authentication using Python. Create the required authentication files and corresponding tests, explain the code, and guide me through running the tests to verify the functionality.

**What AI produced:**

Python authentication code for user registration and login, role handling, password verification, and JWT-based authentication, along with test code for authentication behavior.

**What was wrong or incomplete:**

The implementation used in-memory user storage, so accounts were not persistent across server restarts. The development setup also used temporary credentials and a development JWT secret that would need to be secured before deployment.

**What I did instead:**

I implemented the authentication module and its corresponding tests, then proceeded with the backend integration after checking the authentication behavior.

**Concrete test results:**
- Owner login was tested using `owner@test.com`.
- Viewer registration and login were tested using `viewer@test.com`.
- These accounts were temporary and stored in memory; they would need to be recreated after a server restart.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/23d6f89

### Entry 2: Implementing document management and permission handling

**Prompt / request:**

Help me implement the document-management and permission modules. Owners should be able to manage their documents, share them with eligible viewers, control permissions, and revoke access. Provide the code and tests.

**What AI produced:**

Python modules for document metadata management and sharing permissions, including ownership checks, viewer access, read/download flags, and expiration validation.

**What was wrong or incomplete:**

The document module handled metadata rather than actual file uploads. Recipient validation also needed to ensure that the selected recipient was a registered, active viewer.

**What I did instead:**

I implemented the document and permission modules and added recipient validation to reject ineligible recipients.

**Concrete test results:**
- Owner document creation and listing were tested successfully.
- A viewer could access documents shared with them.
- Revoking a share removed the viewer's access.
- A request with both `can_view` and `can_download` set to `false` returned **HTTP 400 Bad Request**.
- Sharing with an invalid or ineligible recipient returned **HTTP 400 Bad Request**, with the message: `Recipient must be an active viewer account.`

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/73f4d17

### Entry 3: Implementing the audit-trail module

**Prompt / request:**

Help me implement an audit-trail module that records important actions and provides a way to verify the integrity of the audit history.

**What AI produced:**

An audit module that records events, maintains previous-hash references, calculates event hashes, restricts audit-log viewing to administrators, and verifies the audit chain.

**What was wrong or incomplete:**

Audit events were stored in memory and would be lost after a server restart. Hash-chain verification was a useful integrity check, but it did not yet provide persistent, independently protected audit storage.

**What I did instead:**

I implemented the audit module and used a temporary development endpoint to check audit-chain validity.

**Concrete test results:**
- The audit-chain verification endpoint was tested during development. The previously recorded test status was valid (`{"valid": true}`), although the exact test output was not preserved in the conversation.
- The audit-log endpoint was tested with an owner account and correctly denied access with **HTTP 403 Forbidden** and the message: `Only admins can view the audit logs.`
- Successful access by an administrator was not yet confirmed.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/c8f89cf

### Entry 4: Connecting the backend modules through FastAPI

**Prompt / request:**

Help me connect the authentication, document-management, permission, and audit modules through FastAPI. Create the API routes and explain how to test the endpoints using Swagger.

**What AI produced:**

FastAPI routes for registration, login, current-user information, document creation and listing, document deletion, sharing, viewing shared documents, revoking access, and administrator-only audit-log access.

**What was wrong or incomplete:**

Connecting the modules did not automatically guarantee that every operation was properly protected. Each endpoint needed to enforce authentication, role restrictions, and document-level permissions.

**What I did instead:**

I connected the modules through the FastAPI routes and tested the API through Swagger at `http://127.0.0.1:8000/docs`.

**Concrete test results:**
- The FastAPI server started successfully for development testing.
- Owner-only document operations were tested using an authenticated owner.
- An owner attempting to access the administrator audit-log endpoint received **HTTP 403 Forbidden**.
- Viewer access to shared documents and access revocation were tested as part of the API workflow.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/5e2f948

### Entry 5: Testing role-based access control and identifying remaining gaps

**Prompt / request:**

Help me test TrustVault using different user roles. Verify owner and viewer behavior, invalid sharing requests, unauthorized access, administrator audit access, and audit-chain verification.

**What AI produced:**

A testing workflow covering authentication, document creation, sharing, viewing shared documents, revocation, invalid permission combinations, invalid recipients, administrator-only audit access, and audit-chain verification.

**What was wrong or incomplete:**

The backend still relied on in-memory storage. Actual file upload/download, persistent audit storage, and a confirmed successful administrator audit-log test remained incomplete or unverified.

**What I did instead:**

I exercised the API with owner and viewer accounts, checked expected success and failure responses, corrected recipient validation, and tested the audit endpoints. I recorded the remaining limitations instead of treating the backend as production-ready.

**Concrete test results:**

| Test | Observed result |
|---|---|
| Owner login | Tested successfully |
| Viewer registration/login | Tested successfully |
| Owner creates document metadata | Tested successfully |
| Viewer accesses a shared document | Tested successfully |
| Owner revokes viewer access | Tested; access was revoked |
| Invalid permission combination | HTTP 400 |
| Invalid/ineligible share recipient | HTTP 400 |
| Owner accesses admin audit logs | HTTP 403 |
| Audit-chain verification | Previously reported valid |
| Successful admin audit-log access | Not yet confirmed |
| Actual file upload/download | Not implemented yet |
| Data persistence after restart | Not supported by current in-memory implementation |

**Related commits:**

- Authentication and role security: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/23d6f89
- Document permissions and sharing: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/73f4d17
- Audit trail and integrity verification: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/c8f89cf
- FastAPI integration: https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/5e2f948

## Day 3 — October 21, 2026

**Project:** TrustVault — Secure document sharing with a real audit trail

**Purpose:** Record the AI-assisted backend development, Supabase connection troubleshooting, persistent database and storage integration, document-access tests, audit-trail improvements, and unresolved deletion issue completed on Day 3.

---

### Entry 1: Troubleshooting the Supabase database connection

**Prompt / request:**

Help me connect the FastAPI backend to the Supabase PostgreSQL database. Diagnose the connection problems step by step, explain the errors, and help me establish a reliable database connection without exposing credentials.

**What AI produced:**

Guidance for configuring the database connection using environment variables, SQLAlchemy, PostgreSQL, and the Supabase connection pooler. The troubleshooting process included checking the database URL, diagnosing connection failures, and verifying connectivity.

The Supabase project was configured to use the transaction pooler in the Seoul region, with SSL required. The database connection was eventually verified successfully.

**What was wrong or incomplete:**

The initial connection setup did not work immediately. Connection configuration, URL formatting, pooler settings, and environment configuration required investigation. Repeated attempts were needed before the backend could communicate with the database.

**What I did instead:**

I followed the troubleshooting steps, created diagnostic scripts, checked the Supabase connection settings, and corrected the database configuration until the connection succeeded.

The following helper scripts were created during this process:

- `backend/fix_db_url.py` — to help correct or inspect the database URL configuration.
- `backend/diagnose_db.py` — to investigate database connection problems.
- `backend/check_supabase.py` — to check the Supabase connection and configuration.

These were development and troubleshooting utilities, not the main application modules.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/edd780e

 chore: add Supabase database diagnostics
---

### Entry 2: Implementing database connectivity, ORM models, and authentication

**Prompt / request:**

Help me move the backend from temporary in-memory data to a real Supabase PostgreSQL database. Create the necessary database module and models, connect user authentication to persistent storage, and explain how to test signup, login, and authenticated requests.

**What AI produced:**

The backend database and authentication implementation was extended with:

- `backend/app/database.py` — SQLAlchemy engine configuration, database sessions, declarative base, and database dependency handling.
- `backend/app/models.py` — ORM models for users, documents, sharing permissions, and audit logs.
- `backend/app/auth.py` — database-backed signup and login, password hashing, JWT token generation and verification, and retrieval of the authenticated user.

The database tables were created and verified. Authentication was tested using FastAPI Swagger, including signup, login, token authorization, and the authenticated-user endpoint.

**What was wrong or incomplete:**

The database and authentication code required integration and verification. Creating the models alone did not prove that users would persist correctly or that protected endpoints would reject invalid credentials.

The project also needed to keep database credentials, JWT secrets, and Supabase service-role credentials out of source control and the frontend.

**What I did instead:**

I configured the environment variables, connected the application to PostgreSQL, created the database tables, and tested the authentication endpoints. I also verified that the backend `.env` file was ignored by Git.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/d20bfaf

 feat: integrate persistent database authentication
---

### Entry 3: Integrating private Supabase Storage and real document uploads

**Prompt / request:**

Help me integrate actual document storage with TrustVault. Implement a secure upload endpoint that stores the file in a private Supabase Storage bucket, saves its metadata in PostgreSQL, and uses the authenticated owner’s identity to organize and protect uploaded files.

**What AI produced:**

A storage module, `backend/app/storage.py`, using HTTP requests to the Supabase Storage API for file uploads, downloads, and deletions.

The backend upload route in `backend/app/routes.py` was extended to:

- Accept document uploads from authenticated owners.
- Sanitize uploaded filenames.
- Enforce a 20 MB upload limit.
- Generate a unique storage path for each file.
- Upload the actual file bytes to the private `trustvault-documents` bucket.
- Store document metadata and the storage path in PostgreSQL.
- Attempt to clean up the stored file if saving its database metadata fails.
- Record a `document_uploaded` audit event.

The bucket was configured as private, with public access disabled.

**What was wrong or incomplete:**

The earlier document-management implementation primarily handled metadata. Creating a document record did not necessarily mean that an actual file had been uploaded to secure storage.

The database and storage operations also needed to be coordinated so that a failure in one would not leave inconsistent records or files.

**What I did instead:**

I configured the private bucket and uploaded actual PDF documents through FastAPI. I verified that the uploaded files appeared in Supabase Storage and that their metadata was stored in the database.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/35231d3

feat: integrate private Supabase document storage
---

### Entry 4: Implementing real document viewing, downloading, and permission enforcement

**Prompt / request:**

Implement secure document viewing and downloading. An owner should be able to access their own files, while a viewer should only access documents explicitly shared with them. Downloading must be denied when the owner has not granted download permission. Test the successful and unsuccessful cases through Swagger.

**What AI produced:**

The document routes were extended to retrieve actual file bytes from private Supabase Storage.

The implementation included:

- `GET /documents/{document_id}/file` for authorized document viewing.
- `GET /documents/{document_id}/download` for permission-controlled downloading.
- Owner checks for documents owned by the authenticated user.
- Viewer access checks using active sharing permissions.
- Expiration and revocation checks.
- Enforcement of the `can_download` permission.
- Audit events for document viewing and downloading.
- Appropriate response headers for file delivery.

**What was wrong or incomplete:**

A valid login alone must not grant access to every document. The backend must check the relationship between the authenticated user, the document owner, and the sharing permission on each protected request.

The tests also needed to distinguish successful access from a correctly denied request.

**What I did instead:**

I tested the actual document-access flow with owner and viewer accounts.

**Concrete test results:**

| Test | Observed result |
|---|---|
| Owner uploads a real PDF | Successful |
| Uploaded files appear in private Supabase Storage | Verified |
| Owner views an uploaded document | Successful |
| Viewer views a document shared with them | HTTP 200 |
| Viewer downloads when `can_download` is false | HTTP 403 |
| Owner revokes the viewer's sharing permission | Successful |
| Viewer attempts to view the document after revocation | HTTP 403 |
| Fresh viewer login and authenticated-user check | HTTP 200 |

These results demonstrated that the backend was checking document permissions rather than relying solely on frontend visibility.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/7c4c612

feat: enforce document sharing permissions
---

### Entry 5: Making the audit trail persistent and verifiable

**Prompt / request:**

Replace the in-memory audit log with persistent database storage. Record important document activities and maintain a hash chain so that changes to the recorded event sequence can be detected. Restrict access to audit logs to administrators and test the implementation.

**What AI produced:**

The audit module, `backend/app/audit.py`, was updated to store audit events in PostgreSQL using the `AuditLog` model.

The implementation included:

- Persistent audit-event storage.
- Hash calculation for individual events.
- Linking events through previous-event hashes.
- Transaction-level advisory locking during event insertion to coordinate concurrent writes.
- Audit-chain verification.
- Administrator-only access to audit-log listing.

Document-related routes were connected to audit logging for uploads, views, downloads, sharing changes, and deletions.

**What was wrong or incomplete:**

An in-memory audit list would disappear when the backend restarted and would not provide a persistent record of document activity.

Hash chaining also needed to be implemented consistently, and administrator-only access needed to be checked independently of the frontend.

**What I did instead:**

I updated the audit implementation, compiled the backend, checked the imports, and tested audit-event creation and verification.

**Concrete test results:**

| Test | Observed result |
|---|---|
| Audit event creation | Successful |
| Audit record persisted in PostgreSQL | Verified |
| Audit-chain verification | Reported valid |
| Viewer attempts to access administrator-only audit logs | HTTP 403 |

The successful administrator audit-log access test and broader tamper-resistance testing remain to be confirmed. Hash chaining helps detect changes to the event sequence but does not, by itself, prevent a sufficiently privileged attacker from rewriting the entire chain.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/f5fd6c9

 feat: persist and verify audit logs
---

### Entry 6: Creating and using a test-owner promotion utility

**Prompt / request:**

Help me prepare a development utility for promoting a test account to the owner role so that I can test owner-specific document upload, sharing, viewing, and deletion operations without manually modifying the database each time.

**What AI produced:**

A development helper script, `backend/promote_test_owner.py`, for promoting a test account to the owner role.

The script supported development and testing workflows where an account needed owner permissions to exercise protected document-management endpoints.

**What was wrong or incomplete:**

A promotion utility is not part of the normal user-facing application workflow. If exposed or used carelessly, it could create privilege-escalation risks. It must not become an unrestricted production mechanism.

**What I did instead:**

I used development accounts to test role-protected endpoints and kept the promotion utility separate from the normal API workflow. The utility must be reviewed before final deployment, and its use should remain restricted to authorized development operations.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/c63b167

 chore: add test owner promotion utility
---

### Entry 7: Testing document deletion and investigating the Supabase Storage error

**Prompt / request:**

Fix document deletion so that an owner can delete both the actual stored file and its corresponding database metadata. Ensure that the API reports errors accurately and does not silently leave the database and storage in an inconsistent state.

**What AI produced:**

The document-deletion implementation was updated in `backend/app/documents.py` and `backend/app/routes.py`.

The intended deletion sequence was:

1. Confirm that the authenticated owner owns the document.
2. Delete the actual file from Supabase Storage.
3. Delete associated sharing-permission records.
4. Delete the document metadata from PostgreSQL.
5. Record a `document_deleted` audit event after successful deletion.

The storage deletion helper was also updated to report storage failures through HTTP 502 responses and to print diagnostic details during troubleshooting.

**What was wrong or incomplete:**

The deletion test did not finish successfully. The API returned HTTP 502, and further diagnostics showed that Supabase Storage responded with an HTTP 400 error containing:

`{"statusCode":"404","error":"not_found","message":"Object not found","code":"NoSuchKey"}`

This indicates that the requested object was not found at the storage path supplied to Supabase.

The database record appeared to be deleted according to the database check, even though the API returned 502. This observation has not yet been reconciled with the current deletion sequence, which attempts storage deletion before committing the database deletion.

**What I did instead:**

I added temporary diagnostic output to `backend/app/storage.py` and inspected the failed response. I also prepared a temporary diagnostic print in the deletion route to inspect the document's `storage_path`.

The issue was postponed at the end of Day 3 so that development could continue without making further unverified changes.

**Concrete test results:**

| Test | Observed result |
|---|---|
| Delete endpoint request | HTTP 502 |
| Supabase Storage deletion response | HTTP 400 |
| Storage error code | `NoSuchKey` |
| Database record after failed request | Reported as deleted; needs reconciliation |
| Actual file deletion | Not confirmed |
| Successful end-to-end deletion | Not verified |

**Remaining work:**

- Compare the document's stored `storage_path` with the exact object path in the private bucket.
- Determine why Supabase cannot find the requested object.
- Verify the state of the database record and stored file after a failed deletion.
- Correct the deletion workflow so that file and metadata states remain consistent.
- Remove temporary diagnostic output after the issue is resolved.
- Retest until the endpoint returns a successful response and both the database record and stored file are confirmed removed.

**Related commit:** https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail/commit/3694572

Fix: preserve audit history when deleting documents

Fix: improve document deletion handling

6d6ef00 - fix: add Supabase storage implementation
---

### Day 3 summary

Day 3 focused on transitioning TrustVault from a backend prototype toward a persistent, storage-backed document-sharing application.

The main accomplishments were:

- Resolved the Supabase PostgreSQL connection issue.
- Created database, model, and troubleshooting utilities.
- Implemented persistent user authentication.
- Integrated private Supabase Storage for actual document files.
- Tested real PDF uploads and authorized document viewing.
- Verified viewer restrictions on downloads and revoked access.
- Implemented persistent audit logs with hash-chain verification.
- Investigated the document-deletion failure and recorded it as an unresolved issue.

The backend foundation is substantially implemented, but deletion consistency, successful administrator audit-log access, broader security testing, frontend integration, and production-readiness checks remain outstanding.

This record describes the work and test outcomes observed during Day 3. It does not claim that every backend feature is complete or production-ready.

## ## Day 4,5 — Existing-project debugging — October 22 & 23, 2026

### Changes made

- Confirmed `frontend/package.json` already declares Vite and `frontend/package-lock.json` matches it. Installed dependencies from `frontend`; Node 24.22.0 satisfies the Vite 8 and React plugin engine requirements.
- Added account-management checks and transactionally audited deactivation in `backend/app/admin.py`. Deactivation preserves user/document/audit rows and revokes related shares. Existing token validation checks current account status in `backend/app/auth.py`.
- Added `SharingPermission.viewed_at` and the idempotent migration `backend/migrations/003_one_time_share_access.sql`. Viewer view and permitted download requests are limited to one successful storage delivery; the consumed marker and success audit event commit together. Failed storage retrieval does not consume access.
- Connected the owner Share form to `POST /documents/{document_id}/share`; the API resolves an active viewer by email and validates ownership, name, and a future timezone-aware expiration.
- Added the viewer's one-time warning and access actions. This controls future application requests; it cannot prevent a recipient from retaining or capturing a delivered copy.
- Kept the audit actor foreign key: `backend/migrations/002_allow_user_deletion_preserve_audit.sql` no longer removes it. Added isolated database-backed auth, admin, permission, route, and audit tests under `backend/tests`.
- Added Windows setup instructions in `README.md` and non-secret backend configuration placeholders in `backend/.env.example`. Added `pytest` to `backend/requirements.txt`.

### Validation performed

- `npm install` from `frontend`: succeeded; 144 packages audited, 0 vulnerabilities reported.
- `npm run dev` from `frontend`: served the Vite app over HTTP with status 200.
- `npm run lint` and `npm run build` from `frontend`: succeeded.
- `python -m pip install -r requirements.txt` from `backend`: succeeded in `backend\.venv`.
- `python -m pytest -q` from `backend`: 38 passed, 1 skipped. The PostgreSQL row-lock concurrency test is skipped with SQLite because SQLite cannot exercise PostgreSQL locking.
- Started `python -m uvicorn app.main:app` from `backend` and queried `/health` with `curl`: HTTP 200. This health check does not verify database or Supabase connectivity.

### Remaining verification

Apply the numbered SQL migrations to the target database and verify the Supabase connection, private bucket, and real document storage operations using the project's configured services. Run the concurrency test against a disposable PostgreSQL test database before relying on it in production.