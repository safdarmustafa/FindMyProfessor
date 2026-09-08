from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.lab import Lab
from app.schemas.professor import ProfessorListResponse
from app.services.labs import get_lab
from app.services.professors import list_professors_for_lab

router = APIRouter(tags=["labs"])


@router.get("/labs/{lab_id}", response_model=Lab)
def get_lab_by_id(lab_id: UUID):
    lab = get_lab(str(lab_id))
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found.")
    return lab


@router.get("/labs/{lab_id}/professors", response_model=ProfessorListResponse)
def get_lab_professors(lab_id: UUID):
    lab = get_lab(str(lab_id))
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found.")

    professors = list_professors_for_lab(str(lab_id))
    return {
        "professors": professors,
        "count": len(professors),
    }
