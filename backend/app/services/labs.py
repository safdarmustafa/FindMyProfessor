from app.services.query import execute, first_or_none
from app.supabase_client import supabase

LAB_COLUMNS = "id, department_id, name, description, website_url, created_at, updated_at"


def list_labs_for_department(department_id: str) -> list[dict]:
    response = execute(
        supabase.table("labs")
        .select(LAB_COLUMNS)
        .eq("department_id", department_id)
        .order("name")
    )
    return response.data or []


def get_lab(lab_id: str) -> dict | None:
    response = execute(
        supabase.table("labs")
        .select(LAB_COLUMNS)
        .eq("id", lab_id)
        .limit(1)
    )
    return first_or_none(response.data)
