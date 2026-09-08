from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.cv.extraction.schema import (
    ExtractedStudentProfile,
    ProjectExtract,
    PublicationExtract,
    SkillExtract,
)
from app.matching.normalize import normalize_label
from app.matching.scoring import (
    combine_components,
    ComponentScores,
    priority_for_score,
    score_professor,
)

CATALOG = [
    "Computer Vision",
    "Medical AI",
    "Edge AI",
    "Robotics",
    "Computer Science",
    "Machine Learning",
    "Natural Language Processing",
]


def student(**kwargs) -> ExtractedStudentProfile:
    return ExtractedStudentProfile(**kwargs)


def test_exact_research_area_match():
    result = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert result.score > 0
    assert "Computer Vision" in result.research_overlap


def test_case_insensitive_matching():
    result = score_professor(
        student=student(research_interests=["computer vision"]),
        professor_areas=["COMPUTER VISION"],
        catalog_names=CATALOG,
    )
    assert result.score > 0
    assert normalize_label(result.research_overlap[0]) == "computer vision"


def test_whitespace_normalization():
    result = score_professor(
        student=student(research_interests=["  Computer   Vision  "]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert result.score > 0


def test_no_match():
    result = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Robotics"],
        catalog_names=CATALOG,
    )
    assert result.score == 0
    assert result.research_overlap == []


def test_multiple_shared_areas():
    result = score_professor(
        student=student(research_interests=["Computer Vision", "Medical AI", "Edge AI"]),
        professor_areas=["Computer Vision", "Medical AI", "Robotics"],
        catalog_names=CATALOG,
    )
    assert set(result.research_overlap) == {"Computer Vision", "Medical AI"}
    assert result.score == 67


def test_computer_science_does_not_inflate_score():
    without_cs = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    with_cs = score_professor(
        student=student(research_interests=["Computer Vision", "Computer Science"]),
        professor_areas=["Computer Vision", "Computer Science"],
        catalog_names=CATALOG,
    )
    cs_only = score_professor(
        student=student(research_interests=["Computer Science"]),
        professor_areas=["Computer Science"],
        catalog_names=CATALOG,
    )
    assert with_cs.score == without_cs.score
    assert cs_only.score == 0
    assert "Computer Science" not in with_cs.research_overlap


def test_explicit_interest_outranks_weak_signal():
    interest_match = score_professor(
        student=student(
            research_interests=["Computer Vision"],
            research_signals=["Medical AI"],
        ),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    signal_match = score_professor(
        student=student(
            research_interests=["Computer Vision"],
            research_signals=["Medical AI"],
        ),
        professor_areas=["Medical AI"],
        catalog_names=CATALOG,
    )
    assert interest_match.score > signal_match.score


def test_research_signal_matching():
    result = score_professor(
        student=student(research_signals=["Medical AI"]),
        professor_areas=["Medical AI"],
        catalog_names=CATALOG,
    )
    assert result.score > 0
    assert any(
        item.type == "shared_research_area" and item.student_source == "signal"
        for item in result.evidence
    )


def test_project_catalog_evidence():
    result = score_professor(
        student=student(
            projects=[
                ProjectExtract(
                    title="Efficient diabetic retinopathy detection using CNNs",
                    description="Applied Medical AI and Computer Vision methods.",
                )
            ]
        ),
        professor_areas=["Medical AI", "Computer Vision"],
        catalog_names=CATALOG,
    )
    assert result.score > 0
    assert {item.area_name for item in result.evidence if item.student_source == "project"} >= {
        "Medical AI",
        "Computer Vision",
    }


def test_publication_catalog_evidence():
    result = score_professor(
        student=student(
            publications=[
                PublicationExtract(
                    title="A Medical AI study of imaging",
                    venue="MICCAI",
                )
            ]
        ),
        professor_areas=["Medical AI"],
        catalog_names=CATALOG,
    )
    assert any(item.student_source == "publication" for item in result.evidence)
    assert "Medical AI" in result.research_overlap


def test_professor_summary_only_corroborates_existing_match():
    result = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
        research_summary="We develop computer vision systems for robotics platforms.",
    )
    assert any(item.type == "professor_summary_mentions_area" for item in result.evidence)
    excerpt = next(
        item.excerpt for item in result.evidence if item.type == "professor_summary_mentions_area"
    )
    assert excerpt and "computer vision" in excerpt.lower()


def test_professor_summary_cannot_create_new_match():
    result = score_professor(
        student=student(research_interests=["Robotics"]),
        professor_areas=["Robotics"],
        catalog_names=CATALOG,
        research_summary="The lab also mentions Computer Vision in passing.",
    )
    assert "Computer Vision" not in result.research_overlap
    assert not any(
        item.type == "professor_summary_mentions_area" and item.area_name == "Computer Vision"
        for item in result.evidence
    )


def test_skills_do_not_become_research_interests():
    result = score_professor(
        student=student(skills=[SkillExtract(name="Python"), SkillExtract(name="TensorFlow")]),
        professor_areas=["Computer Vision", "Machine Learning"],
        catalog_names=CATALOG,
    )
    assert result.score == 0
    assert result.research_overlap == []


def test_missing_projects_and_publications_handled_safely():
    with_artifacts_missing = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert with_artifacts_missing.score > 0
    assert with_artifacts_missing.components.artifacts is None


def test_missing_research_signals_handled_safely():
    result = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert result.components.signals is None
    assert result.score == score_professor(
        student=student(research_interests=["Computer Vision"], research_signals=[]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    ).score


def test_email_availability_does_not_affect_research_score():
    kwargs = dict(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert score_professor(**kwargs).score == score_professor(**kwargs).score


def test_closed_opportunity_does_not_increase_research_score():
    base = score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    assert base.score == score_professor(
        student=student(research_interests=["Computer Vision"]),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
        research_summary=None,
    ).score


def test_unconfirmed_profile_is_rejected(monkeypatch):
    from app.services import matching as matching_service

    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": str(uuid4()),
            "confirmed": False,
            "extracted_profile": student(research_interests=["Computer Vision"]).model_dump(),
        },
    )
    with pytest.raises(HTTPException) as exc:
        matching_service.match_professors(profile_id=str(uuid4()))
    assert exc.value.status_code == 400
    assert "Confirm" in exc.value.detail


def test_no_cv_is_rejected(monkeypatch):
    from app.services import matching as matching_service

    monkeypatch.setattr(
        matching_service.cv_service,
        "get_active_profile",
        lambda profile_id: {
            "cv_id": None,
            "confirmed": False,
            "extracted_profile": {},
        },
    )
    with pytest.raises(HTTPException) as exc:
        matching_service.match_professors(profile_id=str(uuid4()))
    assert exc.value.status_code == 400


def test_deterministic_repeated_runs():
    args = dict(
        student=student(
            research_interests=["Computer Vision", "Medical AI"],
            research_signals=["Edge AI"],
            projects=[ProjectExtract(title="Computer Vision screening")],
        ),
        professor_areas=["Computer Vision", "Medical AI", "Robotics"],
        catalog_names=CATALOG,
        research_summary="Work in Computer Vision and Medical AI.",
    )
    first = score_professor(**args)
    second = score_professor(**args)
    assert first.score == second.score
    assert first.priority == second.priority
    assert first.research_overlap == second.research_overlap
    assert [item.model_dump() for item in first.evidence] == [item.model_dump() for item in second.evidence]


def test_score_always_remains_in_range():
    result = score_professor(
        student=student(
            research_interests=CATALOG,
            research_signals=CATALOG,
            projects=[ProjectExtract(title=" ".join(CATALOG))],
            publications=[PublicationExtract(title=" ".join(CATALOG))],
        ),
        professor_areas=CATALOG,
        catalog_names=CATALOG,
        research_summary=" ".join(CATALOG),
    )
    assert 0 <= result.score <= 100
    empty = score_professor(
        student=student(),
        professor_areas=[],
        catalog_names=CATALOG,
    )
    assert empty.score == 0


def test_priority_thresholds():
    assert priority_for_score(100) == "high"
    assert priority_for_score(80) == "high"
    assert priority_for_score(79) == "normal"
    assert priority_for_score(50) == "normal"
    assert priority_for_score(49) == "low"
    assert priority_for_score(0) == "low"


def test_no_duplicate_evidence_entries():
    result = score_professor(
        student=student(
            research_interests=["Computer Vision", "Computer Vision"],
            projects=[
                ProjectExtract(title="Computer Vision"),
                ProjectExtract(title="Computer Vision"),
            ],
        ),
        professor_areas=["Computer Vision"],
        catalog_names=CATALOG,
    )
    serialized = [item.model_dump() for item in result.evidence]
    assert len(serialized) == len({tuple(sorted(item.items())) for item in serialized})


def test_area_count_bias_avoided():
    focused = score_professor(
        student=student(research_interests=["Computer Vision", "Medical AI"]),
        professor_areas=["Computer Vision", "Medical AI"],
        catalog_names=CATALOG,
    )
    broad = score_professor(
        student=student(research_interests=["Computer Vision", "Medical AI"]),
        professor_areas=["Computer Vision", "Medical AI", "Robotics", "Edge AI", "Machine Learning"],
        catalog_names=CATALOG,
    )
    assert focused.score == broad.score


def test_unavailable_components_renormalize():
    score = combine_components(
        ComponentScores(interests=100, signals=None, artifacts=None, corroboration=None)
    )
    assert score == 100
