from app.services.query import execute, first_or_none
from app.supabase_client import supabase

DEPARTMENT_COLUMNS = (
    "id, university_id, name, website_url, description, created_at, updated_at"
)


def list_departments_for_university(university_id: str) -> list[dict]:
    response = execute(
        supabase.table("departments")
        .select(DEPARTMENT_COLUMNS)
        .eq("university_id", university_id)
        .order("name")
    )
    return response.data or []


def get_department(department_id: str) -> dict | None:
    response = execute(
        supabase.table("departments")
        .select(DEPARTMENT_COLUMNS)
        .eq("id", department_id)
        .limit(1)
    )
    return first_or_none(response.data)
