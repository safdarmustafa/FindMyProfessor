from __future__ import annotations

import json
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
UI_JS = STATIC / "js" / "matching_ui.js"
API_JS = STATIC / "js" / "matching_api.js"

SAMPLE_MATCH = {
    "professor": {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Ada Lovelace",
        "title": "Professor",
        "email": None,
        "email_available": False,
        "university": {"id": "22222222-2222-2222-2222-222222222222", "name": "Example University"},
        "department": {"id": "33333333-3333-3333-3333-333333333333", "name": "Computer Vision"},
        "lab": None,
    },
    "research_match": {
        "score": 87,
        "priority": "high",
        "why": ["Computer Vision matches your explicit research interest."],
    },
    "research_overlap": ["Computer Vision", "Medical AI"],
    "evidence": [
        {
            "type": "shared_research_area",
            "area_name": "Computer Vision",
            "student_source": "interest",
            "professor_source": "research_area_mapping",
        },
        {
            "type": "university_opportunity",
            "title": "University PhD",
            "opportunity_type": "phd",
            "status": "open",
            "not_professor_specific": True,
        },
    ],
    "university_opportunities": [
        {
            "id": "44444444-4444-4444-4444-444444444444",
            "title": "University PhD",
            "type": "phd",
            "status": "open",
            "not_professor_specific": True,
        }
    ],
    "university_opportunity_fit": {
      "score": 100,
      "best_opportunity_id": "44444444-4444-4444-4444-444444444444",
      "best_opportunity_title": "University PhD",
      "status": "open",
      "non_closed_opportunity_count": 1,
      "why": ["University has an open opportunity."]
    },
}


def test_research_matches_page_loads():
    client = TestClient(app)
    response = client.get("/matches")
    assert response.status_code == 200
    assert "Research Matches" in response.text
    assert "Find professors whose research aligns with your background." in response.text
    assert "Confirm your CV to discover research matches." in response.text
    assert "Unable to load research matches." in response.text
    assert "Loading research matches" in response.text
    assert "skeleton" in response.text
    assert "Opportunity First" in response.text
    assert "No current or upcoming university opportunities found." in response.text


def test_onboarding_still_loads():
    client = TestClient(app)
    response = client.get("/onboarding")
    assert response.status_code == 200
    assert "CV-first" in response.text
    assert 'href="/matches"' in response.text


def test_professor_match_page_loads():
    client = TestClient(app)
    response = client.get(f"/matches/{uuid4()}")
    assert response.status_code == 200
    assert "Professor" in response.text
    assert "Back to research matches" in response.text


def test_json_professor_api_is_unchanged_path():
    client = TestClient(app)
    response = client.get(f"/professors/{uuid4()}")
    assert response.status_code in {404, 503}


def _run_ui_js(script: str) -> str:
    node = f"""
{API_JS.read_text()}
{UI_JS.read_text()}
const match = {json.dumps(SAMPLE_MATCH)};
{script}
"""
    result = subprocess.run(
        ["node", "-e", node],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_api_request_builder_includes_profile_id_and_filters():
    src = API_JS.read_text()
    assert "X-Profile-Id" in src
    assert "/matching/professors" in src
    stdout = _run_ui_js(
        """
        const url = globalThis.FMPMatchingApi.buildMatchingUrl({
          universityId: "uni-1",
          minScore: 50,
          emailOnly: true,
          opportunityType: "phd",
          opportunityStatus: "open",
          limit: 25,
          mode: "research"
        });
        console.log(url);
        const headers = globalThis.FMPMatchingApi.profileHeaders("profile-1");
        console.log(JSON.stringify(headers));
        """
    )
    lines = stdout.strip().splitlines()
    assert "/matching/professors?" in lines[0]
    assert "university_id=uni-1" in lines[0]
    assert "min_score=50" in lines[0]
    assert "email_only=true" in lines[0]
    assert "opportunity_type=phd" in lines[0]
    assert "opportunity_status=open" in lines[0]
    assert "mode=research" in lines[0]
    assert json.loads(lines[1]) == {"X-Profile-Id": "profile-1"}


def test_card_renders_backend_score_priority_overlap_and_evidence():
    html = _run_ui_js(
        "process.stdout.write(globalThis.FMPMatchingUi.renderProfessorCard(match, {detailHref: '/matches/x'}));"
    )
    assert "87/100" in html
    assert "high" in html
    assert "Computer Vision" in html
    assert "Medical AI" in html
    assert "Computer Vision matches your explicit research interest." in html
    assert "Why am I a match?" in html
    assert "Ada Lovelace" in html
    assert "Example University" in html


def test_university_opportunity_is_not_professor_specific():
    html = _run_ui_js("process.stdout.write(globalThis.FMPMatchingUi.renderMatchList([match], {mode: 'opportunity'}));")
    assert "University Opportunity Fit" in html
    assert "University opportunity" in html
    assert "This opportunity is offered by the university, not specifically by this professor." in html
    assert "Opportunities with this professor" not in html
    assert "This professor is offering" not in html
    assert "University opportunity fit: 100" in html or "100/100" in html


def test_missing_email_is_discovery_only_and_lab_is_omitted():
    html = _run_ui_js("process.stdout.write(globalThis.FMPMatchingUi.renderProfessorCard(match));")
    assert "Discovery only" in html
    assert "No email found" not in html
    assert "AI Research Lab" not in html


def test_frontend_does_not_recalculate_scores():
    combined = API_JS.read_text() + UI_JS.read_text() + (STATIC / "matches.html").read_text()
    assert "score +" not in combined
    assert "interests.length" not in combined
    assert "research.score" in UI_JS.read_text()
