from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from tests.conftest import PROFILE_ID


def test_gmail_status_requires_profile(client):
    res = client.get("/gmail/status")
    assert res.status_code == 400
    assert "X-Profile-Id" in res.json()["detail"]


def test_gmail_status_connected_true(client, auth_headers):
    status = SimpleNamespace(connected=True, email="me@gmail.com")
    with patch("app.routers.gmail.gmail_service.get_status", return_value=status):
        res = client.get("/gmail/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == {"connected": True, "email": "me@gmail.com"}


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


def test_gmail_callback_denied_redirects_to_frontend_error(client):
    res = client.get("/gmail/callback", params={"error": "access_denied"})
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-callback-error?reason=denied"


def test_gmail_callback_success_redirects_to_frontend(client):
    with patch("app.routers.gmail.gmail_oauth.consume_state", return_value=PROFILE_ID), \
         patch("app.routers.gmail.gmail_oauth.exchange_code", return_value={"access_token": "tok", "refresh_token": "r", "expires_in": 3600}), \
         patch("app.routers.gmail.gmail_oauth.get_token_email", return_value="me@gmail.com"), \
         patch("app.routers.gmail.gmail_service.upsert_connection"):
        res = client.get("/gmail/callback", params={"code": "abc", "state": "state-1"})
    assert res.status_code == 302
    assert res.headers["location"] == "http://localhost:5173/outreach/gmail-connected"


def test_gmail_disconnect(client, auth_headers):
    with patch("app.routers.gmail.gmail_service.disconnect") as mock_disc:
        res = client.post("/gmail/disconnect", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["disconnected"] is True
    mock_disc.assert_called_once_with(PROFILE_ID)
