from __future__ import annotations

"""
Server-side profile ownership resolution.

BACKGROUND:
Every endpoint previously trusted a client-supplied X-Profile-Id header at
face value, with no verification that the caller was actually the owner of
that profile. Any client could set X-Profile-Id to any UUID and read/modify
that profile's CVs, drafts, and Gmail connection.

This module adds real verification using the existing Supabase project —
no new auth architecture, no new secret. A Supabase access token (the one
supabase-js already holds client-side after Google sign-in) is verified via
supabase.auth.get_user(token), which validates it against Supabase's own
Auth server. profiles.id already equals an auth.users.id by construction
(see app/services/cv.py); a `linked_user_id` column (see migrations/) lets
an existing profile — including one created anonymously before the user
ever signed in — be claimed by a real authenticated user without migrating
its primary key.

TRANSITIONAL COMPATIBILITY:
X-Profile-Id is not removed. When no Authorization header is present at
all, behavior is unchanged from before this change (trust X-Profile-Id) —
this keeps any caller that has not yet been updated to send a Supabase
session working exactly as it did. What changes is: once a caller DOES
present a valid Supabase session, X-Profile-Id can never be used to access
a profile other than the one that session is linked to — an authenticated
user presenting someone else's X-Profile-Id gets 403, not silent access.
This is a deliberate, incremental step; see the audit report for the
remaining gap (a caller presenting no Authorization header at all is still
trusted on X-Profile-Id alone) and what closing it fully would require.
"""

import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.services.query import execute
from app.supabase_client import supabase

logger = logging.getLogger(__name__)


@dataclass
class Identity:
    profile_id: str | None
    user_id: str | None
    authenticated: bool


def get_authenticated_user_id(authorization: str | None) -> str | None:
    """
    Verify a Supabase access token and return the authenticated user's id.
    Returns None for a missing/malformed header or a token Supabase rejects
    — never raises, so callers can treat "not authenticated" as a normal,
    expected state rather than an error. Never logs the token itself.
    """
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    token = parts[1].strip()
    try:
        response = supabase.auth.get_user(token)
    except Exception:
        logger.info("Supabase session token could not be verified.")
        return None
    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None) if user else None
    return str(user_id) if user_id else None


def _find_linked_profile_id(user_id: str) -> str | None:
    """A profile already explicitly linked to this authenticated user, if any."""
    rows = execute(
        supabase.table("profiles").select("id").eq("linked_user_id", user_id).limit(1)
    ).data or []
    if rows:
        return str(rows[0]["id"])
    # A profile whose id was assigned directly from a real auth user (new
    # users going forward, once cv_service stops fabricating an identity
    # for an already-authenticated caller) needs no separate link row.
    rows = execute(
        supabase.table("profiles").select("id").eq("id", user_id).limit(1)
    ).data or []
    return str(rows[0]["id"]) if rows else None


def _profile_link_state(profile_id: str) -> str | None:
    """Returns None if the profile doesn't exist, 'unlinked', or 'linked'."""
    rows = execute(
        supabase.table("profiles").select("id, linked_user_id").eq("id", profile_id).limit(1)
    ).data or []
    if not rows:
        return None
    return "linked" if rows[0].get("linked_user_id") else "unlinked"


def _claim_profile(profile_id: str, user_id: str) -> None:
    """
    Link an existing, currently-unclaimed profile to the authenticated user
    making this request. Scoped to linked_user_id IS NULL so this can never
    steal a profile someone else has already claimed (a concurrent claim
    attempt simply updates 0 rows).
    """
    execute(
        supabase.table("profiles")
        .update({"linked_user_id": user_id})
        .eq("id", profile_id)
        .is_("linked_user_id", "null")
    )


def resolve_identity(
    authorization: str | None = Header(default=None),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> Identity:
    """
    FastAPI dependency resolving "who is making this request" without
    forcing a profile to exist yet — used directly by endpoints (like CV
    upload) that are allowed to create a brand new profile. Most endpoints
    should depend on require_profile_id below instead.
    """
    user_id = get_authenticated_user_id(authorization)
    if not user_id:
        # No verifiable session presented — legacy/anonymous path, unchanged.
        return Identity(profile_id=x_profile_id, user_id=None, authenticated=False)

    linked_id = _find_linked_profile_id(user_id)
    if linked_id:
        if x_profile_id and x_profile_id != linked_id:
            raise HTTPException(
                status_code=403,
                detail="X-Profile-Id does not match the authenticated account.",
            )
        return Identity(profile_id=linked_id, user_id=user_id, authenticated=True)

    if not x_profile_id:
        return Identity(profile_id=None, user_id=user_id, authenticated=True)

    state = _profile_link_state(x_profile_id)
    if state is None:
        # X-Profile-Id doesn't correspond to any real profile — let the
        # caller create one for this authenticated user if that's valid here.
        return Identity(profile_id=None, user_id=user_id, authenticated=True)
    if state == "linked":
        raise HTTPException(
            status_code=403,
            detail="X-Profile-Id belongs to a different account.",
        )
    # Unlinked and it exists: this is a returning user whose profile
    # predates their first authenticated session — claim it for them once.
    _claim_profile(x_profile_id, user_id)
    return Identity(profile_id=x_profile_id, user_id=user_id, authenticated=True)


def require_profile_id(
    authorization: str | None = Header(default=None),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> str:
    """
    FastAPI dependency for endpoints that require an existing profile.
    Returns the authoritative profile_id, or raises:
      - 401 if there is no session and no X-Profile-Id at all.
      - 403 if a session is presented and X-Profile-Id names a profile that
        isn't (and can't be claimed as) the authenticated user's own.
      - 404 if the user is authenticated but has no profile yet.
    """
    identity = resolve_identity(authorization, x_profile_id)
    if identity.profile_id:
        return identity.profile_id
    if identity.authenticated:
        raise HTTPException(
            status_code=404,
            detail="No profile found for this account yet. Upload a CV first.",
        )
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Sign in or provide X-Profile-Id.",
    )
