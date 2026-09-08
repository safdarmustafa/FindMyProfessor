from app.services.query import execute, first_or_none
from app.supabase_client import supabase

PROFESSOR_COLUMNS = (
    "id, lab_id, department_id, name, email, title, linkedin_url, "
    "website_url, recruiting_status, is_active, created_at, updated_at"
)

RECRUITING_OPEN = ("open", "recruiting", "yes", "true", "active")
RECRUITING_CLOSED = ("closed", "not_recruiting", "no", "false", "inactive")
OPPORTUNITY_TYPE_FILTERS = {
    "internship": "internship",
    "ra": "ra",
    "masters": "masters",
    "phd": "phd",
}


def list_professors_for_lab(lab_id: str) -> list[dict]:
    response = execute(
        supabase.table("professors")
        .select(PROFESSOR_COLUMNS)
        .eq("lab_id", lab_id)
        .eq("is_active", True)
        .order("name")
    )
    return response.data or []


def professor_exists(professor_id: str) -> bool:
    response = execute(
        supabase.table("professors")
        .select("id")
        .eq("id", professor_id)
        .limit(1)
    )
    return bool(response.data)


def get_professor(professor_id: str) -> dict | None:
    response = execute(
        supabase.table("professors")
        .select(_detail_select())
        .eq("id", professor_id)
        .limit(1)
    )
    row = first_or_none(response.data)
    if not row:
        return None
    return _flatten_professor(row)


def list_professor_research_areas(professor_id: str) -> list[dict]:
    response = execute(
        supabase.table("professor_research_areas")
        .select("research_areas(id, name, description, created_at)")
        .eq("professor_id", professor_id)
    )
    areas = []
    for item in response.data or []:
        area = item.get("research_areas")
        if area:
            areas.append(area)
    areas.sort(key=lambda item: (item.get("name") or "").lower())
    return areas


def search_professors(
    *,
    q: str | None = None,
    research_area: str | None = None,
    country: str | None = None,
    university_id: str | None = None,
    department_id: str | None = None,
    recruiting: bool | None = None,
    internship: bool | None = None,
    ra: bool | None = None,
    masters: bool | None = None,
    phd: bool | None = None,
    limit: int = 50,
) -> list[dict]:
    opportunity_types = _requested_opportunity_types(
        internship=internship,
        ra=ra,
        masters=masters,
        phd=phd,
    )
    professor_ids = _professor_ids_for_opportunity_types(opportunity_types)
    if opportunity_types and professor_ids is not None and not professor_ids:
        return []

    query = (
        supabase.table("professors")
        .select(_search_select(country=country, university_id=university_id, research_area=research_area))
        .eq("is_active", True)
        .order("name")
        .limit(limit)
    )

    search_term = _sanitize_search_term(q)
    if search_term:
        query = query.or_(
            f"name.ilike.%{search_term}%,title.ilike.%{search_term}%,email.ilike.%{search_term}%"
        )

    if department_id:
        query = query.eq("department_id", department_id)

    if university_id:
        query = query.eq("departments.university_id", university_id)

    country_term = _sanitize_search_term(country)
    if country_term:
        query = query.ilike("departments.universities.country", f"%{country_term}%")

    area_term = _sanitize_search_term(research_area)
    if area_term:
        query = query.ilike("professor_research_areas.research_areas.name", f"%{area_term}%")

    if recruiting is True:
        query = query.in_("recruiting_status", list(RECRUITING_OPEN))
    elif recruiting is False:
        query = query.in_("recruiting_status", list(RECRUITING_CLOSED))

    if professor_ids is not None:
        query = query.in_("id", professor_ids)

    response = execute(query)
    return [_flatten_professor(row) for row in (response.data or [])]


def _detail_select() -> str:
    return (
        f"{PROFESSOR_COLUMNS}, "
        "labs(id, department_id, name, description, website_url, created_at, updated_at), "
        "departments(id, university_id, name, website_url, description, created_at, updated_at, "
        "universities(id, name, country, city, website_url, description, is_active, created_at, updated_at)), "
        "professor_research_areas(research_areas(id, name, description, created_at))"
    )


def _search_select(*, country: str | None, university_id: str | None, research_area: str | None) -> str:
    department_rel = "departments!inner" if university_id or country else "departments"
    university_rel = "universities!inner" if country else "universities"
    research_rel = (
        "professor_research_areas!inner(research_areas!inner(id, name, description, created_at))"
        if research_area
        else "professor_research_areas(research_areas(id, name, description, created_at))"
    )
    return (
        f"{PROFESSOR_COLUMNS}, "
        "labs(id, department_id, name, description, website_url, created_at, updated_at), "
        f"{department_rel}(id, university_id, name, website_url, description, created_at, updated_at, "
        f"{university_rel}(id, name, country, city, website_url, description, is_active, created_at, updated_at)), "
        f"{research_rel}"
    )


def _requested_opportunity_types(
    *,
    internship: bool | None,
    ra: bool | None,
    masters: bool | None,
    phd: bool | None,
) -> list[str]:
    flags = {
        "internship": internship,
        "ra": ra,
        "masters": masters,
        "phd": phd,
    }
    return [OPPORTUNITY_TYPE_FILTERS[key] for key, enabled in flags.items() if enabled]


def _professor_ids_for_opportunity_types(opportunity_types: list[str]) -> list[str] | None:
    """Return matching professor IDs, or None when this filter is unused."""
    if not opportunity_types:
        return None

    matched_ids: set[str] | None = None
    for opportunity_type in opportunity_types:
        response = execute(
            supabase.table("opportunities")
            .select("professor_id")
            .eq("opportunity_type", opportunity_type)
        )
        current_ids = {
            row["professor_id"]
            for row in (response.data or [])
            if row.get("professor_id")
        }
        matched_ids = current_ids if matched_ids is None else matched_ids & current_ids
        if not matched_ids:
            return []

    return list(matched_ids or [])


def _sanitize_search_term(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    for char in (",", ".", "(", ")", ":", "*", '"', "'", "\\", "%", "_"):
        cleaned = cleaned.replace(char, " ")
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def _flatten_professor(row: dict) -> dict:
    department = row.pop("departments", None)
    university = None
    if isinstance(department, dict):
        university = department.pop("universities", None)
    lab = row.pop("labs", None)
    research_links = row.pop("professor_research_areas", None) or []
    row.pop("opportunities", None)

    research_areas = []
    for item in research_links:
        area = item.get("research_areas") if isinstance(item, dict) else None
        if area:
            research_areas.append(area)

    return {
        **row,
        "lab": lab,
        "department": department,
        "university": university,
        "research_areas": research_areas,
    }
