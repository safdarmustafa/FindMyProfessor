from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from tests.conftest import PROFILE_ID
from app.gmail import oauth as gmail_oauth


def test_gmail_status_requires_profile(client):
    # Production hardening: no Supabase session and no X-Profile-Id is
    # genuinely unauthenticated, so this is now 401 (was 400) — app/auth.py.
    res = client.get("/gmail/status")
    assert res.status_code == 401
    assert "X-Profile-Id" in res.json()["detail"]


def test_gmail_status_connected_true(client, auth_headers):
    status = SimpleNamespace(connected=True, email="me@gmail.com")
    with patch("app.routers.gmail.gmail_service.get_status", return_value=status):
        res = client.get("/gmail/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == {"connected": True, "email": "me@gmail.com", "needs_reconnect": False}


def test_gmail_status_connected_false(client, auth_headers):
    status = SimpleNamespace(connected=False, email=None)
    with patch("app.routers.gmail.gmail_service.get_status", return_value=status):
        res = client.get("/gmail/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["connected"] is False


def test_gmail_connect_redirects_to_google(client):
    with patch("app.routers.gmail.gmail_oauth.authorization_url", return_value="https://accounts.google.com/o/oauth2/v2/auth?x=1"):
        res = client.get("/gmail/connect", params={"profile_id": PROFILE_ID})
    assert res.status_code == 302
    assert "accounts.google.com" in res.headers["location"]


def test_gmail_connect_requires_profile(client):
    res = client.get("/gmail/connect")
    assert res.status_code == 400


def test_gmail_connect_passes_return_to_to_authorization_url(client):
    with patch(
        "app.routers.gmail.gmail_oauth.authorization_url",
        return_value="https://accounts.google.com/o/oauth2/v2/auth?x=1",
    ) as mock_auth_url:
        res = client.get(
            "/gmail/connect",
            params={"profile_id": PROFILE_ID, "return_to": "/outreach/compose/prof-123"},
        )
    assert res.status_code == 302
    mock_auth_url.assert_called_once_with(PROFILE_ID, "/outreach/compose/prof-123")


def test_gmail_connect_rejects_unsafe_return_to(client):
    """An absolute or protocol-relative return_to must never reach authorization_url."""
    with patch(
        "app.routers.gmail.gmail_oauth.authorization_url",
        return_value="https://accounts.google.com/o/oauth2/v2/auth?x=1",
    ) as mock_auth_url:
        res = client.get(
            "/gmail/connect",
            params={"profile_id": PROFILE_ID, "return_to": "https://evil.example.com/phish"},
        )
    assert res.status_code == 302
    mock_auth_url.assert_called_once_with(PROFILE_ID, None)


def test_gmail_callback_denied_redirects_to_frontend_error(client):
    res = client.get("/gmail/callback", params={"error": "access_denied"})
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-callback-error?reason=denied"


def test_gmail_callback_success_redirects_to_frontend(client):
    with patch("app.routers.gmail.gmail_oauth.consume_state", return_value={"profile_id": PROFILE_ID, "return_to": None}), \
         patch("app.routers.gmail.gmail_oauth.exchange_code", return_value={"access_token": "tok", "refresh_token": "r", "expires_in": 3600}), \
         patch("app.routers.gmail.gmail_oauth.get_token_email", return_value="me@gmail.com"), \
         patch("app.routers.gmail.gmail_service.upsert_connection"):
        res = client.get("/gmail/callback", params={"code": "abc", "state": "state-1"})
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-connected"


def test_gmail_callback_round_trip_preserves_return_to(client):
    """
    Exercises the REAL create_state/consume_state pair (only the external
    Google/DB calls are mocked) — the originating compose path must survive
    the full OAuth state round trip, not just localStorage.
    """
    state = gmail_oauth.create_state(PROFILE_ID, "/outreach/compose/prof-123")

    with patch("app.routers.gmail.gmail_oauth.exchange_code", return_value={"access_token": "tok", "refresh_token": "r", "expires_in": 3600}), \
         patch("app.routers.gmail.gmail_oauth.get_token_email", return_value="me@gmail.com"), \
         patch("app.routers.gmail.gmail_service.upsert_connection"):
        res = client.get("/gmail/callback", params={"code": "abc", "state": state})

    assert res.status_code == 302
    assert res.headers["location"] == (
        "http://localhost:5173/outreach/gmail-connected?return_to=%2Foutreach%2Fcompose%2Fprof-123"
    )


def test_gmail_callback_no_return_to_omits_query_param(client):
    """When /gmail/connect was called without return_to, the redirect stays bare."""
    state = gmail_oauth.create_state(PROFILE_ID)

    with patch("app.routers.gmail.gmail_oauth.exchange_code", return_value={"access_token": "tok", "refresh_token": "r", "expires_in": 3600}), \
         patch("app.routers.gmail.gmail_oauth.get_token_email", return_value="me@gmail.com"), \
         patch("app.routers.gmail.gmail_service.upsert_connection"):
        res = client.get("/gmail/callback", params={"code": "abc", "state": state})

    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-connected"


def test_gmail_callback_invalid_state_redirects_to_error_safely(client):
    """An unrecognized/expired state token must fail safely, not crash."""
    with patch("app.routers.gmail.gmail_oauth.consume_state", return_value=None):
        res = client.get("/gmail/callback", params={"code": "abc", "state": "not-a-real-token"})
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-callback-error?reason=invalid_state"


def test_gmail_disconnect(client, auth_headers):
    with patch("app.routers.gmail.gmail_service.disconnect") as mock_disc:
        res = client.post("/gmail/disconnect", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["disconnected"] is True
    mock_disc.assert_called_once_with(PROFILE_ID)


def test_gmail_callback_refuses_localhost_fallback_in_production(client, monkeypatch):
    """
    In production, a missing FRONTEND_URL must fail loudly (500) rather than
    silently redirect a real user's browser to a localhost URL.
    """
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("RENDER", raising=False)
    res = client.get("/gmail/callback", params={"code": "abc", "state": "whatever"})
    assert res.status_code == 500


def test_gmail_callback_refuses_localhost_fallback_on_render_even_without_environment_var(client, monkeypatch):
    """
    Live production bug: every user's first Gmail connect succeeded (the
    token exchange completed and the connection was saved), but the final
    redirect after success landed on http://localhost:5173 — "no internet"
    on the user's device — because FRONTEND_URL was unset on Render AND
    ENVIRONMENT was never set to "production" either, so the old guard
    (gated only on ENVIRONMENT=="production") silently returned the
    localhost fallback instead of failing loudly. Render injects RENDER=true
    into every deployed service automatically, so checking that too closes
    this gap even when ENVIRONMENT is left unset — exactly this scenario.
    """
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("RENDER", "true")
    res = client.get("/gmail/callback", params={"code": "abc", "state": "whatever"})
    assert res.status_code == 500


def test_gmail_callback_still_falls_back_to_localhost_for_real_local_development(client, monkeypatch):
    """Neither ENVIRONMENT=production nor RENDER set (a developer's own
    machine) must keep working exactly as before — this is not weakened."""
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    with patch("app.routers.gmail.gmail_oauth.consume_state", return_value=None):
        res = client.get("/gmail/callback", params={"code": "abc", "state": "not-a-real-token"})
    assert res.status_code == 302
    assert res.headers["location"].startswith("http://localhost:5173")


def test_gmail_status_reports_needs_reconnect(client, auth_headers):
    status = SimpleNamespace(connected=False, email=None, needs_reconnect=True)
    with patch("app.routers.gmail.gmail_service.get_status", return_value=status):
        res = client.get("/gmail/status", headers=auth_headers)
    assert res.json() == {"connected": False, "email": None, "needs_reconnect": True}
