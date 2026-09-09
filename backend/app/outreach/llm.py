from __future__ import annotations

"""
Optional LLM-based email generation provider.

This provider is ONLY active when EMAIL_LLM_API_KEY (or LLM_API_KEY) is set.
It is never required; the deterministic provider is always the default.

Security:
- API keys are server-side environment variables only.
- Keys are never logged or returned to the frontend.
- The LLM receives ONLY structured verified facts — no free-text instructions
  that could lead it to invent publications, research claims, or recruiting info.
"""

import os
from typing import Any

from app.cv.extraction.schema import ExtractedStudentProfile
from app.outreach.provider import (
    EmailDraftOutput,
    EmailGenerationProvider,
    MatchContext,
    OpportunityContext,
    ProfessorContext,
)
from app.outreach.deterministic import _last_name, _degree_phrase, _interests_phrase


_SYSTEM_PROMPT = """\
You are an academic research outreach assistant. Your only job is to write a concise, \
humble, professional cold email from a student to a professor.

STRICT RULES:
1. Use ONLY the facts provided in the user message. Do not add any facts.
2. Do not claim the student has read any specific paper unless it is explicitly listed.
3. Do not claim the professor is currently recruiting unless explicitly stated.
4. Do not mention CV attachment.
5. Do not use words like URGENT, IMPORTANT, or exclamation marks.
6. Keep the email between 120 and 220 words (hard maximum 300).
7. Format: Subject line on the first line, blank line, then the email body.
8. The greeting must be: Dear Professor [LastName],
9. Do not invent any research topics, papers, labs, funding, or deadlines.
10. If information is missing, omit that detail rather than guessing.
"""


def _build_user_prompt(
    student: ExtractedStudentProfile,
    professor: ProfessorContext,
    match: MatchContext,
    email_type: str,
    opportunity: OpportunityContext | None,
) -> str:
    name = student.identity.name or "the student"
    degree = _degree_phrase(student)
    interests = _interests_phrase(match.research_overlap, student.research_interests)

    artifacts = "\n".join(
        f"  - {ev.kind.capitalize()}: \"{ev.title}\" (area: {ev.area_name})"
        for ev in match.artifact_evidence
    ) or "  None"

    opp_section = ""
    if email_type == "research_opportunity" and opportunity and opportunity.status != "closed":
        uni = opportunity.university_name or professor.university_name or "the university"
        opp_section = (
            f"\nUNIVERSITY-WIDE OPPORTUNITY (NOT professor-specific):\n"
            f"  Title: {opportunity.title or 'N/A'}\n"
            f"  Type: {opportunity.opportunity_type or 'N/A'}\n"
            f"  Status: {opportunity.status}\n"
            f"  University: {uni}\n"
            f"  NOTE: Do NOT say the professor is offering this. Say the university offers it.\n"
        )

    return f"""\
STUDENT FACTS:
  Name: {name}
  Degree/Program: {degree}
  Verified research interests: {interests}
  Verified shared research areas with this professor: {', '.join(match.research_overlap) or 'None'}

STUDENT ARTIFACTS:
{artifacts}

PROFESSOR FACTS:
  Name: {professor.name}
  University: {professor.university_name or 'N/A'}
  Department: {professor.department_name or 'N/A'}
  Lab: {professor.lab_name or 'N/A'}
  Verified research areas: {', '.join(professor.research_areas) or 'N/A'}

EMAIL TYPE: {email_type}
{opp_section}
Write the email now. First line: subject. Then blank line. Then email body.
Do NOT include anything outside the subject line and email body.
"""


class LlmEmailProvider(EmailGenerationProvider):
    """
    OpenAI-compatible LLM email provider. Uses a strict structured prompt.
    Falls back gracefully if the API call fails.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    def generate(
        self,
        *,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        opportunity: OpportunityContext | None = None,
    ) -> EmailDraftOutput:
        user_prompt = _build_user_prompt(student, professor, match, email_type, opportunity)
        try:
            response = self._call_api(user_prompt)
            subject, body = _parse_llm_response(response)
            provider_label = f"llm:{self._model}"
        except Exception:
            # Fallback to deterministic on any API error — never crash
            from app.outreach.deterministic import DeterministicTemplateProvider
            fallback = DeterministicTemplateProvider()
            out = fallback.generate(
                student=student,
                professor=professor,
                match=match,
                email_type=email_type,
                opportunity=opportunity,
            )
            return out

        evidence = _build_evidence(match, opportunity, professor)
        return EmailDraftOutput(
            subject=subject,
            body=body,
            evidence_used=evidence,
            generation_provider=provider_label,
        )

    def _call_api(self, user_prompt: str) -> str:
        """Call OpenAI-compatible chat completion API via httpx (sync)."""
        import httpx  # already available through httpx / starlette deps

        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 600,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def _parse_llm_response(text: str) -> tuple[str, str]:
    """Extract subject and body from the LLM response."""
    lines = text.split("\n")
    subject_line = ""
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            subject_line = stripped[len("subject:"):].strip()
            body_start = i + 1
            break
        if stripped:
            subject_line = stripped
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return subject_line, body


def _build_evidence(
    match: MatchContext,
    opportunity: OpportunityContext | None,
    professor: ProfessorContext,
) -> list[str]:
    lines: list[str] = []
    for area in match.shared_interest_areas:
        lines.append(f"{area} — explicit research interest match")
    for ev in match.artifact_evidence:
        lines.append(f'Your {ev.kind} "{ev.title}" — {ev.area_name} evidence')
    for area in match.corroborated_areas:
        lines.append(f"{area} — corroborated by professor research summary")
    if opportunity:
        uni = opportunity.university_name or professor.university_name or "university"
        lines.append(
            f"University opportunity: {opportunity.title or opportunity.opportunity_type} "
            f"at {uni} (university-wide, not professor-specific)"
        )
    return lines
