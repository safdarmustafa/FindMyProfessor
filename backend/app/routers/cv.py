from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app import auth
from app.services import cv as cv_service

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/upload")
def upload_cv(
    file: UploadFile = File(...),
    identity: auth.Identity = Depends(auth.resolve_identity),
):
    """
    Upload a CV. Unlike other endpoints, this one is allowed to create a
    brand new profile — so it depends on auth.resolve_identity (which may
    return profile_id=None) rather than auth.require_profile_id (which
    would reject that as "no profile yet").
    """
    content = file.file.read()
    return cv_service.upload_and_parse(
        profile_id=identity.profile_id,
        user_id=identity.user_id,
        filename=file.filename or "cv",
        content=content,
        declared_mime=file.content_type,
    )


@router.get("/{cv_id}")
def get_cv(
    cv_id: str,
    profile_id: str = Depends(auth.require_profile_id),
):
    return cv_service.public_cv(cv_service.get_cv(cv_id, profile_id))


@router.post("/{cv_id}/parse")
def parse_cv(
    cv_id: str,
    profile_id: str = Depends(auth.require_profile_id),
):
    return cv_service.public_cv(cv_service.parse_cv(cv_id, profile_id))
