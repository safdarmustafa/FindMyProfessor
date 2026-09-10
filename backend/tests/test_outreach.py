from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from tests.conftest import PROFILE_ID, PROFESSOR_ID, DRAFT_ID


def _draft(**overrides):
    base = {
        "draft_id": DRAFT_ID,
        "profile_id": PROFILE_ID,
        "professor_id": PROFESSOR_ID,
        "email_type": "research",
        "subject": "Research inquiry",
        "body": "Dear Professor,",
        "matched_research_areas": ["Computer Vision"],
        "evidence_used": [],
        "generation_provider": "test",
        "generation_status": "generated",
        "professor_name": "Jane Smith",
        "professor_email": "jane@stanford.edu",
        "professor_email_available": True,
        "university_name": "Stanford University",
    }
    base.update(overrides)
    return base


def test_generate_draft_requires_profile(client):
    res = client.post(
        "/outreach/drafts/generate",
        json={"professor_id": PROFESSOR_ID, "email_type": "research"},
    )
    assert res.status_code == 400
    assert "X-Profile-Id" in res.json()["detail"]


def test_generate_draft_rejects_invalid_email_type(client, auth_headers):
    res = client.post(
        "/outreach/drafts/generate",
        headers=auth_headers,
        json={"professor_id": PROFESSOR_ID, "email_type": "research_outreach"},
    )
    assert res.status_code == 422
    assert res.json()["detail"]


def test_generate_draft_creates_draft(client, auth_headers):
    created = _draft()
    with patch("app.routers.outreach.outreach_service.generate_draft", return_value=created):
        res = client.post(
            "/outreach/drafts/generate",
            headers=auth_headers,
            json={"professor_id": PROFESSOR_ID, "email_type": "research"},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["draft_id"] == DRAFT_ID
    assert body["subject"] == "Research inquiry"
    assert body["body"]
    assert body["email_type"] == "research"


def test_list_drafts(client, auth_headers):
    with patch("app.routers.outreach.outreach_service.list_drafts", return_value=[_draft()]):
        res = client.get("/outreach/drafts", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()[0]["draft_id"] == DRAFT_ID


def test_get_single_draft(client, auth_headers):
    with patch("app.routers.outreach.outreach_service.get_draft", return_value=_draft()):
        res = client.get(f"/outreach/drafts/{DRAFT_ID}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["draft_id"] == DRAFT_ID


def test_get_draft_not_found_returns_404(client, auth_headers):
    with patch(
        "app.routers.outreach.outreach_service.get_draft",
        side_effect=HTTPException(status_code=404, detail="Draft not found."),
    ):
        res = client.get(f"/outreach/drafts/{uuid4()}", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Draft not found."


def test_patch_draft_updates_subject_body_status(client, auth_headers):
    saved = {"draft_id": DRAFT_ID, "status": "ready", "message": "Draft saved."}
    with patch("app.routers.outreach.outreach_service.save_draft", return_value=saved) as mock_save:
        res = client.patch(
            f"/outreach/drafts/{DRAFT_ID}",
            headers=auth_headers,
            json={"subject": "Updated", "body": "New body", "status": "ready"},
        )
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    mock_save.assert_called_once()
    kwargs = mock_save.call_args.kwargs
    assert kwargs["subject"] == "Updated"
    assert kwargs["body"] == "New body"
    assert kwargs["status"] == "ready"


def test_send_draft(client, auth_headers):
    sent = {
        "draft_id": DRAFT_ID,
        "status": "sent",
        "gmail_message_id": "msg-1",
        "sent_at": "2026-09-10T00:00:00Z",
        "message": "Sent.",
    }
    with patch("app.routers.outreach.outreach_service.send_draft", return_value=sent) as mock_send:
        res = client.post(
            f"/outreach/drafts/{DRAFT_ID}/send",
            headers=auth_headers,
            json={"confirmed": True},
        )
    assert res.status_code == 200
    assert res.json()["status"] == "sent"
    assert mock_send.call_args.kwargs["confirmed"] is True


def test_send_without_confirmation_is_422(client, auth_headers):
    res = client.post(
        f"/outreach/drafts/{DRAFT_ID}/send",
        headers=auth_headers,
        json={},
    )
    assert res.status_code == 422


def test_history_returns_items(client, auth_headers):
    items = [
        {
            "draft_id": DRAFT_ID,
            "professor_name": "Jane Smith",
            "professor_email": "jane@stanford.edu",
            "university_name": "Stanford University",
            "subject": "Research inquiry",
            "status": "ready",
        }
    ]
    with patch("app.routers.outreach.outreach_service.list_history", return_value=items):
        res = client.get("/outreach/history", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()[0]["professor_name"] == "Jane Smith"
    assert res.json()[0]["status"] == "ready"
