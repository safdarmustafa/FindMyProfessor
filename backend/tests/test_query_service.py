"""
Regression tests for app/services/query.py's execute() wrapper.

Added while diagnosing a live "Database query failed" 503 on the CV
selection flow: the underlying Postgrest error (column does not exist —
a pending migration) was being swallowed into a generic message with no
server-side trace, which made the real cause invisible without manually
re-querying the database by hand. execute() now logs the real error
(code/message/hint) while keeping the client-facing message generic.
"""
import logging

import pytest
from fastapi import HTTPException
from postgrest.exceptions import APIError

from app.services.query import execute, is_missing_column_error


class _FailingQuery:
    def __init__(self, error: Exception):
        self._error = error

    def execute(self):
        raise self._error


def _api_error(code: str, message: str, hint: str | None = None) -> APIError:
    return APIError({"code": code, "message": message, "hint": hint, "details": None})


def test_missing_column_error_maps_to_generic_503():
    """A schema mismatch (e.g. an unapplied migration) must not leak
    table/column names to the HTTP client."""
    err = _api_error("42703", "column profiles.linked_user_id does not exist")
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert exc.value.status_code == 503
    assert exc.value.detail == "Database query failed."
    assert "linked_user_id" not in exc.value.detail
    assert "profiles" not in exc.value.detail


def test_missing_column_error_is_logged_server_side(caplog):
    """The real Postgrest error must be visible in server logs even though
    it is not returned to the client, so a schema mismatch like a pending
    migration is diagnosable from logs alone."""
    err = _api_error("42703", "column profiles.linked_user_id does not exist")
    with caplog.at_level(logging.ERROR, logger="app.services.query"):
        with pytest.raises(HTTPException):
            execute(_FailingQuery(err))
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "42703" in logged
    assert "linked_user_id" in logged


def test_invalid_uuid_error_maps_to_400():
    err = _api_error("22P02", "invalid input syntax for type uuid")
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid ID format."


def test_unexpected_exception_maps_to_generic_503_and_is_logged(caplog):
    with caplog.at_level(logging.ERROR, logger="app.services.query"):
        with pytest.raises(HTTPException) as exc:
            execute(_FailingQuery(RuntimeError("connection reset")))
    assert exc.value.status_code == 503
    assert exc.value.detail == "Database query failed."
    assert any("connection reset" in r.getMessage() or r.exc_info for r in caplog.records)


def test_successful_query_passes_through_unchanged():
    class _OkQuery:
        def execute(self):
            return {"data": [{"id": 1}]}

    assert execute(_OkQuery()) == {"data": [{"id": 1}]}


# ---------------------------------------------------------------------------
# is_missing_column_error — used by app/auth.py and app/services/cv.py to
# degrade gracefully for the one specific pending migration
# (profiles.linked_user_id) instead of failing the whole request. Real
# Postgrest reports a missing column differently depending on how it was
# referenced: 42703 for a select/filter, PGRST204 for an insert/update —
# both verified live against the actual database during diagnosis.
# ---------------------------------------------------------------------------

def test_is_missing_column_error_true_for_42703_select_or_filter():
    err = _api_error("42703", "column profiles.linked_user_id does not exist")
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert is_missing_column_error(exc.value, "linked_user_id") is True


def test_is_missing_column_error_true_for_pgrst204_insert_or_update():
    err = _api_error(
        "PGRST204",
        "Could not find the 'linked_user_id' column of 'profiles' in the schema cache",
    )
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert is_missing_column_error(exc.value, "linked_user_id") is True


def test_is_missing_column_error_false_for_a_different_column():
    err = _api_error("42703", "column profiles.linked_user_id does not exist")
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert is_missing_column_error(exc.value, "some_other_column") is False


def test_is_missing_column_error_false_for_unrelated_error():
    err = _api_error("22P02", "invalid input syntax for type uuid")
    with pytest.raises(HTTPException) as exc:
        execute(_FailingQuery(err))
    assert is_missing_column_error(exc.value, "linked_user_id") is False


def test_is_missing_column_error_false_when_no_postgrest_cause():
    plain = HTTPException(status_code=404, detail="Not found.")
    assert is_missing_column_error(plain, "linked_user_id") is False
