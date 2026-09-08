import pytest
from fastapi.testclient import TestClient

from app.cv import storage
from tests.builders import docx_bytes, txt_bytes
from tests.sample_cv import SAMPLE_CV


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "cv_uploads")
    from app.main import app

    return TestClient(app)


def test_upload_parse_edit_confirm_and_preserve_original(client, tmp_path):
    content = txt_bytes(SAMPLE_CV)
    response = client.post(
        "/cv/upload",
        files={"file": ("cv.txt", content, "text/plain")},
    )
    if response.status_code == 503:
        pytest.skip(response.json().get("detail", "profile insert unavailable"))
    assert response.status_code == 200, response.text
    payload = response.json()
    profile_id = payload["profile_id"]
    try:
        _assert_upload_flow(client, tmp_path, content, payload)
    finally:
        _cleanup_profile(profile_id)


def _assert_upload_flow(client, tmp_path, content, payload):
    assert payload["parsing_status"] == "parsed"
    assert payload["original_filename"] == "cv.txt"
    assert payload["file_type"] == "txt"
    assert payload["file_size"] == len(content)
    profile_id = payload["profile_id"]
    cv_id = payload["cv_id"]
    stored = list((tmp_path / "cv_uploads").rglob("cv.txt"))
    assert stored
    assert stored[0].read_bytes() == content

    fetched = client.get(f"/cv/{cv_id}", headers={"X-Profile-Id": profile_id})
    assert fetched.status_code == 200
    assert fetched.json()["extracted_profile"]["identity"]["name"] == "Alex Rivera"

    edited = payload["extracted_profile"]
    edited["research_interests"] = ["Computer Vision", "Medical AI", "Efficient AI"]
    updated = client.put(
        "/profile",
        headers={"X-Profile-Id": profile_id, "Content-Type": "application/json"},
        json={"extracted_profile": edited},
    )
    assert updated.status_code == 200, updated.text
    assert "Efficient AI" in updated.json()["extracted_profile"]["research_interests"]

    confirmed = client.post("/profile/confirm", headers={"X-Profile-Id": profile_id})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["confirmed"] is True

    profile = client.get("/profile", headers={"X-Profile-Id": profile_id})
    assert profile.status_code == 200
    assert profile.json()["confirmed"] is True
    assert profile.json()["persisted"]["full_name"] == "Alex Rivera"


def test_unsupported_upload_rejected(client):
    response = client.post(
        "/cv/upload",
        files={"file": ("notes.png", b"\x89PNG\r\n\x1a\n" + b"abcd", "image/png")},
    )
    assert response.status_code == 415


def test_corrupt_upload_preserves_file(client, tmp_path):
    content = b"%PDF-1.4\nnot-a-real-pdf"
    response = client.post(
        "/cv/upload",
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    if response.status_code == 503:
        pytest.skip(response.json().get("detail", "profile insert unavailable"))
    assert response.status_code == 200
    body = response.json()
    try:
        assert body["parsing_status"] == "failed"
        assert body["parsing_error"]
        stored = list((tmp_path / "cv_uploads").rglob("cv.pdf"))
        assert stored and stored[0].read_bytes() == content
    finally:
        _cleanup_profile(body["profile_id"])


def test_docx_upload_selects_docx_parser(client):
    response = client.post(
        "/cv/upload",
        files={
            "file": (
                "cv.docx",
                docx_bytes(SAMPLE_CV),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    if response.status_code == 503:
        pytest.skip(response.json().get("detail", "profile insert unavailable"))
    assert response.status_code == 200
    body = response.json()
    try:
        assert body["file_type"] == "docx"
        assert body["parsing_status"] == "parsed"
    finally:
        _cleanup_profile(body["profile_id"])


def test_onboarding_page_available(client):
    response = client.get("/onboarding")
    assert response.status_code == 200
    assert b"CV-first" in response.content


def _cleanup_profile(profile_id: str) -> None:
    from app.supabase_client import supabase

    supabase.table("student_projects").delete().eq("profile_id", profile_id).execute()
    supabase.table("student_publications").delete().eq("profile_id", profile_id).execute()
    supabase.table("student_research_areas").delete().eq("profile_id", profile_id).execute()
    supabase.table("cv_versions").delete().eq("profile_id", profile_id).execute()
    supabase.table("profiles").delete().eq("id", profile_id).execute()
    try:
        supabase.auth.admin.delete_user(profile_id)
    except Exception:
        pass
