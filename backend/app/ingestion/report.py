from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.dataset import Dataset
from app.ingestion.paths import department_dir, lab_dir, opportunity_dir, professor_dir, university_dir


def render_report(dataset: Dataset) -> str:
    if dataset.manifest is None:
        return "Manifest is missing. Cannot report on the 30-university dataset.\n"

    lines: list[str] = []
    configured = len(dataset.manifest.universities)
    enabled = sum(1 for item in dataset.manifest.universities if item.enabled)
    with_files = 0
    complete = 0

    lines.append(f"{configured} universities configured")
    lines.append(f"enabled: {enabled}")
    lines.append("")

    for item in dataset.manifest.universities:
        file_path = university_dir() / item.file
        has_file = file_path.exists()
        record = dataset.universities.get(item.id)
        counts = {
            "departments": _file_record_count(department_dir() / f"{item.id}.json", "departments"),
            "labs": _file_record_count(lab_dir() / f"{item.id}.json", "labs"),
            "professors": _file_record_count(professor_dir() / f"{item.id}.json", "professors"),
            "opportunities": _file_record_count(opportunity_dir() / f"{item.id}.json", "opportunities"),
        }
        display_name = (record.name if record else None) or item.name or item.id
        status = _status(item.enabled, has_file, record, counts)
        if has_file:
            with_files += 1
        if status == "complete":
            complete += 1

        lines.append(display_name)
        lines.append(f"  id: {item.id}")
        lines.append(f"  enabled: {str(item.enabled).lower()}")
        lines.append(f"  file: {'present' if has_file else 'missing'} ({item.file})")
        lines.append(f"  departments: {counts['departments']}")
        lines.append(f"  labs: {counts['labs']}")
        lines.append(f"  professors: {counts['professors']}")
        lines.append(f"  opportunities: {counts['opportunities']}")
        lines.append(f"  status: {status}")
        lines.append("")

    lines.append(f"universities with data files: {with_files}")
    lines.append(f"complete: {complete}")
    lines.append("No verified records have been invented by the importer.")
    return "\n".join(lines) + "\n"


def _file_record_count(path: Path, key: str) -> int:
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return len(payload[key])
    return 0


def _status(enabled: bool, has_file: bool, record, counts: dict[str, int]) -> str:
    if not enabled:
        return "incomplete"
    if not has_file or record is None:
        return "incomplete"
    required = [
        record.name,
        record.country,
        record.website_url,
        record.source_url,
        counts["departments"] > 0,
        counts["labs"] > 0,
        counts["professors"] > 0,
    ]
    if all(required):
        return "complete"
    return "incomplete"
