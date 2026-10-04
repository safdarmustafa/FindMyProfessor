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


# ---------------------------------------------------------------------------
# Real-world layouts (synthetic content): a university placement template
# with a letterhead and two columns, and a research CV exported with a
# symbol font (U+F0B7 bullets) and numbered citations.
# ---------------------------------------------------------------------------

from app.cv.extraction.heuristic import HeuristicExtractionProvider as _Heuristic  # noqa: E402

_CATALOG = [
    "Machine Learning", "Deep Learning", "Medical AI", "Computer Vision", "Edge AI",
    "Large Language Models", "AI Agents", "Natural Language Processing", "Computer Science",
]

PLACEMENT_CV = """EXAMPLE UNIVERSITY
(Deemed to be University,
Accredited in 'A' Grade)
School of Engineering Sciences & Technology

SKILLS
LANGUAGES:
● JAVA
● Kotlin , Python ,
ACHIEVEMENTS
● NeurIPS Reviewer - The 40th
Conference on Neural
Information Processing
OTHER DETAILS
● Active Researcher
Riya Kapoor
Email: riya.kapoor@example.com
Phone: +91 9000000000
LinkedIn: www.linkedin.com/in/riya
B.Tech in Computer Science with experience in AI/ML and building AI agents on top of LLMs.
EXPERIENCE / INTERNSHIPS
March 2026 – Present 2026
Android Developer Intern, Nova Labs | Hybrid
● Developed Android features using Kotlin and Jetpack Compose,
improving app
performance.
EDUCATION
B.Tech — Computer Science & Engineering
Example Hamdard University, New Delhi, India
2023 — Present (7th Semester)
Cumulative CGPA: 7.8 / 10
Class 12 — Higher Secondary Schooling
CERTIFICATIONS
● DeepLearning.AI / Coursera - Supervised Machine Learning: Regression and
Classification
PROJECTS
Wallpaper App |
Kotlin · Jetpack Compose · Supabase  Github|| Play Store Link
● Built a subscription system using Razorpay
● Designed analytics to track the funnel
NewsPost App | Hilt, Dagger,MVVM,· Jetpack Compose ·
Mixpanel,Meta SDK  Github || Play Store Link
● Developed a Flutter admin panel.
●
"""

RESEARCH_CV = """Omar Siddiqui
omar.s@example.com | Delhi, India | LinkedIn
EDUCATION
Bachelor of Technology | Major: Computer Science 2023-2027
Example_University, New Delhi, India
RESEARCH INTEREST
 Deep Learning in Healthcare & Medical Imaging
 LLMs Optimization
WORK EXPERIENCE
Peer Reviewer                                    Jun 2026 – Present
NeurIPS 2026 (The 40th Conference) | Remote
 Served as an official reviewer for NeurIPS 2026, contributing technical and
ethics reviews
PUBLICATIONS / CONFERENCES
1. Siddiqui O., & Rao P. (2025). "Knee Osteoarthritis Grading Using Optimized Deep
Learning on Limited Systems." International Conference on Computational Intelligence. [Published]
2. Siddiqui, O., et al. (2025). "Agentic AI in Business: A Bibliometric Analysis." [Under Review]
PROJECTS
Agro 360 – Smart Farming Assistant
 Built an Android app with deep-learning models for crop prediction.
 Skills Learnt: Python, Android (Kotlin, Retrofit), TensorFlow Lite
CERTIFICATION
  Coursera – Introduction To AI.
"""


def test_placement_template_with_letterhead_and_two_columns():
    p = _Heuristic().extract(PLACEMENT_CV, _CATALOG)
    assert p.identity.name == "Riya Kapoor"  # not the university letterhead
    assert p.identity.email == "riya.kapoor@example.com"
    edu = p.education[0]
    assert (edu.degree, edu.field_of_study, edu.institution) == (
        "B.Tech", "Computer Science & Engineering", "Example Hamdard University",
    )
    assert edu.graduation_year is None and edu.current_semester == "7th semester"
    assert [(e.role, e.organization, e.kind) for e in p.experience] == [
        ("Android Developer Intern", "Nova Labs", "internship"),
    ]
    assert [x.title for x in p.projects] == ["Wallpaper App", "NewsPost App"]
    assert "Jetpack Compose" in p.projects[0].technologies
    assert [c.name for c in p.certifications] == ["Supervised Machine Learning: Regression and Classification"]
    assert {"AI Agents", "Large Language Models"} <= set(p.research_signals)


def test_research_cv_with_symbol_font_bullets_and_numbered_citations():
    p = _Heuristic().extract(RESEARCH_CV, _CATALOG)
    assert p.identity.name == "Omar Siddiqui"
    edu = p.education[0]
    assert (edu.field_of_study, edu.institution, edu.graduation_year) == ("Computer Science", "Example University", 2027)
    assert {"Deep Learning", "Medical AI", "Large Language Models"} <= set(p.research_interests)
    reviewer = p.experience[0]
    assert (reviewer.role, reviewer.organization, reviewer.kind) == ("Peer Reviewer", "NeurIPS 2026", "research")
    assert [(x.title, x.publication_type) for x in p.publications] == [
        ("Knee Osteoarthritis Grading Using Optimized Deep Learning on Limited Systems", "published"),
        ("Agentic AI in Business: A Bibliometric Analysis", "under review"),
    ]
    assert p.publications[0].venue == "International Conference on Computational Intelligence"
    assert p.projects[0].title == "Agro 360 – Smart Farming Assistant"
    assert p.projects[0].technologies == ["Python", "Android (Kotlin, Retrofit)", "TensorFlow Lite"]
    assert p.certifications[0].issuer == "IBM / Coursera"
