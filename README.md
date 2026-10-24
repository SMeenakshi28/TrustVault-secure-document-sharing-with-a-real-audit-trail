# TrustVault

TrustVault is a React/Vite frontend with a FastAPI backend, PostgreSQL metadata,
Supabase Storage, and an append-only hash-chained audit log.

## Requirements

- Node.js `20.19+` or `22.12+` (or a later compatible release), and npm.
- Python 3.10+ and the Windows Python launcher `py`.
- A PostgreSQL database and a private Supabase Storage bucket named
  `trustvault-documents`.

## Frontend (PowerShell)

```powershell
Set-Location C:\Users\meeku\Desktop\TrustVault\frontend
npm install
npm run dev
```

For checks and a production bundle:

```powershell
npm run lint
npm run build
```

## Backend (PowerShell)

```powershell
Set-Location C:\Users\meeku\Desktop\TrustVault\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `backend\.env` with the database URL, a random JWT secret of at least 32
characters, the Supabase project URL, and its service-role key. Do not commit
`.env`. You can generate a secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create missing tables, then apply the SQL files in `backend\migrations` in
numeric order through the Supabase SQL editor when upgrading an existing
database. For a new database, table creation uses the current SQLAlchemy models;
the migrations are idempotent. Create the initial administrator only after
setting its three `TRUSTVAULT_BOOTSTRAP_ADMIN_*` variables:

```powershell
python -m app.create_tables
python -m app.bootstrap_admin
python -m uvicorn app.main:app --reload
```

Keep `TRUSTVAULT_CREATE_TEST_OWNER=false`; enabling it creates a development
account with a known password. During development the frontend sends API requests through the same-origin
`/api` Vite proxy, which forwards to `http://127.0.0.1:8000` by default. If the
backend runs at a different address, set `TRUSTVAULT_API_PROXY_TARGET` in
`frontend\.env.local` (for example, `TRUSTVAULT_API_PROXY_TARGET=http://127.0.0.1:8001`)
and restart Vite. For a deployed frontend, configure `VITE_API_BASE_URL` to the
backend API base URL or route `/api` through the deployment's reverse proxy.

Admin account deletion is a reversible deactivation in TrustVault's public
`users` table. Documents, sharing history, and audit records remain; active
shares are revoked. This operation does not delete a Supabase Auth user.

Run backend tests from `backend` (they use an isolated in-memory SQLite
database, not the configured PostgreSQL database):

```powershell
python -m pytest -q
```
