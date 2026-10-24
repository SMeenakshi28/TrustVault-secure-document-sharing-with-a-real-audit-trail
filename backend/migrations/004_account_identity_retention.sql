CREATE TABLE IF NOT EXISTS public.user_identities (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ NULL
);

INSERT INTO public.user_identities (id, name, email, created_at)
SELECT id, name, email, created_at
FROM public.users
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    email = EXCLUDED.email,
    created_at = EXCLUDED.created_at;

ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_logs_actor_id_fkey,
    ADD CONSTRAINT audit_logs_actor_id_fkey
        FOREIGN KEY (actor_id)
        REFERENCES public.user_identities (id);

ALTER TABLE public.documents
    DROP CONSTRAINT IF EXISTS documents_owner_id_fkey,
    ADD CONSTRAINT documents_owner_id_fkey
        FOREIGN KEY (owner_id)
        REFERENCES public.user_identities (id);

ALTER TABLE public.sharing_permissions
    DROP CONSTRAINT IF EXISTS sharing_permissions_owner_id_fkey,
    ADD CONSTRAINT sharing_permissions_owner_id_fkey
        FOREIGN KEY (owner_id)
        REFERENCES public.user_identities (id);

ALTER TABLE public.sharing_permissions
    DROP CONSTRAINT IF EXISTS sharing_permissions_viewer_id_fkey,
    ADD CONSTRAINT sharing_permissions_viewer_id_fkey
        FOREIGN KEY (viewer_id)
        REFERENCES public.user_identities (id);

CREATE OR REPLACE FUNCTION public.sync_user_identity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.user_identities (id, name, email, created_at)
    VALUES (NEW.id, NEW.name, NEW.email, NEW.created_at)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        email = EXCLUDED.email,
        created_at = EXCLUDED.created_at;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS users_sync_identity ON public.users;
CREATE TRIGGER users_sync_identity
AFTER INSERT OR UPDATE OF name, email, created_at ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.sync_user_identity();
