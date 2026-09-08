from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Department(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    university_id: UUID
    name: str
    website_url: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DepartmentListResponse(BaseModel):
    departments: list[Department]
    count: int
