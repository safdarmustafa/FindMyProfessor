from __future__ import annotations

import re

from app.cv.extraction.schema import ExtractedStudentProfile
from app.opportunities.models import OpportunityRecord, UniversityFitResult

STATUS_BASE = {
    "open": 100,
    "upcoming": 80,
    "unknown": 50,
}

UNDERGRAD_RE = re.compile(
    r"\b(b\.?\s*tech\.?|b\.?\s*e\.?|b\.?\s*s\.?|b\.?\s*sc\.?|b\.?\s*eng\.?|"
    r"bachelor(?:'?s)?|undergraduate|undergrad)\b",
    re.I,
)
GRADUATE_RE = re.compile(
    r"\b(m\.?\s*tech\.?|m\.?\s*s\.?|m\.?\s*sc\.?|m\.?\s*eng\.?|master(?:'?s)?|"
    r"mba|ph\.?d\.?|dphil|doctorate|doctoral)\b",
    re.I,
)


def is_clearly_undergraduate(student: ExtractedStudentProfile) -> bool:
    parts: list[str] = []
    for education in student.education:
        parts.extend(
            [
                education.degree or "",
                education.field_of_study or "",
                education.current_semester or "",
                education.institution or "",
                str(education.graduation_year or ""),
            ]
        )
    blob = " ".join(parts).strip()
    if not blob:
        return False
    if GRADUATE_RE.search(blob):
        return False
    return UNDERGRAD_RE.search(blob) is not None


def score_university_opportunities(
    opportunities: list[OpportunityRecord],
    *,
    student_is_undergraduate: bool = False,
) -> UniversityFitResult:
    useful = [item for item in opportunities if not item.is_closed()]
    if not useful:
        return UniversityFitResult(
            score=0,
            best_opportunity=None,
            why=(),
            non_closed_opportunity_count=0,
        )

    ranked: list[tuple[int, str, OpportunityRecord, tuple[str, ...]]] = []
    for item in useful:
        score, reasons = _score_one(item, student_is_undergraduate=student_is_undergraduate)
        ranked.append((score, item.id, item, reasons))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    best_score, _, best_item, best_why = ranked[0]
    return UniversityFitResult(
        score=min(100, best_score),
        best_opportunity=best_item,
        why=best_why,
        non_closed_opportunity_count=len(useful),
    )


def _score_one(
    item: OpportunityRecord,
    *,
    student_is_undergraduate: bool,
) -> tuple[int, tuple[str, ...]]:
    base = STATUS_BASE.get(item.status_key, STATUS_BASE["unknown"])
    reasons: list[str] = []
    if item.status_key == "open":
        reasons.append("University has an open opportunity.")
    elif item.status_key == "upcoming":
        reasons.append("University has an upcoming opportunity.")
    else:
        reasons.append("University has an opportunity with unknown status.")
    score = base
    if item.international_eligible is True:
        score += 5
        reasons.append("International eligibility is confirmed.")
    if item.undergraduate_eligible is True and student_is_undergraduate:
        score += 10
        reasons.append("Undergraduate eligibility is confirmed.")
    return min(100, score), tuple(reasons)
