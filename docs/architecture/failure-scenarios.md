# Important Failure Scenarios

> Part of the [FindMyProfessor Architecture Documentation](../ARCHITECTURE.md). Each row traces: trigger → detection → fallback/response → user-visible result → database state.

## CV pipeline

| Trigger | Detection | Fallback | User-visible result | DB state |
|---|---|---|---|---|
| Unsupported file extension or content doesn't match extension | `cv/validation.py` magic-byte sniff | None — rejected before storage | HTTP 415 | No `cv_versions` row created |
| File over 10 MB or empty | `cv/validation.py:46-52` | None | HTTP 413/415 | No row created |
| Format valid but content corrupt (bad PDF body, encrypted PDF, empty text) | `try/except` in `services/cv.py:210-222` | File is still saved; extraction marked failed | HTTP 200, `parsing_status: "failed"`, generic message | `cv_versions` row created with `parsing_status="failed"` |
| LLM CV-extraction call fails (network/API error) | Broad `except Exception` in `upload_and_parse` | **No fallback to heuristic** — the whole extraction is marked failed | Same generic failure message as above; the real cause is only in server logs | `cv_versions` row created, `parsing_status="failed"` |
| Profile confirm attempted on a failed-parse CV | `confirm_profile()`, `services/cv.py:353-354` | Blocked outright | HTTP 400 with the stored parse-error message | No normalized `profiles`/`student_*` write happens |

## Matching

| Trigger | Detection | Fallback | User-visible result | DB state |
|---|---|---|---|---|
| Matching requested with no confirmed CV | `_confirmed_student()`, `services/matching.py:111-129` | None | HTTP 400 | N/A (read-only endpoint) |
| No professors clear `min_score`/filters | Scoring + filter pipeline naturally returns an empty list | None needed — this is a normal empty result, not an error | Frontend shows an empty-state ("no matches") | N/A |
| Opportunity mode requested but no professor has a usable non-closed opportunity | Filtered out in `services/matching.py` | Professor simply excluded from `opportunity`-mode results | Fewer or zero results in that mode specifically; unaffected in `research` mode | N/A |

## Email generation

| Trigger | Detection | Fallback | User-visible result | DB state |
|---|---|---|---|---|
| CV not confirmed/failed at generation time | `_confirmed_student()`, `outreach/service.py:506-523` | None | HTTP 400 | No draft created |
| Selected opportunity is `closed` | `_load_opportunity_context()`, `service.py:598-619` | None | HTTP 400 | No draft created |
| LLM email generation call fails | `try/except` inside `LlmEmailProvider.generate()`, `outreach/llm.py:117-142` | **Silently falls back to the deterministic template provider** | User sees a normal-looking generated draft — no error surfaced at all | Draft is created and stored with `generation_provider="deterministic"`, indistinguishable from the true no-LLM-configured default |
| Draft save (`store.put()`) fails | No explicit `try/except` around this call in `generate_draft()` | None identified — would surface as an unhandled exception | Likely a generic 500 (NOT VERIFIED whether a global FastAPI exception handler catches this) | Draft not persisted |

## Gmail OAuth

| Trigger | Detection | Fallback | User-visible result | DB state |
|---|---|---|---|---|
| User denies consent on Google's screen | Google redirects with `?error=` | None | Redirect to `/outreach/gmail-callback-error?reason=denied` | No row written to `gmail_connections` |
| OAuth state missing, already consumed, or expired (>10 min) | `consume_state()`, `gmail/oauth.py:121-168` | None — request rejected | Redirect with `?reason=invalid_state` | No connection written; the state row is already gone either way (deleted on first read attempt) |
| Token exchange with Google fails | `try/except` around the exchange call, `routers/gmail.py` | None | Redirect with `?reason=exchange_failed` | No connection written |
| Google returns no access token | Explicit check in the callback | None | Redirect with `?reason=no_token` | No connection written |
| Writing the connection to the DB fails | `try/except` around the `upsert_connection()` call | None | Redirect with `?reason=store_failed` | Tokens were successfully obtained from Google but never persisted — the user must reconnect |

## Gmail send

| Trigger | Detection | Fallback | User-visible result | DB state |
|---|---|---|---|---|
| Gmail access token expiring within 60s | `get_valid_access_token()`, `gmail/service.py:133-201` | Automatic refresh using the stored refresh token | None visible — transparent | `gmail_connections.token_expires_at`, `access_token_encrypted` updated |
| Refresh token rejected by Google (400/401 — revoked/invalid) | Same function | Connection marked unusable | HTTP 401, "please reconnect Gmail" | `gmail_connections.revoked_at` set; draft marked `status="failed"` via `_mark_failed()` |
| Gmail API `messages.send` returns 400/401/403 | `GmailApiError` wrapper, `gmail/client.py` | None — send attempt stops | Generic safe HTTP 502 (no raw Google error text leaked) | Draft marked `status="failed"` with extracted `error_code`/`error_message` |
| CV file missing from storage at send time | `read_cv_bytes()` raises | Send aborted | Error surfaced to user | Draft marked `failed` |
| Two send requests race for the same draft | `atomically_set_sending()` CAS, `outreach/db_store.py:180-201` | The losing request's conditional `UPDATE` affects 0 rows | HTTP 409 Conflict to the loser | Only the winner's transition to `sending` (then `sent`/`failed`) actually happens — the draft can never be double-sent |
| `confirmed` flag omitted or false | Pydantic required-field validation, then an explicit code re-check (`service.py:263-267`) | Send never starts | HTTP 400/422 | No status change — draft stays exactly as it was |

## General

- **No draft can ever get permanently stuck in `"sending"`.** Every failure branch in the send pipeline routes through `_mark_failed()`, which transitions the draft to a terminal `failed` state — the only two terminal outcomes of a send attempt are `sent` or `failed`.
- **No automatic retries exist anywhere** — a failed send, a failed generation, or a failed CV parse all require the user to take the next explicit action (re-upload, re-generate, retry send) themselves. There is no background job that revisits a failure.
