from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.cv.extraction.schema import ExtractedStudentProfile
from app.matching.scoring import MATCH_VERSION, score_professor
from app.opportunities.evidence import university_opportunity_evidence
from app.opportunities.models import OpportunityRecord, UniversityFitResult
from app.opportunities.scoring import is_clearly_undergraduate, score_university_opportunities
from app.schemas.matching import (
    MatchDepartment,
    MatchLab,
    MatchProfessor,
    MatchingResponse,
    MatchUniversity,
    ProfessorMatch,
    ResearchMatchScore,
    UniversityOpportunityContext,
    UniversityOpportunityFit,
)
from app.services import cv as cv_service
from app.services.query import execute
from app.supabase_client import supabase

PAGE_SIZE = 1000


def match_professors(
    *,
    profile_id: str,
    mode: str = "research",
    limit: int = 25,
    university_id: str | None = None,
    min_score: int = 0,
    email_only: bool = False,
    opportunity_type: str | None = None,
    opportunity_status: str | None = None,
) -> MatchingResponse:
    if mode not in {"research", "opportunity", "both"}:
        raise HTTPException(status_code=400, detail="mode must be research, opportunity, or both.")
    student = _confirmed_student(profile_id)
    catalog_names, area_name_by_id = _load_catalog()
    professors = _load_professors(university_id=university_id, email_only=email_only)
    areas_by_professor = _load_professor_areas(area_name_by_id)
    opportunities = _filter_opportunities(
        _load_opportunities(),
        opportunity_type=opportunity_type,
        opportunity_status=opportunity_status,
    )
    student_is_undergrad = is_clearly_undergraduate(student)

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
        related = opportunities_for_professor(opportunities, row)
        fit = score_university_opportunities(
            related,
            student_is_undergraduate=student_is_undergrad,
        )
        if mode == "opportunity" and (fit.best_opportunity is None or fit.score <= 0):
            continue
        evidence = list(result.evidence)
        for opportunity in related:
            evidence.append(
                university_opportunity_evidence(
                    opportunity,
                    university_name=university.name if university else None,
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
                university_opportunities=[_opportunity_context(item) for item in related],
                university_opportunity_fit=_fit_schema(fit),
            )
        )

    matches.sort(key=lambda item: _sort_key(item, mode))
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


def _load_opportunities() -> list[OpportunityRecord]:
    rows = _fetch_all(
        "opportunities",
        "id,professor_id,lab_id,university_id,title,opportunity_type,description,"
        "eligibility,international_eligible,undergraduate_eligible,funding_type,"
        "stipend_amount,tuition_coverage,accommodation_coverage,travel_coverage,"
        "application_deadline,start_date,official_url,status",
    )
    records: list[OpportunityRecord] = []
    for row in rows:
        records.append(
            OpportunityRecord(
                id=str(row["id"]),
                university_id=str(row["university_id"]) if row.get("university_id") else None,
                professor_id=str(row["professor_id"]) if row.get("professor_id") else None,
                lab_id=str(row["lab_id"]) if row.get("lab_id") else None,
                title=row.get("title"),
                opportunity_type=row.get("opportunity_type"),
                description=row.get("description"),
                eligibility=row.get("eligibility"),
                international_eligible=row.get("international_eligible"),
                undergraduate_eligible=row.get("undergraduate_eligible"),
                funding_type=row.get("funding_type"),
                stipend_amount=row.get("stipend_amount"),
                tuition_coverage=row.get("tuition_coverage"),
                accommodation_coverage=row.get("accommodation_coverage"),
                travel_coverage=row.get("travel_coverage"),
                application_deadline=_date_text(row.get("application_deadline")),
                start_date=_date_text(row.get("start_date")),
                official_url=row.get("official_url"),
                status=row.get("status"),
            )
        )
    return records


def _filter_opportunities(
    records: list[OpportunityRecord],
    *,
    opportunity_type: str | None,
    opportunity_status: str | None,
) -> list[OpportunityRecord]:
    filtered = records
    if opportunity_type:
        wanted = opportunity_type.strip().casefold()
        filtered = [
            item for item in filtered if (item.opportunity_type or "").strip().casefold() == wanted
        ]
    if opportunity_status:
        wanted_status = opportunity_status.strip().casefold()
        filtered = [item for item in filtered if item.status_key == wanted_status]
    return filtered


def opportunities_for_professor(
    records: list[OpportunityRecord],
    professor_row: dict[str, Any],
) -> list[OpportunityRecord]:
    professor_id = str(professor_row.get("id") or "")
    lab_id = str(professor_row.get("lab_id") or "") if professor_row.get("lab_id") else None
    university_id = _university_id(professor_row)
    matched: list[OpportunityRecord] = []
    seen: set[str] = set()
    for item in records:
        belongs = False
        if item.professor_id:
            belongs = item.professor_id == professor_id
        elif item.lab_id:
            belongs = bool(lab_id) and item.lab_id == lab_id
        elif item.university_id:
            belongs = bool(university_id) and item.university_id == university_id
        if not belongs or item.id in seen:
            continue
        seen.add(item.id)
        matched.append(item)
    return matched


def _opportunity_context(item: OpportunityRecord) -> UniversityOpportunityContext:
    return UniversityOpportunityContext(
        id=item.id,
        title=item.title,
        type=item.opportunity_type,
        status=item.status,
        not_professor_specific=item.not_professor_specific,
        official_url=item.official_url,
        description=item.description,
        eligibility=item.eligibility,
        international_eligible=item.international_eligible,
        undergraduate_eligible=item.undergraduate_eligible,
        funding_type=item.funding_type,
        stipend_amount=item.stipend_amount,
        tuition_coverage=item.tuition_coverage,
        accommodation_coverage=item.accommodation_coverage,
        travel_coverage=item.travel_coverage,
        application_deadline=item.application_deadline,
        start_date=item.start_date,
        professor_id=item.professor_id,
        lab_id=item.lab_id,
    )


def _fit_schema(fit: UniversityFitResult) -> UniversityOpportunityFit:
    best = fit.best_opportunity
    return UniversityOpportunityFit(
        score=fit.score,
        best_opportunity_id=best.id if best else None,
        best_opportunity_title=best.title if best else None,
        status=best.status if best else None,
        non_closed_opportunity_count=fit.non_closed_opportunity_count,
        why=list(fit.why),
    )


def _sort_key(item: ProfessorMatch, mode: str) -> tuple:
    fit_score = item.university_opportunity_fit.score if item.university_opportunity_fit else 0
    name = item.professor.name.lower()
    professor_id = str(item.professor.id)
    if mode == "opportunity":
        return (-fit_score, -item.research_match.score, name, professor_id)
    if mode == "both":
        return (-item.research_match.score, -fit_score, name, professor_id)
    return (-item.research_match.score, name, professor_id)


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


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
