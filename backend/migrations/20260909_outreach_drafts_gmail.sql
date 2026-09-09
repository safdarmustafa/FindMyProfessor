-- Phase 6: Persistent outreach drafts and Gmail OAuth connections
-- Run this migration against your Supabase database before deploying Phase 6.
--
-- Tables created:
--   outreach_drafts      — persistent email drafts (replaces Phase 5 in-memory store)
--   gmail_connections    — per-user Gmail OAuth credentials (encrypted tokens)

-- ─────────────────────────────────────────────────────────────────────────────
-- outreach_drafts
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outreach_drafts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    professor_id            UUID NOT NULL,
    email_type              TEXT NOT NULL DEFAULT 'research',
    subject                 TEXT NOT NULL DEFAULT '',
    body                    TEXT NOT NULL DEFAULT '',
    selected_opportunity_id UUID REFERENCES opportunities(id) ON DELETE SET NULL,
    cv_version_id           UUID REFERENCES cv_versions(id) ON DELETE SET NULL,
    matched_research_areas  JSONB NOT NULL DEFAULT '[]',
    evidence_used           JSONB NOT NULL DEFAULT '[]',
    generation_provider     TEXT NOT NULL DEFAULT 'deterministic',
    -- status values: generated | edited | ready | sending | sent | failed
    status                  TEXT NOT NULL DEFAULT 'generated',
    sent_at                 TIMESTAMPTZ,
    gmail_message_id        TEXT,
    gmail_thread_id         TEXT,
    error_code              TEXT,
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index to efficiently list drafts for a profile
CREATE INDEX IF NOT EXISTS idx_outreach_drafts_profile_id
    ON outreach_drafts(profile_id);

-- Index for history queries (latest first)
CREATE INDEX IF NOT EXISTS idx_outreach_drafts_profile_created
    ON outreach_drafts(profile_id, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- gmail_connections
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gmail_connections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    -- provider is always 'google' for now; reserved for future expansion
    provider                TEXT NOT NULL DEFAULT 'google',
    -- safe public info — never contains tokens
    provider_account_email  TEXT,
    -- tokens stored encrypted using GOOGLE_TOKEN_ENCRYPTION_KEY (Fernet)
    access_token_encrypted  TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at        TIMESTAMPTZ,
    scopes                  TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at              TIMESTAMPTZ,
    -- one active Gmail connection per profile
    UNIQUE(profile_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_gmail_connections_profile_id
    ON gmail_connections(profile_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- NOTE: Row-Level Security
-- If your Supabase project has RLS enabled, add appropriate policies here.
-- With the current service-role key access used in this application, the
-- server enforces profile isolation at the application layer (profile_id checks).
-- ─────────────────────────────────────────────────────────────────────────────
