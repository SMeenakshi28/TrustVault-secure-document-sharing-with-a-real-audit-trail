-- Preserve document rows referenced by the audit history.
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- Ensure existing accounts have a recognized role.
UPDATE public.users
SET role = 'viewer'
WHERE role IS NULL
   OR role NOT IN ('admin', 'owner', 'viewer');

ALTER TABLE public.users
ALTER COLUMN role SET DEFAULT 'viewer';

ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;