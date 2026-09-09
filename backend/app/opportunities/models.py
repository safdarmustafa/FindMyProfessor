from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OpportunityRecord:
    id: str
    university_id: str | None = None
    professor_id: str | None = None
    lab_id: str | None = None
    title: str | None = None
    opportunity_type: str | None = None
    description: str | None = None
    eligibility: str | None = None
    international_eligible: bool | None = None
    undergraduate_eligible: bool | None = None
    funding_type: str | None = None
    stipend_amount: Any = None
    tuition_coverage: Any = None
    accommodation_coverage: Any = None
    travel_coverage: Any = None
    application_deadline: str | None = None
    start_date: str | None = None
    official_url: str | None = None
    status: str | None = None

    @property
    def not_professor_specific(self) -> bool:
        return self.professor_id is None

    @property
    def status_key(self) -> str:
        value = (self.status or "unknown").strip().casefold()
        return value or "unknown"

    def is_closed(self) -> bool:
        return self.status_key == "closed"


@dataclass(frozen=True)
class UniversityFitResult:
    score: int
    best_opportunity: OpportunityRecord | None
    why: tuple[str, ...]
    non_closed_opportunity_count: int
