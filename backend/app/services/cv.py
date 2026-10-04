from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import HTTPException

from app.cv.extraction.factory import get_extraction_provider
from app.cv.extraction.heuristic import PARSER_VERSION
from app.cv.extraction.schema import ExtractedStudentProfile
from app.cv.parsers.base import ParseError
from app.cv.parsers.registry import extract_normalized_text
from app.cv.storage import CV_FILE_MISSING, available_paths, delete_cv_file, read_cv_bytes, save_cv_bytes
from app.cv.validation import CvTooLargeError, UnsupportedCvError, detect_cv_type
from app.services.query import execute, is_missing_column_error
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

PARSE_FAIL_MESSAGE = (
    "Your CV was uploaded successfully, but we couldn't extract its text. "
    "Please upload another version."
)


def _metadata(
    *,
    original_filename: str,
    file_type: str,
    mime_type: str | None,
    file_size: int,
    parsing_status: str,
    parsing_error: str | None = None,
    extracted_profile: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> str:
    return json.dumps(
        {
            "parser_version": PARSER_VERSION,
            "original_filename": original_filename,
            "file_type": file_type,
            "mime_type": mime_type,
            "file_size": file_size,
            "parsing_status": parsing_status,
            "parsing_error": parsing_error,
            "extracted_profile": extracted_profile,
            "confirmed": confirmed,
        }
    )


def _load_meta(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("description") or "{}"
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


def ensure_profile(profile_id: str | None, user_id: str | None = None) -> str:
    if profile_id:
        existing = execute(
            supabase.table("profiles").select("id").eq("id", profile_id).limit(1)
        ).data
        if existing:
            return profile_id
        raise HTTPException(status_code=404, detail="Profile not found.")
    if user_id:
        # An authenticated Supabase user with no profile yet: use their real
        # auth user id directly as the new profile's id, instead of
        # fabricating a disconnected synthetic identity for them. This is
        # what makes a profile created through this path already "owned" by
        # them for app/auth.py's ownership checks, with no separate linking
        # step required.
        existing = execute(
            supabase.table("profiles").select("id").eq("id", user_id).limit(1)
        ).data
        if existing:
            return user_id
        payload = {"id": user_id, "full_name": "Student", "linked_user_id": user_id}
        try:
            execute(supabase.table("profiles").insert(payload))
        except HTTPException as exc:
            if is_missing_column_error(exc, "linked_user_id"):
                # profiles.linked_user_id is not migrated yet
                # (migrations/20260910_profiles_linked_user_id.sql). It is
                # only a secondary link column — profile.id == user_id
                # already IS the ownership record app/auth.py needs, so
                # insert without it rather than failing profile creation.
                logger.warning(
                    "profiles.linked_user_id is not migrated yet — "
                    "creating profile %s without it.", user_id,
                )
                payload.pop("linked_user_id", None)
                try:
                    execute(supabase.table("profiles").insert(payload))
                except HTTPException as exc2:
                    raise HTTPException(
                        status_code=503,
                        detail="Could not create a student profile for this account.",
                    ) from exc2
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Could not create a student profile for this account.",
                ) from exc
        return user_id
    new_id = _provision_auth_user()
    existing = execute(
        supabase.table("profiles").select("id").eq("id", new_id).limit(1)
    ).data
    if existing:
        return new_id
    try:
        execute(
            supabase.table("profiles").insert(
                {"id": new_id, "full_name": "Student"}
            )
        )
    except HTTPException as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not create a student profile. The profiles table "
                "requires an auth.users row, and inserting that profile failed."
            ),
        ) from exc
    return new_id


def _provision_auth_user() -> str:
    """Create an auth.users row required by profiles.id. No login UI is added."""
    email = f"student-{uuid.uuid4().hex}@local.findmyprofessor.invalid"
    password = uuid.uuid4().hex + "Aa1!"
    try:
        response = supabase.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"source": "cv_onboarding"},
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not create a student profile. Authentication is not "
                "implemented as a login flow; this phase needs permission to "
                "create an auth.users row because profiles.id references users."
            ),
        ) from exc
    user = getattr(response, "user", None)
    if user is None or not getattr(user, "id", None):
        raise HTTPException(
            status_code=503,
            detail="Could not create a student identity in auth.users.",
        )
    return str(user.id)


def _next_version(profile_id: str) -> int:
    rows = execute(
        supabase.table("cv_versions")
        .select("version_number")
        .eq("profile_id", profile_id)
        .order("version_number", desc=True)
        .limit(1)
    ).data or []
    if not rows:
        return 1
    return int(rows[0].get("version_number") or 0) + 1


def _clear_default(profile_id: str) -> None:
    execute(
        supabase.table("cv_versions")
        .update({"is_default": False})
        .eq("profile_id", profile_id)
        .eq("is_default", True)
    )


def upload_and_parse(
    *,
    profile_id: str | None,
    filename: str,
    content: bytes,
    declared_mime: str | None,
    user_id: str | None = None,
) -> dict[str, Any]:
    try:
        detected = detect_cv_type(filename, content, declared_mime)
    except CvTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UnsupportedCvError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    resolved_profile = ensure_profile(profile_id, user_id=user_id)
    relative, _path = save_cv_bytes(resolved_profile, filename, content)
    version = _next_version(resolved_profile)
    _clear_default(resolved_profile)

    extracted = None
    status = "uploaded"
    error = None
    try:
        text = extract_normalized_text(detected.format_id, content)
        labels = _catalog_labels()
        extracted = get_extraction_provider().extract(text, labels)
        status = "parsed"
    except ParseError as exc:
        status = "failed"
        error = str(exc) or PARSE_FAIL_MESSAGE
        logger.info("CV parse failed for format %s", detected.format_id)
    except Exception:
        status = "failed"
        error = PARSE_FAIL_MESSAGE
        logger.exception("Unexpected CV parse failure")

    row = {
        "profile_id": resolved_profile,
        "file_name": filename,
        "storage_path": relative,
        "version_number": version,
        "is_default": True,
        "description": _metadata(
            original_filename=filename,
            file_type=detected.format_id,
            mime_type=detected.mime_type,
            file_size=len(content),
            parsing_status=status,
            parsing_error=error,
            extracted_profile=extracted.model_dump() if extracted else None,
        ),
    }
    inserted = execute(supabase.table("cv_versions").insert(row)).data
    if not inserted:
        raise HTTPException(status_code=503, detail="Could not store the CV version.")
    return public_cv(_cv_payload(inserted[0]))


def get_cv(cv_id: str, profile_id: str | None) -> dict[str, Any]:
    query = supabase.table("cv_versions").select("*").eq("id", cv_id).limit(1)
    if profile_id:
        query = query.eq("profile_id", profile_id)
    rows = execute(query).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="CV version not found.")
    return _cv_payload(rows[0])


def public_cv(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not str(key).startswith("_")}


def parse_cv(cv_id: str, profile_id: str | None) -> dict[str, Any]:
    payload = get_cv(cv_id, profile_id)
    try:
        content = read_cv_bytes(payload["_storage_path"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=CV_FILE_MISSING) from exc
    meta = payload["_meta"]
    try:
        text = extract_normalized_text(meta.get("file_type") or "txt", content)
        extracted = get_extraction_provider().extract(text, _catalog_labels())
        status = "parsed"
        error = None
        profile = extracted.model_dump()
    except ParseError as exc:
        status = "failed"
        error = str(exc) or PARSE_FAIL_MESSAGE
        profile = None
        logger.info("CV reparse failed")
    meta.update(
        {
            "parsing_status": status,
            "parsing_error": error,
            "extracted_profile": profile,
            "parser_version": PARSER_VERSION,
            "edited_by_user": False,
        }
    )
    execute(
        supabase.table("cv_versions")
        .update({"description": json.dumps(meta)})
        .eq("id", cv_id)
    )
    return get_cv(cv_id, profile_id)


# ---------------------------------------------------------------------------
# CV version management (My CV page)
# ---------------------------------------------------------------------------

def list_versions(profile_id: str) -> list[dict[str, Any]]:
    """Every CV version the profile owns, newest first, with file availability."""
    rows = execute(
        supabase.table("cv_versions")
        .select("*")
        .eq("profile_id", profile_id)
        .order("version_number", desc=True)
    ).data or []
    present = available_paths([row.get("storage_path") or "" for row in rows])
    versions: list[dict[str, Any]] = []
    for row in rows:
        payload = _cv_payload(row)
        versions.append({
            "cv_id": str(payload["cv_id"]),
            "file_name": payload["original_filename"] or "CV",
            "file_type": payload["file_type"],
            "file_size": payload["file_size"],
            "created_at": str(payload["created_at"] or ""),
            "version_number": payload["version_number"],
            "is_default": bool(payload["is_default"]),
            "confirmed": bool(payload["_meta"].get("confirmed")),
            "parsing_status": payload["parsing_status"],
            "file_available": (payload["_storage_path"] or "") in present,
        })
    return versions


def set_default_version(profile_id: str, cv_id: str) -> list[dict[str, Any]]:
    """Make one of the profile's CVs the active one (used for matching and drafts)."""
    get_cv(cv_id, profile_id)  # 404 unless it belongs to this profile
    _clear_default(profile_id)
    execute(
        supabase.table("cv_versions")
        .update({"is_default": True})
        .eq("id", cv_id)
        .eq("profile_id", profile_id)
    )
    return list_versions(profile_id)


def delete_version(profile_id: str, cv_id: str) -> list[dict[str, Any]]:
    """
    Permanently delete a CV version and its stored file.

    Drafts that referenced it keep working (their CV selection is cleared and
    can be re-attached). If the active CV is deleted, the newest remaining
    version becomes active.
    """
    payload = get_cv(cv_id, profile_id)  # 404 unless it belongs to this profile
    for table in ("outreach_drafts", "outreach"):
        try:
            execute(supabase.table(table).update({"cv_version_id": None}).eq("cv_version_id", cv_id))
        except HTTPException:
            logger.warning("Could not clear %s.cv_version_id before CV delete.", table)
    execute(supabase.table("cv_versions").delete().eq("id", cv_id).eq("profile_id", profile_id))
    delete_cv_file(payload["_storage_path"])

    if payload.get("is_default"):
        remaining = execute(
            supabase.table("cv_versions")
            .select("id")
            .eq("profile_id", profile_id)
            .order("version_number", desc=True)
            .limit(1)
        ).data or []
        if remaining:
            execute(
                supabase.table("cv_versions").update({"is_default": True}).eq("id", remaining[0]["id"])
            )
    return list_versions(profile_id)


def _refresh_stale_parse(cv: dict[str, Any], profile_id: str) -> dict[str, Any]:
    """
    Re-read a CV parsed by an older parser version, so parser fixes reach
    CVs uploaded before them. Hand-edited profiles are never touched, the
    confirmed flag is kept, and any failure leaves the stored profile as is.
    """
    meta = cv["_meta"]
    if meta.get("edited_by_user") or int(meta.get("parser_version") or 0) >= PARSER_VERSION:
        return cv
    if meta.get("parsing_status") not in (None, "parsed", "uploaded"):
        return cv
    try:
        content = read_cv_bytes(cv["_storage_path"])
        text = extract_normalized_text(meta.get("file_type") or "txt", content)
        extracted = get_extraction_provider().extract(text, _catalog_labels())
    except Exception:
        logger.info("Stale CV re-parse skipped (file unavailable or parse failed).")
        return cv
    meta.update({
        "extracted_profile": extracted.model_dump(),
        "parsing_status": "parsed",
        "parsing_error": None,
        "parser_version": PARSER_VERSION,
    })
    execute(
        supabase.table("cv_versions")
        .update({"description": json.dumps(meta)})
        .eq("id", str(cv["cv_id"]))
        .eq("profile_id", profile_id)
    )
    return get_cv(str(cv["cv_id"]), profile_id)


def get_active_profile(profile_id: str) -> dict[str, Any]:
    ensure_profile(profile_id)
    rows = execute(
        supabase.table("cv_versions")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("is_default", True)
        .limit(1)
    ).data or []
    if not rows:
        persisted = execute(
            supabase.table("profiles").select("*").eq("id", profile_id).limit(1)
        ).data
        return {
            "profile_id": profile_id,
            "confirmed": False,
            "cv_id": None,
            "extracted_profile": ExtractedStudentProfile().model_dump(),
            "persisted": (persisted or [None])[0],
        }
    cv = _refresh_stale_parse(_cv_payload(rows[0]), profile_id)
    profile_row = execute(
        supabase.table("profiles").select("*").eq("id", profile_id).limit(1)
    ).data
    extracted = cv.get("extracted_profile") or ExtractedStudentProfile().model_dump()
    return {
        "profile_id": profile_id,
        "confirmed": bool(cv["_meta"].get("confirmed")),
        "cv_id": cv["cv_id"],
        "extracted_profile": extracted,
        "persisted": (profile_row or [None])[0],
        "parsing_status": cv["parsing_status"],
        "parsing_error": cv["parsing_error"],
    }


def update_extracted_profile(
    profile_id: str, extracted: ExtractedStudentProfile
) -> dict[str, Any]:
    current = get_active_profile(profile_id)
    cv_id = current.get("cv_id")
    if not cv_id:
        raise HTTPException(status_code=404, detail="Upload a CV before editing the profile.")
    cv = get_cv(str(cv_id), profile_id)
    meta = cv["_meta"]
    meta["extracted_profile"] = extracted.model_dump()
    meta["confirmed"] = False
    meta["edited_by_user"] = True  # never overwrite hand edits with a re-parse
    execute(
        supabase.table("cv_versions")
        .update({"description": json.dumps(meta)})
        .eq("id", str(cv_id))
    )
    return get_active_profile(profile_id)


def confirm_profile(profile_id: str) -> dict[str, Any]:
    current = get_active_profile(profile_id)
    cv_id = current.get("cv_id")
    if not cv_id:
        raise HTTPException(status_code=400, detail="Upload and review a CV before confirming.")
    if current.get("parsing_status") == "failed":
        raise HTTPException(status_code=400, detail=current.get("parsing_error") or PARSE_FAIL_MESSAGE)
    extracted = ExtractedStudentProfile.model_validate(current["extracted_profile"])
    _write_normalized_tables(profile_id, extracted)
    cv = get_cv(str(cv_id), profile_id)
    meta = cv["_meta"]
    meta["confirmed"] = True
    execute(
        supabase.table("cv_versions")
        .update({"description": json.dumps(meta)})
        .eq("id", str(cv_id))
    )
    return {
        "profile_id": profile_id,
        "confirmed": True,
        "message": "Profile saved.",
    }


def _write_normalized_tables(profile_id: str, extracted: ExtractedStudentProfile) -> None:
    education = extracted.education[0] if extracted.education else None
    identity = extracted.identity
    payload = {
        "full_name": identity.name or "Student",
        "email": identity.email,
        "university_name": education.institution if education else None,
        "degree": education.degree if education else None,
        "field_of_study": education.field_of_study if education else None,
        "country": education.country if education else None,
        "current_semester": education.current_semester if education else None,
        "graduation_year": education.graduation_year if education else None,
        "research_summary": _research_summary(extracted),
        "bio": _bio(extracted),
    }
    execute(supabase.table("profiles").update(payload).eq("id", profile_id))
    execute(supabase.table("student_projects").delete().eq("profile_id", profile_id))
    execute(supabase.table("student_publications").delete().eq("profile_id", profile_id))
    execute(supabase.table("student_research_areas").delete().eq("profile_id", profile_id))
    for project in extracted.projects:
        execute(
            supabase.table("student_projects").insert(
                {
                    "profile_id": profile_id,
                    "title": project.title,
                    "description": project.description,
                    "technologies": ", ".join(project.technologies) or None,
                }
            )
        )
    for publication in extracted.publications:
        description = publication.authors
        execute(
            supabase.table("student_publications").insert(
                {
                    "profile_id": profile_id,
                    "title": publication.title,
                    "venue": publication.venue,
                    "publication_year": publication.year,
                    "status": publication.publication_type,
                    "description": description,
                }
            )
        )
    area_ids = _research_area_ids()
    used: set[str] = set()
    priority = 1
    for name in extracted.research_interests:
        area_id = area_ids.get(name.casefold())
        if not area_id or area_id in used:
            continue
        used.add(area_id)
        execute(
            supabase.table("student_research_areas").insert(
                {
                    "profile_id": profile_id,
                    "research_area_id": area_id,
                    "priority": priority,
                }
            )
        )
        priority += 1


def _research_summary(extracted: ExtractedStudentProfile) -> str | None:
    parts = []
    if extracted.research_interests:
        parts.append("Research interests: " + ", ".join(extracted.research_interests))
    if extracted.research_signals:
        parts.append("Research signals: " + ", ".join(extracted.research_signals))
    return "\n".join(parts) or None


def _bio(extracted: ExtractedStudentProfile) -> str | None:
    parts = []
    if extracted.identity.phone:
        parts.append(f"Phone: {extracted.identity.phone}")
    if extracted.skills:
        parts.append("Skills: " + ", ".join(item.name for item in extracted.skills))
    return "\n".join(parts) or None


def _catalog_labels() -> list[str]:
    rows = execute(supabase.table("research_areas").select("name")).data or []
    return [row["name"] for row in rows if row.get("name")]


def _research_area_ids() -> dict[str, str]:
    rows = execute(supabase.table("research_areas").select("id,name")).data or []
    return {row["name"].casefold(): row["id"] for row in rows if row.get("name") and row.get("id")}


def _cv_payload(row: dict[str, Any]) -> dict[str, Any]:
    meta = _load_meta(row)
    extracted = meta.get("extracted_profile")
    return {
        "cv_id": row["id"],
        "profile_id": row["profile_id"],
        "original_filename": meta.get("original_filename") or row.get("file_name"),
        "file_type": meta.get("file_type"),
        "file_size": meta.get("file_size"),
        "parsing_status": meta.get("parsing_status") or "uploaded",
        "parsing_error": meta.get("parsing_error"),
        "is_default": row.get("is_default"),
        "version_number": row.get("version_number"),
        "created_at": row.get("created_at"),
        "extracted_profile": extracted,
        "_storage_path": row.get("storage_path"),
        "_meta": meta,
    }
