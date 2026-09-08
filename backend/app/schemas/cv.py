from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.cv.extraction.schema import ExtractedStudentProfile


class CvUploadResponse(BaseModel):
    cv_id: UUID
    profile_id: UUID
    original_filename: str
    file_type: str
    file_size: int
    parsing_status: str
    parsing_error: str | None = None
    is_default: bool
    extracted_profile: ExtractedStudentProfile | None = None


class CvVersionResponse(CvUploadResponse):
    version_number: int
    created_at: datetime | None = None


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile_id: UUID
    confirmed: bool = False
    cv_id: UUID | None = None
    extracted_profile: ExtractedStudentProfile
    persisted: dict[str, Any] | None = None


class StudentProfileUpdate(BaseModel):
    extracted_profile: ExtractedStudentProfile


class ProfileConfirmResponse(BaseModel):
    profile_id: UUID
    confirmed: bool
    message: str
