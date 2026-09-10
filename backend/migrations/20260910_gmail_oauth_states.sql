-- Production hardening: persistent Gmail OAuth state.
-- Run this migration against your Supabase database before deploying.
--
-- Replaces the in-memory Python dict previously used for OAuth CSRF state
-- (app/gmail/oauth.py _state_store). An in-memory store does not survive a
-- Render restart/redeploy, and breaks entirely if the backend ever runs more
-- than one worker/instance — a request handled by one process cannot see
-- state created by another. This table makes state survive both.

CREATE TABLE IF NOT EXISTS gmail_oauth_states (
    token       TEXT PRIMARY KEY,
    profile_id  UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    return_to   TEXT,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Used both to clean up expired rows and to reject expired tokens quickly.
CREATE INDEX IF NOT EXISTS idx_gmail_oauth_states_expires_at
    ON gmail_oauth_states(expires_at);

-- No RLS policy is added: this table is only ever read/written by the
-- backend's service-role Supabase client, never queried directly by a
-- browser client.
