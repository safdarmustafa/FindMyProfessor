from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EmailType = Literal["research", "research_opportunity"]
DraftStatus = Literal["generated", "edited", "ready", "sending", "sent", "failed"]


class EvidenceUsed(BaseModel):
    type: str
    description: str


class GenerateDraftRequest(BaseModel):
    professor_id: UUID
    email_type: EmailType = "research"
    opportunity_id: str | None = None


class EmailDraft(BaseModel):
    draft_id: str
    profile_id: str
    professor_id: str
    email_type: EmailType
    subject: str
    body: str
    matched_research_areas: list[str] = Field(default_factory=list)
    evidence_used: list[EvidenceUsed] = Field(default_factory=list)
    generation_provider: str
    generation_status: DraftStatus = "generated"
    professor_name: str | None = None
    professor_email: str | None = None
    professor_email_available: bool = False
    university_name: str | None = None
    # Phase 6 additions
    cv_version_id: str | None = None
    sent_at: str | None = None
    gmail_message_id: str | None = None


class SaveDraftRequest(BaseModel):
    subject: str
    body: str
    status: DraftStatus = "ready"


class SaveDraftResponse(BaseModel):
    draft_id: str
    status: DraftStatus
    message: str


# Phase 6 — CV version safe metadata (no storage paths)
class CvVersionMeta(BaseModel):
    cv_version_id: str
    display_name: str
    file_type: str | None = None
    file_size: int | None = None
    created_at: str | None = None
    is_default: bool = False
    confirmed: bool = False


class AttachCvRequest(BaseModel):
    cv_version_id: str


class AttachCvResponse(BaseModel):
    draft_id: str
    cv_version_id: str
    display_name: str
    message: str


# Phase 6 — Send
class SendDraftRequest(BaseModel):
    """Explicit send confirmation request. Sending is never automatic."""
    confirmed: bool = Field(..., description="Must be true — user explicitly confirms the send.")


class SendDraftResponse(BaseModel):
    draft_id: str
    status: DraftStatus
    gmail_message_id: str | None = None
    sent_at: str | None = None
    message: str


# Phase 6 — Preview (shown before user clicks Send)
class SendPreview(BaseModel):
    to_address: str
    from_address: str | None  # None when gmail.send scope doesn't expose account email
    subject: str
    body: str
    cv_display_name: str
    gmail_account: str | None  # same — display as "connected account" when None


# Phase 6 — history summary
class DraftHistoryItem(BaseModel):
    draft_id: str
    professor_name: str | None
    professor_email: str | None
    university_name: str | None
    subject: str
    status: DraftStatus
    cv_display_name: str | None = None
    sent_at: str | None = None
    created_at: str | None = None
