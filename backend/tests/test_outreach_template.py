"""The deterministic email must read like a person wrote it and never invent facts."""
from __future__ import annotations

import re

import pytest

from app.cv.extraction.schema import (
    EducationExtract,
    ExperienceExtract,
    ExtractedStudentProfile,
    IdentityExtract,
    PublicationExtract,
    SkillExtract,
)
from app.outreach.deterministic import DeterministicTemplateProvider, summary_topics
from app.outreach.provider import ArtifactEvidence, MatchContext, OpportunityContext, ProfessorContext

STOCK_PHRASES = re.compile(
    r"—|!|resonat|aligns? closely|introduce myself|delve|passionate|hope this (?:email|message) finds",
    re.I,
)


def professor(**overrides) -> ProfessorContext:
    data = dict(
        professor_id="p1",
        name="Jane Smith",
        title="Associate Professor",
        email="jane@example.edu",
        university_name="Example University",
        department_name=None,
        lab_name=None,
        research_areas=["Natural Language Processing"],
        research_summary="Research on dialogue systems, low-resource NLP, and machine learning.",
    )
    data.update(overrides)
    return ProfessorContext(**data)


def match(**overrides) -> MatchContext:
    data = dict(
        research_score=100,
        research_overlap=["Natural Language Processing"],
        shared_interest_areas=["Natural Language Processing"],
        artifact_evidence=[],
        corroborated_areas=[],
    )
    data.update(overrides)
    return MatchContext(**data)


def full_student() -> ExtractedStudentProfile:
    return ExtractedStudentProfile(
        identity=IdentityExtract(name="Priya Sharma"),
        education=[
            EducationExtract(
                degree="B.Tech",
                field_of_study="Computer Science",
                institution="Indian Institute of Technology Delhi",
            )
        ],
        research_interests=["Natural Language Processing"],
        skills=[SkillExtract(name="Python", category="language"), SkillExtract(name="PyTorch", category="ml_tool")],
    )


def generate(student=None, prof=None, ctx=None, email_type="research", opportunity=None):
    return DeterministicTemplateProvider().generate(
        student=student or full_student(),
        professor=prof or professor(),
        match=ctx or match(),
        email_type=email_type,
        opportunity=opportunity,
    )


@pytest.mark.parametrize("_round", range(6))  # cover every rotating variant
def test_formal_register_and_sensible_length(_round):
    out = generate()
    text = out.subject + out.body
    assert not STOCK_PHRASES.search(text)
    assert not re.search(r"\b(?:I'm|I've|don't|can't|won't|it's)\b", text)  # no contractions
    assert 80 <= len(out.body.split()) <= 400
    assert out.body.startswith("Dear Professor Smith,")
    assert "I am writing to" in out.body
    assert re.search(r"\n(?:Sincerely|Kind regards),\nPriya Sharma\nB\.Tech in Computer Science, Indian Institute of Technology Delhi", out.body)


def test_uses_professor_specific_topic_from_summary():
    out = generate()
    assert "dialogue systems" in out.body


def test_missing_name_is_never_replaced_with_a_placeholder():
    student = full_student()
    student.identity.name = None
    out = generate(student=student)
    assert "My name is" not in out.body
    assert "None" not in out.body and "[" not in out.body
    assert re.search(r"(?:Sincerely|Kind regards),\nB\.Tech", out.body)


def test_publication_is_cited_with_title_venue_and_status():
    student = full_student()
    student.publications = [
        PublicationExtract(title="A Survey of Agents", publication_type="under review"),
        PublicationExtract(title="Low-resource Hindi QA", venue="ACL 2025", year=2025, publication_type="published"),
    ]
    ctx = match(artifact_evidence=[ArtifactEvidence(
        kind="publication", title="Low-resource Hindi QA", area_name="Natural Language Processing",
    )])
    out = generate(student=student, ctx=ctx)
    assert ('In terms of research experience, I have co-authored two research papers. '
            'The one most relevant to your work is "Low-resource Hindi QA", published at ACL.') in out.body
    assert 'I have also contributed to "A Survey of Agents", which is currently under review.' in out.body


def test_most_relevant_paper_is_chosen_over_a_generic_one():
    student = full_student()
    student.publications = [
        PublicationExtract(title="Machine Learning for Everything", venue="Workshop X", publication_type="published"),
        PublicationExtract(title="Dialogue Systems for Hindi", venue="ACL", publication_type="published"),
    ]
    ctx = match(artifact_evidence=[
        ArtifactEvidence(kind="publication", title="Machine Learning for Everything", area_name="Machine Learning"),
        ArtifactEvidence(kind="publication", title="Dialogue Systems for Hindi", area_name="Natural Language Processing"),
    ])
    assert '"Dialogue Systems for Hindi"' in generate(student=student, ctx=ctx).body


def test_research_role_is_mentioned_with_its_organisation():
    student = full_student()
    student.experience = [
        ExperienceExtract(role="Software Intern", organization="Acme", kind="internship"),
        ExperienceExtract(role="Peer Reviewer", organization="NeurIPS 2026", kind="research"),
    ]
    body = generate(student=student).body
    assert "In terms of research experience, I have served as a peer reviewer for NeurIPS 2026." in body
    # The internship is never presented as research; only as practical experience.
    assert "served as a software intern" not in body
    assert "My practical experience includes working as a software intern at Acme." in body


def test_internship_is_used_when_there_is_no_research_evidence():
    student = full_student()
    student.experience = [ExperienceExtract(role="Android Developer Intern", organization="Square Nova", kind="internship")]
    body = generate(student=student).body
    assert "My practical experience includes working as an Android developer intern at Square Nova." in body


def test_specific_shared_area_leads_over_broad_one():
    ctx = match(research_overlap=["Machine Learning", "Natural Language Processing"])
    out = generate(ctx=ctx)
    assert out.subject.startswith("Research Internship Inquiry: Natural Language Processing")
    assert len(out.subject) <= 95  # credentials are dropped rather than overflow the subject


def test_ask_matches_student_level():
    undergrad = generate().body
    masters_student = full_student()
    masters_student.education[0].degree = "MS"
    masters = generate(student=masters_student).body
    assert "undergraduate" in undergrad
    assert "PhD" in masters and "undergraduate" not in masters
    assert "an MS student" in masters


def test_related_only_match_is_described_honestly():
    ctx = match(
        research_overlap=[],
        shared_interest_areas=[],
        related_areas=[("Healthcare AI", "Medical AI")],
    )
    out = generate(ctx=ctx)
    assert "healthcare AI" in out.body and "medical AI" in out.body
    assert "closely connected" in out.body or "central to your research" in out.body


def test_opportunity_is_university_wide_and_closed_ones_are_ignored():
    open_opp = OpportunityContext("o1", "Summer Research Programme", "internship", "open", "Example University", True)
    out = generate(email_type="research_opportunity", opportunity=open_opp)
    assert "Summer Research Programme" in out.body
    assert "you are offering" not in out.body.lower()

    closed = OpportunityContext("o2", "Old Programme", "internship", "closed", "Example University", True)
    out = generate(email_type="research_opportunity", opportunity=closed)
    assert "Old Programme" not in out.body


def test_greeting_handles_titles_and_honorifics():
    assert generate(prof=professor(name="Dr. John Doe Jr.")).body.startswith("Dear Professor Doe,")
    assert generate(prof=professor(name="Ann Lee", title="Senior Lecturer")).body.startswith("Dear Dr. Lee,")
    assert generate(prof=professor(name="")).body.startswith("Dear Professor,")


def test_empty_profile_still_produces_a_clean_draft():
    out = generate(student=ExtractedStudentProfile(), ctx=match(research_overlap=[], shared_interest_areas=[]))
    assert out.subject
    assert not STOCK_PHRASES.search(out.body)
    assert "None" not in out.body


def test_summary_topics_skip_scraping_notes_and_echoes():
    assert summary_topics("Official faculty listing. Research statement not fetched.", ["Robotics"]) == []
    assert summary_topics("Computer vision, robotics.", ["Computer Vision"]) == []
    assert summary_topics("3D computer vision, quantum computing.", ["Computer Vision"]) == ["3D computer vision"]


def test_letterhead_is_never_used_as_the_students_name():
    student = full_student()
    student.identity.name = "INDIAN INSTITUTE OF TECHNOLOGY DELHI"
    body = generate(student=student).body
    assert "My name is" not in body
    assert "Indian Institute Of Technology Delhi\n" not in body


def test_detailed_email_uses_papers_roles_projects_and_internship():
    from app.cv.extraction.schema import ProjectExtract
    student = full_student()
    student.research_interests = ["Natural Language Processing", "Medical AI", "Edge AI"]
    student.publications = [
        PublicationExtract(title="Dialogue Systems for Hindi", venue="ICML Workshop: NLP in Practice", publication_type="published"),
        PublicationExtract(title="Agents in Business", publication_type="under review"),
    ]
    student.experience = [
        ExperienceExtract(role="Peer Reviewer", organization="NeurIPS 2026", kind="research"),
        ExperienceExtract(role="Android Developer Intern", organization="Nova Labs", kind="internship",
                          description="Developed Android features using Kotlin. Integrated APIs."),
    ]
    student.projects = [
        ProjectExtract(title="Payments App", description="Built a subscription system using Razorpay."),
        ProjectExtract(title="Hindi QA – Question Answering Bot", description="Built production chatbot for Hindi question answering with LLMs."),
    ]
    ctx = match(artifact_evidence=[
        ArtifactEvidence(kind="publication", title="Dialogue Systems for Hindi", area_name="Natural Language Processing"),
        ArtifactEvidence(kind="project", title="Hindi QA – Question Answering Bot", area_name="Natural Language Processing"),
    ])
    body = generate(student=student, ctx=ctx).body
    assert "My broader research interests include medical AI and edge AI." in body or \
        "More broadly, my research interests centre on medical AI and edge AI." in body
    assert '"Dialogue Systems for Hindi", published at the ICML Workshop: NLP in Practice.' in body
    assert "In addition, I have served as a peer reviewer for NeurIPS 2026." in body
    assert ("in my project Hindi QA (Question Answering Bot), I built a production chatbot for Hindi "
            "question answering with LLMs.") in body
    assert "This work is closely related to your research in natural language processing." in body
    assert "Payments App" not in body  # unrelated, non-research project is left out
    assert "working as an Android developer intern at Nova Labs, where I developed Android features using Kotlin." in body
    assert "I believe this combination of research and practical experience would allow me to contribute" in body
