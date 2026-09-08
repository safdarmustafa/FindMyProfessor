from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class University(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    country: str | None = None
    city: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UniversityListResponse(BaseModel):
    universities: list[University]
    count: int
