from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.department import DepartmentListResponse
from app.schemas.university import University, UniversityListResponse
from app.services.departments import list_departments_for_university
from app.services.universities import get_university, list_universities

router = APIRouter(tags=["universities"])


@router.get("/universities", response_model=UniversityListResponse)
def get_universities():
    universities = list_universities()
    return {
        "universities": universities,
        "count": len(universities),
    }


@router.get("/universities/{university_id}", response_model=University)
def get_university_by_id(university_id: UUID):
    university = get_university(str(university_id))
    if not university:
        raise HTTPException(status_code=404, detail="University not found.")
    return university


@router.get(
    "/universities/{university_id}/departments",
    response_model=DepartmentListResponse,
)
def get_university_departments(university_id: UUID):
    university = get_university(str(university_id))
    if not university:
        raise HTTPException(status_code=404, detail="University not found.")

    departments = list_departments_for_university(str(university_id))
    return {
        "departments": departments,
        "count": len(departments),
    }
