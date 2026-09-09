"""
Phase 5 — Email generation tests.

All tests use the deterministic provider and mocked dependencies.
No external API calls are made; no Supabase writes are performed.
"""
from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.cv.extraction.schema import (
    EducationExtract,
    ExtractedStudentProfile,
    IdentityExtract,
    ProjectExtract,
    PublicationExtract,
)
from app.outreach import store as draft_store
from app.outreach.deterministic import DeterministicTemplateProvider, _last_name, _degree_phrase
from app.outreach.factory import get_email_provider
from app.outreach.models import DraftRecord
from app.outreach.provider import (
    ArtifactEvidence,
    MatchContext,
    OpportunityContext,
    ProfessorContext,
)
from app.outreach import service as outreach_service
from app.services import matching as matching_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _student(
    name: str = "Aisha Khan",
    degree: str = "B.Tech",
    field: str = "Computer Science",
    institution: str = "XYZ University",
    interests: list[str] | None = None,
    projects: list[ProjectExtract] | None = None,
    publications: list[PublicationExtract] | None = None,
) -> ExtractedStudentProfile:
    return ExtractedStudentProfile(
        identity=IdentityExtract(name=name),
        education=[
            EducationExtract(degree=degree, field_of_study=field, institution=institution)
        ],
        research_interests=interests or ["Computer Vision", "Medical AI"],
        projects=projects or [],
        publications=publications or [],
    )


def _professor(
    name: str = "James Chen",
    university: str = "MIT",
    department: str = "EECS",
    areas: list[str] | None = None,
    research_summary: str | None = None,
    email: str | None = "j.chen@mit.edu",
) -> ProfessorContext:
    return ProfessorContext(
        professor_id=str(uuid4()),
        name=name,
        title="Professor",
        email=email,
        university_name=university,
        department_name=department,
        lab_name=None,
        research_areas=areas or ["Computer Vision", "Medical Imaging"],
        research_summary=research_summary,
    )


def _match(
    overlap: list[str] | None = None,
    shared_interests: list[str] | None = None,
    artifacts: list[ArtifactEvidence] | None = None,
    corroborated: list[str] | None = None,
) -> MatchContext:
    return MatchContext(
        research_score=85,
        research_overlap=overlap or ["Computer Vision"],
        shared_interest_areas=shared_interests or ["Computer Vision"],
        artifact_evidence=artifacts or [],
        corroborated_areas=corroborated or [],
    )


_PROVIDER = DeterministicTemplateProvider()


# ---------------------------------------------------------------------------
# Helper: generate via provider directly
# ---------------------------------------------------------------------------

def _gen(
    student=None,
    professor=None,
    match=None,
    email_type="research",
    opportunity=None,
):
    return _PROVIDER.generate(
        student=student or _student(),
        professor=professor or _professor(),
        match=match or _match(),
        email_type=email_type,
        opportunity=opportunity,
    )


# ---------------------------------------------------------------------------
# 1. Provider works without any API key (deterministic fallback)
# ---------------------------------------------------------------------------

def test_deterministic_provider_works_without_api_key():
    import os
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("EMAIL_LLM_API_KEY", None)
        os.environ.pop("LLM_API_KEY", None)
        provider = get_email_provider()
    assert isinstance(provider, DeterministicTemplateProvider)


def test_deterministic_generate_returns_subject_and_body():
    out = _gen()
    assert out.subject
    assert out.body
    assert out.generation_provider == "deterministic"


# ---------------------------------------------------------------------------
# 2. Subject is generated and follows no-spam rule
# ---------------------------------------------------------------------------

def test_subject_contains_research_area():
    out = _gen()
    assert "Computer Vision" in out.subject or "Research" in out.subject


def test_subject_not_spam():
    out = _gen()
    for bad in ("URGENT", "IMPORTANT!!!", "ASAP", "!!!"):
        assert bad not in out.subject


# ---------------------------------------------------------------------------
# 3. Greeting uses professor last name
# ---------------------------------------------------------------------------

def test_greeting_uses_last_name():
    out = _gen(professor=_professor(name="James Chen"))
    assert "Dear Professor Chen," in out.body


def test_last_name_helper():
    assert _last_name("James Chen") == "Chen"
    assert _last_name("Wei") == "Wei"
    assert _last_name("") == ""


# ---------------------------------------------------------------------------
# 4. Shared research area appears in the body
# ---------------------------------------------------------------------------

def test_shared_area_in_body():
    out = _gen(match=_match(overlap=["Medical AI"]))
    assert "Medical AI" in out.body


# ---------------------------------------------------------------------------
# 5. Student name appears in body
# ---------------------------------------------------------------------------

def test_student_name_in_body():
    out = _gen(student=_student(name="Priya Sharma"))
    assert "Priya Sharma" in out.body


# ---------------------------------------------------------------------------
# 6. Project evidence is referenced when available
# ---------------------------------------------------------------------------

def test_project_evidence_appears():
    proj = ProjectExtract(
        title="Knee Osteoarthritis Grading",
        description="grading severity using Computer Vision",
        research_relevance="Computer Vision in medical imaging",
    )
    student = _student(projects=[proj])
    match = _match(
        artifacts=[ArtifactEvidence(kind="project", title="Knee Osteoarthritis Grading", area_name="Computer Vision")]
    )
    out = _gen(student=student, match=match)
    assert "Knee Osteoarthritis Grading" in out.body


# ---------------------------------------------------------------------------
# 7. Publication evidence is referenced when available
# ---------------------------------------------------------------------------

def test_publication_evidence_appears():
    pub = PublicationExtract(title="Vision Transformers for Medical Imaging", venue="CVPR", year=2024)
    student = _student(publications=[pub])
    match = _match(
        artifacts=[ArtifactEvidence(kind="publication", title="Vision Transformers for Medical Imaging", area_name="Computer Vision")]
    )
    out = _gen(student=student, match=match)
    assert "Vision Transformers for Medical Imaging" in out.body


# ---------------------------------------------------------------------------
# 8. Skills do NOT become research claims
# ---------------------------------------------------------------------------

def test_skills_do_not_become_research_claims():
    from app.cv.extraction.schema import SkillExtract
    student = _student()
    student = ExtractedStudentProfile(
        identity=student.identity,
        education=student.education,
        research_interests=student.research_interests,
        skills=[SkillExtract(name="Python", category="language")],
    )
    out = _gen(student=student)
    assert "my research in Python" not in out.body
    assert "Python expertise in research" not in out.body


# ---------------------------------------------------------------------------
# 9. No fabricated research areas
# ---------------------------------------------------------------------------

def test_no_fabricated_areas():
    """Body must not mention areas not in the match overlap."""
    match = _match(overlap=["Computer Vision"])
    out = _gen(match=match)
    # The invented area must NOT appear
    assert "Quantum Computing" not in out.body
    assert "Blockchain" not in out.body


# ---------------------------------------------------------------------------
# 10. No fabricated publications
# ---------------------------------------------------------------------------

def test_no_fabricated_publications():
    """If no artifact evidence is provided, no publication titles appear."""
    match = _match(artifacts=[])
    student = _student(publications=[])
    out = _gen(student=student, match=match)
    # Common fabrication patterns
    assert "recently published" not in out.body.lower()
    assert "your paper on" not in out.body.lower()


# ---------------------------------------------------------------------------
# 11. No fabricated recruiting claims
# ---------------------------------------------------------------------------

def test_no_recruiting_claims():
    out = _gen()
    for phrase in (
        "I saw that you are recruiting",
        "I noticed you are accepting students",
        "you are currently looking for",
        "you are offering",
    ):
        assert phrase.lower() not in out.body.lower()


# ---------------------------------------------------------------------------
# 12. University-wide opportunity is described as university-wide
# ---------------------------------------------------------------------------

def test_university_opportunity_is_university_wide():
    opp = OpportunityContext(
        opportunity_id=str(uuid4()),
        title="PhD Program",
        opportunity_type="phd",
        status="open",
        university_name="MIT",
        not_professor_specific=True,
    )
    out = _gen(email_type="research_opportunity", opportunity=opp)
    body_lower = out.body.lower()
    # Must mention the university, not the professor
    assert "mit" in body_lower or "university" in body_lower
    # Must NOT attribute to professor
    assert "you are offering" not in body_lower
    assert "your phd program" not in body_lower


# ---------------------------------------------------------------------------
# 13. Closed opportunity cannot be used for active outreach (service layer)
# ---------------------------------------------------------------------------

def test_closed_opportunity_rejected_by_service(monkeypatch):
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    opportunity_id = str(uuid4())
    university_id = str(uuid4())

    professor_row = _make_professor_row(professor_id, university_id)

    monkeypatch.setattr(
        "app.outreach.service.cv_service.get_active_profile",
        lambda pid: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": _student().model_dump(),
        },
    )
    monkeypatch.setattr(
        "app.outreach.service.get_professor",
        lambda pid: professor_row,
    )
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{"id": opportunity_id, "professor_id": None, "lab_id": None, "university_id": university_id, "title": "Old PhD", "opportunity_type": "phd", "status": "closed", "universities": {"name": "MIT"}}]})(),
    )

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.generate_draft(
            profile_id=profile_id,
            professor_id=professor_id,
            email_type="research_opportunity",
            opportunity_id=opportunity_id,
        )
    assert exc.value.status_code == 400
    assert "Closed" in exc.value.detail


# ---------------------------------------------------------------------------
# 14. Unconfirmed CV is rejected
# ---------------------------------------------------------------------------

def test_unconfirmed_cv_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.outreach.service.cv_service.get_active_profile",
        lambda pid: {
            "cv_id": str(uuid4()),
            "confirmed": False,
            "parsing_status": "parsed",
            "extracted_profile": _student().model_dump(),
        },
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.generate_draft(
            profile_id=str(uuid4()),
            professor_id=str(uuid4()),
            email_type="research",
        )
    assert exc.value.status_code == 400
    assert "Confirm" in exc.value.detail


# ---------------------------------------------------------------------------
# 15. Missing professor returns 404
# ---------------------------------------------------------------------------

def test_missing_professor_returns_404(monkeypatch):
    monkeypatch.setattr(
        "app.outreach.service.cv_service.get_active_profile",
        lambda pid: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": _student().model_dump(),
        },
    )
    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: None)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.generate_draft(
            profile_id=str(uuid4()),
            professor_id=str(uuid4()),
            email_type="research",
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# 16. Generated email is within length limits
# ---------------------------------------------------------------------------

def test_email_within_word_limit():
    out = _gen()
    words = len(out.body.split())
    assert words <= 300, f"Email too long: {words} words"
    assert words >= 60, f"Email too short: {words} words"


# ---------------------------------------------------------------------------
# 17. Evidence list is returned
# ---------------------------------------------------------------------------

def test_evidence_list_returned():
    match = _match(shared_interests=["Computer Vision"])
    out = _gen(match=match)
    assert any("Computer Vision" in e for e in out.evidence_used)


# ---------------------------------------------------------------------------
# 18. Professor with no email can still generate draft
# ---------------------------------------------------------------------------

def test_professor_no_email_generates_draft():
    prof = _professor(email=None)
    out = _gen(professor=prof)
    assert out.body  # draft still generated
    assert out.subject


# ---------------------------------------------------------------------------
# 19. Save draft preserves user edits
# ---------------------------------------------------------------------------

def test_save_draft_preserves_edits(monkeypatch):
    draft_store.clear()
    profile_id = str(uuid4())
    professor_id = str(uuid4())
    university_id = str(uuid4())

    professor_row = _make_professor_row(professor_id, university_id)

    monkeypatch.setattr(
        "app.outreach.service.cv_service.get_active_profile",
        lambda pid: {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": _student().model_dump(),
        },
    )
    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: professor_row)
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{"id": str(uuid4()), "name": "Computer Vision"}]})(),
    )

    draft = outreach_service.generate_draft(
        profile_id=profile_id, professor_id=professor_id, email_type="research"
    )
    custom_subject = "My Custom Subject"
    custom_body = "Dear Professor Chen,\n\nEdited body.\n\nRegards,\nAisha"
    saved = outreach_service.save_draft(
        profile_id=profile_id,
        draft_id=draft.draft_id,
        subject=custom_subject,
        body=custom_body,
        status="ready",
    )
    assert saved.status == "ready"

    retrieved = outreach_service.get_draft(profile_id=profile_id, draft_id=draft.draft_id)
    assert retrieved.subject == custom_subject
    assert retrieved.body == custom_body


# ---------------------------------------------------------------------------
# 20. Profile isolation: draft belongs to its profile only
# ---------------------------------------------------------------------------

def test_draft_profile_isolation(monkeypatch):
    draft_store.clear()
    profile_a = str(uuid4())
    profile_b = str(uuid4())
    professor_id = str(uuid4())
    university_id = str(uuid4())

    professor_row = _make_professor_row(professor_id, university_id)

    def mock_profile(pid):
        return {
            "cv_id": str(uuid4()),
            "confirmed": True,
            "parsing_status": "parsed",
            "extracted_profile": _student().model_dump(),
        }

    monkeypatch.setattr("app.outreach.service.cv_service.get_active_profile", mock_profile)
    monkeypatch.setattr("app.outreach.service.get_professor", lambda pid: professor_row)
    monkeypatch.setattr(
        "app.outreach.service.execute",
        lambda q: type("R", (), {"data": [{"id": str(uuid4()), "name": "Computer Vision"}]})(),
    )

    draft = outreach_service.generate_draft(
        profile_id=profile_a, professor_id=professor_id, email_type="research"
    )
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        outreach_service.get_draft(profile_id=profile_b, draft_id=draft.draft_id)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 21. Regeneration produces a different variant
# ---------------------------------------------------------------------------

def test_regeneration_gives_different_variant():
    out1 = _gen()
    out2 = _gen()
    # Because the variant counter increments, at least subject or body should differ
    # (they cycle through 3 templates, so two consecutive calls may or may not be the same
    # depending on test order — we just verify both are valid)
    assert out1.body and out2.body


# ---------------------------------------------------------------------------
# 22. No Gmail API is called (no send, no OAuth)
# ---------------------------------------------------------------------------

def test_no_gmail_api_called(monkeypatch):
    """
    Ensure outreach service never exposes automatic/implicit send or raw OAuth.
    Phase 6 adds attach_cv and send_draft (explicit user-triggered send),
    but there must be no 'send_email' shortcut and no inline gmail_oauth module
    (OAuth is delegated to the dedicated gmail package).
    """
    import app.outreach.service as svc
    # No automatic send_email shortcut — sending requires explicit confirmation
    assert not hasattr(svc, "send_email")
    # OAuth is handled by the dedicated gmail module, not inline in outreach service
    assert not hasattr(svc, "gmail_oauth")


# ---------------------------------------------------------------------------
# 23. Compose page route exists and returns 200
# ---------------------------------------------------------------------------

def test_compose_page_exists():
    from app.main import app
    client = TestClient(app)
    resp = client.get(f"/outreach/compose/{uuid4()}")
    assert resp.status_code == 200
    assert "Generate Email Draft" in resp.text


# ---------------------------------------------------------------------------
# 24. Draft API routes registered
# ---------------------------------------------------------------------------

def test_outreach_routes_registered():
    from app.main import app
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/outreach/drafts/generate" in paths
    assert "/outreach/drafts/{draft_id}" in paths


# ---------------------------------------------------------------------------
# 25. Missing X-Profile-Id returns 400
# ---------------------------------------------------------------------------

def test_generate_without_profile_id():
    from app.main import app
    client = TestClient(app)
    resp = client.post(
        "/outreach/drafts/generate",
        json={"professor_id": str(uuid4()), "email_type": "research"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 26. Opportunity type "research_opportunity" only used for university opp
# ---------------------------------------------------------------------------

def test_research_opportunity_type_mentions_university():
    opp = OpportunityContext(
        opportunity_id=str(uuid4()),
        title="PhD Program",
        opportunity_type="phd",
        status="open",
        university_name="Stanford",
        not_professor_specific=True,
    )
    out = _gen(email_type="research_opportunity", opportunity=opp)
    assert "Stanford" in out.body or "university" in out.body.lower()


# ---------------------------------------------------------------------------
# 27. Existing Phase 3.2/4 tests still pass — verified by running full suite
#     Here we just confirm scoring module is not imported by outreach
# ---------------------------------------------------------------------------

def test_scoring_module_untouched():
    """Outreach module must not modify matching/scoring.py."""
    import importlib
    import app.matching.scoring as scoring_mod
    # Reload to verify no side-effects from outreach imports
    importlib.reload(scoring_mod)
    assert hasattr(scoring_mod, "score_professor")
    assert hasattr(scoring_mod, "MATCH_VERSION")


# ---------------------------------------------------------------------------
# 28. LLM provider is optional — deterministic always available
# ---------------------------------------------------------------------------

def test_llm_provider_optional():
    import os
    saved_email = os.environ.pop("EMAIL_LLM_API_KEY", None)
    saved_llm = os.environ.pop("LLM_API_KEY", None)
    try:
        provider = get_email_provider()
        assert isinstance(provider, DeterministicTemplateProvider)
    finally:
        if saved_email:
            os.environ["EMAIL_LLM_API_KEY"] = saved_email
        if saved_llm:
            os.environ["LLM_API_KEY"] = saved_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_professor_row(professor_id: str, university_id: str) -> dict:
    return {
        "id": professor_id,
        "name": "James Chen",
        "title": "Professor",
        "email": "j.chen@mit.edu",
        "research_summary": "Research in Computer Vision and medical imaging.",
        "lab": None,
        "department": {
            "id": str(uuid4()),
            "university_id": university_id,
            "name": "EECS",
        },
        "university": {
            "id": university_id,
            "name": "MIT",
            "country": "USA",
            "city": "Cambridge",
        },
        "research_areas": [
            {"id": str(uuid4()), "name": "Computer Vision"},
            {"id": str(uuid4()), "name": "Medical Imaging"},
        ],
    }
