"""
Phase 6 — Comprehensive tests.

Coverage:
- Draft DB store (test mode)
- Profile isolation for drafts
- CV version listing and attachment
- Gmail crypto
- Gmail OAuth state
- Gmail service (status, connect, disconnect, token refresh)
- Gmail router endpoints (status, disconnect, callback)
- Send validations (all preconditions)
- Double-send protection
- Successful send (mocked Gmail client)
- Gmail API failure handling
- MIME message construction
- Attachment bytes / filename / MIME type
- History listing
- Pages registered (history, gmail-connected, gmail-error)
- Existing Phase 5 tests unaffected

REAL GMAIL API IS NEVER CALLED.
REAL EMAILS ARE NEVER SENT.
All Gmail API calls are mocked at the client boundary.
"""
from __future__ import annotations

import base64
import email as email_lib
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.cv.extraction.schema import (
    EducationExtract,
    ExtractedStudentProfile,
    IdentityExtract,
)
from app.gmail import crypto as gmail_crypto
from app.gmail import oauth as gmail_oauth
from app.gmail.client import GmailApiError, GmailSendResult, build_mime_message
from app.gmail import service as gmail_service
from app.outreach import db_store, store
from app.outreach import service as outreach_service
from app.outreach.models import DraftRecord, EvidenceLine
from app.outreach.provider import (
    ArtifactEvidence,
    MatchContext,
    ProfessorContext,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_record(
    profile_id: str | None = None,
    professor_id: str | None = None,
    subject: str = "Research Inquiry",
    body: str = "Dear Professor Smith,\n\nBody text here.\n\nRegards,\nAisha",
    status: str = "ready",
    cv_version_id: str | None = None,
) -> DraftRecord:
    r = DraftRecord(
        draft_id=str(uuid4()),
        profile_id=profile_id or str(uuid4()),
        professor_id=professor_id or str(uuid4()),
        email_type="research",
        subject=subject,
        body=body,
        generation_status=status,  # type: ignore[arg-type]
    )
    if cv_version_id:
        r.cv_version_id = cv_version_id
    return r


def _student() -> ExtractedStudentProfile:
    return ExtractedStudentProfile(
        identity=IdentityExtract(name="Aisha Khan"),
        education=[EducationExtract(degree="B.Tech", institution="XYZ University")],
        research_interests=["Computer Vision"],
    )


def _prof_row(professor_id: str, email: str | None = "prof@uni.edu") -> dict:
    uni_id = str(uuid4())
    return {
        "id": professor_id,
        "name": "James Smith",
        "title": "Professor",
        "email": email,
        "research_summary": "Research in Computer Vision.",
        "lab": None,
        "department": {"id": str(uuid4()), "university_id": uni_id, "name": "CS"},
        "university": {"id": uni_id, "name": "MIT", "country": "USA", "city": "Cambridge"},
        "research_areas": [{"id": str(uuid4()), "name": "Computer Vision"}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB store — test mode
# ─────────────────────────────────────────────────────────────────────────────

def test_db_store_test_mode_put_and_get():
    db_store.clear()
    r = _make_record()
    db_store.put(r.draft_id, r)
    retrieved = db_store.get(r.draft_id)
    assert retrieved is r


def test_db_store_get_missing_returns_none():
    db_store.clear()
    assert db_store.get("nonexistent-id") is None


def test_db_store_all_for_profile():
    db_store.clear()
    pid = str(uuid4())
    r1 = _make_record(profile_id=pid)
    r2 = _make_record(profile_id=pid)
    r3 = _make_record()  # different profile
    db_store.put(r1.draft_id, r1)
    db_store.put(r2.draft_id, r2)
    db_store.put(r3.draft_id, r3)
    results = db_store.all_for_profile(pid)
    ids = {r.draft_id for r in results}
    assert r1.draft_id in ids
    assert r2.draft_id in ids
    assert r3.draft_id not in ids


def test_db_store_atomic_sending_transition():
    db_store.clear()
    r = _make_record(status="ready")
    db_store.put(r.draft_id, r)
    assert db_store.atomically_set_sending(r.draft_id, r.profile_id) is True
    r2 = db_store.get(r.draft_id)
    assert r2.generation_status == "sending"


def test_db_store_atomic_sending_rejects_non_ready():
    db_store.clear()
    r = _make_record(status="sent")
    db_store.put(r.draft_id, r)
    assert db_store.atomically_set_sending(r.draft_id, r.profile_id) is False


def test_db_store_double_send_rejected():
    db_store.clear()
    r = _make_record(status="ready")
    db_store.put(r.draft_id, r)
    first = db_store.atomically_set_sending(r.draft_id, r.profile_id)
    second = db_store.atomically_set_sending(r.draft_id, r.profile_id)
    assert first is True
    assert second is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Profile isolation via store
# ─────────────────────────────────────────────────────────────────────────────

def test_get_draft_wrong_profile_raises_403(monkeypatch):
    db_store.clear()
    profile_a = str(uuid4())
    profile_b = str(uuid4())
    r = _make_record(profile_id=profile_a)
    db_store.put(r.draft_id, r)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.get_draft(profile_id=profile_b, draft_id=r.draft_id)
    assert exc.value.status_code == 403


def test_save_draft_wrong_profile_raises_403(monkeypatch):
    db_store.clear()
    profile_a = str(uuid4())
    profile_b = str(uuid4())
    r = _make_record(profile_id=profile_a)
    db_store.put(r.draft_id, r)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.save_draft(
            profile_id=profile_b, draft_id=r.draft_id,
            subject="X", body="Y",
        )
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 3. CV version listing (safe metadata only — no storage paths in response)
# ─────────────────────────────────────────────────────────────────────────────

def test_list_cv_versions_returns_safe_metadata(monkeypatch):
    import json
    profile_id = str(uuid4())
    cv_id = str(uuid4())
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id,
            "profile_id": profile_id,
            "file_name": "cv.pdf",
            "description": json.dumps({
                "original_filename": "My_CV.pdf",
                "file_type": "pdf",
                "file_size": 102400,
                "confirmed": True,
            }),
            "is_default": True,
            "version_number": 1,
            "created_at": "2026-09-01T10:00:00Z",
        }]})(),
    )
    versions = outreach_service.list_cv_versions(profile_id=profile_id)
    assert len(versions) == 1
    v = versions[0]
    assert v.cv_version_id == cv_id
    assert v.display_name == "My_CV.pdf"
    assert v.confirmed is True
    assert not hasattr(v, "storage_path")


# ─────────────────────────────────────────────────────────────────────────────
# 4. CV attachment validates ownership
# ─────────────────────────────────────────────────────────────────────────────

def test_attach_cv_wrong_profile_rejected(monkeypatch):
    db_store.clear()
    profile_a = str(uuid4())
    profile_b = str(uuid4())
    cv_id = str(uuid4())

    r = _make_record(profile_id=profile_a)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id,
            "profile_id": profile_b,  # different profile!
            "file_name": "cv.pdf",
            "description": "{}",
            "storage_path": "some/path.pdf",
        }]})(),
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.attach_cv(
            profile_id=profile_a,
            draft_id=r.draft_id,
            cv_version_id=cv_id,
        )
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 5. Gmail crypto — encrypt / decrypt
# ─────────────────────────────────────────────────────────────────────────────

def test_crypto_round_trip():
    plaintext = "my_secret_access_token_12345"
    ciphertext = gmail_crypto.encrypt(plaintext)
    assert ciphertext != plaintext
    assert gmail_crypto.decrypt(ciphertext) == plaintext


def test_crypto_decrypt_tampered_raises():
    with pytest.raises(ValueError):
        gmail_crypto.decrypt("not-a-valid-fernet-token")


def test_crypto_two_encryptions_differ():
    token = "same_token"
    c1 = gmail_crypto.encrypt(token)
    c2 = gmail_crypto.encrypt(token)
    # Fernet uses random IV so ciphertexts differ
    assert c1 != c2
    # But both decrypt to the same value
    assert gmail_crypto.decrypt(c1) == token
    assert gmail_crypto.decrypt(c2) == token


# ─────────────────────────────────────────────────────────────────────────────
# 6. OAuth state management
# ─────────────────────────────────────────────────────────────────────────────

def test_oauth_state_create_and_consume():
    profile_id = str(uuid4())
    state = gmail_oauth.create_state(profile_id)
    assert len(state) > 20
    result = gmail_oauth.consume_state(state)
    assert result == profile_id


def test_oauth_state_cannot_be_reused():
    profile_id = str(uuid4())
    state = gmail_oauth.create_state(profile_id)
    gmail_oauth.consume_state(state)  # first consume
    result = gmail_oauth.consume_state(state)  # second consume
    assert result is None


def test_oauth_state_invalid_returns_none():
    result = gmail_oauth.consume_state("invalid-state-token")
    assert result is None


def test_oauth_state_missing_authorization_code():
    """Callback with missing code should reject."""
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/callback?state=somestate", follow_redirects=False)
    # Should redirect to error page (no code)
    assert resp.status_code in (302, 307)
    assert "error" in resp.headers.get("location", "").lower() or "callback-error" in resp.headers.get("location", "")


def test_oauth_callback_denied():
    """Callback with error=access_denied should redirect to error page."""
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/callback?error=access_denied&state=x", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error" in resp.headers.get("location", "")


def test_oauth_callback_invalid_state():
    """Callback with valid code but invalid state should redirect to error page."""
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/callback?code=someCode&state=invalid-state", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error" in resp.headers.get("location", "")


def test_oauth_callback_successful(monkeypatch):
    """Successful callback stores tokens and redirects to connected page."""
    profile_id = str(uuid4())
    state = gmail_oauth.create_state(profile_id)

    monkeypatch.setattr(
        "app.gmail.oauth.exchange_code",
        lambda code: {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr("app.gmail.oauth.get_token_email", lambda token: "student@gmail.com")
    monkeypatch.setattr("app.gmail.service.execute", lambda q: type("R", (), {"data": []})())

    from app.main import app
    client = TestClient(app)
    resp = client.get(f"/gmail/callback?code=authcode&state={state}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "gmail-connected" in resp.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Gmail status endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_gmail_status_disconnected(monkeypatch):
    monkeypatch.setattr("app.gmail.service.execute", lambda q: type("R", (), {"data": []})())
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["email"] is None


def test_gmail_status_connected(monkeypatch):
    encrypted_token = gmail_crypto.encrypt("some_access_token")
    encrypted_refresh = gmail_crypto.encrypt("some_refresh_token")
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "profile_id": str(uuid4()),
            "provider": "google",
            "provider_account_email": "student@gmail.com",
            "access_token_encrypted": encrypted_token,
            "refresh_token_encrypted": encrypted_refresh,
            "token_expires_at": None,
            "scopes": "https://www.googleapis.com/auth/gmail.send",
            "revoked_at": None,
        }]})(),
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["email"] == "student@gmail.com"
    # Token MUST NOT be in response
    assert "token" not in str(data)
    assert "access_token" not in str(data)


def test_gmail_status_revoked_shows_disconnected(monkeypatch):
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": "student@gmail.com",
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": "2026-09-09T10:00:00Z",
        }]})(),
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    data = resp.json()
    assert data["connected"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 7b. Root cause fix — NULL provider_account_email and UI "not connected" bug
# ─────────────────────────────────────────────────────────────────────────────

def _make_fake_get(gmail_data=None, userinfo_data=None):
    """Factory: returns a fake httpx.get that returns different data per URL."""
    class FakeResponse:
        def __init__(self, data):
            self._data = data
        @property
        def is_success(self):
            return self._data is not None
        def json(self):
            return self._data or {}

    def fake_get(url, *, headers, timeout):
        if "gmail.googleapis.com" in url:
            return FakeResponse(gmail_data)
        return FakeResponse(userinfo_data)

    return fake_get


class _FakeHttpx:
    """Minimal httpx replacement for monkeypatching get_token_email."""
    def __init__(self, get_fn):
        self._get_fn = get_fn
    def get(self, url, **kwargs):
        return self._get_fn(url, **kwargs)


class _FakeResp:
    def __init__(self, success, data):
        self.is_success = success
        self._data = data
        self.status_code = 200 if success else 400
        self.content = b"x"
    def json(self):
        return self._data


def test_get_token_email_uses_tokeninfo_primary(monkeypatch):
    """
    Root cause 2 fix: get_token_email() must use Google tokeninfo endpoint as primary.
    tokeninfo works with ANY valid Google token regardless of granted scopes.
    gmail.send only → users.getProfile returns 403 (wrong scope) and
    userinfo returns 401/403 (requires email/openid scope).
    tokeninfo is Google's documented token introspection endpoint.
    """
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if "tokeninfo" in url:
            return _FakeResp(True, {"email": "student@gmail.com", "scope": gmail_oauth.GMAIL_SEND_SCOPE})
        return _FakeResp(False, {})

    import app.gmail.oauth as _oauth_mod
    monkeypatch.setattr(_oauth_mod, "httpx", _FakeHttpx(fake_get))
    email = _oauth_mod.get_token_email("any_access_token")
    assert email == "student@gmail.com"
    assert any("tokeninfo" in c for c in calls), "Must call tokeninfo endpoint"
    assert not any("gmail.googleapis.com" in c for c in calls), \
        "Must NOT call users.getProfile — it requires gmail.readonly/modify scope, not gmail.send"


def test_get_token_email_tokeninfo_passes_token_as_query_param(monkeypatch):
    """
    tokeninfo must receive the access_token as a query parameter (not Authorization header).
    This is Google's documented usage for token introspection.
    """
    received_kwargs = {}

    class FakeHttpxCapture:
        def get(self, url, **kwargs):
            if "tokeninfo" in url:
                received_kwargs.update(kwargs)
                return _FakeResp(True, {"email": "student@gmail.com"})
            return _FakeResp(False, {})

    import app.gmail.oauth as _oauth_mod
    monkeypatch.setattr(_oauth_mod, "httpx", FakeHttpxCapture())
    _oauth_mod.get_token_email("my_test_token")
    assert "params" in received_kwargs, "Token must be passed via params= for tokeninfo"
    assert "access_token" in received_kwargs["params"], "params must contain access_token key"
    # We deliberately do NOT check the value to avoid logging/asserting token values


def test_get_token_email_falls_back_to_userinfo(monkeypatch):
    """When tokeninfo fails, fall back to userinfo endpoint."""
    def fake_get(url, **kwargs):
        if "tokeninfo" in url:
            return _FakeResp(False, {"error": "invalid_token"})
        return _FakeResp(True, {"email": "fallback@gmail.com"})

    import app.gmail.oauth as _oauth_mod
    monkeypatch.setattr(_oauth_mod, "httpx", _FakeHttpx(fake_get))
    email = _oauth_mod.get_token_email("any_access_token")
    assert email == "fallback@gmail.com"


def test_get_token_email_returns_none_when_both_fail(monkeypatch):
    """When both endpoints fail, return None (not an exception)."""
    import app.gmail.oauth as _oauth_mod
    monkeypatch.setattr(_oauth_mod, "httpx", _FakeHttpx(lambda url, **kw: _FakeResp(False, {})))
    assert _oauth_mod.get_token_email("any_access_token") is None


def test_dev_key_persisted_to_disk_survives_reload(tmp_path, monkeypatch):
    """
    Root cause 1 fix: the dev Fernet key must persist to disk so that
    --reload / process restart doesn't generate a new key that breaks
    decryption of tokens stored during a previous process.
    """
    import app.gmail.crypto as _crypto
    key_file = tmp_path / "gmail_dev.key"

    # Patch the file location to our temp path
    monkeypatch.setattr(_crypto, "_DEV_KEY_FILE", key_file)
    monkeypatch.setattr(_crypto, "_dev_key", None)  # reset in-memory cache

    # First "process": encrypt something
    fernet1 = _crypto._get_dev_fernet()
    ciphertext = fernet1.encrypt(b"access_token_abc")

    # Simulate server reload: clear in-memory cache (new process)
    monkeypatch.setattr(_crypto, "_dev_key", None)

    # Second "process": load key from disk and decrypt
    fernet2 = _crypto._get_dev_fernet()
    plaintext = fernet2.decrypt(ciphertext)
    assert plaintext == b"access_token_abc", "Key must be stable across process reload"
    assert key_file.exists(), "Dev key must be persisted to disk"


def test_crypto_encrypt_decrypt_stable_across_simulated_reload(tmp_path, monkeypatch):
    """High-level: encrypt/decrypt round-trip survives a simulated reload."""
    import app.gmail.crypto as _crypto
    monkeypatch.setattr(_crypto, "_DEV_KEY_FILE", tmp_path / "k.key")
    monkeypatch.setattr(_crypto, "_dev_key", None)

    ciphertext = _crypto.encrypt("my_access_token")

    monkeypatch.setattr(_crypto, "_dev_key", None)  # simulate reload

    plaintext = _crypto.decrypt(ciphertext)
    assert plaintext == "my_access_token"


def test_get_status_invalid_token_encrypted_still_returns_connected(monkeypatch):
    """
    If access_token_encrypted is corrupt (wrong key), get_status must still return
    connected=True with email=None. No lazy fetch, no exception surfaced.
    get_status never decrypts tokens — only get_connection/_row_to_connection does.
    """
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "profile_id": "test_pid",
            "provider": "google",
            "provider_account_email": None,
            "access_token_encrypted": "not-a-valid-fernet-token",
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": None,
        }]})(),
    )
    status = gmail_service.get_status("test_pid")
    assert status.connected is True
    assert status.email is None


def test_get_status_connected_true_even_when_email_null(monkeypatch):
    """
    Root cause 2 fix: connected=True must be returned regardless of email.
    The frontend must not show 'not connected' when email is null.
    """
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": None,
            "access_token_encrypted": None,  # can't lazy fetch
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": None,
        }]})(),
    )
    status = gmail_service.get_status("any_pid")
    assert status.connected is True
    assert status.email is None  # email is None but connected is still True


def test_gmail_status_endpoint_returns_connected_true_with_null_email(monkeypatch):
    """
    The /gmail/status API endpoint must return connected=true even when
    provider_account_email is NULL, so the frontend can react correctly.
    """
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": None,
            "access_token_encrypted": None,
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": None,
        }]})(),
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True   # must be true even with null email
    assert data["email"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 8. Gmail disconnect
# ─────────────────────────────────────────────────────────────────────────────

def test_gmail_disconnect(monkeypatch):
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": "s@gmail.com",
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": None,
        }]})(),
    )
    monkeypatch.setattr("app.gmail.service.revoke_token", lambda t: None)
    from app.main import app
    client = TestClient(app)
    resp = client.post("/gmail/disconnect", headers={"X-Profile-Id": str(uuid4())})
    assert resp.status_code == 200
    assert resp.json()["disconnected"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 9. Send validations
# ─────────────────────────────────────────────────────────────────────────────

def _setup_send_test(monkeypatch, *, status="ready", professor_email="prof@uni.edu",
                     cv_version_id=None, gmail_connected=True):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = cv_version_id or str(uuid4())

    r = _make_record(profile_id=profile_id, professor_id=professor_id,
                     status=status, cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr(
        "app.outreach.service.get_professor",
        lambda pid: _prof_row(professor_id, email=professor_email),
    )
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": gmail_connected, "email": "s@gmail.com" if gmail_connected else None})(),
    )
    # Mock CV lookup so it returns the right profile_id
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id, "profile_id": profile_id,
            "file_name": "cv.pdf",
            "description": '{"original_filename":"cv.pdf","file_type":"pdf"}',
            "storage_path": "fake/cv.pdf",
        }]})(),
    )
    # Also mock resolve_storage_path and file existence to avoid fs errors
    import tempfile, pathlib
    _tmp = pathlib.Path(tempfile.mktemp(suffix=".pdf"))
    _tmp.write_bytes(b"fake")
    monkeypatch.setattr("app.outreach.service.resolve_storage_path", lambda p: _tmp)
    return profile_id, r.draft_id, cv_id


def test_send_requires_explicit_confirmation(monkeypatch):
    db_store.clear()
    r = _make_record(status="ready")
    db_store.put(r.draft_id, r)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(
            profile_id=r.profile_id,
            draft_id=r.draft_id,
            confirmed=False,
        )
    assert exc.value.status_code == 400


def test_send_already_sent_rejected(monkeypatch):
    db_store.clear()
    profile_id, draft_id, _ = _setup_send_test(monkeypatch, status="sent")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=draft_id, confirmed=True)
    assert exc.value.status_code == 409


def test_send_missing_professor_email(monkeypatch):
    db_store.clear()
    profile_id, draft_id, _ = _setup_send_test(monkeypatch, professor_email=None)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=draft_id, confirmed=True)
    assert exc.value.status_code == 400
    assert "email" in exc.value.detail.lower()


def test_send_empty_subject_rejected():
    db_store.clear()
    r = _make_record(subject="", status="ready")
    db_store.put(r.draft_id, r)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=r.profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 400


def test_send_empty_body_rejected():
    db_store.clear()
    r = _make_record(body="", status="ready")
    db_store.put(r.draft_id, r)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=r.profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 400


def test_send_missing_gmail_connection(monkeypatch):
    db_store.clear()
    profile_id, draft_id, _ = _setup_send_test(monkeypatch, gmail_connected=False)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=draft_id, confirmed=True)
    assert exc.value.status_code == 400
    assert "gmail" in exc.value.detail.lower()


def test_send_no_cv_attached(monkeypatch):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready")
    r.cv_version_id = None  # no CV attached
    db_store.put(r.draft_id, r)
    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: _prof_row(professor_id))
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "s@gmail.com"})(),
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 400
    assert "cv" in exc.value.detail.lower()


def test_send_cv_ownership_mismatch(monkeypatch):
    """CV belongs to a different profile — should reject."""
    db_store.clear()
    profile_id = str(uuid4())
    other_profile = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())

    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready", cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: _prof_row(professor_id))
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "s@gmail.com"})(),
    )
    # CV row belongs to other_profile
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id, "profile_id": other_profile,
            "file_name": "cv.pdf", "description": "{}", "storage_path": "other/cv.pdf",
        }]})(),
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 10. Successful send (mocked Gmail client)
# ─────────────────────────────────────────────────────────────────────────────

def test_successful_send(monkeypatch, tmp_path):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())

    # Create a real temp CV file
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"%PDF-1.4 fake cv content")

    r = _make_record(profile_id=profile_id, professor_id=professor_id,
                     status="ready", cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: _prof_row(professor_id))
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "student@gmail.com"})(),
    )
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id, "profile_id": profile_id,
            "file_name": "My_CV.pdf", "description": '{"original_filename":"My_CV.pdf","file_type":"pdf"}',
            "storage_path": "fake/path.pdf",
        }]})(),
    )
    monkeypatch.setattr(
        "app.outreach.service.resolve_storage_path",
        lambda path: cv_file,
    )
    monkeypatch.setattr(
        "app.outreach.service.get_valid_access_token",
        lambda pid: "mocked_access_token",
    )
    monkeypatch.setattr(
        "app.outreach.service.build_mime_message",
        lambda **kwargs: {"raw": "encoded"},
    )
    monkeypatch.setattr(
        "app.outreach.service.send_message",
        lambda **kwargs: GmailSendResult(message_id="msg_123", thread_id="thread_456"),
    )

    result = outreach_service.send_draft(
        profile_id=profile_id,
        draft_id=r.draft_id,
        confirmed=True,
    )

    assert result.status == "sent"
    assert result.gmail_message_id == "msg_123"
    assert result.sent_at is not None

    # Verify persisted record
    updated = db_store.get(r.draft_id)
    assert updated.generation_status == "sent"
    assert updated.gmail_message_id == "msg_123"
    assert updated.sent_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 11. Gmail API failure — marks draft as failed
# ─────────────────────────────────────────────────────────────────────────────

def test_gmail_api_failure_marks_draft_failed(monkeypatch, tmp_path):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"fake content")

    r = _make_record(profile_id=profile_id, professor_id=professor_id,
                     status="ready", cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: _prof_row(professor_id))
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "s@gmail.com"})(),
    )
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id, "profile_id": profile_id,
            "file_name": "cv.pdf", "description": '{"original_filename":"cv.pdf","file_type":"pdf"}',
            "storage_path": "fake/path.pdf",
        }]})(),
    )
    monkeypatch.setattr("app.outreach.service.resolve_storage_path", lambda p: cv_file)
    monkeypatch.setattr("app.outreach.service.get_valid_access_token", lambda pid: "tok")
    monkeypatch.setattr("app.outreach.service.build_mime_message", lambda **kw: {"raw": "x"})
    monkeypatch.setattr(
        "app.outreach.service.send_message",
        lambda **kw: (_ for _ in ()).throw(GmailApiError("API error", code="http_403")),
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 502

    failed = db_store.get(r.draft_id)
    assert failed.generation_status == "failed"
    assert failed.error_code is not None


# ─────────────────────────────────────────────────────────────────────────────
# 12. Double-send protection via atomic transition
# ─────────────────────────────────────────────────────────────────────────────

def test_double_send_protection(monkeypatch, tmp_path):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"fake")

    r = _make_record(profile_id=profile_id, professor_id=professor_id,
                     status="ready", cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: _prof_row(professor_id))
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "s@gmail.com"})(),
    )
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": cv_id, "profile_id": profile_id, "file_name": "cv.pdf",
            "description": '{"original_filename":"cv.pdf"}', "storage_path": "fake/p.pdf",
        }]})(),
    )
    monkeypatch.setattr("app.outreach.service.resolve_storage_path", lambda p: cv_file)
    monkeypatch.setattr("app.outreach.service.get_valid_access_token", lambda pid: "tok")
    monkeypatch.setattr("app.outreach.service.build_mime_message", lambda **kw: {"raw": "x"})
    monkeypatch.setattr(
        "app.outreach.service.send_message",
        lambda **kw: GmailSendResult(message_id="msg_ok", thread_id=None),
    )

    outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 13. MIME message construction
# ─────────────────────────────────────────────────────────────────────────────

def test_mime_correct_headers(tmp_path):
    cv_file = tmp_path / "My_CV.pdf"
    cv_file.write_bytes(b"fake pdf content")

    mime = build_mime_message(
        from_addr="student@gmail.com",
        to_addr="prof@uni.edu",
        subject="Research Inquiry",
        body="Dear Professor Smith,\n\nBody.\n\nRegards,\nAisha",
        attachment_path=cv_file,
        attachment_display_name="My_CV.pdf",
    )
    raw_bytes = base64.urlsafe_b64decode(mime["raw"] + "==")
    msg = email_lib.message_from_bytes(raw_bytes)

    assert msg["To"] == "prof@uni.edu"
    assert msg["From"] == "student@gmail.com"
    assert msg["Subject"] == "Research Inquiry"


def test_mime_attachment_present(tmp_path):
    cv_bytes = b"PDF file content here"
    cv_file = tmp_path / "thesis_CV.pdf"
    cv_file.write_bytes(cv_bytes)

    mime = build_mime_message(
        from_addr="s@g.com",
        to_addr="p@u.edu",
        subject="Hi",
        body="Body text",
        attachment_path=cv_file,
        attachment_display_name="thesis_CV.pdf",
    )
    raw_bytes = base64.urlsafe_b64decode(mime["raw"] + "==")
    msg = email_lib.message_from_bytes(raw_bytes)

    attachments = [part for part in msg.walk() if part.get_filename()]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "thesis_CV.pdf"
    assert attachments[0].get_payload(decode=True) == cv_bytes


def test_mime_body_text(tmp_path):
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"pdf")
    body_text = "Dear Professor,\n\nHello.\n\nBest,\nStudent"
    mime = build_mime_message(
        from_addr="a@b.com",
        to_addr="c@d.edu",
        subject="S",
        body=body_text,
        attachment_path=cv_file,
        attachment_display_name="cv.pdf",
    )
    raw_bytes = base64.urlsafe_b64decode(mime["raw"] + "==")
    msg = email_lib.message_from_bytes(raw_bytes)
    text_parts = [p for p in msg.walk() if p.get_content_type() == "text/plain"]
    assert any(body_text in (p.get_payload(decode=True) or b"").decode("utf-8", errors="ignore")
               for p in text_parts)


# ─────────────────────────────────────────────────────────────────────────────
# 14. Token refresh behavior
# ─────────────────────────────────────────────────────────────────────────────

def test_token_refresh_on_expiry(monkeypatch):
    profile_id = str(uuid4())
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    encrypted_access = gmail_crypto.encrypt("old_access_token")
    encrypted_refresh = gmail_crypto.encrypt("my_refresh_token")

    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "profile_id": profile_id,
            "provider": "google",
            "provider_account_email": "s@gmail.com",
            "access_token_encrypted": encrypted_access,
            "refresh_token_encrypted": encrypted_refresh,
            "token_expires_at": expired_at,
            "scopes": gmail_oauth.GMAIL_SEND_SCOPE,
            "revoked_at": None,
        }]})(),
    )
    monkeypatch.setattr(
        "app.gmail.service.refresh_access_token",
        lambda rt: {"access_token": "new_token", "expires_in": 3600},
    )

    new_token = gmail_service.get_valid_access_token(profile_id)
    assert new_token == "new_token"


def test_token_refresh_failure_raises_401(monkeypatch):
    profile_id = str(uuid4())
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()

    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "profile_id": profile_id,
            "provider": "google",
            "provider_account_email": "s@gmail.com",
            "access_token_encrypted": gmail_crypto.encrypt("old"),
            "refresh_token_encrypted": gmail_crypto.encrypt("refresh"),
            "token_expires_at": expired_at,
            "scopes": gmail_oauth.GMAIL_SEND_SCOPE,
            "revoked_at": None,
        }]})(),
    )
    monkeypatch.setattr(
        "app.gmail.service.refresh_access_token",
        lambda rt: (_ for _ in ()).throw(Exception("network error")),
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        gmail_service.get_valid_access_token(profile_id)
    assert exc.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 15. History listing
# ─────────────────────────────────────────────────────────────────────────────

def test_history_returns_all_drafts():
    db_store.clear()
    pid = str(uuid4())
    for status in ("generated", "ready", "sent", "failed"):
        r = _make_record(profile_id=pid, status=status)
        r.professor_name = "Prof X"
        db_store.put(r.draft_id, r)
    items = outreach_service.list_history(profile_id=pid)
    statuses = {i.status for i in items}
    assert "sent" in statuses
    assert "failed" in statuses


# ─────────────────────────────────────────────────────────────────────────────
# 16. New pages are registered
# ─────────────────────────────────────────────────────────────────────────────

def test_history_page_exists():
    from app.main import app
    client = TestClient(app)
    # Legacy HTML history view was removed; React owns /outreach/history.
    assert client.get("/outreach/history-view").status_code == 404


def test_gmail_connected_page_exists():
    from app.main import app
    client = TestClient(app)
    assert client.get("/outreach/gmail-connected").status_code == 404


def test_gmail_error_page_exists():
    from app.main import app
    client = TestClient(app)
    assert client.get("/outreach/gmail-callback-error").status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 17. API routes registered
# ─────────────────────────────────────────────────────────────────────────────

def test_phase6_routes_registered():
    from app.main import app
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/outreach/cv-versions" in paths
    assert "/outreach/drafts/{draft_id}/attach-cv" in paths
    assert "/outreach/drafts/{draft_id}/send" in paths
    assert "/outreach/drafts/{draft_id}/preview" in paths
    assert "/outreach/history" in paths
    assert "/gmail/status" in paths
    assert "/gmail/connect" in paths
    assert "/gmail/disconnect" in paths


# ─────────────────────────────────────────────────────────────────────────────
# 18. No tokens in API responses
# ─────────────────────────────────────────────────────────────────────────────

def test_gmail_status_never_returns_tokens(monkeypatch):
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": "s@g.com",
            "access_token_encrypted": gmail_crypto.encrypt("secret_access_token"),
            "refresh_token_encrypted": gmail_crypto.encrypt("secret_refresh_token"),
            "token_expires_at": None,
            "scopes": None,
            "revoked_at": None,
        }]})(),
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    body = resp.text
    assert "secret_access_token" not in body
    assert "secret_refresh_token" not in body
    assert "access_token_encrypted" not in body
    assert "refresh_token_encrypted" not in body


# ─────────────────────────────────────────────────────────────────────────────
# 19. Invalid professor email formats rejected
# ─────────────────────────────────────────────────────────────────────────────

def test_invalid_professor_email_rejected(monkeypatch):
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())

    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready",
                     cv_version_id=str(uuid4()))
    db_store.put(r.draft_id, r)

    monkeypatch.setattr(
        "app.outreach.service.get_professor",
        lambda pid: _prof_row(professor_id, email="not-an-email"),
    )
    monkeypatch.setattr(
        "app.outreach.service.get_status",
        lambda pid: type("S", (), {"connected": True, "email": "s@gmail.com"})(),
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 400
    assert "email" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 20. Send endpoint requires X-Profile-Id
# ─────────────────────────────────────────────────────────────────────────────

def test_send_endpoint_requires_profile_id():
    from app.main import app
    client = TestClient(app)
    resp = client.post(f"/outreach/drafts/{uuid4()}/send", json={"confirmed": True})
    assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 21. email=null is a VALID connected state (architectural requirement)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_status_connected_true_email_none_is_valid(monkeypatch):
    """connected=True with email=None must be returned unchanged — no lazy fetch."""
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": None,    # no email — normal with gmail.send scope
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": "https://www.googleapis.com/auth/gmail.send",
            "revoked_at": None,
        }]})(),
    )
    status = gmail_service.get_status(str(uuid4()))
    assert status.connected is True
    assert status.email is None  # accepted — not an error


def test_get_status_no_tokeninfo_call_made(monkeypatch):
    """get_status must NOT call get_token_email / tokeninfo on every request."""
    import httpx

    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": None,
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": "https://www.googleapis.com/auth/gmail.send",
            "revoked_at": None,
        }]})(),
    )

    called = []
    original_get = httpx.get
    def spy_get(url, **kwargs):  # noqa: ANN001
        called.append(url)
        return original_get(url, **kwargs)

    monkeypatch.setattr("app.gmail.oauth.httpx.get", spy_get)

    gmail_service.get_status(str(uuid4()))
    # tokeninfo / userinfo must NOT have been contacted
    assert all("tokeninfo" not in u and "userinfo" not in u for u in called), (
        f"get_status made unexpected HTTP call(s): {called}"
    )


def test_gmail_status_endpoint_email_null_returns_connected_true(monkeypatch):
    """HTTP endpoint: email=null + connected=true must be a 200 with connected=true."""
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": None,
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": "https://www.googleapis.com/auth/gmail.send",
            "revoked_at": None,
        }]})(),
    )
    from app.main import app
    client = TestClient(app)
    resp = client.get("/gmail/status", headers={"X-Profile-Id": str(uuid4())})
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["email"] is None  # null is valid


# ─────────────────────────────────────────────────────────────────────────────
# 22. Send path does NOT require provider_account_email
# ─────────────────────────────────────────────────────────────────────────────

def _gmail_status_no_email(pid):  # noqa: ANN001
    return type("S", (), {"connected": True, "email": None})()


def test_send_draft_succeeds_with_null_gmail_email(monkeypatch, tmp_path):
    """send_draft must complete when Gmail is connected but email is None."""
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"%PDF-dummy")

    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready",
                     cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor",
                        lambda pid: _prof_row(professor_id, email="prof@uni.edu"))
    monkeypatch.setattr("app.outreach.service.get_status", _gmail_status_no_email)
    monkeypatch.setattr("app.outreach.service._load_cv_row",
                        lambda cv_id, profile_id: {
                            "id": cv_id, "profile_id": profile_id,
                            "original_filename": "cv.pdf",
                            "_storage_path": str(cv_file),
                        })
    monkeypatch.setattr("app.outreach.service._validate_cv_file", lambda row: None)
    monkeypatch.setattr("app.outreach.service._cv_display_name", lambda row: "cv.pdf")
    monkeypatch.setattr("app.outreach.service.get_valid_access_token", lambda pid: "access_tok")
    monkeypatch.setattr(
        "app.outreach.service.send_message",
        lambda **kw: GmailSendResult(message_id="msg_id_123", thread_id="thr_1"),
    )
    monkeypatch.setattr("app.outreach.service.resolve_storage_path", lambda p: Path(p))

    result = outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert result.status == "sent"
    assert result.gmail_message_id == "msg_id_123"


def test_validate_for_send_rejects_disconnected_not_missing_email(monkeypatch):
    """_validate_for_send must reject when connected=False, not when email=None."""
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())

    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready",
                     cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor",
                        lambda pid: _prof_row(professor_id, email="p@x.edu"))
    # connected=False is the only thing that should block sending
    monkeypatch.setattr("app.outreach.service.get_status",
                        lambda pid: type("S", (), {"connected": False, "email": None})())
    monkeypatch.setattr("app.outreach.service._load_cv_row",
                        lambda cv_id, profile_id: {
                            "id": cv_id, "profile_id": profile_id,
                            "original_filename": "cv.pdf",
                            "_storage_path": "/tmp/cv.pdf",
                        })
    monkeypatch.setattr("app.outreach.service._validate_cv_file", lambda row: None)
    monkeypatch.setattr("app.outreach.service._cv_display_name", lambda row: "cv.pdf")

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 400
    assert "not connected" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 23. Expired access token is refreshed before send
# ─────────────────────────────────────────────────────────────────────────────

def test_expired_token_is_refreshed(monkeypatch):
    """get_valid_access_token must use refresh_token when access_token is expired."""
    profile_id = str(uuid4())

    # Expired 5 minutes ago
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    # Row with encrypted tokens
    row = {
        "id": str(uuid4()),
        "profile_id": profile_id,
        "provider": "google",
        "provider_account_email": None,
        "access_token_encrypted": gmail_crypto.encrypt("old_access_token"),
        "refresh_token_encrypted": gmail_crypto.encrypt("stored_refresh_token"),
        "token_expires_at": expired_at.isoformat(),
        "scopes": "https://www.googleapis.com/auth/gmail.send",
        "revoked_at": None,
    }
    monkeypatch.setattr("app.gmail.service.execute",
                        lambda q: type("R", (), {"data": [row]})())

    refresh_called = []
    def mock_refresh(refresh_token):  # noqa: ANN001
        refresh_called.append(refresh_token)
        return {"access_token": "new_access_token", "expires_in": 3600}

    monkeypatch.setattr("app.gmail.service.refresh_access_token", mock_refresh)

    token = gmail_service.get_valid_access_token(profile_id)
    assert token == "new_access_token"
    assert len(refresh_called) == 1
    assert refresh_called[0] == "stored_refresh_token"  # correct refresh token used


def test_expired_token_no_refresh_token_raises(monkeypatch):
    """When the access token is expired and there is no refresh_token, raise 401."""
    from fastapi import HTTPException
    profile_id = str(uuid4())

    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    row = {
        "id": str(uuid4()),
        "profile_id": profile_id,
        "provider": "google",
        "provider_account_email": None,
        "access_token_encrypted": gmail_crypto.encrypt("old_token"),
        "refresh_token_encrypted": None,   # no refresh token stored
        "token_expires_at": expired_at.isoformat(),
        "scopes": "https://www.googleapis.com/auth/gmail.send",
        "revoked_at": None,
    }
    monkeypatch.setattr("app.gmail.service.execute",
                        lambda q: type("R", (), {"data": [row]})())

    with pytest.raises(HTTPException) as exc:
        gmail_service.get_valid_access_token(profile_id)
    assert exc.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 24. Revoked / invalid credentials reported as reconnect-required
# ─────────────────────────────────────────────────────────────────────────────

def test_revoked_connection_returns_not_connected(monkeypatch):
    """A row with revoked_at set must return connected=False."""
    monkeypatch.setattr(
        "app.gmail.service.execute",
        lambda q: type("R", (), {"data": [{
            "id": str(uuid4()),
            "provider": "google",
            "provider_account_email": "old@gmail.com",
            "access_token_encrypted": gmail_crypto.encrypt("tok"),
            "refresh_token_encrypted": None,
            "token_expires_at": None,
            "scopes": "https://www.googleapis.com/auth/gmail.send",
            "revoked_at": datetime.now(timezone.utc).isoformat(),
        }]})(),
    )
    status = gmail_service.get_status(str(uuid4()))
    assert status.connected is False


def test_gmail_api_error_marks_draft_failed(monkeypatch, tmp_path):
    """When Gmail API raises GmailApiError, draft becomes 'failed' and 502 is raised."""
    db_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    cv_id = str(uuid4())
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"%PDF-dummy")

    r = _make_record(profile_id=profile_id, professor_id=professor_id, status="ready",
                     cv_version_id=cv_id)
    db_store.put(r.draft_id, r)

    monkeypatch.setattr("app.outreach.service.get_professor",
                        lambda pid: _prof_row(professor_id, email="prof@uni.edu"))
    monkeypatch.setattr("app.outreach.service.get_status", _gmail_status_no_email)
    monkeypatch.setattr("app.outreach.service._load_cv_row",
                        lambda cid, pid: {
                            "id": cid, "profile_id": pid,
                            "original_filename": "cv.pdf",
                            "_storage_path": str(cv_file),
                        })
    monkeypatch.setattr("app.outreach.service._validate_cv_file", lambda row: None)
    monkeypatch.setattr("app.outreach.service._cv_display_name", lambda row: "cv.pdf")
    monkeypatch.setattr("app.outreach.service.get_valid_access_token", lambda pid: "tok")
    monkeypatch.setattr("app.outreach.service.resolve_storage_path", lambda p: Path(p))
    monkeypatch.setattr(
        "app.outreach.service.send_message",
        lambda **kw: (_ for _ in ()).throw(GmailApiError("invalid credentials", code="http_401")),
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.send_draft(profile_id=profile_id, draft_id=r.draft_id, confirmed=True)
    assert exc.value.status_code == 502

    # draft must be marked failed
    updated = db_store.get(r.draft_id)
    assert updated.generation_status == "failed"
    assert updated.error_code == "http_401"


# ─────────────────────────────────────────────────────────────────────────────
# 25. OAuth scope is exactly gmail.send — not broader
# ─────────────────────────────────────────────────────────────────────────────

def test_oauth_scope_is_gmail_send_only():
    """GMAIL_SEND_SCOPE constant must be exactly the send scope, nothing broader."""
    from app.gmail.oauth import GMAIL_SEND_SCOPE
    assert GMAIL_SEND_SCOPE == "https://www.googleapis.com/auth/gmail.send"
    # Must not contain any broader scopes
    forbidden = ("gmail.readonly", "gmail.compose", "gmail.modify",
                 "openid", "email", "profile")
    for f in forbidden:
        assert f not in GMAIL_SEND_SCOPE, f"Scope must not include '{f}'"


def test_build_authorization_url_uses_only_gmail_send_scope(monkeypatch):
    """The authorization URL must request only gmail.send."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost/callback")

    from app.gmail.oauth import authorization_url
    url = authorization_url(profile_id=str(uuid4()))
    assert "gmail.send" in url
    for forbidden in ("gmail.readonly", "gmail.compose", "openid", "profile", "email"):
        assert forbidden not in url, f"Authorization URL must not include scope '{forbidden}'"


# ─────────────────────────────────────────────────────────────────────────────
# 26. build_mime_message works when from_addr is None
# ─────────────────────────────────────────────────────────────────────────────

def test_build_mime_message_from_addr_none(tmp_path):
    """build_mime_message must not raise when from_addr is None."""
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"%PDF-test")

    msg = build_mime_message(
        from_addr=None,
        to_addr="prof@uni.edu",
        subject="Hello",
        body="Dear Professor,",
        attachment_path=cv_file,
        attachment_display_name="cv.pdf",
    )
    assert "raw" in msg
    # Decode and verify From is absent (or empty)
    raw_bytes = base64.urlsafe_b64decode(msg["raw"])
    parsed = email_lib.message_from_bytes(raw_bytes)
    assert parsed["From"] is None or parsed["From"] == ""


def test_build_mime_message_from_addr_empty_string(tmp_path):
    """build_mime_message must not raise when from_addr is empty string."""
    cv_file = tmp_path / "cv.pdf"
    cv_file.write_bytes(b"%PDF-test")

    msg = build_mime_message(
        from_addr="",
        to_addr="prof@uni.edu",
        subject="Subject",
        body="Body",
        attachment_path=cv_file,
        attachment_display_name="cv.pdf",
    )
    assert "raw" in msg
