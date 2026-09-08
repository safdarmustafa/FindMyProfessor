from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas.matching import MatchingResponse
from app.services.matching import match_professors

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/professors", response_model=MatchingResponse)
def get_matching_professors(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
    mode: str = Query(default="research"),
    limit: int = Query(default=25, ge=1, le=100),
    university_id: UUID | None = Query(default=None),
    min_score: int = Query(default=0, ge=0, le=100),
    email_only: bool = Query(default=False),
):
    if not x_profile_id:
        raise HTTPException(
            status_code=400,
            detail="X-Profile-Id header is required. Confirm a CV profile first.",
        )
    return match_professors(
        profile_id=x_profile_id,
        mode=mode,
        limit=limit,
        university_id=str(university_id) if university_id else None,
        min_score=min_score,
        email_only=email_only,
    )
