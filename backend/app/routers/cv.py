from __future__ import annotations

from fastapi import APIRouter, File, Header, UploadFile

from app.services import cv as cv_service

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/upload")
def upload_cv(
    file: UploadFile = File(...),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    content = file.file.read()
    return cv_service.upload_and_parse(
        profile_id=x_profile_id,
        filename=file.filename or "cv",
        content=content,
        declared_mime=file.content_type,
    )


@router.get("/{cv_id}")
def get_cv(
    cv_id: str,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    return cv_service.public_cv(cv_service.get_cv(cv_id, x_profile_id))


@router.post("/{cv_id}/parse")
def parse_cv(
    cv_id: str,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
):
    return cv_service.public_cv(cv_service.parse_cv(cv_id, x_profile_id))
