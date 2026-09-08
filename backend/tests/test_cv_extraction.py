from app.cv.extraction.heuristic import HeuristicExtractionProvider
from tests.sample_cv import CATALOG, SAMPLE_CV, SKILLS_ONLY_CV


def test_extracts_structured_fields_without_inventing():
    profile = HeuristicExtractionProvider().extract(SAMPLE_CV, CATALOG)
    assert profile.identity.name == "Alex Rivera"
    assert profile.identity.email == "alex.rivera@example.com"
    assert profile.identity.phone is not None
    assert profile.education
    assert profile.education[0].degree is not None
    assert "Computer Vision" in profile.research_interests
    assert "Medical AI" in profile.research_interests
    skill_names = {item.name for item in profile.skills}
    assert {"Python", "Kotlin", "TensorFlow", "SQL"} <= skill_names
    assert any("Knee Osteoarthritis" in (item.title or "") for item in profile.projects)
    assert profile.publications
    assert profile.certifications
    assert profile.education[0].country is None


def test_skills_are_not_treated_as_research_interests():
    profile = HeuristicExtractionProvider().extract(SKILLS_ONLY_CV, CATALOG)
    assert profile.research_interests == []
    assert profile.research_signals == []
    assert {item.name for item in profile.skills} >= {"Python", "TensorFlow", "SQL"}
    assert profile.projects == []
    assert profile.publications == []
    assert profile.education == []
