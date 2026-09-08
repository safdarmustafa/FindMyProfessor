from app.services.query import execute, first_or_none
from app.supabase_client import supabase

UNIVERSITY_COLUMNS = (
    "id, name, country, city, website_url, description, is_active, created_at, updated_at"
)


def list_universities() -> list[dict]:
    response = execute(
        supabase.table("universities")
        .select(UNIVERSITY_COLUMNS)
        .eq("is_active", True)
        .order("name")
    )
    return response.data or []


def get_university(university_id: str) -> dict | None:
    response = execute(
        supabase.table("universities")
        .select(UNIVERSITY_COLUMNS)
        .eq("id", university_id)
        .limit(1)
    )
    return first_or_none(response.data)
