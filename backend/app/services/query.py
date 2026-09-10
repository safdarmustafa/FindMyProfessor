import logging

from postgrest.exceptions import APIError
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def execute(query):
    """Run a Supabase/PostgREST query and map failures to HTTP errors.

    The client-facing message is intentionally generic (never leaks table/
    column names or query shape). The real Postgrest error — code, message,
    hint — is logged server-side so a schema mismatch (e.g. a pending
    migration) is diagnosable from application logs instead of requiring
    manual DB introspection.
    """
    try:
        return query.execute()
    except APIError as exc:
        logger.error(
            "Supabase query failed: code=%s message=%s hint=%s",
            exc.code, exc.message, exc.hint,
        )
        if exc.code == "22P02":
            raise HTTPException(status_code=400, detail="Invalid ID format.") from exc
        raise HTTPException(status_code=503, detail="Database query failed.") from exc
    except Exception as exc:
        logger.exception("Unexpected error running Supabase query.")
        raise HTTPException(status_code=503, detail="Database query failed.") from exc


def first_or_none(data: list | None) -> dict | None:
    if not data:
        return None
    return data[0]


# Postgrest reports a missing column differently depending on how the
# column was referenced:
#   42703    — the raw Postgres "undefined column" error, raised when the
#              column appears in a filter/select clause (e.g. .eq(), .select()).
#   PGRST204 — Postgrest's own "column not in schema cache" error, raised
#              for an insert/update whose JSON payload names a column that
#              isn't in its cached schema — never reaches Postgres itself.
# Both mean the same thing from the caller's perspective: this column does
# not exist (yet) as far as Postgrest can tell.
_MISSING_COLUMN_CODES = {"42703", "PGRST204"}


def is_missing_column_error(exc: HTTPException, column: str) -> bool:
    """
    True if `exc` was raised by execute() for a Postgrest "column does not
    exist" error (see _MISSING_COLUMN_CODES) naming `column` specifically.

    Lets a caller that knows about one specific, optional, not-yet-migrated
    column degrade gracefully (e.g. treat a lookup as "not found", or an
    insert as "retry without this field", instead of failing the whole
    request) without execute() having to special-case any particular
    column, and without weakening its behavior for every other caller —
    any other Postgrest error still raises as before.
    """
    cause = exc.__cause__
    return (
        isinstance(cause, APIError)
        and cause.code in _MISSING_COLUMN_CODES
        and column in (cause.message or "")
    )
