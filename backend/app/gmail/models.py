from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GmailConnection:
    """Deserialized, decrypted Gmail connection for use in the application layer."""
    connection_id: str
    profile_id: str
    provider: str
    provider_account_email: str | None
    access_token: str           # decrypted, never logged, never sent to frontend
    refresh_token: str | None   # decrypted, never logged, never sent to frontend
    token_expires_at: datetime | None
    scopes: str | None


@dataclass
class GmailStatus:
    """Safe public view of the connection state — contains NO tokens."""
    connected: bool
    email: str | None
    # A connection row exists but its tokens can't be used here (e.g. they
    # were encrypted with a different GOOGLE_TOKEN_ENCRYPTION_KEY): reconnect.
    needs_reconnect: bool = False
