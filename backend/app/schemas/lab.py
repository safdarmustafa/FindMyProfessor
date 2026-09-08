from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Lab(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    department_id: UUID
    name: str
    description: str | None = None
    website_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LabListResponse(BaseModel):
    labs: list[Lab]
    count: int
