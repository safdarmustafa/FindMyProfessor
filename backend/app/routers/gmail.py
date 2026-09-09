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

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse

from app.gmail import oauth as gmail_oauth
from app.gmail import service as gmail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])

SCOPES_STRING = gmail_oauth.GMAIL_SEND_SCOPE


def _require_profile(x_profile_id: str | None) -> str:
    if not x_profile_id:
        raise HTTPException(
            status_code=400,
            detail="X-Profile-Id header is required.",
        )
    return x_profile_id


# ---------------------------------------------------------------------------
# GET /gmail/connect
# ---------------------------------------------------------------------------

@router.get("/connect")
def gmail_connect(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
    profile_id: str | None = Query(default=None),
):
    """
    Redirect the user to Google's OAuth consent page.

    The profile_id may be passed as a query parameter (for browser navigation)
    or as the X-Profile-Id header. The state token binds the OAuth flow to the
    profile server-side.
    """
    pid = x_profile_id or profile_id
    if not pid:
        raise HTTPException(
            status_code=400,
            detail="profile_id query parameter or X-Profile-Id header is required.",
        )
    try:
        url = gmail_oauth.authorization_url(pid)
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
    - Redirects to the draft compose flow.
    """
    if error:
        logger.info("OAuth callback received error.")
        return RedirectResponse(
            url="/outreach/gmail-callback-error?reason=denied",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url="/outreach/gmail-callback-error?reason=missing_params",
            status_code=302,
        )

    profile_id = gmail_oauth.consume_state(state)
    if not profile_id:
        return RedirectResponse(
            url="/outreach/gmail-callback-error?reason=invalid_state",
            status_code=302,
        )

    try:
        token_response = gmail_oauth.exchange_code(code)
    except Exception:
        logger.warning("OAuth code exchange failed.")
        return RedirectResponse(
            url="/outreach/gmail-callback-error?reason=exchange_failed",
            status_code=302,
        )

    access_token = token_response.get("access_token", "")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)

    if not access_token:
        return RedirectResponse(
            url="/outreach/gmail-callback-error?reason=no_token",
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
            url="/outreach/gmail-callback-error?reason=store_failed",
            status_code=302,
        )

    return RedirectResponse(url="/outreach/gmail-connected", status_code=302)


# ---------------------------------------------------------------------------
# GET /gmail/status
# ---------------------------------------------------------------------------

@router.get("/status")
def gmail_status(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    """Return safe connection status. Never returns tokens."""
    profile_id = _require_profile(x_profile_id)
    status = gmail_service.get_status(profile_id)
    return {"connected": status.connected, "email": status.email}


# ---------------------------------------------------------------------------
# POST /gmail/disconnect
# ---------------------------------------------------------------------------

@router.post("/disconnect")
def gmail_disconnect(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    """
    Disconnect Gmail.
    - Revokes token with Google (best-effort).
    - Clears stored tokens.
    - Preserves historical sent draft records.
    """
    profile_id = _require_profile(x_profile_id)
    gmail_service.disconnect(profile_id)
    return {"disconnected": True, "message": "Gmail disconnected."}
