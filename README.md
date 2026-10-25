# TrustVault — Secure Document Sharing with an Audit Trail

## Overview

TrustVault is a secure document-sharing web application focused on **controlled access** and an **auditable record of document activity**. Owners upload private documents and share them with registered users for a limited time, with optional download permission. Every important action is written to a hash-chained audit log that Owners and Admins can review.

The frontend is a React (Vite) single-page app. The backend is a FastAPI REST API that stores metadata in PostgreSQL and files in a private Supabase Storage bucket.

## Problem Statement

Sharing sensitive files over email or open links gives the sender little control once a file is sent: access cannot easily be limited, expired or withdrawn, and there is rarely a trustworthy record of who opened what. TrustVault addresses this by letting the backend decide, on every request, who may view or download a document, and by recording each access in a tamper-evident log.

## Key Features

All features below were confirmed in the source code.

- **Role-based access control** with three roles: Admin, Owner and Viewer, enforced by the backend using the role stored in the database.
- **Authentication:** signup (always creates a Viewer), login with a JWT access token (30-minute expiry), Argon2 password hashing, and rejection of disabled accounts.
- **Document upload and management:** Owners upload files (max 20 MB) to private storage, list their documents, and delete them. Deletion removes the stored file, marks the record as deleted and revokes its active shares, while audit history is kept.
- **Sharing with permissions:** an Owner shares a document with an existing, active user by email, sets a required expiry date/time, and chooses whether download is allowed (view is always granted).
- **Expiration and revocation:** expired or revoked shares are denied, and Owners can revoke a share at any time.
- **One-time access:** a share is consumed by the first successful view or download; later attempts are denied with "This share has already been viewed."
- **View vs. download restrictions:** downloading requires the share's download permission.
- **Private file storage:** files live in a Supabase Storage bucket named `trustvault-documents`, accessed only by the backend using a server-side key. Files are streamed through the API after a permission check.
- **Audit logging:** uploads, views, downloads, denied access attempts, shares, revocations, deletions, role changes, account deletions, profile name changes and Owner-access requests are logged. Each entry stores the hash of the previous entry (SHA-256 chain).
- **User and access management (Admin):** list users, change roles, activate/deactivate accounts, delete accounts, view all audit logs and the document count. The last active Admin cannot be demoted or deactivated.
- **Owner-access requests:** a Viewer can request Owner access; an Admin approves or rejects it.
- **Account self-service:** users can update their display name and delete their own account (Admins cannot self-delete). Deleting an account revokes its active shares and retains an identity record for audit integrity.

## User Roles

| Role | Responsibilities |
|------|------------------|
| **Admin** | Manages users (roles, activation, deletion), reviews Owner-access requests, views the full audit log and the total document count. Admins cannot view or download shared documents through the document endpoints. |
| **Owner** | Uploads, lists and deletes their own documents; shares documents with users, sets expiry and download permission; revokes shares; views an audit log of their own activity and their documents' activity. Owners can also open documents that another Owner has shared with them. |
| **Viewer** | Default role on signup. Views documents shared with them ("Shared with me"), downloads them where download was granted, can update their profile or delete their account, and can request Owner access. |

The first Admin is created with a command-line script (see [Installation and Setup](#installation-and-setup)); it cannot be created through signup.

## Demo Accounts

TrustVault supports three user roles: Admin, Owner, and Viewer. The following demo accounts are intended to help reviewers explore the application and understand how role-based access control works.

| Role | Name | Demo Email | Demo Password |
|---|---|---|
| Admin | Rahul Sharma |`rahul.sharma@trustvault.example` | `RahulAdmin@2026!` |
| Owner | Priya Reddy |`priya.reddy@trustvault.example` | `PriyaOwner@2026!` |
| Viewer | Arjun Kumar |`arjun.kumar@trustvault.example` | `ArjunView@2026!` |

**Note:** These are sample credentials. The accounts must be created and assigned the correct roles in the application before they can be used to log in.

### How to Test Each Role

- **Admin:** Explore user management, role administration, and audit logs.
- **Owner:** Upload a sample document, manage its permissions, share it, and revoke access.
- **Viewer:** Access documents shared with the account and test the available viewing and download permissions.

### Why Three Roles?

TrustVault uses role-based access control to separate administrative responsibilities, document ownership, and document access. Testing all three roles helps demonstrate that users have different permissions and cannot perform actions outside their authorized scope.

**Security notice:** These credentials are for demonstration purposes only. Do not use real or confidential documents with public demo accounts. Ensure demo data is isolated, restrict destructive actions where appropriate, and never use these passwords for real accounts.

## Tech Stack

| Layer | Technologies (from `package.json` / `requirements.txt`) |
|-------|---------------------------------------------------------|
| Frontend | React 19, Vite, ESLint (plain JavaScript/JSX, CSS) |
| Backend | Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic (`email-validator`), `python-multipart` |
| Authentication | PyJWT (HS256), `pwdlib` with Argon2 |
| Database | PostgreSQL via `psycopg` (SQLite in-memory is used only by the tests) |
| File storage | Supabase Storage (private bucket), accessed over HTTP with `httpx` |
| Testing | pytest |
| Hosting configuration | Vercel (`backend/vercel.json` using `@vercel/python`) |

> `@supabase/supabase-js` is listed in the frontend `package.json`, but no frontend source file imports it. The frontend talks only to the TrustVault API.

## System Architecture

```text
Browser (React + Vite)
        │  HTTPS, JSON / multipart, Authorization: Bearer <JWT>
        ▼
FastAPI backend ──► PostgreSQL  (users, documents, sharing_permissions,
        │                        owner_access_requests, audit_logs, user_identities)
        │
        └─────────► Supabase Storage (private bucket "trustvault-documents")
```

- The frontend sends requests to `VITE_API_BASE_URL`, or to `/api` by default. In development, the Vite dev server proxies `/api` to the backend.
- Every protected route resolves the user from the JWT and reloads the account from the database, so the current database role and active status decide access, not claims supplied by the browser.
- Documents are never served directly from storage. The backend checks permissions, fetches the file with its service key, records an audit event, and returns the file.
- Audit events are appended inside the same database transaction as the action where applicable, each linked to the previous event's hash.

Backend modules (`backend/app/`): `routes.py` (API routes), `auth.py`, `permissions.py` (sharing), `documents.py`, `admin.py`, `access_requests.py`, `audit.py`, `storage.py`, `models.py`, `database.py`, `security.py`.

## API Documentation

The backend is FastAPI, so interactive documentation is generated automatically:

| Resource | Local | Deployed |
|----------|-------|----------|
| Swagger UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | `<BACKEND_DEPLOYMENT_URL>/docs` |
| OpenAPI schema | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) | `<BACKEND_DEPLOYMENT_URL>/openapi.json` |

**How to use it:** start the backend, open `/docs`, call `POST /auth/login`, copy the `access_token` from the response, click **Authorize**, paste the token, and try the protected endpoints.

**Authentication:** protected endpoints require the header `Authorization: Bearer <access_token>`. Tokens expire after 30 minutes.

### Public

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| GET | `/` | Welcome message and status | None |
| GET | `/health` | Health check | None |

### Authentication and account

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| POST | `/auth/signup` | Register an account (name, email, password ≥ 8 chars); always creates a Viewer | None |
| POST | `/auth/login` | Log in with email and password; returns a JWT and user info | None |
| GET | `/auth/me` | Get the current user | Any signed-in user |
| PATCH | `/auth/profile` | Update own display name | Any signed-in user |
| DELETE | `/auth/account` | Delete own account; revokes active shares, keeps audit identity | Any signed-in user except Admin |
| GET | `/auth/owner-access-request` | Get own latest Owner-access request | Viewer or Owner |
| POST | `/auth/owner-access-request` | Request Owner access | Viewer |

### Documents

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| POST | `/documents/upload` | Upload a file (multipart field `file`, max 20 MB) | Owner |
| POST | `/documents` | Create a document metadata record (JSON; no file) | Owner |
| GET | `/documents` | List the caller's own documents | Owner |
| GET | `/documents/{document_id}/file` | View a document inline | Owner of the document, or a Viewer/Owner with an active share |
| GET | `/documents/{document_id}/download` | Download a document as an attachment | Owner of the document, or a Viewer/Owner with an active share that allows download |
| DELETE | `/documents/{document_id}` | Delete a document and revoke its shares | Owner (own documents) |

### Sharing

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| POST | `/documents/{document_id}/share` | Share with a registered user. Body: `recipient_name`, `recipient_email`, `expires_at`, `can_download` (default `false`) | Owner (own documents) |
| GET | `/shared-with-me` | List documents shared with the caller | Any signed-in user (the API returns data for the caller only) |
| GET | `/owner/shares` | List shares the Owner has created | Owner |
| DELETE | `/shares/{share_id}` | Revoke a share | Owner (own shares) |

### Audit logs

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| GET | `/owner/audit-logs` | Events by the Owner or on the Owner's documents | Owner |
| GET | `/admin/audit-logs` | All audit events | Admin |

### Admin

| Method | Endpoint | Purpose | Auth / Role |
|--------|----------|---------|-------------|
| GET | `/admin/users` | List users | Admin |
| PATCH | `/admin/users/{target_user_id}/role` | Change a user's role. Body: `{"role": "admin" \| "owner" \| "viewer"}` | Admin |
| PATCH | `/admin/users/{target_user_id}/active` | Activate or deactivate a user. Body: `{"active": true \| false}` | Admin |
| DELETE | `/admin/users/{target_user_id}` | Delete a user account (Admin accounts cannot be deleted) | Admin |
| GET | `/admin/document-count` | Count of active documents | Admin |
| GET | `/admin/owner-access-requests` | List pending Owner-access requests | Admin |
| PATCH | `/admin/owner-access-requests/{request_id}` | Review a request. Body: `{"decision": "approve" \| "reject"}` | Admin |

## Security Features

These are the protections present in the code. This is a hackathon project: it has not had an independent security review, and this list is not a guarantee of security.

- **Server-side authorization** on every protected route. The role and active status are read from the database for each request.
- **Password hashing** with Argon2 (`pwdlib`); minimum 8 characters at signup, 12 for the bootstrap Admin.
- **Signed JWTs** (HS256) with 30-minute expiry. The server refuses to start if `TRUSTVAULT_JWT_SECRET` is missing or shorter than 32 characters.
- **Signup cannot choose a role.** New accounts are Viewers; Admin roles are granted only by an Admin. The last active Admin is protected from demotion or deactivation.
- **Private storage:** files are fetched only by the backend using a server-side service key, with `X-Content-Type-Options: nosniff` on file responses.
- **Scoped sharing:** access requires an active, unexpired, unrevoked share tied to that user and document. Shares are single-use, and the "consume" step is an atomic database update.
- **Audit trail:** events are chained by SHA-256 hashes, with serialised writes on PostgreSQL. Denied access attempts are recorded. `verify_audit_chain()` in `backend/app/audit.py` checks the chain, but it is currently exercised by the tests and is **not exposed through an API endpoint**.
- **Upload limits:** 20 MB maximum, empty files rejected, filename path components stripped.
- **Audit retention on deletion:** deleting documents or accounts keeps the records needed for audit history.

**Known limitations (from the code):**

- The audit chain uses plain SHA-256 (no secret key). Someone with direct database write access could recompute a consistent chain, and no database-level append-only protection was found.
- No request rate limiting was found in the application.
- Access tokens are not revoked at logout; they remain valid until they expire (the account's active status is still checked on each request).
- Uploaded file types are taken from the client-supplied content type; no file-type validation was found.
- Sharing and "shared with me" are in-app only: no emails or share links are sent (see [Future Enhancements](#future-enhancements)).
- `THREATS.md` in the repository contains a more detailed threat discussion.

## Installation and Setup

### Prerequisites

- [Node.js](https://nodejs.org/) 20.19+ or 22.12+ (with npm)
- [Python](https://www.python.org/downloads/) 3.10+
- A PostgreSQL database (for example, a Supabase project)
- A **private** Supabase Storage bucket named exactly `trustvault-documents`
- The Supabase project URL and its service-role key

### 1. Clone the repository

```bash
git clone <GITHUB_REPOSITORY_URL>
cd TrustVault
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

### 3. Backend environment variables

Create a file named `backend/.env` (it is git-ignored; never commit it). The repository's `.env.example` only contains a comment, so use this template and replace every value:

```env
DATABASE_URL=<postgresql connection string, e.g. postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME>
TRUSTVAULT_JWT_SECRET=<random string, at least 32 characters>
SUPABASE_URL=<your Supabase project URL>
SUPABASE_SERVICE_ROLE_KEY=<your Supabase service-role key>

# Used only by the one-time bootstrap Admin script
TRUSTVAULT_BOOTSTRAP_ADMIN_NAME=<admin display name>
TRUSTVAULT_BOOTSTRAP_ADMIN_EMAIL=<admin email>
TRUSTVAULT_BOOTSTRAP_ADMIN_PASSWORD=<at least 12 characters>
```

Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Keep `TRUSTVAULT_CREATE_TEST_OWNER` unset or `false`. Setting it to `true` creates a development account (`owner@test.com`) with a known password.
> The service-role key has full access to your Supabase project. Keep it on the server only.

### 4. Database setup

From the `backend` folder, with the virtual environment active:

```bash
python -m app.create_tables
python -m app.bootstrap_admin
```

- `create_tables` creates the tables from the SQLAlchemy models.
- `bootstrap_admin` creates the first Admin from the `TRUSTVAULT_BOOTSTRAP_ADMIN_*` variables.
- The SQL files in `backend/migrations/` (`001` to `005`) are for upgrading an **existing** database created before those changes. Run them in numeric order in the Supabase SQL editor if needed. For a fresh database, the repository README states the migrations are idempotent, but this was not tested against a live database.

### 5. Frontend setup

```bash
cd ../frontend
npm install
```

No frontend `.env` file is needed for local development: the Vite dev server proxies `/api` to `http://127.0.0.1:8000`. If the backend runs elsewhere, create `frontend/.env.local`:

```env
TRUSTVAULT_API_PROXY_TARGET=http://127.0.0.1:8001
```

## Running the Application

Start the backend (from `backend/`, virtual environment active):

```bash
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

Start the frontend in a second terminal (from `frontend/`):

```bash
npm run dev
```

Open the URL Vite prints (normally http://localhost:5173, which is the origin allowed by the backend CORS settings). Other frontend commands: `npm run lint`, `npm run build`, `npm run preview`.

## Running Tests

The backend has a pytest suite in `backend/tests/` (authentication, roles, documents, sharing, audit, admin and routes). It uses an in-memory SQLite database, so it needs no PostgreSQL or Supabase credentials; storage is replaced with a test double in route tests.

```bash
cd backend
python -m pytest tests -q
```

At the time this README was written, the suite was run on a fresh install and reported **70 passed, 1 skipped**. No frontend test suite exists; `npm run lint` is the only frontend check configured.

## Deployment

| Item | Link |
|------|------|
| **Live Frontend** | `sakala-meenakshi-trustvault.vercel.app` |
| **Backend API** | `trustvault-backend-api.vercel.app` |
| **Interactive API Documentation** | `trustvault-backend-api.vercel.app/docs` |
| **GitHub Repository** | `https://github.com/SMeenakshi28/TrustVault-secure-document-sharing-with-a-real-audit-trail` |

Both the frontend and backend are intended to be deployed as separate Vercel projects. Configuration found in the repository:

- **Backend:** `backend/vercel.json` builds `app/main.py` with `@vercel/python` and routes all paths to it. Set the Vercel project's **Root Directory** to `backend`.
- **Frontend:** there is no `vercel.json`. Vercel's standard Vite settings apply (root directory `frontend`, build command `npm run build`, output directory `dist`).

**Backend environment variables** (Vercel project settings): `DATABASE_URL`, `TRUSTVAULT_JWT_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`. Do not set `TRUSTVAULT_CREATE_TEST_OWNER` to `true`. Run the database setup commands above against the production database once to create the tables and the first Admin.

**Frontend environment variable:** set `VITE_API_BASE_URL` to the deployed backend URL (no trailing slash) **before building**. If it is unset, the app calls `/api` on its own domain, which does not exist on a static Vercel deployment (the `/api` proxy works only in the Vite dev server).

**CORS:** allowed origins are hard-coded in `backend/app/main.py` (`http://localhost:5173`, `http://127.0.0.1:5173` and one `*.vercel.app` frontend address). If your deployed frontend URL differs, add it to `allow_origins` and redeploy the backend.

**Database and storage:** use a PostgreSQL instance reachable from Vercel and a private `trustvault-documents` bucket in Supabase.

> **Not verified:** configuration files alone do not prove a working deployment. Confirm the live frontend, `<BACKEND_DEPLOYMENT_URL>/health`, login, and a full upload → share → view flow after deploying. Also confirm that uploads near the 20 MB limit work, since Vercel serverless functions have their own request-size limits.

## Future Enhancements

The following are **planned and not implemented** in the current code.

**A. Email verification**
- Send a verification email to newly registered users.
- Require the email to be verified before the account can be used, following the intended authentication flow.

**B. Forgot / reset password**
- Let users request a password reset by email.
- Use a secure, time-limited reset mechanism.

**C. Email-based secure document sharing**
- When an Owner shares a document, generate a unique share link and a separate secret code and email both to the recipient.
- Require the secret code before the link grants access. The code must never appear in the URL.
- Tie each link to its document and permissions, support configured expiry, and allow the Owner to revoke it.
- Record relevant access attempts and actions in the audit trail.
- Consider hashed storage of codes, code expiry, rate limiting and attempt validation.

## Project Type

Solo Project

## Author

**Sakala Meenakshi**
