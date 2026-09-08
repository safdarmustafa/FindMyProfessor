from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.cv.extraction.schema import ExtractedStudentProfile
from app.matching.models import MatchEvidence
from app.matching.scoring import MATCH_VERSION, score_professor
from app.schemas.matching import (
    MatchDepartment,
    MatchLab,
    MatchProfessor,
    MatchingResponse,
    MatchUniversity,
    ProfessorMatch,
    ResearchMatchScore,
    UniversityOpportunityContext,
)
from app.services import cv as cv_service
from app.services.query import execute
from app.supabase_client import supabase

PAGE_SIZE = 1000
GENERIC_CLOSED = "closed"


def match_professors(
    *,
    profile_id: str,
    mode: str = "research",
    limit: int = 25,
    university_id: str | None = None,
    min_score: int = 0,
    email_only: bool = False,
) -> MatchingResponse:
    if mode not in {"research", "opportunity", "both"}:
        raise HTTPException(status_code=400, detail="mode must be research, opportunity, or both.")
    student = _confirmed_student(profile_id)
    catalog_names, area_name_by_id = _load_catalog()
    professors = _load_professors(university_id=university_id, email_only=email_only)
    areas_by_professor = _load_professor_areas(area_name_by_id)
    opportunities_by_university = _load_opportunities_by_university()

    if mode == "opportunity":
        useful_universities = {
            uni_id
            for uni_id, opps in opportunities_by_university.items()
            if any(not _is_closed(item) for item in opps)
        }
        professors = [
            row for row in professors if _university_id(row) in useful_universities
        ]

    matches: list[ProfessorMatch] = []
    seen_professors: set[str] = set()
    for row in professors:
        professor_id = str(row["id"])
        if professor_id in seen_professors:
            continue
        seen_professors.add(professor_id)
        result = score_professor(
            student=student,
            professor_areas=areas_by_professor.get(professor_id, []),
            catalog_names=catalog_names,
            research_summary=row.get("research_summary"),
        )
        if result.score < min_score:
            continue
        university = _university(row)
        opportunities = opportunities_by_university.get(str(university.id) if university and university.id else "", [])
        evidence = list(result.evidence)
        for opportunity in opportunities:
            if opportunity.not_professor_specific:
                evidence.append(
                    MatchEvidence(
                        type="university_opportunity",
                        opportunity_id=str(opportunity.id),
                        title=opportunity.title,
                        opportunity_type=opportunity.type,
                        status=opportunity.status,
                        university=university.name if university else None,
                        not_professor_specific=True,
                    )
                )
        matches.append(
            ProfessorMatch(
                professor=_professor_card(row),
                research_match=ResearchMatchScore(
                    score=result.score,
                    priority=result.priority,
                    why=result.why,
                ),
                research_overlap=result.research_overlap,
                evidence=evidence,
                university_opportunities=opportunities,
                university_opportunity_fit=_university_opportunity_fit(opportunities),
            )
        )

    matches.sort(key=lambda item: (-item.research_match.score, item.professor.name.lower(), str(item.professor.id)))
    matches = matches[:limit]
    return MatchingResponse(
        profile_id=profile_id,
        mode=mode,  # type: ignore[arg-type]
        match_version=MATCH_VERSION,
        count=len(matches),
        matches=matches,
    )


def _confirmed_student(profile_id: str) -> ExtractedStudentProfile:
    current = cv_service.get_active_profile(profile_id)
    if not current.get("cv_id"):
        raise HTTPException(
            status_code=400,
            detail="Upload and confirm a CV before requesting professor matches.",
        )
    if current.get("parsing_status") == "failed":
        raise HTTPException(
            status_code=400,
            detail=current.get("parsing_error")
            or "The current CV could not be parsed. Upload another version and confirm it.",
        )
    if not current.get("confirmed"):
        raise HTTPException(
            status_code=400,
            detail="Confirm the extracted CV profile before requesting professor matches.",
        )
    return ExtractedStudentProfile.model_validate(current.get("extracted_profile") or {})


def _load_catalog() -> tuple[list[str], dict[str, str]]:
    rows = _fetch_all("research_areas", "id,name")
    names = [row["name"] for row in rows if row.get("name")]
    by_id = {str(row["id"]): row["name"] for row in rows if row.get("id") and row.get("name")}
    return names, by_id


def _load_professors(*, university_id: str | None, email_only: bool) -> list[dict[str, Any]]:
    department_rel = "departments!inner" if university_id else "departments"
    query = (
        supabase.table("professors")
        .select(
            "id, lab_id, department_id, name, title, email, research_summary, is_active, "
            "labs(id, name), "
            f"{department_rel}(id, university_id, name, "
            "universities(id, name, country, city))"
        )
        .eq("is_active", True)
        .order("name")
    )
    if university_id:
        query = query.eq("departments.university_id", university_id)
    rows = _execute_paged(query)
    if email_only:
        rows = [row for row in rows if row.get("email")]
    return rows


def _load_professor_areas(area_name_by_id: dict[str, str]) -> dict[str, list[str]]:
    rows = _fetch_all("professor_research_areas", "professor_id,research_area_id")
    grouped: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for row in rows:
        professor_id = str(row.get("professor_id") or "")
        area_id = str(row.get("research_area_id") or "")
        name = area_name_by_id.get(area_id)
        if not professor_id or not name:
            continue
        used = seen.setdefault(professor_id, set())
        if name in used:
            continue
        used.add(name)
        grouped.setdefault(professor_id, []).append(name)
    return grouped


def _load_opportunities_by_university() -> dict[str, list[UniversityOpportunityContext]]:
    rows = _fetch_all(
        "opportunities",
        "id,professor_id,lab_id,university_id,title,opportunity_type,status,official_url",
    )
    grouped: dict[str, list[UniversityOpportunityContext]] = {}
    for row in rows:
        university_id = str(row.get("university_id") or "")
        if not university_id:
            continue
        professor_id = row.get("professor_id")
        grouped.setdefault(university_id, []).append(
            UniversityOpportunityContext(
                id=row["id"],
                title=row.get("title"),
                type=row.get("opportunity_type"),
                status=row.get("status"),
                not_professor_specific=professor_id is None,
                official_url=row.get("official_url"),
            )
        )
    return grouped


def _university_opportunity_fit(opportunities: list[UniversityOpportunityContext]) -> int:
    if not opportunities:
        return 0
    statuses = { (item.status or "unknown").casefold() for item in opportunities }
    if statuses == {"closed"} or all(_is_closed(item) for item in opportunities):
        return 0
    if "open" in statuses:
        return 100
    if "upcoming" in statuses:
        return 60
    return 40


def _is_closed(item: UniversityOpportunityContext) -> bool:
    return (item.status or "").casefold() == GENERIC_CLOSED


def _professor_card(row: dict[str, Any]) -> MatchProfessor:
    department = row.get("departments") if isinstance(row.get("departments"), dict) else None
    university_row = None
    department_view = None
    if department:
        university_row = department.get("universities")
        department_view = {key: value for key, value in department.items() if key != "universities"}
    lab = row.get("labs") if isinstance(row.get("labs"), dict) else None
    return MatchProfessor(
        id=row["id"],
        name=row["name"],
        title=row.get("title"),
        email=row.get("email"),
        email_available=bool(row.get("email")),
        university=MatchUniversity.model_validate(university_row) if university_row else None,
        department=MatchDepartment.model_validate(department_view) if department_view else None,
        lab=MatchLab.model_validate(lab) if lab else None,
    )


def _university(row: dict[str, Any]) -> MatchUniversity | None:
    department = row.get("departments")
    if not isinstance(department, dict):
        return None
    university_row = department.get("universities")
    if not isinstance(university_row, dict):
        return None
    return MatchUniversity.model_validate(university_row)


def _university_id(row: dict[str, Any]) -> str | None:
    university = _university(row)
    return str(university.id) if university and university.id else None


def _fetch_all(table: str, columns: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        response = execute(
            supabase.table(table).select(columns).range(start, start + PAGE_SIZE - 1)
        )
        chunk = response.data or []
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return rows


def _execute_paged(query) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        response = execute(query.range(start, start + PAGE_SIZE - 1))
        chunk = response.data or []
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return rows
