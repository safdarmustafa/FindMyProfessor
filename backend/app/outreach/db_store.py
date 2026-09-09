from __future__ import annotations

"""
Supabase-backed draft persistence for Phase 6.

This module replaces the Phase 5 in-memory store with a proper database backend.

TEST MODE:
For backward compatibility with existing tests, this module supports a
test-mode dict override activated by calling clear(). When _test_store is
not None, all operations use the in-memory dict instead of Supabase.
This allows existing test_outreach.py tests (which call clear() before
test logic) to continue working without a real database connection.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.query import execute
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

TABLE = "outreach_drafts"

# When set to a dict, all operations use this in-memory override (test mode).
_test_store: dict[str, Any] | None = None


def clear() -> None:
    """
    Activate test mode and clear the in-memory override.
    Call this at the start of tests to prevent Supabase calls.
    """
    global _test_store
    _test_store = {}


def disable_test_mode() -> None:
    """Deactivate test mode and re-enable Supabase operations."""
    global _test_store
    _test_store = None


def put(draft_id: str, record: Any) -> None:
    if _test_store is not None:
        _test_store[draft_id] = record
        return
    _upsert(record)


def get(draft_id: str) -> Any | None:
    if _test_store is not None:
        return _test_store.get(draft_id)
    return _fetch_by_id(draft_id)


def all_for_profile(profile_id: str) -> list[Any]:
    if _test_store is not None:
        return [v for v in _test_store.values() if _profile_id_of(v) == profile_id]
    return _fetch_for_profile(profile_id)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _upsert(record: Any) -> None:
    """Insert or update a draft record in the database."""
    from app.outreach.models import DraftRecord
    row = _record_to_row(record)
    existing = execute(
        supabase.table(TABLE).select("id").eq("id", record.draft_id).limit(1)
    ).data or []
    if existing:
        execute(
            supabase.table(TABLE)
            .update(row)
            .eq("id", record.draft_id)
        )
    else:
        execute(supabase.table(TABLE).insert(row))


def _fetch_by_id(draft_id: str) -> Any | None:
    rows = execute(
        supabase.table(TABLE).select("*").eq("id", draft_id).limit(1)
    ).data or []
    if not rows:
        return None
    return _row_to_record(rows[0])


def _fetch_for_profile(profile_id: str) -> list[Any]:
    rows = execute(
        supabase.table(TABLE)
        .select("*")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
    ).data or []
    return [_row_to_record(r) for r in rows]


def _record_to_row(record: Any) -> dict[str, Any]:
    """Serialize a DraftRecord to a database row dict."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": record.draft_id,
        "profile_id": record.profile_id,
        "professor_id": record.professor_id,
        "email_type": record.email_type,
        "subject": record.subject,
        "body": record.body,
        "selected_opportunity_id": getattr(record, "selected_opportunity_id", None),
        "cv_version_id": getattr(record, "cv_version_id", None),
        "matched_research_areas": json.dumps(record.matched_research_areas),
        "evidence_used": json.dumps([{"type": e.type, "description": e.description} for e in record.evidence_used]),
        "generation_provider": record.generation_provider,
        "status": record.generation_status,
        "sent_at": getattr(record, "sent_at", None),
        "gmail_message_id": getattr(record, "gmail_message_id", None),
        "gmail_thread_id": getattr(record, "gmail_thread_id", None),
        "error_code": getattr(record, "error_code", None),
        "error_message": getattr(record, "error_message", None),
        "updated_at": now,
    }


def _row_to_record(row: dict[str, Any]) -> Any:
    """Deserialize a database row to a DraftRecord."""
    from app.outreach.models import DraftRecord, EvidenceLine

    matched = row.get("matched_research_areas") or "[]"
    if isinstance(matched, str):
        try:
            matched = json.loads(matched)
        except json.JSONDecodeError:
            matched = []

    evidence_raw = row.get("evidence_used") or "[]"
    if isinstance(evidence_raw, str):
        try:
            evidence_raw = json.loads(evidence_raw)
        except json.JSONDecodeError:
            evidence_raw = []
    evidence = [EvidenceLine(type=e.get("type", "evidence"), description=e.get("description", "")) for e in evidence_raw]

    record = DraftRecord(
        draft_id=str(row["id"]),
        profile_id=str(row["profile_id"]),
        professor_id=str(row["professor_id"]),
        email_type=row.get("email_type", "research"),
        subject=row.get("subject", ""),
        body=row.get("body", ""),
        matched_research_areas=matched if isinstance(matched, list) else [],
        evidence_used=evidence,
        generation_provider=row.get("generation_provider", "deterministic"),
        generation_status=row.get("status", "generated"),
    )
    record.cv_version_id = row.get("cv_version_id")
    record.selected_opportunity_id = row.get("selected_opportunity_id")
    record.sent_at = row.get("sent_at")
    record.gmail_message_id = row.get("gmail_message_id")
    record.gmail_thread_id = row.get("gmail_thread_id")
    record.error_code = row.get("error_code")
    record.error_message = row.get("error_message")
    return record


def _profile_id_of(record: Any) -> str:
    return str(getattr(record, "profile_id", ""))


def atomically_set_sending(draft_id: str, profile_id: str) -> bool:
    """
    Atomically transition a draft from 'ready' to 'sending'.
    Returns True if the transition succeeded (only one caller wins).
    Returns False if the draft was not in 'ready' state.
    """
    if _test_store is not None:
        record = _test_store.get(draft_id)
        if not record or record.generation_status != "ready":
            return False
        record.generation_status = "sending"
        return True

    result = execute(
        supabase.table(TABLE)
        .update({"status": "sending", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", draft_id)
        .eq("profile_id", profile_id)
        .eq("status", "ready")
    ).data or []
    return len(result) > 0
