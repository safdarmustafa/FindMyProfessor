-- Production hardening: link profiles to their real Supabase-authenticated
-- user, without breaking existing profiles.
--
-- BACKGROUND:
-- profiles.id already equals an auth.users.id today — but for a profile
-- created via the CV-upload-before-login path, that auth.users row is a
-- synthetic one fabricated by cv_service._provision_auth_user(), NOT the
-- real Google-authenticated user. There is currently no way to tell "this
-- profile really belongs to the person who is now signed in with Google"
-- from "this profile_id is just whatever a client happened to send us" —
-- that is the X-Profile-Id trust problem.
--
-- linked_user_id is a SEPARATE column (not profiles.id itself) specifically
-- so that an EXISTING profile (under its old, possibly-synthetic id) can be
-- claimed by a real authenticated user without migrating its primary key —
-- which would cascade through cv_versions, outreach_drafts,
-- gmail_connections, etc. The backend claims it automatically, exactly
-- once, the first time that authenticated user makes a request presenting
-- both a valid Supabase session and their existing X-Profile-Id (see
-- app/auth.py resolve_profile_id). No manual data migration is required or
-- performed by this migration — it only adds the column.

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS linked_user_id UUID REFERENCES auth.users(id);

-- A given Supabase user may only ever be linked to one profile.
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_linked_user_id
    ON profiles(linked_user_id)
    WHERE linked_user_id IS NOT NULL;
