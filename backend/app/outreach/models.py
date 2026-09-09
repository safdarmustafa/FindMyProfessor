from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Phase 6 extends the status with sending/sent/failed
DraftStatus = Literal["generated", "edited", "ready", "sending", "sent", "failed"]


@dataclass
class EvidenceLine:
    """One human-readable evidence line used to generate the email."""
    type: str
    description: str


@dataclass
class DraftRecord:
    """
    Draft record — persisted to outreach_drafts table in Phase 6.

    Phase 5 compatibility: when db_store is in test mode (after clear()),
    records are kept in an in-memory dict with no DB interaction.
    """
    draft_id: str
    profile_id: str
    professor_id: str
    email_type: str
    subject: str
    body: str
    matched_research_areas: list[str] = field(default_factory=list)
    evidence_used: list[EvidenceLine] = field(default_factory=list)
    generation_provider: str = "deterministic"
    generation_status: DraftStatus = "generated"

    # Phase 5 display fields (not persisted to separate columns)
    professor_name: str | None = None
    professor_email: str | None = None
    professor_email_available: bool = False
    university_name: str | None = None

    # Phase 6 fields
    cv_version_id: str | None = None
    selected_opportunity_id: str | None = None
    sent_at: str | None = None
    gmail_message_id: str | None = None
    gmail_thread_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
