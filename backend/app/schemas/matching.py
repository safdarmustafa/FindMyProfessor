from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.matching.models import MatchEvidence

MatchMode = Literal["research", "opportunity", "both"]


class MatchUniversity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID | None = None
    name: str | None = None
    country: str | None = None
    city: str | None = None


class MatchDepartment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID | None = None
    name: str | None = None


class MatchLab(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID | None = None
    name: str | None = None


class MatchProfessor(BaseModel):
    id: UUID
    name: str
    title: str | None = None
    email: str | None = None
    email_available: bool
    university: MatchUniversity | None = None
    department: MatchDepartment | None = None
    lab: MatchLab | None = None


class ResearchMatchScore(BaseModel):
    score: int = Field(ge=0, le=100)
    priority: Literal["high", "normal", "low"]
    why: list[str] = Field(default_factory=list)


class UniversityOpportunityContext(BaseModel):
    id: UUID | str
    title: str | None = None
    type: str | None = None
    status: str | None = None
    not_professor_specific: bool = True
    official_url: str | None = None


class ProfessorMatch(BaseModel):
    professor: MatchProfessor
    research_match: ResearchMatchScore
    research_overlap: list[str]
    evidence: list[MatchEvidence]
    university_opportunities: list[UniversityOpportunityContext] = Field(default_factory=list)
    university_opportunity_fit: int | None = Field(
        default=None,
        description="University-level context only. Never a professor-specific opportunity score.",
        ge=0,
        le=100,
    )


class MatchingResponse(BaseModel):
    profile_id: UUID
    mode: MatchMode
    match_version: str
    count: int
    matches: list[ProfessorMatch]
