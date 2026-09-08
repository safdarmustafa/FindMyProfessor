from __future__ import annotations

import re
import uuid
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parents[2] / "var" / "cv_uploads"


def safe_filename(original: str) -> str:
    name = Path(original or "cv").name
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        name = "cv"
    return name[:180]


def save_cv_bytes(profile_id: str, original_filename: str, content: bytes) -> tuple[str, Path]:
    cv_id = str(uuid.uuid4())
    directory = STORAGE_ROOT / profile_id / cv_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / safe_filename(original_filename)
    path.write_bytes(content)
    relative = path.relative_to(STORAGE_ROOT).as_posix()
    return relative, path


def resolve_storage_path(storage_path: str) -> Path:
    relative = Path(storage_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid storage path.")
    full = (STORAGE_ROOT / relative).resolve()
    root = STORAGE_ROOT.resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Invalid storage path.")
    return full
