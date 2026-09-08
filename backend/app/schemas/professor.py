from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.department import Department
from app.schemas.lab import Lab
from app.schemas.research_area import ResearchArea
from app.schemas.university import University


class Professor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    lab_id: UUID | None = None
    department_id: UUID | None = None
    name: str
    email: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None
    recruiting_status: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfessorDetail(Professor):
    lab: Lab | None = None
    department: Department | None = None
    university: University | None = None
    research_areas: list[ResearchArea] = []


class ProfessorListResponse(BaseModel):
    professors: list[Professor]
    count: int


class ProfessorSearchResponse(BaseModel):
    professors: list[ProfessorDetail]
    count: int
