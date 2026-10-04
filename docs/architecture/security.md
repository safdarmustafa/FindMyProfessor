# Security

> Part of the [FindMyProfessor Architecture Documentation](../ARCHITECTURE.md). This section only states what is actually implemented, verified against code — no invented vulnerabilities, no hidden mitigations.

## 1. Mechanisms actually implemented

| Mechanism | Where | What it does |
|---|---|---|
| Supabase JWT verification | `backend/app/auth.py:53-73` | `supabase.auth.get_user(token)` — a real round-trip check against Supabase's Auth server, not a locally-decoded/unverified JWT |
| Profile-ownership enforcement once authenticated | `backend/app/auth.py:156-196` | Once a valid session is presented, `X-Profile-Id` can never reach a different account's profile — mismatch is a hard 403 |
| Explicit CORS allow-list | `backend/app/main.py:22-57` | No wildcard origin; specific origins only, because auth here is header-based (not cookie-based), so a wildcard + credentials would let any site's JS probe the API |
| OAuth CSRF state | `backend/app/gmail/oauth.py` | `secrets.token_urlsafe(32)`, 10-minute TTL, single-use via delete-on-consume, persisted in a real table (survives restarts/multi-worker) |
| Gmail token encryption at rest | `backend/app/gmail/crypto.py` | Fernet, keyed by `GOOGLE_TOKEN_ENCRYPTION_KEY`, hard-required in a declared-production environment |
| Minimal OAuth scope | `backend/app/gmail/oauth.py:64` | Exactly `gmail.send` — no read access, no broader Gmail/Google account access requested |
| Explicit send confirmation | `backend/app/schemas/outreach.py:79-81`, `service.py:263-267` | `confirmed: bool` is a required field, re-checked in code, not just enforced by the UI |
| Atomic send transition | `backend/app/outreach/db_store.py:180-201` | Conditional `UPDATE ... WHERE status='ready'` prevents double-send races |
| No bulk sending, no automation | Confirmed by repo-wide search for scheduler/cron patterns (none found) | Every email send is one explicit, synchronous, human-confirmed HTTP request |
| CV file-type validation via content sniffing | `backend/app/cv/validation.py:96-126` | Magic-byte inspection, not just trusting the extension or declared `Content-Type` |
| CV path-traversal protection | `backend/app/cv/storage.py:68-77` | `resolve_storage_path()` guards against a crafted filename escaping the storage root |
| CV file path never exposed to clients | `backend/app/services/cv.py:256-257` (`public_cv`, strips `_`-prefixed internal keys) | Send-time CV retrieval is resolved server-side from a `cv_version_id`, never from a client-supplied path |
| Safe, generic error messages | `backend/app/services/query.py:9-30` | Real Postgrest error codes/messages/hints are logged server-side only, never returned to the client |
| Search-term sanitization | `backend/app/services/professors.py:199-206` | Strips characters that have special meaning in Postgrest `ilike`/`or_` filter syntax before building a query from user input |

## 2. Known security gaps / production hardening — only what the code shows

**These are not hypothetical — each one is grounded in a specific code location, and several are explicitly self-documented by the codebase's own comments.**

1. **`X-Profile-Id` is still trusted at face value when no `Authorization` header is present at all.** This is the headline gap, and `backend/app/auth.py:29-32` says so directly: *"a caller presenting no Authorization header at all is still trusted on X-Profile-Id alone."* The hardening added in `auth.py` only protects a caller who *does* present a Supabase session; any client that simply omits the header (a script, a direct API call, a stale frontend build) still gets the pre-hardening behavior.
2. **Authorization has no database-level backstop.** The backend connects with the Supabase service-role key, which bypasses Row-Level Security entirely (`backend/app/supabase_client.py:14`). Every isolation guarantee (`profile_id` filtering) is enforced purely in application code — see [Data Model §5](data-model.md#5-row-level-security--explicitly-not-used). A single missed `profile_id` filter in a new endpoint would have no safety net underneath it.
3. **Gmail token-encryption production guard checks only `ENVIRONMENT`, not `RENDER`** — while a different, adjacent guard in the same feature area (`backend/app/routers/gmail.py:49-51`) explicitly checks `RENDER` too, specifically because `ENVIRONMENT` was once left unset on a real Render deployment. `crypto.py` was not updated to match. See [Gmail OAuth §7](gmail-oauth.md#7-token-encryption).
4. **CV file storage defaults to local disk**, which the code's own comment (`backend/app/cv/storage.py:11-22`) calls unsafe on Render's ephemeral filesystem — and the escape hatch (`SUPABASE_CV_BUCKET`) is unset in every `.env` file present in this repo. See [Deployment §5](deployment.md#5-cv-storage-local-disk-by-default-flagged-unsafe-by-the-code-itself).
5. **No virus/malware scanning of uploaded CV files.**
6. **`outreach_drafts.status` has no database `CHECK` constraint** — the enum is enforced only in application code (`backend/migrations/20260909_outreach_drafts_gmail.sql:23-24`, comment-only). `save_draft()` also has no state-machine guard (`backend/app/outreach/service.py:117-140`) — it will write any status value a caller sends, including jumping a fresh draft directly to `"sent"` via a raw `PATCH`. See [Email Generation §1](email-generation.md#1-draft-lifecycle--state-machine).
7. **`outreach_drafts.professor_id` has no foreign-key constraint** to the `professors` table (`20260909_outreach_drafts_gmail.sql:14`) — the database will not stop a draft from referencing a nonexistent professor id; only application code checks this.
8. **No rate limiting was found anywhere in the codebase** — no middleware, no per-IP or per-profile throttling on any endpoint, including CV upload, matching queries, or email generation/send. **NOT VERIFIED FROM CURRENT CODEBASE as an intentional omission or a hosting-platform-level mitigation outside the repo (e.g. Render's own infra); only that no application-level rate limiting exists in this code.**
9. **Anti-fabrication in AI-generated emails is preventative only, not verified.** The LLM email-generation path restricts what data it's given and instructs it not to fabricate, but there is no post-generation check that the output actually matches the supplied evidence. See [Email Generation §6](email-generation.md#6-anti-hallucination--anti-fabrication-measures--the-honest-picture).
10. **`profiles.linked_user_id` — the column the current auth hardening depends on — was, at least at one point during development, not yet applied to the live production database**, discovered while diagnosing a real bug (per a test-file comment: *"confirmed by direct introspection of the live database while diagnosing the CV selection 'Database query failed' bug,"* `backend/tests/test_auth.py:118-124`). The code degrades gracefully when this column is missing (`app/auth.py`'s `is_missing_column_error` handling), but whether the migration has since been applied to the current live database is **NOT VERIFIABLE from this repository alone** — it would need to be confirmed against the actual Supabase project.

## 3. What this adds up to

The system's security model is best summarized honestly as: **real, server-verified authentication when a client sends a session token, graceful-but-permissive fallback when it doesn't; authorization enforced entirely in application code with no database backstop; and a small number of specific, self-documented gaps that the codebase's own comments already flag as known trade-offs rather than accidental oversights.** That combination — genuine hardening work visible in the commit history, paired with candid comments about what's still incomplete — is a more accurate and more defensible story to tell a supervisor or interviewer than either "it's fully secure" or "it's insecure": it's a system in the middle of a deliberate, incremental hardening effort, with the exact remaining gap named in its own source code.
