"""Alias resolution, related-area credit, tie-break ranking and CV parsing fixes."""
from __future__ import annotations

from app.cv.extraction.heuristic import HeuristicExtractionProvider, _education, _looks_like_name
from app.cv.extraction.schema import ExtractedStudentProfile, ProjectExtract
from app.matching.ranking import area_frequencies, rank_key
from app.matching.scoring import score_professor

CATALOG = [
    "Machine Learning",
    "Computer Vision",
    "Natural Language Processing",
    "Large Language Models",
    "Robotics",
    "Medical AI",
    "Healthcare AI",
    "Reinforcement Learning",
    "Computer Science",
]


def student(**kwargs) -> ExtractedStudentProfile:
    return ExtractedStudentProfile(**kwargs)


# --- aliases -------------------------------------------------------------

def test_common_abbreviations_resolve_to_catalog_labels():
    result = score_professor(
        student=student(research_interests=["NLP", "LLMs"]),
        professor_areas=["Natural Language Processing", "Large Language Models"],
        catalog_names=CATALOG,
    )
    assert result.score == 100
    assert result.research_overlap == ["Natural Language Processing", "Large Language Models"]


def test_free_text_interest_is_scanned_for_areas():
    result = score_professor(
        student=student(research_interests=["object detection for medical imaging"]),
        professor_areas=["Computer Vision", "Medical AI"],
        catalog_names=CATALOG,
    )
    assert set(result.research_overlap) == {"Computer Vision", "Medical AI"}


def test_project_alias_counts_as_artifact_evidence():
    result = score_professor(
        student=student(projects=[ProjectExtract(title="Quadruped robot locomotion")]),
        professor_areas=["Robotics"],
        catalog_names=CATALOG,
    )
    assert result.score > 0
    assert any(e.student_source == "project" and e.area_name == "Robotics" for e in result.evidence)


def test_alias_matching_is_word_bounded():
    # "rl" must not fire inside "world"; "ml" must not fire inside "html".
    result = score_professor(
        student=student(research_interests=["world models in html"]),
        professor_areas=["Reinforcement Learning", "Machine Learning"],
        catalog_names=CATALOG,
    )
    assert result.score == 0


# --- related areas -------------------------------------------------------

def test_related_area_gets_partial_credit_but_is_not_a_shared_area():
    related = score_professor(
        student=student(research_interests=["Healthcare AI"]),
        professor_areas=["Medical AI"],
        catalog_names=CATALOG,
    )
    exact = score_professor(
        student=student(research_interests=["Healthcare AI"]),
        professor_areas=["Healthcare AI"],
        catalog_names=CATALOG,
    )
    assert 0 < related.score < exact.score
    assert related.research_overlap == []
    assert related.related_areas == [("Healthcare AI", "Medical AI")]
    assert any("closely related" in line for line in related.why)


def test_exact_match_is_not_also_reported_as_related():
    result = score_professor(
        student=student(research_interests=["Medical AI"]),
        professor_areas=["Medical AI", "Healthcare AI"],
        catalog_names=CATALOG,
    )
    assert result.research_overlap == ["Medical AI"]
    assert result.related_areas == []


# --- ranking -------------------------------------------------------------

def test_rare_shared_area_outranks_generic_one_at_equal_score():
    me = student(research_interests=["Machine Learning", "Medical AI"])
    professors = {
        "Alice Generic": ["Machine Learning"],
        "Zed Specific": ["Medical AI"],
        **{f"Filler {i}": ["Machine Learning"] for i in range(20)},
    }
    frequencies = area_frequencies(professors.values())
    generic = score_professor(student=me, professor_areas=professors["Alice Generic"], catalog_names=CATALOG)
    specific = score_professor(student=me, professor_areas=professors["Zed Specific"], catalog_names=CATALOG)
    assert generic.score == specific.score
    key = lambda name, result: rank_key(result, professors[name], frequencies, len(professors), name)  # noqa: E731
    assert key("Zed Specific", specific) < key("Alice Generic", generic)


def test_focused_professor_outranks_broad_one_at_equal_score():
    me = student(research_interests=["Computer Vision"])
    focused_areas = ["Computer Vision"]
    broad_areas = ["Computer Vision", "Robotics", "Reinforcement Learning", "Healthcare AI"]
    frequencies = area_frequencies([focused_areas, broad_areas])
    focused = score_professor(student=me, professor_areas=focused_areas, catalog_names=CATALOG)
    broad = score_professor(student=me, professor_areas=broad_areas, catalog_names=CATALOG)
    assert focused.score == broad.score
    assert rank_key(focused, focused_areas, frequencies, 2, "Zz") < rank_key(broad, broad_areas, frequencies, 2, "Aa")


# --- CV parsing ----------------------------------------------------------

def test_interest_list_is_never_taken_as_the_student_name():
    cv = "Education\nMaster's in Mechanical Engineering, University of Lahore, 2026\nInterests\nSLAM, autonomous navigation\n"
    profile = HeuristicExtractionProvider().extract(cv, CATALOG)
    assert profile.identity.name is None
    assert profile.research_interests == ["Robotics"]


def test_name_shape_check():
    assert _looks_like_name("Jean-Luc O'Neil")
    assert _looks_like_name("Muhammad Saif Raza")
    assert not _looks_like_name("Curriculum Vitae")
    assert not _looks_like_name("SLAM, autonomous navigation, reinforcement learning")


def test_institution_keeps_leading_words():
    edu = _education(["B.Tech in Computer Science, Indian Institute of Technology Delhi, 2027"])[0]
    assert edu.institution == "Indian Institute of Technology Delhi"
