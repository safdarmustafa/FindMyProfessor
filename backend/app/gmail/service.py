from __future__ import annotations

"""
Gmail integration service.

Responsibilities:
- Store and retrieve Gmail OAuth connections (encrypted tokens in DB).
- Refresh expired access tokens transparently.
- Validate connection readiness before send.
- Provide GmailConnection to the send flow.
- Revoke connections on disconnect.

SECURITY:
- Tokens are encrypted at rest using Fernet (crypto.py).
- Tokens are NEVER returned to the frontend.
- provider_account_email is the only public field.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import HTTPException

from app.gmail.crypto import decrypt, encrypt
from app.gmail.models import GmailConnection, GmailStatus
from app.gmail.oauth import refresh_access_token, revoke_token, GMAIL_SEND_SCOPE
from app.services.query import execute
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

TABLE = "gmail_connections"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_connection(profile_id: str) -> GmailConnection | None:
    """Load and decrypt the Gmail connection for a profile. Returns None if not connected."""
    row = _fetch_row(profile_id)
    if not row or row.get("revoked_at"):
        return None
    return _row_to_connection(row)


def get_status(profile_id: str) -> GmailStatus:
    """Return safe public connection status (no tokens).

    provider_account_email is OPTIONAL metadata. A valid connection exists
    whenever a non-revoked row is present, regardless of whether the email
    field is populated. gmail.send scope does not expose the account email
    via any Google endpoint without additional scopes, so email may be null.
    """
    row = _fetch_row(profile_id)
    if not row or row.get("revoked_at"):
        return GmailStatus(connected=False, email=None)
    # email may legitimately be None — callers must not require it
    return GmailStatus(connected=True, email=row.get("provider_account_email"))


def upsert_connection(
    *,
    profile_id: str,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: datetime | None,
    provider_account_email: str | None,
    scopes: str | None,
) -> None:
    """Store (insert or update) an encrypted Gmail connection for a profile."""
    payload: dict[str, Any] = {
        "profile_id": profile_id,
        "provider": "google",
        "provider_account_email": provider_account_email,
        "access_token_encrypted": encrypt(access_token),
        "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
        "scopes": scopes,
        "revoked_at": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if refresh_token:
        payload["refresh_token_encrypted"] = encrypt(refresh_token)

    # Try update first; if 0 rows affected, insert
    existing = _fetch_row(profile_id)
    if existing:
        execute(
            supabase.table(TABLE)
            .update(payload)
            .eq("profile_id", profile_id)
            .eq("provider", "google")
        )
    else:
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        execute(supabase.table(TABLE).insert(payload))


def disconnect(profile_id: str) -> None:
    """
    Disconnect Gmail for a profile.
    - Revokes the access token with Google (best-effort).
    - Marks the connection revoked_at and clears encrypted tokens.
    - Does NOT delete historical sent draft records.
    """
    row = _fetch_row(profile_id)
    if not row:
        return

    # Best-effort token revocation
    try:
        if row.get("access_token_encrypted"):
            token = decrypt(row["access_token_encrypted"])
            revoke_token(token)
    except Exception:
        pass  # silently continue — token may already be invalid

    execute(
        supabase.table(TABLE)
        .update({
            "access_token_encrypted": None,
            "refresh_token_encrypted": None,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("profile_id", profile_id)
        .eq("provider", "google")
    )


def get_valid_access_token(profile_id: str) -> str:
    """
    Return a valid access token, refreshing if expired.
    Raises HTTPException(401) if no connection or refresh fails.
    NEVER logs the token.
    """
    conn = get_connection(profile_id)
    if not conn:
        raise HTTPException(
            status_code=401,
            detail="Gmail is not connected. Connect via /gmail/connect.",
        )

    # Check expiry with 60-second buffer
    now = datetime.now(timezone.utc)
    if conn.token_expires_at and (conn.token_expires_at - now).total_seconds() < 60:
        if not conn.refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Gmail access token expired and no refresh token is available. Please reconnect.",
            )
        try:
            token_response = refresh_access_token(conn.refresh_token)
        except Exception as exc:
            logger.warning("Token refresh failed.")
            raise HTTPException(
                status_code=401,
                detail="Gmail access token could not be refreshed. Please reconnect.",
            ) from exc

        new_access_token = token_response.get("access_token", "")
        if not new_access_token:
            raise HTTPException(
                status_code=401,
                detail="Gmail token refresh returned no access token. Please reconnect.",
            )
        expires_in = token_response.get("expires_in", 3600)
        new_expires_at = now + timedelta(seconds=int(expires_in))
        # Update stored token
        upsert_connection(
            profile_id=profile_id,
            access_token=new_access_token,
            refresh_token=conn.refresh_token,
            token_expires_at=new_expires_at,
            provider_account_email=conn.provider_account_email,
            scopes=conn.scopes,
        )
        return new_access_token

    return conn.access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------



def _fetch_row(profile_id: str) -> dict[str, Any] | None:
    rows = execute(
        supabase.table(TABLE)
        .select("*")
        .eq("profile_id", profile_id)
        .eq("provider", "google")
        .limit(1)
    ).data or []
    return rows[0] if rows else None


def _row_to_connection(row: dict[str, Any]) -> GmailConnection | None:
    try:
        access_token = decrypt(row["access_token_encrypted"]) if row.get("access_token_encrypted") else ""
    except ValueError:
        logger.warning("Could not decrypt access token for profile.")
        return None

    try:
        refresh_token = decrypt(row["refresh_token_encrypted"]) if row.get("refresh_token_encrypted") else None
    except ValueError:
        refresh_token = None

    expires_raw = row.get("token_expires_at")
    if expires_raw:
        try:
            token_expires_at = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        except ValueError:
            token_expires_at = None
    else:
        token_expires_at = None

    return GmailConnection(
        connection_id=str(row["id"]),
        profile_id=str(row["profile_id"]),
        provider=row.get("provider", "google"),
        provider_account_email=row.get("provider_account_email"),
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
        scopes=row.get("scopes"),
    )
