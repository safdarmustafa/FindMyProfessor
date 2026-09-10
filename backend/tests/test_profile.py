from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from tests.conftest import PROFILE_ID


def test_get_profile_requires_header(client):
    # Production hardening: a request with neither a Supabase session nor
    # X-Profile-Id is genuinely unauthenticated, so this is now 401 (was
    # 400) — see app/auth.py.
    res = client.get("/profile")
    assert res.status_code == 401
    assert "X-Profile-Id" in res.json()["detail"]


def test_get_profile_returns_user_profile(client, auth_headers):
    payload = {
        "profile_id": PROFILE_ID,
        "confirmed": True,
        "cv_id": str(uuid4()),
        "extracted_profile": {
            "identity": {"name": "Ada Lovelace"},
            "research_interests": ["Computer Vision"],
            "research_signals": [],
            "skills": [],
            "education": [],
            "projects": [],
        },
    }
    with patch("app.routers.profile.cv_service.get_active_profile", return_value=payload):
        res = client.get("/profile", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["profile_id"] == PROFILE_ID
    assert body["extracted_profile"]["identity"]["name"] == "Ada Lovelace"
    assert "Computer Vision" in body["extracted_profile"]["research_interests"]


def test_cv_upload_accepts_pdf_and_returns_extracted_data(client, auth_headers):
    extracted = {
        "cv_id": str(uuid4()),
        "profile_id": PROFILE_ID,
        "original_filename": "cv.pdf",
        "file_type": "pdf",
        "file_size": 12,
        "parsing_status": "parsed",
        "parsing_error": None,
        "is_default": True,
        "extracted_profile": {
            "identity": {"name": "Ada"},
            "research_interests": ["NLP"],
        },
    }
    with patch("app.routers.cv.cv_service.upload_and_parse", return_value=extracted):
        res = client.post(
            "/cv/upload",
            headers=auth_headers,
            files={"file": ("cv.pdf", BytesIO(b"%PDF-test"), "application/pdf")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["profile_id"] == PROFILE_ID
    assert body["extracted_profile"]["research_interests"] == ["NLP"]


def test_list_cv_versions_via_outreach(client, auth_headers):
    versions = [
        {
            "cv_version_id": str(uuid4()),
            "display_name": "Resume.pdf",
            "file_type": "pdf",
            "is_default": True,
            "confirmed": True,
        }
    ]
    with patch("app.routers.outreach.outreach_service.list_cv_versions", return_value=versions):
        res = client.get("/outreach/cv-versions", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()[0]["display_name"] == "Resume.pdf"
