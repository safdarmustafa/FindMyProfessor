from unittest.mock import patch
from uuid import uuid4

from tests.conftest import PROFILE_ID, PROFESSOR_ID


def _match_payload(ids):
    return {
        "profile_id": PROFILE_ID,
        "mode": "research",
        "match_version": "v1",
        "count": 1,
        "matches": [
            {
                "professor": {
                    "id": PROFESSOR_ID,
                    "name": "Jane Smith",
                    "title": "Associate Professor",
                    "email": "jane@stanford.edu",
                    "email_available": True,
                    "university": {"id": ids["university_id"], "name": "Stanford University"},
                    "department": {"id": ids["department_id"], "name": "Computer Science"},
                    "lab": {"id": ids["lab_id"], "name": "Vision Lab"},
                },
                "research_match": {
                    "score": 87,
                    "priority": "high",
                    "why": ["Shared computer vision focus"],
                },
                "research_overlap": ["Computer Vision"],
                "evidence": [
                    {"type": "shared_research_area", "area_name": "Computer Vision"},
                ],
                "university_opportunities": [],
            }
        ],
    }


def test_matching_requires_profile_header(client):
    # Production hardening: no Supabase session and no X-Profile-Id is
    # genuinely unauthenticated, so this is now 401 (was 400) — app/auth.py.
    res = client.get("/matching/professors")
    assert res.status_code == 401
    assert "X-Profile-Id" in res.json()["detail"]


def test_get_matches_returns_professor_matches(client, auth_headers, ids):
    payload = _match_payload(ids)
    with patch("app.routers.matching.match_professors", return_value=payload):
        res = client.get("/matching/professors", headers=auth_headers)
    assert res.status_code == 200
    match = res.json()["matches"][0]
    prof = match["professor"]
    assert prof["name"] == "Jane Smith"
    assert prof["title"] == "Associate Professor"
    assert prof["university"]["name"] == "Stanford University"
    assert prof["department"]["name"] == "Computer Science"
    assert prof["lab"]["name"] == "Vision Lab"
    assert match["research_match"]["score"] == 87
    assert match["research_match"]["priority"] == "high"
    assert match["research_match"]["why"]
    assert match["research_overlap"]


def test_get_professor_detail_shape(client, ids):
    area_id = ids["area_id"]
    detail = {
        "id": PROFESSOR_ID,
        "name": "Jane Smith",
        "title": "Associate Professor",
        "email": "jane@stanford.edu",
        "lab": {
            "id": ids["lab_id"],
            "department_id": ids["department_id"],
            "name": "Vision Lab",
        },
        "department": {
            "id": ids["department_id"],
            "university_id": ids["university_id"],
            "name": "Computer Science",
        },
        "university": {
            "id": ids["university_id"],
            "name": "Stanford University",
        },
        "research_areas": [{"id": area_id, "name": "Computer Vision"}],
    }
    with patch("app.routers.professors.get_professor", return_value=detail):
        res = client.get(f"/professors/{PROFESSOR_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Jane Smith"
    assert body["title"] == "Associate Professor"
    assert body["university"]["name"] == "Stanford University"
    assert body["department"]["name"] == "Computer Science"
    assert body["lab"]["name"] == "Vision Lab"
    assert body["research_areas"][0]["name"] == "Computer Vision"


def test_get_professor_not_found(client):
    missing = str(uuid4())
    with patch("app.routers.professors.get_professor", return_value=None):
        res = client.get(f"/professors/{missing}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
