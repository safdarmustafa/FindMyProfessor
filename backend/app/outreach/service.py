from __future__ import annotations

"""
Outreach service — Phase 5 + Phase 6.

Phase 5 responsibilities (unchanged):
- Load confirmed student profile.
- Load verified professor data.
- Run Phase 3.2 scoring to obtain deterministic match evidence.
- Call the configured email-generation provider.
- Store / retrieve drafts.
- Save / update draft subject and body.

Phase 6 additions:
- Persist drafts to Supabase (via db_store, with in-memory test fallback).
- Attach a CV version to a draft.
- Build send preview.
- Execute send via Gmail API (with all safety validations).
- Record sent result / failure.
- List draft history.

This module must NOT:
- Log email body, CV contents, OAuth tokens, or file paths.
- Trust browser-supplied file paths or CV content.
- Send automatically — send is always triggered by explicit user action.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.cv.extraction.schema import ExtractedStudentProfile
from app.cv.storage import cv_file_exists, read_cv_bytes
from app.gmail.client import GmailApiError, build_mime_message, send_message
from app.gmail.service import get_status, get_valid_access_token
from app.matching.scoring import score_professor
from app.opportunities.models import OpportunityRecord
from app.outreach import store
from app.outreach.factory import get_email_provider
from app.outreach.models import DraftRecord, EvidenceLine
from app.outreach.provider import (
    ArtifactEvidence,
    MatchContext,
    OpportunityContext,
    ProfessorContext,
)
from app.schemas.outreach import (
    AttachCvResponse,
    CvVersionMeta,
    DraftHistoryItem,
    EmailDraft,
    SaveDraftResponse,
    SendDraftResponse,
    SendPreview,
)
from app.services import cv as cv_service
from app.services.professors import get_professor
from app.services.query import execute
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 5 — Generate / save / retrieve drafts
# ---------------------------------------------------------------------------

def generate_draft(
    *,
    profile_id: str,
    professor_id: str,
    email_type: str,
    opportunity_id: str | None = None,
) -> EmailDraft:
    student = _confirmed_student(profile_id)
    professor = _load_professor(professor_id)
    prof_ctx = _professor_context(professor)
    catalog_names, _ = _load_catalog()
    match_ctx = _build_match_context(student, prof_ctx, catalog_names)
    opp_ctx = _load_opportunity_context(opportunity_id, prof_ctx) if opportunity_id else None

    provider = get_email_provider()
    output = provider.generate(
        student=student,
        professor=prof_ctx,
        match=match_ctx,
        email_type=email_type,
        opportunity=opp_ctx,
    )
    output = _enforce_length(output)

    draft_id = str(uuid.uuid4())
    evidence_lines = [EvidenceLine(type="evidence", description=e) for e in output.evidence_used]
    record = DraftRecord(
        draft_id=draft_id,
        profile_id=profile_id,
        professor_id=professor_id,
        email_type=email_type,
        subject=output.subject,
        body=output.body,
        matched_research_areas=list(match_ctx.research_overlap),
        evidence_used=evidence_lines,
        generation_provider=output.generation_provider,
        generation_status="generated",
        professor_name=prof_ctx.name,
        professor_email=prof_ctx.email,
        professor_email_available=bool(prof_ctx.email),
        university_name=prof_ctx.university_name,
    )
    store.put(draft_id, record)
    return _to_schema(record)


def save_draft(
    *,
    profile_id: str,
    draft_id: str,
    subject: str,
    body: str,
    status: str = "ready",
) -> SaveDraftResponse:
    record = store.get(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if record.profile_id != profile_id:
        raise HTTPException(status_code=403, detail="Draft does not belong to this profile.")

    record.subject = subject
    record.body = body
    record.generation_status = status  # type: ignore[assignment]
    store.put(draft_id, record)

    return SaveDraftResponse(
        draft_id=draft_id,
        status=record.generation_status,
        message="Draft saved.",
    )


def get_draft(*, profile_id: str, draft_id: str) -> EmailDraft:
    record = store.get(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if record.profile_id != profile_id:
        raise HTTPException(status_code=403, detail="Draft does not belong to this profile.")
    return _to_schema(record)


def list_drafts(*, profile_id: str) -> list[EmailDraft]:
    return [_to_schema(r) for r in store.all_for_profile(profile_id)]


# ---------------------------------------------------------------------------
# Phase 6 — CV attachment
# ---------------------------------------------------------------------------

def list_cv_versions(*, profile_id: str) -> list[CvVersionMeta]:
    """
    List CV versions owned by this profile. Returns safe metadata only.
    Never exposes storage paths.
    """
    rows = execute(
        supabase.table("cv_versions")
        .select("id, file_name, description, is_default, version_number, created_at")
        .eq("profile_id", profile_id)
        .order("version_number", desc=True)
    ).data or []

    result: list[CvVersionMeta] = []
    for row in rows:
        import json as _json
        meta_raw = row.get("description") or "{}"
        try:
            meta = _json.loads(meta_raw) if isinstance(meta_raw, str) else {}
        except Exception:
            meta = {}
        display_name = meta.get("original_filename") or row.get("file_name") or "CV"
        result.append(CvVersionMeta(
            cv_version_id=str(row["id"]),
            display_name=display_name,
            file_type=meta.get("file_type"),
            file_size=meta.get("file_size"),
            created_at=str(row.get("created_at") or ""),
            is_default=bool(row.get("is_default")),
            confirmed=bool(meta.get("confirmed")),
        ))
    return result


def attach_cv(*, profile_id: str, draft_id: str, cv_version_id: str) -> AttachCvResponse:
    """
    Attach an exact CV version to a draft.
    Validates:
    - Draft belongs to profile.
    - CV version belongs to profile.
    - CV file exists on disk.
    """
    record = store.get(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if record.profile_id != profile_id:
        raise HTTPException(status_code=403, detail="Draft does not belong to this profile.")

    cv_row = _load_cv_row(cv_version_id, profile_id)
    display_name = _cv_display_name(cv_row)
    _validate_cv_file(cv_row)

    record.cv_version_id = cv_version_id
    store.put(draft_id, record)

    return AttachCvResponse(
        draft_id=draft_id,
        cv_version_id=cv_version_id,
        display_name=display_name,
        message="CV attached to draft.",
    )


# ---------------------------------------------------------------------------
# Phase 6 — Send preview
# ---------------------------------------------------------------------------

def build_send_preview(*, profile_id: str, draft_id: str) -> SendPreview:
    """
    Build the full preview shown to the student before they click Send.
    All information is verified server-side.
    """
    record, prof, gmail_email, cv_meta = _validate_for_send(profile_id, draft_id)
    return SendPreview(
        to_address=prof["email"],
        from_address=gmail_email,          # may be None; displayed as "connected account"
        subject=record.subject,
        body=record.body,
        cv_display_name=cv_meta["display_name"],
        gmail_account=gmail_email,         # may be None
    )


# ---------------------------------------------------------------------------
# Phase 6 — Send
# ---------------------------------------------------------------------------

def send_draft(*, profile_id: str, draft_id: str, confirmed: bool) -> SendDraftResponse:
    """
    Send the approved draft via Gmail API.

    Validations (all server-side, never trust browser input):
    1. Draft belongs to profile.
    2. Draft status is 'ready'.
    3. Professor exists and has verified email.
    4. Selected CV exists and belongs to profile.
    5. CV file exists on disk.
    6. Gmail is connected and tokens are usable.
    7. Explicit user confirmation (confirmed=True).
    8. Atomic status transition: ready → sending (prevents double-send).

    On success: status → sent, sent_at, gmail_message_id, gmail_thread_id recorded.
    On failure: status → failed, error_code, error_message recorded.
    """
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit confirmation (confirmed=true) is required to send.",
        )

    # Validate everything before acquiring the sending lock
    record, prof, gmail_email, cv_meta = _validate_for_send(profile_id, draft_id)

    # Atomic status transition: ready → sending
    acquired = store.atomically_set_sending(draft_id, profile_id)
    if not acquired:
        # Re-check to give a better error
        record = store.get(draft_id)
        current_status = getattr(record, "generation_status", "unknown") if record else "unknown"
        if current_status == "sent":
            raise HTTPException(status_code=409, detail="This draft has already been sent.")
        if current_status == "sending":
            raise HTTPException(status_code=409, detail="This draft is currently being sent.")
        raise HTTPException(
            status_code=409,
            detail=f"Cannot send: draft status is '{current_status}'. Save as 'ready' first.",
        )

    # Refresh the record after atomic update
    record = store.get(draft_id)

    # Resolve CV file (server-side; never expose path/bytes to browser)
    try:
        cv_bytes = read_cv_bytes(cv_meta["storage_path"])
    except FileNotFoundError:
        _mark_failed(record, "cv_unavailable", "CV file is not available.")
        raise HTTPException(status_code=400, detail="CV file is not available.")

    # Get valid access token (refreshes if needed)
    try:
        access_token = get_valid_access_token(profile_id)
    except HTTPException:
        _mark_failed(record, "token_unavailable", "Gmail access token could not be obtained.")
        raise

    # Build MIME message. from_addr may be None when only gmail.send scope was
    # granted — the Gmail API overwrites From from the authenticated account.
    try:
        mime_msg = build_mime_message(
            from_addr=gmail_email or "",
            to_addr=prof["email"],
            subject=record.subject,
            body=record.body,
            attachment_bytes=cv_bytes,
            attachment_display_name=cv_meta["display_name"],
        )
    except Exception as exc:
        _mark_failed(record, "mime_build_failed", "Could not construct the email.")
        raise HTTPException(status_code=500, detail="Could not construct the email message.") from exc

    # Send via Gmail API
    try:
        result = send_message(access_token=access_token, mime_message=mime_msg)
    except GmailApiError as exc:
        safe_message = "Gmail API refused the message. Check connection and try again."
        _mark_failed(record, exc.code or "gmail_error", safe_message)
        raise HTTPException(status_code=502, detail=safe_message) from exc
    except Exception as exc:
        _mark_failed(record, "unknown", "An unexpected error occurred during send.")
        raise HTTPException(status_code=502, detail="An unexpected error occurred while sending.") from exc

    # Mark sent
    sent_at = datetime.now(timezone.utc).isoformat()
    record.generation_status = "sent"  # type: ignore[assignment]
    record.sent_at = sent_at
    record.gmail_message_id = result.message_id
    record.gmail_thread_id = result.thread_id
    record.error_code = None
    record.error_message = None
    store.put(draft_id, record)

    return SendDraftResponse(
        draft_id=draft_id,
        status="sent",
        gmail_message_id=result.message_id,
        sent_at=sent_at,
        message="Email sent successfully.",
    )


# ---------------------------------------------------------------------------
# Phase 6 — History
# ---------------------------------------------------------------------------

def _display_name(value: Any) -> str | None:
    """String or nested {name} / {title} object → display string."""
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name") or value.get("title")
        return str(name) if name else None
    name = getattr(value, "name", None)
    return str(name) if name else None


def list_history(*, profile_id: str) -> list[DraftHistoryItem]:
    """
    List all drafts for a profile as history items.
    Includes sent and failed drafts.
    """
    records = store.all_for_profile(profile_id)
    items: list[DraftHistoryItem] = []
    for record in records:
        cv_display = None
        if getattr(record, "cv_version_id", None):
            try:
                cv_row = _load_cv_row(record.cv_version_id, profile_id)
                cv_display = _cv_display_name(cv_row)
            except Exception:
                pass
        professor_name = _display_name(getattr(record, "professor_name", None))
        university_name = _display_name(getattr(record, "university_name", None))
        professor_email = getattr(record, "professor_email", None)
        # Draft rows do not persist denormalized names; hydrate from professor.
        if not professor_name or not university_name:
            try:
                prof = get_professor(record.professor_id)
            except Exception:
                prof = None
            if prof:
                professor_name = professor_name or _display_name(prof.get("name")) or (
                    " ".join(
                        p for p in (prof.get("first_name"), prof.get("last_name")) if p
                    ) or None
                )
                university_name = university_name or _display_name(prof.get("university"))
                professor_email = professor_email or prof.get("email")
        items.append(DraftHistoryItem(
            draft_id=record.draft_id,
            professor_name=professor_name,
            professor_email=professor_email,
            university_name=university_name,
            subject=record.subject,
            status=record.generation_status,  # type: ignore[arg-type]
            cv_display_name=cv_display,
            sent_at=getattr(record, "sent_at", None),
        ))
    return items


# ---------------------------------------------------------------------------
# Internal — validation pipeline
# ---------------------------------------------------------------------------

def _validate_for_send(
    profile_id: str,
    draft_id: str,
) -> tuple[DraftRecord, dict[str, Any], str | None, dict[str, Any]]:
    """
    Validates all preconditions for sending.
    Returns (record, prof, gmail_email_or_none, cv_meta).
    gmail_email may be None when only gmail.send scope is granted — this is
    acceptable. The Gmail API uses userId='me' and sets From automatically.
    Raises HTTPException on any validation failure.
    """
    # 1. Draft ownership
    record = store.get(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if record.profile_id != profile_id:
        raise HTTPException(status_code=403, detail="Draft does not belong to this profile.")

    # 2. Subject and body are non-empty
    if not (record.subject or "").strip():
        raise HTTPException(status_code=400, detail="Draft subject is empty.")
    if not (record.body or "").strip():
        raise HTTPException(status_code=400, detail="Draft body is empty.")

    # 3. Sendable status
    if record.generation_status == "sent":
        raise HTTPException(status_code=409, detail="This draft has already been sent.")
    if record.generation_status == "sending":
        raise HTTPException(status_code=409, detail="This draft is currently being sent.")
    if record.generation_status not in ("ready", "edited"):
        raise HTTPException(
            status_code=400,
            detail=f"Draft status is '{record.generation_status}'. Save as 'ready' before sending.",
        )

    # 4. Professor with verified email
    prof = get_professor(record.professor_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Professor not found.")
    prof_email = prof.get("email") or ""
    if not prof_email or not _valid_email(prof_email):
        raise HTTPException(
            status_code=400,
            detail="Professor does not have a verified email address.",
        )

    # 5. CV version selected
    if not getattr(record, "cv_version_id", None):
        raise HTTPException(
            status_code=400,
            detail="No CV version selected. Attach a CV before sending.",
        )

    # 6. CV belongs to profile and file exists
    cv_row = _load_cv_row(record.cv_version_id, profile_id)
    cv_display = _cv_display_name(cv_row)
    _validate_cv_file(cv_row)
    cv_meta = {
        "display_name": cv_display,
        "storage_path": cv_row["_storage_path"],
    }

    # 7. Gmail connected — only the connected flag matters.
    # provider_account_email is optional metadata; gmail.send scope does not
    # expose the account email. The Gmail API uses userId='me' and sets the
    # From header automatically from the authenticated credentials.
    status = get_status(profile_id)
    if not status.connected:
        raise HTTPException(
            status_code=400,
            detail="Gmail is not connected. Connect via /gmail/connect.",
        )

    return record, prof, status.email, cv_meta


def _mark_failed(record: DraftRecord, code: str, message: str) -> None:
    """Record a failed send attempt. Does not raise."""
    try:
        record.generation_status = "failed"  # type: ignore[assignment]
        record.error_code = code
        record.error_message = message
        store.put(record.draft_id, record)
    except Exception:
        logger.error("Could not persist failed send status for draft.")


# ---------------------------------------------------------------------------
# Internal — helpers
# ---------------------------------------------------------------------------

def _confirmed_student(profile_id: str) -> ExtractedStudentProfile:
    current = cv_service.get_active_profile(profile_id)
    if not current.get("cv_id"):
        raise HTTPException(
            status_code=400,
            detail="Upload and confirm a CV before generating an email draft.",
        )
    if current.get("parsing_status") == "failed":
        raise HTTPException(
            status_code=400,
            detail=current.get("parsing_error") or "CV could not be parsed. Upload another version.",
        )
    if not current.get("confirmed"):
        raise HTTPException(
            status_code=400,
            detail="Confirm your CV profile before generating an email draft.",
        )
    return ExtractedStudentProfile.model_validate(current.get("extracted_profile") or {})


def _load_professor(professor_id: str) -> dict[str, Any]:
    prof = get_professor(professor_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Professor not found.")
    return prof


def _professor_context(professor: dict[str, Any]) -> ProfessorContext:
    department = professor.get("department") or {}
    university = professor.get("university") or {}
    lab = professor.get("lab") or {}
    areas = [
        a["name"]
        for a in (professor.get("research_areas") or [])
        if isinstance(a, dict) and a.get("name")
    ]
    return ProfessorContext(
        professor_id=str(professor["id"]),
        name=professor.get("name") or "Professor",
        title=professor.get("title"),
        email=professor.get("email"),
        university_name=university.get("name") if isinstance(university, dict) else None,
        department_name=department.get("name") if isinstance(department, dict) else None,
        lab_name=lab.get("name") if isinstance(lab, dict) else None,
        research_areas=areas,
        research_summary=professor.get("research_summary"),
    )


def _load_catalog() -> tuple[list[str], dict[str, str]]:
    rows = execute(supabase.table("research_areas").select("id,name")).data or []
    names = [row["name"] for row in rows if row.get("name")]
    by_id = {str(row["id"]): row["name"] for row in rows if row.get("id") and row.get("name")}
    return names, by_id


def _build_match_context(
    student: ExtractedStudentProfile,
    professor: ProfessorContext,
    catalog_names: list[str],
) -> MatchContext:
    result = score_professor(
        student=student,
        professor_areas=professor.research_areas,
        catalog_names=catalog_names,
        research_summary=professor.research_summary,
    )
    shared_interests: list[str] = []
    artifacts: list[ArtifactEvidence] = []
    corroborated: list[str] = []

    for ev in result.evidence:
        if ev.type == "shared_research_area" and ev.area_name and ev.student_source == "interest":
            shared_interests.append(ev.area_name)
        elif ev.type == "artifact_research_area" and ev.area_name and ev.artifact_title:
            artifacts.append(ArtifactEvidence(
                kind=ev.student_source or "project",
                title=ev.artifact_title,
                area_name=ev.area_name,
            ))
        elif ev.type == "professor_summary_mentions_area" and ev.area_name:
            corroborated.append(ev.area_name)

    return MatchContext(
        research_score=result.score,
        research_overlap=result.research_overlap,
        shared_interest_areas=shared_interests,
        artifact_evidence=artifacts,
        corroborated_areas=corroborated,
    )


def _load_opportunity_context(opportunity_id: str, professor: ProfessorContext) -> OpportunityContext | None:
    rows = execute(
        supabase.table("opportunities")
        .select("id,professor_id,lab_id,university_id,title,opportunity_type,status,universities(name)")
        .eq("id", opportunity_id)
        .limit(1)
    ).data or []
    if not rows:
        return None
    row = rows[0]
    if (row.get("status") or "").strip().casefold() == "closed":
        raise HTTPException(status_code=400, detail="Closed opportunities cannot be used in active email drafts.")
    uni_row = row.get("universities")
    university_name = (uni_row.get("name") if isinstance(uni_row, dict) else None) or professor.university_name
    return OpportunityContext(
        opportunity_id=str(row["id"]),
        title=row.get("title"),
        opportunity_type=row.get("opportunity_type"),
        status=row.get("status") or "unknown",
        university_name=university_name,
        not_professor_specific=row.get("professor_id") is None,
    )


def _enforce_length(output: Any) -> Any:
    words = output.body.split()
    if len(words) <= 300:
        return output
    output.body = " ".join(words[:300]) + "…"
    return output


def _load_cv_row(cv_version_id: str, profile_id: str) -> dict[str, Any]:
    """Load a CV row and verify ownership. Raises 404/403 as appropriate."""
    rows = execute(
        supabase.table("cv_versions")
        .select("id, profile_id, file_name, description, is_default, storage_path")
        .eq("id", cv_version_id)
        .limit(1)
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="CV version not found.")
    row = rows[0]
    if str(row.get("profile_id", "")) != profile_id:
        raise HTTPException(status_code=403, detail="CV version does not belong to this profile.")

    import json as _json
    meta_raw = row.get("description") or "{}"
    try:
        meta = _json.loads(meta_raw) if isinstance(meta_raw, str) else {}
    except Exception:
        meta = {}

    return {
        "_storage_path": row.get("storage_path"),
        "file_name": row.get("file_name"),
        "original_filename": meta.get("original_filename"),
        "file_type": meta.get("file_type"),
        "file_size": meta.get("file_size"),
        "confirmed": meta.get("confirmed", False),
    }


def _cv_display_name(cv_row: dict[str, Any]) -> str:
    return cv_row.get("original_filename") or cv_row.get("file_name") or "CV"


def _validate_cv_file(cv_row: dict[str, Any]) -> None:
    """Verify that the CV file exists in whichever storage backend is active."""
    storage_path = cv_row.get("_storage_path")
    if not storage_path:
        raise HTTPException(status_code=400, detail="CV version has no storage path.")
    if not cv_file_exists(storage_path):
        raise HTTPException(status_code=400, detail="CV file is not available.")


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _to_schema(record: DraftRecord) -> EmailDraft:
    from app.schemas.outreach import EvidenceUsed

    return EmailDraft(
        draft_id=record.draft_id,
        profile_id=record.profile_id,
        professor_id=record.professor_id,
        email_type=record.email_type,  # type: ignore[arg-type]
        subject=record.subject,
        body=record.body,
        matched_research_areas=record.matched_research_areas,
        evidence_used=[
            EvidenceUsed(type=e.type, description=e.description)
            for e in record.evidence_used
        ],
        generation_provider=record.generation_provider,
        generation_status=record.generation_status,  # type: ignore[arg-type]
        professor_name=record.professor_name,
        professor_email=record.professor_email,
        professor_email_available=record.professor_email_available,
        university_name=record.university_name,
        cv_version_id=getattr(record, "cv_version_id", None),
        sent_at=getattr(record, "sent_at", None),
        gmail_message_id=getattr(record, "gmail_message_id", None),
    )
