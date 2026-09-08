from postgrest.exceptions import APIError
from fastapi import HTTPException


def execute(query):
    """Run a Supabase/PostgREST query and map failures to HTTP errors."""
    try:
        return query.execute()
    except APIError as exc:
        if exc.code == "22P02":
            raise HTTPException(status_code=400, detail="Invalid ID format.") from exc
        raise HTTPException(status_code=503, detail="Database query failed.") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database query failed.") from exc


def first_or_none(data: list | None) -> dict | None:
    if not data:
        return None
    return data[0]
