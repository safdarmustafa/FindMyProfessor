from __future__ import annotations

import random

from app.cv.extraction.schema import ExtractedStudentProfile
from app.outreach.provider import (
    ArtifactEvidence,
    EmailDraftOutput,
    EmailGenerationProvider,
    MatchContext,
    OpportunityContext,
    ProfessorContext,
)

# ---------------------------------------------------------------------------
# Subject-line templates (keyed by email_type)
# ---------------------------------------------------------------------------
_SUBJECT_RESEARCH = [
    "Research Inquiry — {area}",
    "Prospective Research Student — {area}",
    "Research Opportunity Inquiry — {area}",
]

_SUBJECT_OPPORTUNITY = [
    "Research + Opportunity Inquiry — {area}",
    "Prospective Research Student — {area}",
    "Research Opportunity Inquiry — {area}",
]

# ---------------------------------------------------------------------------
# Sentence templates for the introduction paragraph
# ---------------------------------------------------------------------------
_INTRO_TEMPLATES = [
    (
        "My name is {name}, a {degree_phrase} with research interests in {interests}."
    ),
    (
        "I am {name}, a {degree_phrase} whose research focuses on {interests}."
    ),
    (
        "I am writing to introduce myself — {name}, a {degree_phrase} "
        "with a background in {interests}."
    ),
]

# ---------------------------------------------------------------------------
# Research paragraph openers
# ---------------------------------------------------------------------------
_RESEARCH_OPENERS = [
    "I am particularly drawn to your work in {area}, which aligns closely with my own research.",
    "Your research in {area} resonates strongly with my background.",
    "I noticed your group's focus on {area}, an area I have been actively working in.",
]

# ---------------------------------------------------------------------------
# Artifact hooks
# ---------------------------------------------------------------------------
_PROJECT_HOOKS = [
    (
        "In my project \"{title}\", I explored {area}, "
        "which I believe connects directly to your research focus."
    ),
    (
        "My work on \"{title}\" involved {area}, "
        "giving me hands-on experience relevant to your research."
    ),
]

_PUBLICATION_HOOKS = [
    (
        "My publication \"{title}\" addresses {area}, "
        "a topic that intersects with your research."
    ),
    (
        "I contributed to \"{title}\", which engages with {area} "
        "in ways that relate to your group's work."
    ),
]

# ---------------------------------------------------------------------------
# Fit / ask paragraph
# ---------------------------------------------------------------------------
_FIT_TEMPLATES_RESEARCH = [
    (
        "Given this overlap, I would welcome the opportunity to learn more about your current "
        "work and explore whether there is any possibility of a research position or "
        "graduate-level collaboration."
    ),
    (
        "I believe my background could contribute to your research, and I would be grateful "
        "to discuss any potential for collaboration or graduate study in your group."
    ),
]

_OPPORTUNITY_ADDITION = [
    (
        "I also noticed that {university} has an open {opp_type} opportunity — "
        "I would be glad to discuss that further as well."
    ),
    (
        "I was also pleased to see that {university} offers a {opp_type} opportunity, "
        "which I believe aligns with my goals."
    ),
]

_CLOSING_TEMPLATES = [
    (
        "Thank you for your time. I hope to hear from you.\n\n"
        "Warm regards,\n{name}"
    ),
    (
        "I appreciate your consideration and look forward to any response.\n\n"
        "Best regards,\n{name}"
    ),
]


class DeterministicTemplateProvider(EmailGenerationProvider):
    """
    Generates a concise, evidence-grounded email from structured verified data.
    No external API calls. No invented facts.
    """

    # Seed is fixed within a single generate() call so regeneration returns
    # a different controlled variant — not truly random, but rotates templates.
    _variant_counter: int = 0

    def generate(
        self,
        *,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        opportunity: OpportunityContext | None = None,
    ) -> EmailDraftOutput:
        # Rotate through template variants deterministically
        DeterministicTemplateProvider._variant_counter += 1
        v = DeterministicTemplateProvider._variant_counter

        subject = self._subject(professor, match, email_type, v)
        body = self._body(student, professor, match, email_type, opportunity, v)
        evidence = self._evidence_lines(student, professor, match, opportunity)

        return EmailDraftOutput(
            subject=subject,
            body=body,
            evidence_used=evidence,
            generation_provider="deterministic",
        )

    # ------------------------------------------------------------------
    # Subject
    # ------------------------------------------------------------------

    def _subject(
        self,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        v: int,
    ) -> str:
        area = match.research_overlap[0] if match.research_overlap else "Research"
        pool = _SUBJECT_OPPORTUNITY if email_type == "research_opportunity" else _SUBJECT_RESEARCH
        template = pool[v % len(pool)]
        return template.format(area=area)

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    def _body(
        self,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        opportunity: OpportunityContext | None,
        v: int,
    ) -> str:
        parts: list[str] = []

        # Greeting
        last_name = _last_name(professor.name)
        greeting = f"Dear Professor {last_name},"
        parts.append(greeting)
        parts.append("")

        # Introduction
        name = student.identity.name or "I"
        degree_phrase = _degree_phrase(student)
        interests = _interests_phrase(match.research_overlap, student.research_interests)
        intro = _INTRO_TEMPLATES[v % len(_INTRO_TEMPLATES)].format(
            name=name,
            degree_phrase=degree_phrase,
            interests=interests,
        )
        parts.append(intro)
        parts.append("")

        # Research paragraph
        area = match.research_overlap[0] if match.research_overlap else None
        if area:
            opener = _RESEARCH_OPENERS[v % len(_RESEARCH_OPENERS)].format(area=area)
            parts.append(opener)

            # Artifact hook (best project or publication)
            artifact = _best_artifact(match.artifact_evidence, match.research_overlap)
            if artifact:
                if artifact.kind == "publication":
                    hook = _PUBLICATION_HOOKS[v % len(_PUBLICATION_HOOKS)].format(
                        title=artifact.title, area=artifact.area_name
                    )
                else:
                    hook = _PROJECT_HOOKS[v % len(_PROJECT_HOOKS)].format(
                        title=artifact.title, area=artifact.area_name
                    )
                parts.append(hook)

            parts.append("")

        # Fit / ask paragraph
        fit = _FIT_TEMPLATES_RESEARCH[v % len(_FIT_TEMPLATES_RESEARCH)]
        parts.append(fit)

        # Opportunity paragraph (only when explicitly requested and available)
        if email_type == "research_opportunity" and opportunity and not opportunity.status == "closed":
            uni_name = opportunity.university_name or professor.university_name or "the university"
            opp_type = opportunity.opportunity_type or "research"
            opp_tmpl = _OPPORTUNITY_ADDITION[v % len(_OPPORTUNITY_ADDITION)]
            parts.append("")
            parts.append(opp_tmpl.format(university=uni_name, opp_type=opp_type))

        parts.append("")

        # Closing
        closing = _CLOSING_TEMPLATES[v % len(_CLOSING_TEMPLATES)].format(name=name)
        parts.append(closing)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Evidence list (human-readable)
    # ------------------------------------------------------------------

    def _evidence_lines(
        self,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        opportunity: OpportunityContext | None,
    ) -> list[str]:
        lines: list[str] = []
        for area in match.shared_interest_areas:
            lines.append(f"{area} — explicit research interest match")
        for ev in match.artifact_evidence:
            kind = ev.kind
            lines.append(f'Your {kind} "{ev.title}" — {ev.area_name} evidence')
        for area in match.corroborated_areas:
            lines.append(f"{area} — corroborated by professor research summary")
        if opportunity:
            uni = opportunity.university_name or professor.university_name or "university"
            lines.append(
                f"University opportunity: {opportunity.title or opportunity.opportunity_type} "
                f"at {uni} (university-wide, not professor-specific)"
            )
        return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_name(full_name: str) -> str:
    """Return the last token of the name as the last name."""
    if not full_name:
        return full_name
    parts = full_name.strip().split()
    return parts[-1] if parts else full_name


def _degree_phrase(student: ExtractedStudentProfile) -> str:
    education = student.education[0] if student.education else None
    if not education:
        return "research student"
    parts = []
    if education.degree:
        parts.append(education.degree)
    if education.field_of_study:
        parts.append(f"student in {education.field_of_study}")
    if education.institution:
        parts.append(f"at {education.institution}")
    if parts:
        return " ".join(parts)
    return "research student"


def _interests_phrase(overlap: list[str], raw_interests: list[str]) -> str:
    """Use the verified overlap areas; fall back to raw interests if none."""
    areas = overlap or raw_interests
    if not areas:
        return "research"
    if len(areas) == 1:
        return areas[0]
    return ", ".join(areas[:-1]) + f", and {areas[-1]}"


def _best_artifact(
    artifacts: list[ArtifactEvidence],
    overlap: list[str],
) -> ArtifactEvidence | None:
    """Prefer publications over projects; prefer artifacts in the overlap set."""
    overlap_set = {a.lower() for a in overlap}
    in_overlap = [a for a in artifacts if a.area_name.lower() in overlap_set]
    ranked = in_overlap or artifacts
    # Publications first
    pubs = [a for a in ranked if a.kind == "publication"]
    projs = [a for a in ranked if a.kind == "project"]
    return (pubs + projs + [None])[0]
