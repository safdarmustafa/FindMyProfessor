from __future__ import annotations

import mimetypes
import os
import re
import uuid
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parents[2] / "var" / "cv_uploads"

# Object-storage backend selection for CV files.
#
# Render's local disk does NOT persist across redeploys/restarts, so local
# disk alone is unsafe for production CV storage even though DB rows
# (cv_versions) do persist. When SUPABASE_CV_BUCKET is set, CV bytes are
# stored in a private Supabase Storage bucket instead — reachable only
# through this backend's service-role client, never a public URL — and
# `storage_path` (already stored per CV version) is reused unchanged as the
# object key. When the variable is unset, behavior is byte-for-byte the same
# as before this change: files live under STORAGE_ROOT on local disk. That
# keeps every existing test, and any deployment that hasn't provisioned the
# bucket yet, working exactly as before.
SUPABASE_CV_BUCKET = os.getenv("SUPABASE_CV_BUCKET")


def _bucket():
    from app.supabase_client import supabase

    return supabase.storage.from_(SUPABASE_CV_BUCKET)


def safe_filename(original: str) -> str:
    name = Path(original or "cv").name
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        name = "cv"
    return name[:180]


def save_cv_bytes(profile_id: str, original_filename: str, content: bytes) -> tuple[str, Path | None]:
    """
    Persist CV bytes for a profile and return (storage_path, local_path).

    storage_path is the opaque key stored in cv_versions.storage_path and
    passed back into read_cv_bytes()/cv_file_exists(). local_path is only
    populated when using the local-disk backend (kept for backward
    compatibility with any caller that still wants it); it is None when
    using Supabase Storage.
    """
    cv_id = str(uuid.uuid4())
    filename = safe_filename(original_filename)
    relative = f"{profile_id}/{cv_id}/{filename}"

    if SUPABASE_CV_BUCKET:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        _bucket().upload(relative, content, {"content-type": content_type})
        return relative, None

    directory = STORAGE_ROOT / profile_id / cv_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_bytes(content)
    relative = path.relative_to(STORAGE_ROOT).as_posix()
    return relative, path


def resolve_storage_path(storage_path: str) -> Path:
    """Resolve a storage_path to a local filesystem Path. Local-disk backend only."""
    relative = Path(storage_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid storage path.")
    full = (STORAGE_ROOT / relative).resolve()
    root = STORAGE_ROOT.resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Invalid storage path.")
    return full


def read_cv_bytes(storage_path: str) -> bytes:
    """Read CV file content, from Supabase Storage or local disk, whichever is active."""
    if SUPABASE_CV_BUCKET:
        try:
            return _bucket().download(storage_path)
        except Exception as exc:
            raise FileNotFoundError(storage_path) from exc
    path = resolve_storage_path(storage_path)
    if not path.exists():
        raise FileNotFoundError(storage_path)
    return path.read_bytes()


def cv_file_exists(storage_path: str) -> bool:
    """Check CV file availability without necessarily downloading it."""
    if not storage_path:
        return False
    if SUPABASE_CV_BUCKET:
        directory, _, filename = storage_path.rpartition("/")
        try:
            listing = _bucket().list(directory or None)
        except Exception:
            return False
        return any(item.get("name") == filename for item in listing)
    try:
        path = resolve_storage_path(storage_path)
    except ValueError:
        return False
    return path.exists()
