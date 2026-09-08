from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResearchArea(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    description: str | None = None
    created_at: datetime | None = None


class ResearchAreaListResponse(BaseModel):
    research_areas: list[ResearchArea]
    count: int
