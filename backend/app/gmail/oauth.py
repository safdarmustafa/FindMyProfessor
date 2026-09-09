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
import time
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server-side OAuth state store
# Maps state_token → {profile_id, expires_at}
# Lost on restart — acceptable for a 10-minute OAuth window.
# ---------------------------------------------------------------------------
_state_store: dict[str, dict[str, Any]] = {}

_STATE_TTL_SECONDS = 600  # 10 minutes

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


def create_state(profile_id: str) -> str:
    """Create a cryptographically random state token bound to a profile_id."""
    token = secrets.token_urlsafe(32)
    _state_store[token] = {
        "profile_id": profile_id,
        "expires_at": time.monotonic() + _STATE_TTL_SECONDS,
    }
    return token


def consume_state(token: str) -> str | None:
    """
    Verify and consume a state token.
    Returns the bound profile_id, or None if invalid/expired.
    Consumed tokens cannot be reused.
    """
    _expire_old_states()
    entry = _state_store.pop(token, None)
    if not entry:
        logger.warning("OAuth state token not found.")
        return None
    if time.monotonic() > entry["expires_at"]:
        logger.warning("OAuth state token expired.")
        return None
    return entry["profile_id"]


def _expire_old_states() -> None:
    now = time.monotonic()
    expired = [k for k, v in _state_store.items() if now > v["expires_at"]]
    for k in expired:
        del _state_store[k]


def authorization_url(profile_id: str) -> str:
    """Build the Google authorization URL for the OAuth flow."""
    state = create_state(profile_id)
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
