from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app import auth
from app.schemas.matching import MatchingResponse
from app.services.matching import match_professors

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/professors", response_model=MatchingResponse)
def get_matching_professors(
    profile_id: str = Depends(auth.require_profile_id),
    mode: str = Query(default="research"),
    limit: int = Query(default=25, ge=1, le=100),
    university_id: UUID | None = Query(default=None),
    min_score: int = Query(default=0, ge=0, le=100),
    email_only: bool = Query(default=False),
    opportunity_type: str | None = Query(default=None),
    opportunity_status: str | None = Query(default=None),
):
    return match_professors(
        profile_id=profile_id,
        mode=mode,
        limit=limit,
        university_id=str(university_id) if university_id else None,
        min_score=min_score,
        email_only=email_only,
        opportunity_type=opportunity_type,
        opportunity_status=opportunity_status,
    )
