"""
Regression tests for CORS configuration (production hardening, Task 7):
allow_origins must be an explicit allow-list, not "*", since allow_credentials
is True and auth headers (Authorization, X-Profile-Id) are honored — a
wildcard would let any website's JavaScript make cross-origin calls against
this API and read the response.
"""
from app.main import _cors_allowed_origins


def test_cors_does_not_allow_wildcard_origin():
    origins = _cors_allowed_origins()
    assert "*" not in origins


def test_cors_allows_known_production_frontend_by_default():
    assert "https://findmyprofessor.online" in _cors_allowed_origins()


def test_cors_allows_local_dev_server():
    origins = _cors_allowed_origins()
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins


def test_cors_includes_frontend_url_env_var(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://staging.findmyprofessor.online/")
    assert "https://staging.findmyprofessor.online" in _cors_allowed_origins()


def test_cors_includes_extra_origins_env_var(monkeypatch):
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", "https://preview-1.example.com, https://preview-2.example.com/")
    origins = _cors_allowed_origins()
    assert "https://preview-1.example.com" in origins
    assert "https://preview-2.example.com" in origins


def test_cors_preflight_rejects_untrusted_origin(client):
    res = client.options(
        "/universities",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_cors_preflight_allows_production_frontend_origin(client):
    res = client.options(
        "/universities",
        headers={
            "Origin": "https://findmyprofessor.online",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "https://findmyprofessor.online"
