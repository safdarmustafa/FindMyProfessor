from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.professor import ProfessorDetail, ProfessorSearchResponse
from app.schemas.research_area import ResearchAreaListResponse
from app.services.professors import (
    get_professor,
    list_professor_research_areas,
    professor_exists,
    search_professors,
)

router = APIRouter(tags=["professors"])


@router.get("/professors/search", response_model=ProfessorSearchResponse)
def search_professors_endpoint(
    q: str | None = Query(default=None, description="Search professor name, title, or email."),
    research_area: str | None = Query(default=None),
    country: str | None = Query(default=None),
    university_id: UUID | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    recruiting: bool | None = Query(default=None),
    internship: bool | None = Query(default=None),
    ra: bool | None = Query(default=None),
    masters: bool | None = Query(default=None),
    phd: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
):
    professors = search_professors(
        q=q,
        research_area=research_area,
        country=country,
        university_id=str(university_id) if university_id else None,
        department_id=str(department_id) if department_id else None,
        recruiting=recruiting,
        internship=internship,
        ra=ra,
        masters=masters,
        phd=phd,
        limit=limit,
    )
    return {
        "professors": professors,
        "count": len(professors),
    }


@router.get("/professors/{professor_id}", response_model=ProfessorDetail)
def get_professor_by_id(professor_id: UUID):
    professor = get_professor(str(professor_id))
    if not professor:
        raise HTTPException(status_code=404, detail="Professor not found.")
    return professor


@router.get(
    "/professors/{professor_id}/research-areas",
    response_model=ResearchAreaListResponse,
)
def get_professor_research_areas(professor_id: UUID):
    if not professor_exists(str(professor_id)):
        raise HTTPException(status_code=404, detail="Professor not found.")

    research_areas = list_professor_research_areas(str(professor_id))
    return {
        "research_areas": research_areas,
        "count": len(research_areas),
    }
