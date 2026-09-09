from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path

from app.outreach import service as outreach_service
from app.schemas.outreach import (
    AttachCvRequest,
    AttachCvResponse,
    CvVersionMeta,
    DraftHistoryItem,
    EmailDraft,
    GenerateDraftRequest,
    SaveDraftRequest,
    SaveDraftResponse,
    SendDraftRequest,
    SendDraftResponse,
    SendPreview,
)

router = APIRouter(prefix="/outreach", tags=["outreach"])


def _require_profile(x_profile_id: str | None) -> str:
    if not x_profile_id:
        raise HTTPException(
            status_code=400,
            detail="X-Profile-Id header is required. Confirm a CV profile first.",
        )
    return x_profile_id


# ---------------------------------------------------------------------------
# Phase 5 — generate / save / retrieve
# ---------------------------------------------------------------------------

@router.post("/drafts/generate", response_model=EmailDraft)
def generate_draft(
    body: GenerateDraftRequest,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> EmailDraft:
    """
    Generate a personalized email draft for a professor match.
    - Requires a confirmed CV (source of truth).
    - Uses deterministic Phase 3.2 evidence; never re-invents facts.
    - Does NOT send the email or attach any file.
    """
    profile_id = _require_profile(x_profile_id)
    return outreach_service.generate_draft(
        profile_id=profile_id,
        professor_id=str(body.professor_id),
        email_type=body.email_type,
        opportunity_id=body.opportunity_id,
    )


@router.patch("/drafts/{draft_id}", response_model=SaveDraftResponse)
def save_draft(
    draft_id: str = Path(...),
    body: SaveDraftRequest = ...,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> SaveDraftResponse:
    """Save (or update) the subject and body of an existing draft."""
    profile_id = _require_profile(x_profile_id)
    return outreach_service.save_draft(
        profile_id=profile_id,
        draft_id=draft_id,
        subject=body.subject,
        body=body.body,
        status=body.status,
    )


@router.get("/drafts/{draft_id}", response_model=EmailDraft)
def get_draft(
    draft_id: str = Path(...),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> EmailDraft:
    """Retrieve a saved draft."""
    profile_id = _require_profile(x_profile_id)
    return outreach_service.get_draft(profile_id=profile_id, draft_id=draft_id)


@router.get("/drafts", response_model=list[EmailDraft])
def list_drafts(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> list[EmailDraft]:
    """List all drafts for the current profile."""
    profile_id = _require_profile(x_profile_id)
    return outreach_service.list_drafts(profile_id=profile_id)


# ---------------------------------------------------------------------------
# Phase 6 — CV selection
# ---------------------------------------------------------------------------

@router.get("/cv-versions", response_model=list[CvVersionMeta])
def list_cv_versions(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> list[CvVersionMeta]:
    """
    List CV versions available for attachment.
    Returns safe metadata only — never storage paths.
    """
    profile_id = _require_profile(x_profile_id)
    return outreach_service.list_cv_versions(profile_id=profile_id)


@router.post("/drafts/{draft_id}/attach-cv", response_model=AttachCvResponse)
def attach_cv(
    draft_id: str = Path(...),
    body: AttachCvRequest = ...,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> AttachCvResponse:
    """
    Attach a specific CV version to a draft.
    Validates draft ownership, CV ownership, and file existence.
    """
    profile_id = _require_profile(x_profile_id)
    return outreach_service.attach_cv(
        profile_id=profile_id,
        draft_id=draft_id,
        cv_version_id=body.cv_version_id,
    )


# ---------------------------------------------------------------------------
# Phase 6 — Preview & Send
# ---------------------------------------------------------------------------

@router.get("/drafts/{draft_id}/preview", response_model=SendPreview)
def send_preview(
    draft_id: str = Path(...),
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> SendPreview:
    """
    Build the full send preview (To, From, Subject, Body, Attachment, Gmail account).
    All information is verified server-side.
    No email is sent at this point.
    """
    profile_id = _require_profile(x_profile_id)
    return outreach_service.build_send_preview(profile_id=profile_id, draft_id=draft_id)


@router.post("/drafts/{draft_id}/send", response_model=SendDraftResponse)
def send_draft(
    draft_id: str = Path(...),
    body: SendDraftRequest = ...,
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> SendDraftResponse:
    """
    Send the draft via Gmail API.

    - Requires confirmed=true in the request body (explicit user confirmation).
    - Validates all preconditions server-side.
    - Atomically transitions status to 'sending' to prevent double-send.
    - Never sends automatically — the user must explicitly click Send.
    - No CV attachment is exposed to the browser; the server reads the file.
    """
    profile_id = _require_profile(x_profile_id)
    return outreach_service.send_draft(
        profile_id=profile_id,
        draft_id=draft_id,
        confirmed=body.confirmed,
    )


# ---------------------------------------------------------------------------
# Phase 6 — History
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[DraftHistoryItem])
def outreach_history(
    x_profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
) -> list[DraftHistoryItem]:
    """List all drafts (history) for the current profile."""
    profile_id = _require_profile(x_profile_id)
    return outreach_service.list_history(profile_id=profile_id)
