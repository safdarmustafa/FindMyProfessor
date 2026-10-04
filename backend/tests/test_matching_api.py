from __future__ import annotations

from uuid import uuid4

from app.cv.extraction.schema import ExtractedStudentProfile
from app.opportunities.models import OpportunityRecord
from app.services import matching as matching_service


def _professor_row(*, name: str, university_id: str, email: str | None, areas_unused=None):
    professor_id = str(uuid4())
    return {
        "id": professor_id,
        "name": name,
        "title": "Professor",
        "email": email,
        "research_summary": "Research in Computer Vision.",
        "labs": None,
        "departments": {
            "id": str(uuid4()),
            "university_id": university_id,
            "name": "CS",
            "universities": {
                "id": university_id,
                "name": "Example University",
                "country": "UAE",
                "city": "Abu Dhabi",
            },
        },
    }


def test_university_wide_opportunity_is_not_professor_specific(monkeypatch):
    university_id = str(uuid4())
    professor = _professor_row(name="Ada", university_id=university_id, email="ada@example.com")
    student = ExtractedStudentProfile(research_interests=["Computer Vision"])

    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": student.model_dump(),
        },
    )
    monkeypatch.setattr(
        matching_service,
        "_load_catalog",
        lambda: (["Computer Vision"], {"area-1": "Computer Vision"}),
    )
    monkeypatch.setattr(matching_service, "_load_professors", lambda **kwargs: [professor])
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {str(professor["id"]): ["Computer Vision"]},
    )
    monkeypatch.setattr(
        matching_service,
        "_load_opportunities",
        lambda: [
            OpportunityRecord(
                id=str(uuid4()),
                university_id=university_id,
                title="University PhD",
                opportunity_type="phd",
                status="open",
            )
        ],
    )

    response = matching_service.match_professors(profile_id=str(uuid4()), mode="research")
    assert response.count == 1
    match = response.matches[0]
    assert match.university_opportunities[0].not_professor_specific is True
    assert all(
        item.not_professor_specific is True
        for item in match.evidence
        if item.type == "university_opportunity"
    )
    assert match.professor.university.id is not None
    assert str(match.professor.university.id) == university_id


def test_opportunity_context_uses_professor_university(monkeypatch):
    uni_a = str(uuid4())
    uni_b = str(uuid4())
    professor = _professor_row(name="Bea", university_id=uni_a, email="bea@example.com")
    student = ExtractedStudentProfile(research_interests=["Computer Vision"])
    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": student.model_dump(),
        },
    )
    monkeypatch.setattr(matching_service, "_load_catalog", lambda: (["Computer Vision"], {}))
    monkeypatch.setattr(matching_service, "_load_professors", lambda **kwargs: [professor])
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {str(professor["id"]): ["Computer Vision"]},
    )
    opp_a = OpportunityRecord(id=str(uuid4()), university_id=uni_a, title="A-open", opportunity_type="phd", status="open")
    opp_b = OpportunityRecord(id=str(uuid4()), university_id=uni_b, title="B-open", opportunity_type="phd", status="open")
    monkeypatch.setattr(
        matching_service,
        "_load_opportunities",
        lambda: [opp_a, opp_b],
    )
    match = matching_service.match_professors(profile_id=str(uuid4())).matches[0]
    titles = [item.title for item in match.university_opportunities]
    assert titles == ["A-open"]
    assert "B-open" not in titles


def test_closed_opportunity_fit_is_zero_and_does_not_change_score():
    from app.opportunities.scoring import score_university_opportunities

    closed = [
        OpportunityRecord(id=str(uuid4()), university_id="u", title="Old", opportunity_type="phd", status="closed")
    ]
    open_opp = [
        OpportunityRecord(id=str(uuid4()), university_id="u", title="New", opportunity_type="phd", status="open")
    ]
    assert score_university_opportunities(closed).score == 0
    assert score_university_opportunities(open_opp).score == 100


def test_no_duplicate_professor_matches(monkeypatch):
    university_id = str(uuid4())
    professor = _professor_row(name="Cara", university_id=university_id, email="cara@example.com")
    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": ExtractedStudentProfile(
                research_interests=["Computer Vision"]
            ).model_dump(),
        },
    )
    monkeypatch.setattr(matching_service, "_load_catalog", lambda: (["Computer Vision"], {}))
    monkeypatch.setattr(matching_service, "_load_professors", lambda **kwargs: [professor, professor])
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {str(professor["id"]): ["Computer Vision"]},
    )
    monkeypatch.setattr(matching_service, "_load_opportunities", lambda: [])
    response = matching_service.match_professors(profile_id=str(uuid4()), limit=10)
    ids = [str(item.professor.id) for item in response.matches]
    assert ids == [str(professor["id"])]


def test_email_only_is_filter_not_score(monkeypatch):
    university_id = str(uuid4())
    with_email = _professor_row(name="Dana", university_id=university_id, email="dana@example.com")
    without_email = _professor_row(name="Evan", university_id=university_id, email=None)
    captured = {}

    def load_professors(**kwargs):
        captured.update(kwargs)
        rows = [with_email, without_email]
        if kwargs.get("email_only"):
            rows = [row for row in rows if row.get("email")]
        return rows

    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": ExtractedStudentProfile(
                research_interests=["Computer Vision"]
            ).model_dump(),
        },
    )
    monkeypatch.setattr(matching_service, "_load_catalog", lambda: (["Computer Vision"], {}))
    monkeypatch.setattr(matching_service, "_load_professors", load_professors)
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {
            str(with_email["id"]): ["Computer Vision"],
            str(without_email["id"]): ["Computer Vision"],
        },
    )
    monkeypatch.setattr(matching_service, "_load_opportunities", lambda: [])
    all_matches = matching_service.match_professors(profile_id=str(uuid4()), email_only=False)
    filtered = matching_service.match_professors(profile_id=str(uuid4()), email_only=True)
    # Professors without a verified email are never offered as matches,
    # whatever the flag says, and filtering never changes anyone's score.
    assert {item.professor.name for item in all_matches.matches} == {"Dana"}
    assert {item.professor.name for item in filtered.matches} == {"Dana"}
    assert all_matches.matches[0].research_match.score == filtered.matches[0].research_match.score


def test_opportunity_mode_filters_to_universities_with_non_closed(monkeypatch):
    uni_open = str(uuid4())
    uni_closed = str(uuid4())
    open_prof = _professor_row(name="Fay", university_id=uni_open, email="fay@example.com")
    closed_prof = _professor_row(name="Gus", university_id=uni_closed, email="gus@example.com")
    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": ExtractedStudentProfile(
                research_interests=["Computer Vision"]
            ).model_dump(),
        },
    )
    monkeypatch.setattr(matching_service, "_load_catalog", lambda: (["Computer Vision"], {}))
    monkeypatch.setattr(
        matching_service,
        "_load_professors",
        lambda **kwargs: [open_prof, closed_prof],
    )
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {
            str(open_prof["id"]): ["Computer Vision"],
            str(closed_prof["id"]): ["Computer Vision"],
        },
    )
    monkeypatch.setattr(
        matching_service,
        "_load_opportunities",
        lambda: [
            OpportunityRecord(
                id=str(uuid4()),
                university_id=uni_open,
                title="Open PhD",
                opportunity_type="phd",
                status="open",
            ),
            OpportunityRecord(
                id=str(uuid4()),
                university_id=uni_closed,
                title="Closed PhD",
                opportunity_type="phd",
                status="closed",
            ),
        ],
    )
    research = matching_service.match_professors(profile_id=str(uuid4()), mode="research")
    opportunity = matching_service.match_professors(profile_id=str(uuid4()), mode="opportunity")
    assert {item.professor.name for item in research.matches} == {"Fay", "Gus"}
    assert {item.professor.name for item in opportunity.matches} == {"Fay"}
    assert research.matches[0].research_match.score == opportunity.matches[0].research_match.score


def test_both_mode_keeps_research_and_opportunity_separate(monkeypatch):
    university_id = str(uuid4())
    professor = _professor_row(name="Hana", university_id=university_id, email="hana@example.com")
    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": ExtractedStudentProfile(
                research_interests=["Computer Vision"]
            ).model_dump(),
        },
    )
    monkeypatch.setattr(matching_service, "_load_catalog", lambda: (["Computer Vision"], {}))
    monkeypatch.setattr(matching_service, "_load_professors", lambda **kwargs: [professor])
    monkeypatch.setattr(
        matching_service,
        "_load_professor_areas",
        lambda names: {str(professor["id"]): ["Computer Vision"]},
    )
    monkeypatch.setattr(
        matching_service,
        "_load_opportunities",
        lambda: [
            OpportunityRecord(
                id=str(uuid4()),
                university_id=university_id,
                title="Open PhD",
                opportunity_type="phd",
                status="open",
                international_eligible=True,
            )
        ],
    )
    research = matching_service.match_professors(profile_id=str(uuid4()), mode="research")
    both = matching_service.match_professors(profile_id=str(uuid4()), mode="both")
    assert research.matches[0].research_match.score == both.matches[0].research_match.score
    assert both.matches[0].university_opportunity_fit.score == 100
    assert both.matches[0].university_opportunities[0].not_professor_specific is True


def test_matching_router_registered():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert "/matching/professors" in spec["paths"]
    params = spec["paths"]["/matching/professors"]["get"]["parameters"]
    names = {item.get("name") for item in params}
    assert {"mode", "limit", "university_id", "min_score", "email_only", "opportunity_type", "opportunity_status"} <= names


def test_health_docs_and_pages():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/health").status_code in {200, 503}
    # Interactive API docs are intentionally disabled in production (main.py).
    assert client.get("/docs").status_code == 404
    assert client.get("/onboarding").status_code == 404
    assert client.get("/matches").status_code == 404
    # Production hardening: no Supabase session and no X-Profile-Id is
    # genuinely unauthenticated, so this is now 401 (was 400) — app/auth.py.
    missing = client.get("/matching/professors")
    assert missing.status_code == 401
    research = client.get("/matching/professors", params={"mode": "research"})
    opportunity = client.get("/matching/professors", params={"mode": "opportunity"})
    both = client.get("/matching/professors", params={"mode": "both"})
    assert research.status_code == 401
    assert opportunity.status_code == 401
    assert both.status_code == 401
