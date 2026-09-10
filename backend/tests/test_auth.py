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
from postgrest.exceptions import APIError

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
# A second fake, mirroring the CURRENT live `profiles` table exactly:
# no `linked_user_id` column at all yet (migrations/
# 20260910_profiles_linked_user_id.sql has not been applied — confirmed by
# direct introspection of the live database while diagnosing the CV
# selection "Database query failed" bug). Raises the exact real Postgrest
# errors Postgrest itself returns for a missing column: 42703 for a
# filter/select referencing it, PGRST204 for an insert/update naming it —
# and, unlike `fake_supabase` above, does NOT bypass the real execute()
# wrapper, so these tests exercise the actual production error-mapping and
# degradation path end-to-end, not just the app logic in isolation.
# ---------------------------------------------------------------------------

def _missing_column_error(code: str, column: str) -> APIError:
    if code == "42703":
        message = f"column profiles.{column} does not exist"
    else:
        message = f"Could not find the '{column}' column of 'profiles' in the schema cache"
    return APIError({"code": code, "message": message, "hint": None, "details": None})


class _NoLinkColumnQuery:
    def __init__(self, rows: dict, op: str = "select"):
        self._rows = rows
        self._op = op
        self._filters: dict = {}
        self._is_null_filters: set = set()
        self._payload: dict | None = None
        self._references_link_column = False

    def select(self, cols: str = "*", *_a, **_kw):
        # Real Postgrest raises 42703 for a nonexistent column named in the
        # select column list too, not just in a filter — verified live.
        if "linked_user_id" in [c.strip() for c in cols.split(",")]:
            self._references_link_column = True
        return self

    def eq(self, field, value):
        if field == "linked_user_id":
            self._references_link_column = True
        self._filters[field] = value
        return self

    def is_(self, field, _value):
        if field == "linked_user_id":
            self._references_link_column = True
        self._is_null_filters.add(field)
        return self

    def limit(self, _n):
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = dict(payload)
        if "linked_user_id" in payload:
            self._references_link_column = True
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = dict(payload)
        if "linked_user_id" in payload:
            self._references_link_column = True
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
        if self._references_link_column:
            code = "PGRST204" if self._op in ("insert", "update") else "42703"
            raise _missing_column_error(code, "linked_user_id")
        if self._op == "insert":
            row = dict(self._payload)
            self._rows[row["id"]] = row
            return _Result([row])
        matched = [r for r in self._rows.values() if self._matches(r)]
        if self._op == "update":
            for row in matched:
                row.update(self._payload)
        return _Result(matched)


class FakeProfilesTableNoLinkColumn:
    def __init__(self, rows):
        self._rows = rows

    def select(self, cols: str = "*", *_a, **_kw):
        return _NoLinkColumnQuery(self._rows, "select").select(cols)

    def insert(self, payload):
        return _NoLinkColumnQuery(self._rows).insert(payload)

    def update(self, payload):
        return _NoLinkColumnQuery(self._rows).update(payload)


class FakeSupabaseNoLinkColumn:
    def __init__(self, profiles: dict):
        self._profiles = profiles
        self.auth = FakeAuth()

    def table(self, name):
        assert name == "profiles"
        return FakeProfilesTableNoLinkColumn(self._profiles)


@pytest.fixture
def fake_supabase_current_schema(profiles_db, monkeypatch):
    """
    Patches BOTH app.auth and app.services.cv onto the real (un-migrated)
    live schema shape. Unlike the autouse `fake_supabase` fixture above
    (which bypasses execute() entirely — app.auth.execute = q.execute()),
    this restores the REAL execute() in app.auth, so these tests exercise
    the actual production error-mapping/degradation code end-to-end, not a
    test double standing in for it.
    """
    from app.services.query import execute as real_execute

    fake = FakeSupabaseNoLinkColumn(profiles_db)
    monkeypatch.setattr("app.auth.supabase", fake)
    monkeypatch.setattr("app.auth.execute", real_execute)
    monkeypatch.setattr("app.services.cv.supabase", fake)
    return fake


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


# ---------------------------------------------------------------------------
# CV selection flow (list + attach) — HTTP-layer regression tests added
# after diagnosing a live "Database query failed" 503 on this exact flow.
# Root cause: app/auth.py's ownership resolution queries
# profiles.linked_user_id (migrations/20260910_profiles_linked_user_id.sql),
# which had not yet been applied to the live database — a schema/deployment
# gap, not a code defect. These tests exercise the full router -> auth ->
# service path with a fake profiles table that DOES have the column (i.e.
# the intended, post-migration schema), proving the application code itself
# is correct; they cannot catch a live schema that lags behind migrations
# in the repo — that class of issue is now caught earlier via the
# server-side error logging added to app/services/query.py instead.
# ---------------------------------------------------------------------------

from app.outreach import db_store as _db_store
from app.outreach.models import DraftRecord as _DraftRecord


def _cv_row(cv_id: str, profile_id: str, **overrides) -> dict:
    row = {
        "id": cv_id,
        "profile_id": profile_id,
        "file_name": "resume.pdf",
        "description": '{"original_filename":"resume.pdf","file_type":"pdf","file_size":1024,"confirmed":true}',
        "storage_path": f"{profile_id}/{cv_id}/resume.pdf",
        "is_default": True,
        "version_number": 1,
        "created_at": "2026-09-01T10:00:00Z",
    }
    row.update(overrides)
    return row


def _draft_record(profile_id: str) -> _DraftRecord:
    return _DraftRecord(
        draft_id=str(uuid4()),
        profile_id=profile_id,
        professor_id=str(uuid4()),
        email_type="research",
        subject="Research inquiry",
        body="Dear Professor,",
        generation_status="ready",
    )


def test_uploaded_cv_is_listed_for_its_owning_profile(client, profiles_db, monkeypatch):
    """"Uploaded CV exists" + "CV list loads" for the authenticated owner."""
    user_a = str(uuid4())
    profile_a = str(uuid4())
    cv_id = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [_cv_row(cv_id, profile_a)]})(),
    )

    res = client.get(
        "/outreach/cv-versions",
        headers={"Authorization": "Bearer t", "X-Profile-Id": profile_a},
    )
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) == 1
    assert versions[0]["cv_version_id"] == cv_id
    assert versions[0]["display_name"] == "resume.pdf"
    # Never leak the internal storage path to the client.
    assert "storage_path" not in versions[0]


def test_cv_versions_list_rejects_mismatched_authenticated_user(client, profiles_db, monkeypatch):
    user_a = str(uuid4())
    profile_a = str(uuid4())
    other_profile = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    res = client.get(
        "/outreach/cv-versions",
        headers={"Authorization": "Bearer t", "X-Profile-Id": other_profile},
    )
    assert res.status_code == 403


def test_selecting_an_existing_owned_cv_succeeds(client, profiles_db, monkeypatch):
    """Selecting (attaching) a CV the authenticated user actually owns succeeds."""
    user_a = str(uuid4())
    profile_a = str(uuid4())
    cv_id = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    record = _draft_record(profile_a)
    _db_store.clear()
    _db_store.put(record.draft_id, record)

    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [_cv_row(cv_id, profile_a)]})(),
    )
    monkeypatch.setattr("app.outreach.service.cv_file_exists", lambda p: True)

    try:
        res = client.post(
            f"/outreach/drafts/{record.draft_id}/attach-cv",
            headers={"Authorization": "Bearer t", "X-Profile-Id": profile_a},
            json={"cv_version_id": cv_id},
        )
        assert res.status_code == 200, res.text
        assert res.json()["cv_version_id"] == cv_id
    finally:
        _db_store.disable_test_mode()


def test_selecting_another_users_cv_is_rejected(client, profiles_db, monkeypatch):
    """Selecting a CV owned by a different profile must be rejected, even
    though the requesting user is otherwise fully authenticated and owns
    the draft itself."""
    user_a = str(uuid4())
    profile_a = str(uuid4())
    profile_b = str(uuid4())  # a different user's profile
    cv_id = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "linked_user_id": user_a}
    _authed_as(monkeypatch, user_a)

    record = _draft_record(profile_a)
    _db_store.clear()
    _db_store.put(record.draft_id, record)

    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [_cv_row(cv_id, profile_b)]})(),
    )

    try:
        res = client.post(
            f"/outreach/drafts/{record.draft_id}/attach-cv",
            headers={"Authorization": "Bearer t", "X-Profile-Id": profile_a},
            json={"cv_version_id": cv_id},
        )
        assert res.status_code == 403
    finally:
        _db_store.disable_test_mode()


# ---------------------------------------------------------------------------
# Regression tests for the "Database query failed" 503 diagnosed on CV
# selection: profiles.linked_user_id is not yet migrated in the live
# database (confirmed via direct introspection — 42703 on select/filter,
# PGRST204 on insert/update). These prove the CV selection query succeeds
# against the CURRENT (unmigrated) schema shape, not just the intended
# future one, and that ownership enforcement is unaffected by the
# degradation. See app/auth.py, app/services/cv.py, app/services/query.py
# (is_missing_column_error).
# ---------------------------------------------------------------------------

def test_find_linked_profile_id_resolves_direct_match_even_without_link_column(
    fake_supabase_current_schema, profiles_db,
):
    """The common case (profile.id == user_id) needs no linked_user_id
    lookup at all, so it must work even against the current live schema."""
    user_id = str(uuid4())
    profiles_db[user_id] = {"id": user_id, "full_name": "Student"}
    assert auth._find_linked_profile_id(user_id) == user_id


def test_find_linked_profile_id_degrades_gracefully_without_link_column(
    fake_supabase_current_schema, profiles_db,
):
    """No direct match and the link column doesn't exist yet: must return
    None (safe — no profile handed out), never a 503."""
    user_id = str(uuid4())
    result = auth._find_linked_profile_id(user_id)
    assert result is None


def test_profile_link_state_degrades_gracefully_without_link_column(
    fake_supabase_current_schema, profiles_db,
):
    profile_id = str(uuid4())
    profiles_db[profile_id] = {"id": profile_id, "full_name": "Student"}
    assert auth._profile_link_state(profile_id) is None


def test_require_profile_id_works_end_to_end_without_link_column(
    fake_supabase_current_schema, profiles_db, monkeypatch,
):
    """The full require_profile_id path for a user whose profile.id already
    equals their auth user id must succeed against the current schema."""
    user_id = str(uuid4())
    profiles_db[user_id] = {"id": user_id, "full_name": "Student"}
    monkeypatch.setattr("app.auth.get_authenticated_user_id", lambda _a: user_id)

    result = auth.require_profile_id(authorization="Bearer t", x_profile_id=None)
    assert result == user_id


def test_ensure_profile_creates_row_when_link_column_is_missing(
    fake_supabase_current_schema, profiles_db,
):
    """CV upload for a brand-new authenticated user (app/services/cv.py's
    ensure_profile) must succeed even though the insert can no longer
    include linked_user_id."""
    from app.services import cv as cv_service

    user_id = str(uuid4())
    result = cv_service.ensure_profile(None, user_id=user_id)
    assert result == user_id
    assert profiles_db[user_id]["id"] == user_id
    assert "linked_user_id" not in profiles_db[user_id]


def test_cv_versions_endpoint_succeeds_against_current_unmigrated_schema(
    client, fake_supabase_current_schema, profiles_db, monkeypatch,
):
    """End-to-end HTTP reproduction of the reported bug: GET
    /outreach/cv-versions for a logged-in user whose profile.id equals
    their auth user id must return 200, not 503, against the current
    (unmigrated) live schema shape."""
    user_id = str(uuid4())
    cv_id = str(uuid4())
    profiles_db[user_id] = {"id": user_id, "full_name": "Student"}
    monkeypatch.setattr("app.auth.get_authenticated_user_id", lambda _a: user_id)
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [_cv_row(cv_id, user_id)]})(),
    )

    res = client.get("/outreach/cv-versions", headers={"Authorization": "Bearer t"})
    assert res.status_code == 200, res.text
    assert res.json()[0]["cv_version_id"] == cv_id


def test_ownership_still_enforced_against_current_unmigrated_schema(
    client, fake_supabase_current_schema, profiles_db, monkeypatch,
):
    """Degrading gracefully for a missing column must never widen access:
    an authenticated user presenting someone else's X-Profile-Id is still
    rejected, even while profiles.linked_user_id is unavailable."""
    user_a = str(uuid4())
    profile_a = str(uuid4())
    other_profile = str(uuid4())
    profiles_db[profile_a] = {"id": profile_a, "full_name": "Student"}
    monkeypatch.setattr("app.auth.get_authenticated_user_id", lambda _a: user_a)

    res = client.get(
        "/outreach/cv-versions",
        headers={"Authorization": "Bearer t", "X-Profile-Id": other_profile},
    )
    # other_profile doesn't belong to user_a (and can't be auto-claimed
    # without the link column) — must never be silently granted.
    assert res.status_code in (403, 404)
    assert res.status_code != 200
