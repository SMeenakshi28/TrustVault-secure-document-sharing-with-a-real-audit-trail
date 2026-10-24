ALTER TABLE public.sharing_permissions
ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMPTZ NULL;
