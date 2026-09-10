"""
Regression tests for app/auth.py — Supabase JWT verification and profile
ownership resolution (production hardening: X-Profile-Id is no longer
sufficient on its own to access another user's data once a session is
presented).
"""
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app import auth


# ---------------------------------------------------------------------------
# A minimal fake Supabase client backing a `profiles` table, so these tests
# exercise auth.py's real query logic without a live database connection.
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, op, base_filter=None):
        self._rows = rows
        self._op = op
        self._filters = dict(base_filter or {})
        self._is_null_filters = {}
        self._payload = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def is_(self, field, _value):
        self._is_null_filters[field] = True
        return self

    def limit(self, _n):
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def _matches(self, row):
        for k, v in self._filters.items():
            if row.get(k) != v:
                return False
        for k in self._is_null_filters:
            if row.get(k) is not None:
                return False
        return True

    def execute(self):
        matched = [r for r in self._rows.values() if self._matches(r)]
        if self._op == "update":
            for row in matched:
                row.update(self._payload)
            return _Result(matched)
        return _Result(matched)


class FakeProfilesTable:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_kw):
        return _Query(self._rows, "select")

    def update(self, payload):
        q = _Query(self._rows, "update")
        return q.update(payload)


class FakeAuth:
    def __init__(self):
        self.get_user = lambda token: SimpleNamespace(user=None)


class FakeSupabase:
    def __init__(self, profiles: dict):
        self._profiles = profiles
        self.auth = FakeAuth()

    def table(self, name):
        assert name == "profiles"
        return FakeProfilesTable(self._profiles)


@pytest.fixture
def profiles_db():
    return {}


@pytest.fixture(autouse=True)
def fake_supabase(profiles_db, monkeypatch):
    fake = FakeSupabase(profiles_db)
    monkeypatch.setattr("app.auth.supabase", fake)
    monkeypatch.setattr("app.auth.execute", lambda q: q.execute())
    return fake


def _mock_authed_user(user_id: str):
    return patch("app.auth.get_authenticated_user_id", return_value=user_id)


# ---------------------------------------------------------------------------
# 1. Valid authenticated user can access own profile.
# ---------------------------------------------------------------------------

def test_authenticated_user_resolves_own_linked_profile(profiles_db):
    user_id = str(uuid4())
    profile_id = str(uuid4())
    profiles_db[profile_id] = {"id": profile_id, "linked_user_id": user_id}

    with _mock_authed_user(user_id):
        result = auth.require_profile_id(authorization="Bearer real-token", x_profile_id=None)

    assert result == profile_id


def test_authenticated_user_whose_profile_id_equals_their_auth_id(profiles_db):
    """A new user whose profile was created post-hardening (id == auth user
    id directly, no separate link row needed)."""
    user_id = str(uuid4())
    profiles_db[user_id] = {"id": user_id, "linked_user_id": None}

    with _mock_authed_user(user_id):
        result = auth.require_profile_id(authorization="Bearer real-token", x_profile_id=None)

    assert result == user_id


# ---------------------------------------------------------------------------
# 2. Valid authenticated user cannot access another user's profile.
# 3. Cannot use X-Profile-Id to impersonate another user.
# ---------------------------------------------------------------------------

def test_authenticated_user_cannot_impersonate_via_mismatched_x_profile_id(profiles_db):
    user_a = str(uuid4())
    profile_a = str(uuid4())
    profile_b = str(uuid4())  # belongs to a different user, not modeled here
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}

    with _mock_authed_user(user_a):
        with pytest.raises(HTTPException) as exc:
            auth.require_profile_id(authorization="Bearer real-token", x_profile_id=profile_b)

    assert exc.value.status_code == 403


def test_authenticated_user_cannot_claim_a_profile_already_linked_to_someone_else(profiles_db):
    user_a = str(uuid4())
    user_b = str(uuid4())
    victim_profile = str(uuid4())
    profiles_db[victim_profile] = {"id": victim_profile, "linked_user_id": user_b}

    with _mock_authed_user(user_a):
        with pytest.raises(HTTPException) as exc:
            auth.require_profile_id(authorization="Bearer real-token", x_profile_id=victim_profile)

    assert exc.value.status_code == 403
    # And the victim's profile must remain linked to its real owner.
    assert profiles_db[victim_profile]["linked_user_id"] == user_b


def test_first_authenticated_request_claims_a_matching_unlinked_legacy_profile(profiles_db):
    """
    A returning user whose profile predates their first authenticated
    session (created anonymously via the old CV-upload-first flow) — their
    own X-Profile-Id should be adopted, not rejected, exactly once.
    """
    user_id = str(uuid4())
    legacy_profile = str(uuid4())
    profiles_db[legacy_profile] = {"id": legacy_profile, "linked_user_id": None}

    with _mock_authed_user(user_id):
        result = auth.require_profile_id(authorization="Bearer real-token", x_profile_id=legacy_profile)

    assert result == legacy_profile
    assert profiles_db[legacy_profile]["linked_user_id"] == user_id

    # A second request from the SAME user now resolves without needing
    # X-Profile-Id at all — it's linked.
    with _mock_authed_user(user_id):
        result2 = auth.require_profile_id(authorization="Bearer real-token", x_profile_id=None)
    assert result2 == legacy_profile


# ---------------------------------------------------------------------------
# 7. Unauthenticated protected requests return 401.
# ---------------------------------------------------------------------------

def test_no_session_and_no_x_profile_id_returns_401():
    with pytest.raises(HTTPException) as exc:
        auth.require_profile_id(authorization=None, x_profile_id=None)
    assert exc.value.status_code == 401


def test_invalid_bearer_token_falls_back_to_legacy_unauthenticated_path(fake_supabase):
    """A garbage/expired token must not crash the request — it's treated
    as simply not authenticated, same as no header at all. This exercises
    the real get_authenticated_user_id (not mocked), including its
    exception handling around the actual Supabase verification call."""
    def _raise(token):
        raise Exception("invalid jwt")

    fake_supabase.auth.get_user = _raise

    # No X-Profile-Id either -> still unauthenticated -> 401.
    with pytest.raises(HTTPException) as exc:
        auth.require_profile_id(authorization="Bearer garbage", x_profile_id=None)
    assert exc.value.status_code == 401

    # With X-Profile-Id -> legacy trust path, unchanged from pre-hardening.
    result = auth.require_profile_id(authorization="Bearer garbage", x_profile_id="legacy-id")
    assert result == "legacy-id"


def test_get_authenticated_user_id_rejects_malformed_headers(fake_supabase):
    """Pure header-shape validation, independent of Supabase entirely."""
    assert auth.get_authenticated_user_id(None) is None
    assert auth.get_authenticated_user_id("") is None
    assert auth.get_authenticated_user_id("NotBearer sometoken") is None
    assert auth.get_authenticated_user_id("Bearer") is None
    assert auth.get_authenticated_user_id("Bearer   ") is None


def test_get_authenticated_user_id_returns_user_id_for_a_valid_token(fake_supabase):
    user_id = str(uuid4())
    fake_supabase.auth.get_user = lambda token: SimpleNamespace(user=SimpleNamespace(id=user_id))
    assert auth.get_authenticated_user_id("Bearer real-token") == user_id


def test_authenticated_user_with_no_profile_and_no_x_profile_id_returns_404(profiles_db):
    """Distinguish "authenticated but never uploaded a CV yet" (404 — go
    upload one) from "not authenticated at all" (401)."""
    user_id = str(uuid4())
    with _mock_authed_user(user_id):
        with pytest.raises(HTTPException) as exc:
            auth.require_profile_id(authorization="Bearer real-token", x_profile_id=None)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Legacy backward compatibility: no Authorization header at all still
# trusts X-Profile-Id exactly as before this change.
# ---------------------------------------------------------------------------

def test_legacy_caller_with_no_authorization_header_is_unaffected():
    result = auth.require_profile_id(authorization=None, x_profile_id="whatever-id")
    assert result == "whatever-id"


# ---------------------------------------------------------------------------
# 4/5/6. CV, outreach draft, and Gmail connection access are all isolated —
# exercised at the real HTTP layer (via the `client` fixture from
# conftest.py), proving the ownership check is actually wired into these
# routers, not just correct in isolation.
# ---------------------------------------------------------------------------

def _authed_as(monkeypatch, user_id: str) -> None:
    monkeypatch.setattr("app.auth.get_authenticated_user_id", lambda _authorization: user_id)


def test_cv_endpoint_rejects_mismatched_authenticated_user(client, profiles_db, monkeypatch):
    user_a = str(uuid4())
    profile_a = str(uuid4())
    other_profile = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    res = client.get(
        "/cv/some-cv-id",
        headers={"Authorization": "Bearer t", "X-Profile-Id": other_profile},
    )
    assert res.status_code == 403


def test_outreach_drafts_endpoint_rejects_mismatched_authenticated_user(client, profiles_db, monkeypatch):
    user_a = str(uuid4())
    profile_a = str(uuid4())
    other_profile = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    res = client.get(
        "/outreach/drafts",
        headers={"Authorization": "Bearer t", "X-Profile-Id": other_profile},
    )
    assert res.status_code == 403


def test_gmail_status_endpoint_rejects_mismatched_authenticated_user(client, profiles_db, monkeypatch):
    user_a = str(uuid4())
    profile_a = str(uuid4())
    other_profile = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    res = client.get(
        "/gmail/status",
        headers={"Authorization": "Bearer t", "X-Profile-Id": other_profile},
    )
    assert res.status_code == 403


def test_cv_endpoint_allows_correctly_authenticated_owner(client, profiles_db, monkeypatch):
    """The isolation checks above don't just reject everything — a
    correctly-matched owner still gets through to the real endpoint logic
    (here surfacing as a 404 for a CV id that doesn't exist, proving the
    request reached cv_service rather than being blocked at the auth layer)."""
    user_a = str(uuid4())
    profile_a = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    res = client.get(
        f"/cv/{uuid4()}",
        headers={"Authorization": "Bearer t", "X-Profile-Id": profile_a},
    )
    assert res.status_code == 404  # "CV version not found" — not 403


# ---------------------------------------------------------------------------
# 8. Public catalog endpoints remain accessible where intended (no auth
# required at all — unaffected by any of this).
# ---------------------------------------------------------------------------

def test_public_catalog_endpoints_require_no_authentication(client):
    for path in ("/universities", "/professors/search"):
        res = client.get(path)
        assert res.status_code != 401, f"{path} should not require authentication"
