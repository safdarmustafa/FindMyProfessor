from __future__ import annotations

"""
Google OAuth 2.0 helpers for the per-user Gmail 'send' flow.

SECURITY NOTES:
- State tokens are cryptographically random and server-side only.
- The state token binds the OAuth callback to the profile that initiated it.
- State tokens expire after 10 minutes.
- client_secret and tokens are never returned to the browser.

LIMITATION:
The current application uses X-Profile-Id (a shared header, not a real
authenticated session). The OAuth state mechanism here does the best it can
without a proper session: state is stored server-side and the profile_id is
verified at callback time. A future phase should replace X-Profile-Id with
proper session authentication.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.query import execute
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server-side OAuth state store
#
# Persisted in the `gmail_oauth_states` table (see migrations/) instead of an
# in-memory dict. An in-memory store does not survive a Render restart or
# redeploy, and breaks entirely under more than one worker/instance, since a
# request handled by one process cannot see state created by another.
#
# TEST MODE: mirrors app/outreach/db_store.py's pattern — call clear() at the
# start of a test to activate an in-memory dict override and avoid needing a
# real database connection; call disable_test_mode() to revert.
# ---------------------------------------------------------------------------
TABLE = "gmail_oauth_states"

_test_store: dict[str, dict[str, Any]] | None = None

_STATE_TTL_SECONDS = 600  # 10 minutes


def clear() -> None:
    """Activate test mode and clear the in-memory override."""
    global _test_store
    _test_store = {}


def disable_test_mode() -> None:
    """Deactivate test mode and re-enable Supabase-backed storage."""
    global _test_store
    _test_store = None

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def _client_id() -> str:
    value = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not value:
        raise RuntimeError("GOOGLE_CLIENT_ID environment variable is not set.")
    return value


def _client_secret() -> str:
    value = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not value:
        raise RuntimeError("GOOGLE_CLIENT_SECRET environment variable is not set.")
    return value


def _redirect_uri() -> str:
    value = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if not value:
        raise RuntimeError("GOOGLE_REDIRECT_URI environment variable is not set.")
    return value


def create_state(profile_id: str, return_to: str | None = None) -> str:
    """
    Create a cryptographically random state token bound to a profile_id and,
    optionally, the frontend path the browser should return to once the
    OAuth round trip completes. Persisted so the token survives a restart
    and is visible across worker processes/instances.
    """
    _expire_old_states()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL_SECONDS)

    if _test_store is not None:
        _test_store[token] = {
            "profile_id": profile_id,
            "return_to": return_to,
            "expires_at": expires_at,
        }
        return token

    execute(
        supabase.table(TABLE).insert({
            "token": token,
            "profile_id": profile_id,
            "return_to": return_to,
            "expires_at": expires_at.isoformat(),
        })
    )
    return token


def consume_state(token: str) -> dict[str, Any] | None:
    """
    Verify and consume a state token.
    Returns {"profile_id": str, "return_to": str | None}, or None if
    invalid/expired. Consumed tokens cannot be reused — the row is deleted
    as part of consuming it, so a concurrent/repeat consume of the same
    token can never succeed twice.
    """
    now = datetime.now(timezone.utc)

    if _test_store is not None:
        entry = _test_store.pop(token, None)
        if not entry:
            logger.warning("OAuth state token not found.")
            return None
        if now > entry["expires_at"]:
            logger.warning("OAuth state token expired.")
            return None
        return {"profile_id": entry["profile_id"], "return_to": entry.get("return_to")}

    rows = execute(
        supabase.table(TABLE).select("*").eq("token", token).limit(1)
    ).data or []
    if not rows:
        logger.warning("OAuth state token not found.")
        return None
    entry = rows[0]

    # Delete immediately on read — this is what makes the token single-use
    # even if two requests race to consume it at the same instant: only the
    # request whose delete actually removes a row may proceed.
    deleted = execute(
        supabase.table(TABLE).delete().eq("token", token)
    ).data or []
    if not deleted:
        logger.warning("OAuth state token already consumed.")
        return None

    expires_at = entry.get("expires_at")
    try:
        expires_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        expires_dt = None
    if expires_dt is None or now > expires_dt:
        logger.warning("OAuth state token expired.")
        return None

    return {"profile_id": entry["profile_id"], "return_to": entry.get("return_to")}


def _expire_old_states() -> None:
    """Best-effort cleanup of stale rows. Not required for correctness —
    consume_state already rejects expired tokens on read — but keeps the
    table from growing unboundedly with abandoned OAuth attempts."""
    now = datetime.now(timezone.utc)
    if _test_store is not None:
        expired = [k for k, v in _test_store.items() if now > v["expires_at"]]
        for k in expired:
            del _test_store[k]
        return
    try:
        execute(supabase.table(TABLE).delete().lt("expires_at", now.isoformat()))
    except Exception:
        logger.warning("Could not clean up expired OAuth state rows.")


def authorization_url(profile_id: str, return_to: str | None = None) -> str:
    """Build the Google authorization URL for the OAuth flow."""
    state = create_state(profile_id, return_to)
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": GMAIL_SEND_SCOPE,
        "access_type": "offline",
        "prompt": "consent",   # force refresh_token to be returned
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    """
    Exchange an authorization code for access + refresh tokens.
    Returns the raw token response dict.
    Raises an exception on failure.
    NEVER logs the token response.
    """
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """
    Use a refresh token to obtain a new access token.
    Returns the raw token response dict (access_token, expires_in).
    NEVER logs the token response.
    """
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def revoke_token(token: str) -> None:
    """
    Attempt to revoke a token with Google.
    Silently continues if Google returns an error (token may already be revoked).
    NEVER logs the token.
    """
    try:
        httpx.post(
            GOOGLE_REVOKE_URL,
            params={"token": token},
            timeout=10.0,
        )
    except Exception:
        logger.info("Token revocation request failed (may already be revoked).")


def get_token_email(access_token: str) -> str | None:
    """
    Fetch the Gmail account email associated with the access token.
    NEVER logs the access token or the Authorization header.

    Strategy (tried in order):

    1. Google tokeninfo endpoint — works with ANY valid Google access token,
       regardless of which OAuth scopes were granted.
       Passes the token as a query parameter (Google's documented introspection API).
       Returns 'email' field for user-account tokens.

    2. Google userinfo endpoint — fallback for flows that also include
       openid/email OIDC scopes alongside gmail.send.

    NOTE: Gmail API users.getProfile was intentionally removed because it
    requires gmail.readonly / gmail.compose / gmail.modify scopes. It returns
    403 with only gmail.send scope, making it useless for this flow.

    Returns None if both attempts fail (e.g., token expired/invalid).
    """
    # 1. Token introspection — scope-independent
    # Note: tokeninfo returns email only when the token was issued with email/openid
    # scope. With gmail.send only, the response omits the email field (HTTP 200 but
    # no 'email' key). This is expected; callers treat None email as normal.
    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": access_token},
            timeout=10.0,
        )
        if resp.is_success:
            email = resp.json().get("email")
            if email:
                return email
            logger.debug(
                "get_token_email: tokeninfo 200 but no email field (expected with gmail.send only scope)"
            )
        else:
            logger.debug("get_token_email: tokeninfo returned HTTP %s", resp.status_code)
    except Exception as exc:
        logger.debug("get_token_email: tokeninfo request failed: %s", type(exc).__name__)

    # 2. Userinfo fallback — only succeeds with openid/email scope
    try:
        resp = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        if resp.is_success:
            return resp.json().get("email")
        logger.debug("get_token_email: userinfo returned HTTP %s (expected 401 with gmail.send only)", resp.status_code)
    except Exception as exc:
        logger.debug("get_token_email: userinfo request failed: %s", type(exc).__name__)

    return None
