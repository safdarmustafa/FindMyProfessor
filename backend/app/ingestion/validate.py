from __future__ import annotations

from dataclasses import dataclass, field

from app.ingestion.dataset import Dataset
from app.ingestion.models import ProfessorRecord
from app.ingestion.normalize import identity_key, is_http_url, normalize_research_area_key


@dataclass
class ValidationIssue:
    entity: str
    record_id: str
    message: str


@dataclass
class EntityCounts:
    valid: int = 0
    invalid: int = 0
    duplicates: int = 0


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    counts: dict[str, EntityCounts] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return len(self.issues)

    def add(self, entity: str, record_id: str, message: str) -> None:
        self.issues.append(ValidationIssue(entity, record_id, message))
        self.counts.setdefault(entity, EntityCounts()).invalid += 1

    def mark_valid(self, entity: str) -> None:
        self.counts.setdefault(entity, EntityCounts()).valid += 1

    def mark_duplicate(self, entity: str) -> None:
        self.counts.setdefault(entity, EntityCounts()).duplicates += 1


def validate_dataset(dataset: Dataset) -> ValidationReport:
    report = ValidationReport()

    for issue in dataset.issues:
        report.add("files", issue.path, issue.message)

    if dataset.manifest is None:
        return report

    _validate_manifest(dataset, report)
    _validate_universities(dataset, report)
    _validate_departments(dataset, report)
    _validate_labs(dataset, report)
    _validate_research_areas(dataset, report)
    _validate_professors(dataset, report)
    _validate_opportunities(dataset, report)
    return report


def _validate_manifest(dataset: Dataset, report: ValidationReport) -> None:
    ids: set[str] = set()
    files: set[str] = set()
    for item in dataset.manifest.universities:
        if item.id in ids:
            report.add("manifest", item.id, "Duplicate university id in manifest.")
        ids.add(item.id)
        if item.file in files:
            report.add("manifest", item.id, f"Duplicate file name '{item.file}' in manifest.")
        files.add(item.file)
        if item.enabled and not item.name and item.id not in dataset.universities:
            report.add("manifest", item.id, "Enabled university has no name and no data file.")

    expected = dataset.manifest.expected_count
    actual = len(dataset.manifest.universities)
    if actual != expected:
        report.add(
            "manifest",
            "expected_count",
            f"Manifest expected_count is {expected} but {actual} universities are listed.",
        )


def _validate_universities(dataset: Dataset, report: ValidationReport) -> None:
    seen_names: set[str] = set()
    for record in dataset.universities.values():
        entity_id = record.id
        ok = True
        if not record.name:
            report.add("universities", entity_id, "name is required.")
            ok = False
        name_key = identity_key(record.name) if record.name else ""
        if name_key:
            if name_key in seen_names:
                report.add("universities", entity_id, f"Duplicate university name '{record.name}'.")
                report.mark_duplicate("universities")
                ok = False
            seen_names.add(name_key)
        ok = _check_urls(report, "universities", entity_id, record.website_url, record.source_url) and ok
        if not record.source_url:
            report.add("universities", entity_id, "source_url is required for verified university records.")
            ok = False
        if ok:
            report.mark_valid("universities")


def _validate_departments(dataset: Dataset, report: ValidationReport) -> None:
    seen: set[str] = set()
    for record in dataset.departments:
        ok = True
        if record.university not in dataset.universities:
            report.add("departments", record.id, f"Unknown university '{record.university}'.")
            ok = False
        if not record.name:
            report.add("departments", record.id, "name is required.")
            ok = False
        dup_key = identity_key(record.university, record.name or "")
        if dup_key in seen:
            report.add("departments", record.id, f"Duplicate department '{record.name}' for {record.university}.")
            report.mark_duplicate("departments")
            ok = False
        seen.add(dup_key)
        ok = _check_urls(report, "departments", record.id, record.website_url, record.source_url) and ok
        if not record.source_url:
            report.add("departments", record.id, "source_url is required for verified department records.")
            ok = False
        if ok:
            report.mark_valid("departments")


def _validate_labs(dataset: Dataset, report: ValidationReport) -> None:
    department_ids = {(item.university, item.id) for item in dataset.departments}
    seen: set[str] = set()
    for record in dataset.labs:
        ok = True
        if record.university not in dataset.universities:
            report.add("labs", record.id, f"Unknown university '{record.university}'.")
            ok = False
        if (record.university, record.department) not in department_ids:
            report.add(
                "labs",
                record.id,
                f"Unknown department '{record.department}' for university '{record.university}'.",
            )
            ok = False
        if not record.name:
            report.add("labs", record.id, "name is required.")
            ok = False
        dup_key = identity_key(record.university, record.department, record.name or "")
        if dup_key in seen:
            report.add("labs", record.id, f"Duplicate lab '{record.name}'.")
            report.mark_duplicate("labs")
            ok = False
        seen.add(dup_key)
        ok = _check_urls(report, "labs", record.id, record.website_url, record.source_url) and ok
        if not record.source_url:
            report.add("labs", record.id, "source_url is required for verified lab records.")
            ok = False
        if ok:
            report.mark_valid("labs")


def _validate_research_areas(dataset: Dataset, report: ValidationReport) -> None:
    for key, record in dataset.research_areas.items():
        ok = True
        if not record.name:
            report.add("research_areas", key, "name is required.")
            ok = False
        if record.source_url and not is_http_url(record.source_url):
            report.add("research_areas", record.name, "source_url must be an http(s) URL.")
            ok = False
        if ok:
            report.mark_valid("research_areas")


def _validate_professors(dataset: Dataset, report: ValidationReport) -> None:
    department_ids = {(item.university, item.id) for item in dataset.departments}
    lab_ids = {(item.university, item.id): item for item in dataset.labs}
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    seen_emails: set[str] = set()

    for record in dataset.professors:
        ok = True
        ident = f"{record.university}/{record.id}"
        if record.university not in dataset.universities:
            report.add("professors", ident, f"Unknown university '{record.university}'.")
            ok = False
        professor_key = f"{record.university}:{record.id}"
        if professor_key in seen_ids:
            report.add("professors", ident, "Duplicate professor id.")
            report.mark_duplicate("professors")
            ok = False
        seen_ids.add(professor_key)
        if not record.name:
            report.add("professors", ident, "name is required.")
            ok = False
        if record.department and (record.university, record.department) not in department_ids:
            report.add("professors", ident, f"Unknown department '{record.department}'.")
            ok = False
        if record.lab:
            lab = lab_ids.get((record.university, record.lab))
            if lab is None:
                report.add("professors", ident, f"Unknown lab '{record.lab}'.")
                ok = False
            elif record.department and lab.department != record.department:
                report.add(
                    "professors",
                    ident,
                    f"Lab '{record.lab}' belongs to department '{lab.department}', not '{record.department}'.",
                )
                ok = False
        if not record.department and not record.lab:
            report.add("professors", ident, "Professor needs a department or lab reference.")
            ok = False
        name_key = identity_key(record.university, record.name or "")
        if record.name and name_key in seen_names:
            report.add("professors", ident, f"Duplicate professor name '{record.name}' at {record.university}.")
            report.mark_duplicate("professors")
            ok = False
        if record.name:
            seen_names.add(name_key)
        if record.email:
            if record.email in seen_emails:
                report.add("professors", ident, f"Duplicate email '{record.email}'.")
                report.mark_duplicate("professors")
                ok = False
            seen_emails.add(record.email)
        ok = _check_urls(
            report,
            "professors",
            ident,
            record.website_url,
            record.source_url,
            record.linkedin_url,
        ) and ok
        if not record.source_url:
            report.add("professors", ident, "source_url is required for verified professor records.")
            ok = False
        for area in record.area_records():
            if not normalize_research_area_key(area.name):
                report.add("professors", ident, "research area name cannot be empty.")
                ok = False
        if ok:
            report.mark_valid("professors")


def _validate_opportunities(dataset: Dataset, report: ValidationReport) -> None:
    professors = {(item.university, item.id): item for item in dataset.professors}
    labs = {(item.university, item.id) for item in dataset.labs}
    seen: set[str] = set()

    for record in dataset.opportunities:
        ident = record.id or f"{record.university}:{record.opportunity_type}:{record.title or 'untitled'}"
        ok = True
        if not record.university:
            report.add("opportunities", ident, "university is required.")
            ok = False
        elif record.university not in dataset.universities:
            report.add("opportunities", ident, f"Unknown university '{record.university}'.")
            ok = False

        professor = None
        if record.professor:
            professor = _resolve_professor(
                record.university,
                record.professor,
                professors,
                dataset.professors,
            )
            if professor is None:
                report.add("opportunities", ident, f"Unknown professor '{record.professor}'.")
                ok = False
            elif professor.university != record.university:
                report.add(
                    "opportunities",
                    ident,
                    f"Professor '{record.professor}' does not belong to university '{record.university}'.",
                )
                ok = False

        if record.lab:
            if (record.university, record.lab) not in labs:
                report.add("opportunities", ident, f"Unknown lab '{record.lab}'.")
                ok = False

        dup_key = identity_key(
            record.university or "",
            record.professor or "",
            record.lab or "",
            record.opportunity_type,
            record.title or "",
        )
        if dup_key in seen:
            report.add(
                "opportunities",
                ident,
                "Duplicate opportunity for the same university/professor/lab/type/title.",
            )
            report.mark_duplicate("opportunities")
            ok = False
        seen.add(dup_key)
        ok = _check_urls(report, "opportunities", ident, record.official_url, record.source_url) and ok
        if not record.source_url and not record.official_url:
            report.add(
                "opportunities",
                ident,
                "source_url or official_url is required for verified opportunity records.",
            )
            ok = False
        if ok:
            report.mark_valid("opportunities")


def _resolve_professor(
    university: str | None,
    professor_id: str | None,
    by_pair: dict[tuple[str, str], ProfessorRecord],
    professors: list[ProfessorRecord],
) -> ProfessorRecord | None:
    if not professor_id:
        return None
    if university:
        return by_pair.get((university, professor_id))
    matches = [item for item in professors if item.id == professor_id]
    if len(matches) == 1:
        return matches[0]
    return None


def _check_urls(report: ValidationReport, entity: str, record_id: str, *urls: str | None) -> bool:
    ok = True
    for url in urls:
        if url is None:
            continue
        if not is_http_url(url):
            report.add(entity, record_id, f"Invalid URL '{url}'. Use http(s).")
            ok = False
    return ok
