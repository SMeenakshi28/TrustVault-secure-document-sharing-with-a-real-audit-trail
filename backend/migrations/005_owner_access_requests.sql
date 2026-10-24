CREATE TABLE IF NOT EXISTS public.owner_access_requests (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL
        REFERENCES public.user_identities (id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by VARCHAR(36) NULL
        REFERENCES public.user_identities (id),
    reviewed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_owner_access_requests_user_id
    ON public.owner_access_requests (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_owner_access_request_pending_user
    ON public.owner_access_requests (user_id)
    WHERE status = 'pending';
