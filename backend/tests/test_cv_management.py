"""
End-to-end CV management against the real database (same pattern as
test_cv_api.py): upload versions, list, switch the active CV, delete, and
ownership isolation. Files go to a temp local directory; every row created
here is removed afterwards.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.cv import storage
from tests.builders import txt_bytes
from tests.sample_cv import SAMPLE_CV
from tests.test_cv_api import _cleanup_profile


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "cv_uploads")
    from app.main import app

    return TestClient(app)


def _upload(client, name: str, profile_id: str | None = None):
    headers = {"X-Profile-Id": profile_id} if profile_id else {}
    response = client.post(
        "/cv/upload",
        headers=headers,
        files={"file": (name, txt_bytes(SAMPLE_CV), "text/plain")},
    )
    if response.status_code == 503:
        pytest.skip(response.json().get("detail", "database unavailable"))
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_list_switch_and_delete_cv_versions(client, tmp_path):
    first = _upload(client, "first.txt")
    profile_id = first["profile_id"]
    headers = {"X-Profile-Id": profile_id}
    try:
        second = _upload(client, "second.txt", profile_id)

        # Newest first; only the latest upload is active; files are present.
        listed = client.get("/cv", headers=headers).json()
        assert [v["file_name"] for v in listed] == ["second.txt", "first.txt"]
        assert [v["is_default"] for v in listed] == [True, False]
        assert all(v["file_available"] for v in listed)

        # Switch the active CV back to the first upload.
        switched = client.post(f"/cv/{first['cv_id']}/default", headers=headers)
        assert switched.status_code == 200, switched.text
        assert {v["file_name"]: v["is_default"] for v in switched.json()} == {"first.txt": True, "second.txt": False}
        assert client.get("/profile", headers=headers).json()["cv_id"] == first["cv_id"]

        # Deleting the active CV promotes the remaining one and removes the file.
        deleted = client.delete(f"/cv/{first['cv_id']}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        remaining = deleted.json()
        assert [(v["file_name"], v["is_default"]) for v in remaining] == [("second.txt", True)]
        assert not list((tmp_path / "cv_uploads").rglob("first.txt"))
        assert list((tmp_path / "cv_uploads").rglob("second.txt"))

        # The attach-CV list used by the compose page agrees.
        attachable = client.get("/outreach/cv-versions", headers=headers).json()
        assert [(v["display_name"], v["file_available"]) for v in attachable] == [("second.txt", True)]

        # Deleting the last CV leaves an empty list and no active profile CV.
        assert client.delete(f"/cv/{second['cv_id']}", headers=headers).json() == []
        assert client.get("/profile", headers=headers).json()["cv_id"] is None
    finally:
        _cleanup_profile(profile_id)


def test_missing_file_is_reported_not_hidden(client, tmp_path):
    upload = _upload(client, "gone.txt")
    profile_id = upload["profile_id"]
    try:
        for path in (tmp_path / "cv_uploads").rglob("gone.txt"):
            path.unlink()
        listed = client.get("/cv", headers={"X-Profile-Id": profile_id}).json()
        assert listed[0]["file_available"] is False
        # It can still be deleted cleanly.
        assert client.delete(f"/cv/{upload['cv_id']}", headers={"X-Profile-Id": profile_id}).status_code == 200
    finally:
        _cleanup_profile(profile_id)


def test_cannot_manage_another_profiles_cv(client):
    owner = _upload(client, "owner.txt")
    intruder = _upload(client, "intruder.txt")
    try:
        cv_id = owner["cv_id"]
        intruder_headers = {"X-Profile-Id": intruder["profile_id"]}
        assert client.delete(f"/cv/{cv_id}", headers=intruder_headers).status_code == 404
        assert client.post(f"/cv/{cv_id}/default", headers=intruder_headers).status_code == 404
        still_there = client.get("/cv", headers={"X-Profile-Id": owner["profile_id"]}).json()
        assert [v["cv_id"] for v in still_there] == [cv_id]
    finally:
        _cleanup_profile(owner["profile_id"])
        _cleanup_profile(intruder["profile_id"])


def test_unknown_cv_returns_404(client):
    upload = _upload(client, "mine.txt")
    try:
        headers = {"X-Profile-Id": upload["profile_id"]}
        assert client.delete(f"/cv/{uuid4()}", headers=headers).status_code == 404
        assert client.post(f"/cv/{uuid4()}/default", headers=headers).status_code == 404
    finally:
        _cleanup_profile(upload["profile_id"])


def test_cv_parsed_by_an_older_parser_is_re_read_automatically(client):
    """Parser fixes must reach CVs uploaded before them (root cause of a
    letterhead showing up as the student's name)."""
    import json
    from app.supabase_client import supabase

    upload = _upload(client, "stale.txt")
    profile_id, cv_id = upload["profile_id"], upload["cv_id"]
    headers = {"X-Profile-Id": profile_id}
    try:
        row = supabase.table("cv_versions").select("description").eq("id", cv_id).execute().data[0]
        meta = json.loads(row["description"])
        meta["parser_version"] = 1
        meta["extracted_profile"]["identity"]["name"] = "EXAMPLE UNIVERSITY"  # what the old parser produced
        supabase.table("cv_versions").update({"description": json.dumps(meta)}).eq("id", cv_id).execute()

        profile = client.get("/profile", headers=headers).json()
        assert profile["extracted_profile"]["identity"]["name"] == "Alex Rivera"
        stored = json.loads(supabase.table("cv_versions").select("description").eq("id", cv_id).execute().data[0]["description"])
        assert stored["parser_version"] >= 3
    finally:
        _cleanup_profile(profile_id)


def test_hand_edited_profile_is_never_overwritten_by_a_re_parse(client):
    import json
    from app.supabase_client import supabase

    upload = _upload(client, "edited.txt")
    profile_id, cv_id = upload["profile_id"], upload["cv_id"]
    headers = {"X-Profile-Id": profile_id}
    try:
        edited = upload["extracted_profile"]
        edited["identity"]["name"] = "Alexandra Rivera-Lopez"
        assert client.put("/profile", headers=headers, json={"extracted_profile": edited}).status_code == 200
        row = supabase.table("cv_versions").select("description").eq("id", cv_id).execute().data[0]
        meta = json.loads(row["description"])
        meta["parser_version"] = 1  # pretend the parser has since improved
        supabase.table("cv_versions").update({"description": json.dumps(meta)}).eq("id", cv_id).execute()

        profile = client.get("/profile", headers=headers).json()
        assert profile["extracted_profile"]["identity"]["name"] == "Alexandra Rivera-Lopez"
    finally:
        _cleanup_profile(profile_id)
