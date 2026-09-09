from __future__ import annotations

"""
Outreach draft store — public interface.

Delegates to db_store (Supabase-backed in production; in-memory in tests).
Calling clear() activates test mode which uses an in-memory dict.

Phase 5 tests call clear() before exercising store operations. This design
preserves full backward compatibility while enabling Supabase persistence
in production.
"""

from app.outreach.db_store import (
    all_for_profile,
    atomically_set_sending,
    clear,
    disable_test_mode,
    get,
    put,
)

__all__ = [
    "put",
    "get",
    "all_for_profile",
    "clear",
    "disable_test_mode",
    "atomically_set_sending",
]
