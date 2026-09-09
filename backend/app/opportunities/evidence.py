from __future__ import annotations

from app.matching.models import MatchEvidence
from app.opportunities.models import OpportunityRecord, UniversityFitResult


def university_opportunity_evidence(
    item: OpportunityRecord,
    *,
    university_name: str | None,
) -> MatchEvidence:
    return MatchEvidence(
        type="university_opportunity",
        opportunity_id=item.id,
        title=item.title,
        opportunity_type=item.opportunity_type,
        status=item.status,
        university=university_name,
        not_professor_specific=item.not_professor_specific,
    )


def fit_why_lines(fit: UniversityFitResult) -> list[str]:
    return list(fit.why)
