from __future__ import annotations

from fastapi import APIRouter, Depends

from app import auth
from app.schemas.cv import StudentProfileUpdate
from app.services import cv as cv_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(profile_id: str = Depends(auth.require_profile_id)):
    return cv_service.get_active_profile(profile_id)


@router.put("")
def put_profile(
    body: StudentProfileUpdate,
    profile_id: str = Depends(auth.require_profile_id),
):
    return cv_service.update_extracted_profile(profile_id, body.extracted_profile)


@router.post("/confirm")
def confirm_profile(profile_id: str = Depends(auth.require_profile_id)):
    return cv_service.confirm_profile(profile_id)
