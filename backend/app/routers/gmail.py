from __future__ import annotations

"""
Gmail OAuth endpoints.

GET  /gmail/connect       — start OAuth flow (redirect to Google)
GET  /gmail/callback      — handle OAuth callback, store tokens, redirect to compose
GET  /gmail/status        — safe connection status (no tokens)
POST /gmail/disconnect    — revoke + remove stored connection
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse

from app import auth
from app.gmail import oauth as gmail_oauth
from app.gmail import service as gmail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])

SCOPES_STRING = gmail_oauth.GMAIL_SEND_SCOPE


def _is_hosted_environment() -> bool:
    """
    True when this process is running on a real hosting platform, not a
    developer's own machine — WITHOUT depending on anyone having remembered
    to set ENVIRONMENT=production themselves.

    Bug found live in production: every new user's first Gmail connect
    succeeded (the token exchange completed and the connection was saved),
    but the final post-callback redirect landed on http://localhost:5173,
    which doesn't exist on the user's device ("no internet"). Root cause:
    FRONTEND_URL was not set on Render, and ENVIRONMENT was never set to
    "production" either, so the old guard below (gated only on
    ENVIRONMENT=="production") never triggered and silently returned the
    localhost fallback instead of failing loudly. Render (like most hosts)
    injects its own RENDER=true into every deployed service's environment
    automatically — checking that too means this can't silently recur just
    because ENVIRONMENT was left unset.
    """
    if os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod"):
        return True
    return os.getenv("RENDER", "").strip().lower() in ("true", "1")


def _frontend_url() -> str:
    """
    React frontend base URL — override with the FRONTEND_URL env var.
    All post-OAuth browser redirects must land on the React SPA, not FastAPI.

    On a real hosted deployment this must never silently fall back to
    localhost: if FRONTEND_URL is unset there, fail loudly instead of
    redirecting a real user's browser to a URL that doesn't exist for them.
    """
    value = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if value:
        return value
    if _is_hosted_environment():
        raise RuntimeError(
            "FRONTEND_URL environment variable is not set in this hosted "
            "environment. Refusing to fall back to a localhost redirect."
        )
    return "http://localhost:5173"


def _sanitize_return_to(return_to: str | None) -> str | None:
    """
    Only allow a same-app relative path (e.g. /outreach/compose/<id>) to be
    carried through the OAuth round trip. Rejects absolute URLs and
    protocol-relative paths ("//host/...") to prevent open-redirect abuse.
    """
    if not return_to:
        return None
    if not return_to.startswith("/") or return_to.startswith("//"):
        return None
    if "://" in return_to:
        return None
    return return_to


# ---------------------------------------------------------------------------
# GET /gmail/connect
# ---------------------------------------------------------------------------

@router.get("/connect")
def gmail_connect(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
    profile_id: str | None = Query(default=None),
    return_to: str | None = Query(default=None),
):
    """
    Redirect the user to Google's OAuth consent page.

    The profile_id may be passed as a query parameter (for browser navigation)
    or as the X-Profile-Id header. The state token binds the OAuth flow to the
    profile server-side, and — if provided — the originating frontend path
    the browser should return to once the callback completes.

    NOTE ON OWNERSHIP: this endpoint is reached via a full-page browser
    navigation (window.location.href), which cannot carry a custom
    Authorization header — there is no way to verify a Supabase session
    here the way auth.require_profile_id does elsewhere. The worst case of
    trusting the given profile_id is that a Gmail account ends up attached
    to the wrong (but still server-verified-to-exist, via ensure_profile
    downstream) profile — it does not expose another profile's private data,
    since nothing is read here. Closing this fully would require passing a
    short-lived signed token instead of a bare profile_id in the query
    string; flagged as a follow-up, not done here to keep this change
    surgical.
    """
    pid = x_profile_id or profile_id
    if not pid:
        raise HTTPException(
            status_code=400,
            detail="profile_id query parameter or X-Profile-Id header is required.",
        )
    try:
        url = gmail_oauth.authorization_url(pid, _sanitize_return_to(return_to))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RedirectResponse(url=url, status_code=302)


# ---------------------------------------------------------------------------
# GET /gmail/callback
# ---------------------------------------------------------------------------

@router.get("/callback")
def gmail_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """
    Handle the OAuth callback from Google.

    - Validates the state token (CSRF protection).
    - Exchanges the authorization code for tokens.
    - Stores encrypted tokens in the database.
    - Redirects to the draft compose flow, preserving the originating page
      (carried through the state token, not just localStorage) when one was
      provided to /gmail/connect.
    """
    try:
        frontend_url = _frontend_url()
    except RuntimeError as exc:
        logger.error("Cannot complete OAuth callback: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if error:
        logger.info("OAuth callback received error.")
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=denied",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=missing_params",
            status_code=302,
        )

    consumed = gmail_oauth.consume_state(state)
    if not consumed:
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=invalid_state",
            status_code=302,
        )
    profile_id = consumed["profile_id"]
    return_to = consumed.get("return_to")

    try:
        token_response = gmail_oauth.exchange_code(code)
    except Exception:
        logger.warning("OAuth code exchange failed.")
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=exchange_failed",
            status_code=302,
        )

    access_token = token_response.get("access_token", "")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)

    if not access_token:
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=no_token",
            status_code=302,
        )

    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    # Fetch the account email
    provider_email = gmail_oauth.get_token_email(access_token)

    try:
        gmail_service.upsert_connection(
            profile_id=profile_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            provider_account_email=provider_email,
            scopes=SCOPES_STRING,
        )
    except Exception:
        logger.error("Failed to store Gmail connection.")
        return RedirectResponse(
            url=f"{frontend_url}/outreach/gmail-callback-error?reason=store_failed",
            status_code=302,
        )

    destination = f"{frontend_url}/outreach/gmail-connected"
    if return_to:
        destination += f"?return_to={quote(return_to, safe='')}"
    return RedirectResponse(url=destination, status_code=302)


# ---------------------------------------------------------------------------
# GET /gmail/status
# ---------------------------------------------------------------------------

@router.get("/status")
def gmail_status(
    profile_id: str = Depends(auth.require_profile_id),
):
    """Return safe connection status. Never returns tokens."""
    status = gmail_service.get_status(profile_id)
    return {"connected": status.connected, "email": status.email, "needs_reconnect": getattr(status, "needs_reconnect", False)}


# ---------------------------------------------------------------------------
# POST /gmail/disconnect
# ---------------------------------------------------------------------------

@router.post("/disconnect")
def gmail_disconnect(
    profile_id: str = Depends(auth.require_profile_id),
):
    """
    Disconnect Gmail.
    - Revokes token with Google (best-effort).
    - Clears stored tokens.
    - Preserves historical sent draft records.
    """
    gmail_service.disconnect(profile_id)
    return {"disconnected": True, "message": "Gmail disconnected."}
