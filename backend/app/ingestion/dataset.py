from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ValidationError

from app.ingestion.models import (
    DepartmentRecord,
    LabRecord,
    Manifest,
    OpportunityRecord,
    ProfessorRecord,
    ResearchAreaRecord,
    UniversityRecord,
)
from app.ingestion.normalize import canonical_research_area_name, normalize_research_area_key
from app.ingestion.paths import (
    department_dir,
    lab_dir,
    manifest_path,
    opportunity_dir,
    professor_dir,
    research_area_dir,
    university_dir,
)

T = TypeVar("T")


@dataclass
class LoadIssue:
    path: str
    message: str


@dataclass
class Dataset:
    manifest: Manifest
    universities: dict[str, UniversityRecord] = field(default_factory=dict)
    departments: list[DepartmentRecord] = field(default_factory=list)
    labs: list[LabRecord] = field(default_factory=list)
    professors: list[ProfessorRecord] = field(default_factory=list)
    research_areas: dict[str, ResearchAreaRecord] = field(default_factory=dict)
    opportunities: list[OpportunityRecord] = field(default_factory=list)
    issues: list[LoadIssue] = field(default_factory=list)

    def add_research_area(self, area: ResearchAreaRecord) -> None:
        key = normalize_research_area_key(area.name)
        if not key:
            return
        existing = self.research_areas.get(key)
        if existing is None:
            self.research_areas[key] = ResearchAreaRecord(
                name=canonical_research_area_name(area.name),
                description=area.description,
                source_url=area.source_url,
            )
            return
        if existing.description is None and area.description:
            existing.description = area.description
        if existing.source_url is None and area.source_url:
            existing.source_url = area.source_url


def load_dataset() -> Dataset:
    issues: list[LoadIssue] = []
    manifest = _load_manifest(issues)
    dataset = Dataset(manifest=manifest, issues=issues)

    if manifest is None:
        return dataset

    enabled_ids = {item.id for item in manifest.universities if item.enabled}
    for item in manifest.universities:
        if not item.enabled:
            continue
        path = university_dir() / item.file
        record = _load_university_file(path, item.id, issues)
        if record:
            dataset.universities[record.id] = record

    dataset.departments = _load_record_list(
        department_dir(),
        "departments",
        DepartmentRecord,
        enabled_ids,
        issues,
    )
    dataset.labs = _load_record_list(
        lab_dir(),
        "labs",
        LabRecord,
        enabled_ids,
        issues,
    )
    dataset.professors = _load_record_list(
        professor_dir(),
        "professors",
        ProfessorRecord,
        enabled_ids,
        issues,
    )
    dataset.opportunities = _load_record_list(
        opportunity_dir(),
        "opportunities",
        OpportunityRecord,
        enabled_ids,
        issues,
        university_field="university",
        university_required=True,
    )

    _load_research_area_catalog(dataset, issues)
    for professor in dataset.professors:
        for area in professor.area_records():
            dataset.add_research_area(area)

    return dataset


def _load_manifest(issues: list[LoadIssue]) -> Manifest | None:
    path = manifest_path()
    if not path.exists():
        issues.append(LoadIssue(str(path), "Manifest file is missing."))
        return None
    try:
        payload = _read_json(path)
        return Manifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        issues.append(LoadIssue(str(path), f"Invalid manifest: {exc}"))
        return None


def _load_university_file(
    path: Path,
    expected_id: str,
    issues: list[LoadIssue],
) -> UniversityRecord | None:
    if not path.exists():
        issues.append(LoadIssue(str(path), f"Enabled university '{expected_id}' is missing its data file."))
        return None
    try:
        payload = _read_json(path)
        if isinstance(payload, list):
            issues.append(LoadIssue(str(path), "University file must be a JSON object, not an array."))
            return None
        record = UniversityRecord.model_validate(payload)
        if record.id != expected_id:
            issues.append(
                LoadIssue(str(path), f"University id '{record.id}' does not match manifest id '{expected_id}'.")
            )
        return record
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        issues.append(LoadIssue(str(path), f"Invalid university file: {exc}"))
        return None


def _load_record_list(
    directory: Path,
    key: str,
    model: type[T],
    enabled_ids: set[str],
    issues: list[LoadIssue],
    university_field: str = "university",
    university_required: bool = True,
) -> list[T]:
    records: list[T] = []
    if not directory.exists():
        issues.append(LoadIssue(str(directory), f"Missing data directory for {key}."))
        return records

    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_") or path.name == "manifest.json":
            continue
        try:
            payload = _read_json(path)
            items = _unwrap_list(payload, key)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            issues.append(LoadIssue(str(path), str(exc)))
            continue

        for index, item in enumerate(items):
            try:
                record = model.model_validate(item)
            except ValidationError as exc:
                issues.append(LoadIssue(str(path), f"Record {index}: {exc}"))
                continue

            university_id = getattr(record, university_field, None)
            if university_required and not university_id:
                issues.append(LoadIssue(str(path), f"Record {index} is missing a university reference."))
                continue
            if university_id and university_id not in enabled_ids:
                # Data for a university that is not enabled is ignored, not treated as an error.
                continue
            records.append(record)
    return records


def _load_research_area_catalog(dataset: Dataset, issues: list[LoadIssue]) -> None:
    path = research_area_dir() / "catalog.json"
    if not path.exists():
        return
    try:
        payload = _read_json(path)
        items = _unwrap_list(payload, "research_areas")
        for index, item in enumerate(items):
            if isinstance(item, str):
                dataset.add_research_area(ResearchAreaRecord(name=item))
                continue
            try:
                dataset.add_research_area(ResearchAreaRecord.model_validate(item))
            except ValidationError as exc:
                issues.append(LoadIssue(str(path), f"Research area {index}: {exc}"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        issues.append(LoadIssue(str(path), f"Invalid research area catalog: {exc}"))


def _unwrap_list(payload: Any, key: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if key in payload and isinstance(payload[key], list):
            return payload[key]
        if "items" in payload and isinstance(payload["items"], list):
            return payload["items"]
        raise ValueError(f"Expected a JSON array or an object with '{key}'.")
    raise ValueError("Expected JSON array or object.")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
