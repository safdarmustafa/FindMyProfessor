from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas.cv import StudentProfileUpdate
from app.services import cv as cv_service

router = APIRouter(prefix="/profile", tags=["profile"])


def _require_profile(x_profile_id: str | None) -> str:
    if not x_profile_id:
        raise HTTPException(
            status_code=400,
            detail="X-Profile-Id header is required. Upload a CV first to create a profile.",
        )
    return x_profile_id


@router.get("")
def get_profile(x_profile_id: str | None = Header(default=None, alias="X-Profile-Id")):
    profile_id = _require_profile(x_profile_id)
    return cv_service.get_active_profile(profile_id)


@router.put("")
def put_profile(
    body: StudentProfileUpdate,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    profile_id = _require_profile(x_profile_id)
    return cv_service.update_extracted_profile(profile_id, body.extracted_profile)


@router.post("/confirm")
def confirm_profile(x_profile_id: str | None = Header(default=None, alias="X-Profile-Id")):
    profile_id = _require_profile(x_profile_id)
    return cv_service.confirm_profile(profile_id)
