from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALLOWED_OPPORTUNITY_TYPES = ("internship", "ra", "masters", "phd")
KNOWN_RECRUITING_STATUSES = {
    "open",
    "closed",
    "recruiting",
    "not_recruiting",
    "unknown",
    "yes",
    "no",
    "true",
    "false",
    "active",
    "inactive",
}


def blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    return value


class SeedModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_strings_to_none(cls, value: Any) -> Any:
        return blank_to_none(value)


class ManifestUniversity(SeedModel):
    id: str
    name: str | None = None
    file: str
    enabled: bool = False


class Manifest(SeedModel):
    expected_count: int = 30
    notes: str | None = None
    universities: list[ManifestUniversity]


class UniversityRecord(SeedModel):
    id: str
    name: str
    country: str | None = None
    city: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool = True
    source_url: str | None = None


class DepartmentRecord(SeedModel):
    id: str
    university: str
    name: str
    website_url: str | None = None
    description: str | None = None
    source_url: str | None = None


class LabRecord(SeedModel):
    id: str
    university: str
    department: str
    name: str
    website_url: str | None = None
    description: str | None = None
    research_summary: str | None = None
    source_url: str | None = None


class ResearchAreaRecord(SeedModel):
    name: str
    description: str | None = None
    source_url: str | None = None


class ProfessorRecord(SeedModel):
    id: str
    university: str
    department: str | None = None
    lab: str | None = None
    name: str
    title: str | None = None
    email: str | None = None
    website_url: str | None = None
    linkedin_url: str | None = None
    biography: str | None = None
    research_summary: str | None = None
    recent_work_summary: str | None = None
    recruiting_status: str | None = None
    internship_available: bool | None = None
    ra_available: bool | None = None
    masters_available: bool | None = None
    phd_available: bool | None = None
    is_active: bool = True
    source_url: str | None = None
    research_areas: list[str | ResearchAreaRecord] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("email must be a valid address or null")
        return value.lower()

    def area_records(self) -> list[ResearchAreaRecord]:
        areas: list[ResearchAreaRecord] = []
        for item in self.research_areas:
            if isinstance(item, ResearchAreaRecord):
                areas.append(item)
            else:
                areas.append(ResearchAreaRecord(name=item))
        return areas


class OpportunityRecord(SeedModel):
    id: str | None = None
    university: str
    professor: str | None = None
    lab: str | None = None
    title: str | None = None
    opportunity_type: str
    description: str | None = None
    eligibility: str | None = None
    international_eligible: bool | None = None
    undergraduate_eligible: bool | None = None
    funding_type: str | None = None
    stipend_amount: float | int | str | None = None
    tuition_coverage: bool | None = None
    accommodation_coverage: bool | None = None
    travel_coverage: bool | None = None
    application_deadline: date | None = None
    start_date: date | None = None
    official_url: str | None = None
    status: str | None = None
    source_url: str | None = None

    @field_validator("opportunity_type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("application_deadline", "start_date", mode="before")
    @classmethod
    def _parse_date(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @model_validator(mode="after")
    def _check_opportunity_type(self) -> "OpportunityRecord":
        if self.opportunity_type not in ALLOWED_OPPORTUNITY_TYPES:
            raise ValueError(
                f"opportunity_type must be one of {', '.join(ALLOWED_OPPORTUNITY_TYPES)}"
            )
        return self
