from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.department import Department
from app.schemas.lab import LabListResponse
from app.services.departments import get_department
from app.services.labs import list_labs_for_department

router = APIRouter(tags=["departments"])


@router.get("/departments/{department_id}", response_model=Department)
def get_department_by_id(department_id: UUID):
    department = get_department(str(department_id))
    if not department:
        raise HTTPException(status_code=404, detail="Department not found.")
    return department


@router.get("/departments/{department_id}/labs", response_model=LabListResponse)
def get_department_labs(department_id: UUID):
    department = get_department(str(department_id))
    if not department:
        raise HTTPException(status_code=404, detail="Department not found.")

    labs = list_labs_for_department(str(department_id))
    return {
        "labs": labs,
        "count": len(labs),
    }
