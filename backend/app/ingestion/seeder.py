from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from postgrest.exceptions import APIError

from app.ingestion.dataset import Dataset
from app.ingestion.models import DepartmentRecord, LabRecord, OpportunityRecord, ProfessorRecord, UniversityRecord
from app.ingestion.normalize import identity_key, normalize_research_area_key


UNIVERSITY_COLUMNS = (
    "name",
    "country",
    "city",
    "website_url",
    "description",
    "is_active",
)
DEPARTMENT_COLUMNS = ("university_id", "name", "website_url", "description")
LAB_COLUMNS = ("department_id", "name", "website_url", "description", "research_summary")
PROFESSOR_COLUMNS = (
    "lab_id",
    "department_id",
    "name",
    "title",
    "email",
    "website_url",
    "linkedin_url",
    "biography",
    "research_summary",
    "recent_work_summary",
    "recruiting_status",
    "internship_available",
    "ra_available",
    "masters_available",
    "phd_available",
    "is_active",
)
RESEARCH_AREA_COLUMNS = ("name", "description")
OPPORTUNITY_COLUMNS = (
    "professor_id",
    "lab_id",
    "university_id",
    "title",
    "opportunity_type",
    "description",
    "eligibility",
    "international_eligible",
    "undergraduate_eligible",
    "funding_type",
    "stipend_amount",
    "tuition_coverage",
    "accommodation_coverage",
    "travel_coverage",
    "application_deadline",
    "start_date",
    "official_url",
    "status",
)


@dataclass
class EntityStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    messages: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors += 1
        self.messages.append(message)


class SeedResult:
    def __init__(self) -> None:
        self.stats = {
            "universities": EntityStats(),
            "departments": EntityStats(),
            "labs": EntityStats(),
            "research_areas": EntityStats(),
            "professors": EntityStats(),
            "professor_research_areas": EntityStats(),
            "opportunities": EntityStats(),
        }

    def print(self) -> None:
        labels = [
            ("universities", "Universities"),
            ("departments", "Departments"),
            ("labs", "Labs"),
            ("research_areas", "Research Areas"),
            ("professors", "Professors"),
            ("professor_research_areas", "Professor research areas"),
            ("opportunities", "Opportunities"),
        ]
        for key, title in labels:
            item = self.stats[key]
            print(title)
            print(f"  inserted: {item.inserted}")
            print(f"  updated: {item.updated}")
            print(f"  skipped: {item.skipped}")
            print(f"  errors: {item.errors}")
            for message in item.messages:
                print(f"  - {message}")
            print()


class Seeder:
    def __init__(self, client: Any, dataset: Dataset) -> None:
        self.client = client
        self.dataset = dataset
        self.result = SeedResult()
        self.university_ids: dict[str, str] = {}
        self.department_ids: dict[tuple[str, str], str] = {}
        self.lab_ids: dict[tuple[str, str], str] = {}
        self.professor_ids: dict[tuple[str, str], str] = {}
        self.research_area_ids: dict[str, str] = {}

    def run(self) -> SeedResult:
        self._seed_universities()
        self._seed_departments()
        self._seed_labs()
        self._seed_research_areas()
        self._seed_professors()
        self._seed_professor_research_areas()
        self._seed_opportunities()
        return self.result

    def _seed_universities(self) -> None:
        stats = self.result.stats["universities"]
        existing = self._select("universities", "id, name, country, city, website_url, description, is_active")
        by_name = {identity_key(row["name"]): row for row in existing if row.get("name")}
        for record in self.dataset.universities.values():
            payload = _payload(record, UNIVERSITY_COLUMNS)
            match = by_name.get(identity_key(record.name))
            db_id = self._upsert("universities", payload, match, stats, record.id)
            if db_id:
                self.university_ids[record.id] = db_id

    def _seed_departments(self) -> None:
        stats = self.result.stats["departments"]
        existing = self._select("departments", "id, university_id, name, website_url, description")
        by_key = {
            (row["university_id"], identity_key(row["name"])): row
            for row in existing
            if row.get("name") and row.get("university_id")
        }
        for record in self.dataset.departments:
            university_id = self.university_ids.get(record.university)
            if not university_id:
                stats.error(f"{record.id}: university '{record.university}' was not seeded.")
                continue
            payload = _payload(record, DEPARTMENT_COLUMNS, university_id=university_id)
            match = by_key.get((university_id, identity_key(record.name)))
            db_id = self._upsert("departments", payload, match, stats, record.id)
            if db_id:
                self.department_ids[(record.university, record.id)] = db_id

    def _seed_labs(self) -> None:
        stats = self.result.stats["labs"]
        existing = self._select("labs", "id, department_id, name, website_url, description, research_summary")
        by_key = {
            (row["department_id"], identity_key(row["name"])): row
            for row in existing
            if row.get("name") and row.get("department_id")
        }
        for record in self.dataset.labs:
            department_id = self.department_ids.get((record.university, record.department))
            if not department_id:
                stats.error(f"{record.id}: department '{record.department}' was not seeded.")
                continue
            payload = _payload(record, LAB_COLUMNS, department_id=department_id)
            match = by_key.get((department_id, identity_key(record.name)))
            db_id = self._upsert("labs", payload, match, stats, record.id)
            if db_id:
                self.lab_ids[(record.university, record.id)] = db_id

    def _seed_research_areas(self) -> None:
        stats = self.result.stats["research_areas"]
        existing = self._select("research_areas", "id, name, description")
        by_key = {
            normalize_research_area_key(row["name"]): row
            for row in existing
            if row.get("name")
        }
        for key, record in self.dataset.research_areas.items():
            payload = _payload(record, RESEARCH_AREA_COLUMNS)
            match = by_key.get(key)
            db_id = self._upsert("research_areas", payload, match, stats, record.name)
            if db_id:
                self.research_area_ids[key] = db_id

    def _seed_professors(self) -> None:
        stats = self.result.stats["professors"]
        existing = self._select(
            "professors",
            "id, department_id, lab_id, name, title, email, website_url, linkedin_url, "
            "biography, research_summary, recent_work_summary, recruiting_status, "
            "internship_available, ra_available, masters_available, phd_available, is_active",
        )
        by_email = {row["email"].casefold(): row for row in existing if row.get("email")}
        by_name = {
            (row.get("department_id"), identity_key(row["name"])): row
            for row in existing
            if row.get("name")
        }
        for record in self.dataset.professors:
            department_id = (
                self.department_ids.get((record.university, record.department))
                if record.department
                else None
            )
            lab_id = self.lab_ids.get((record.university, record.lab)) if record.lab else None
            if record.department and not department_id:
                stats.error(f"{record.id}: department '{record.department}' was not seeded.")
                continue
            if record.lab and not lab_id:
                stats.error(f"{record.id}: lab '{record.lab}' was not seeded.")
                continue
            payload = _payload(
                record,
                PROFESSOR_COLUMNS,
                department_id=department_id,
                lab_id=lab_id,
            )
            match = None
            if record.email:
                match = by_email.get(record.email.casefold())
            if match is None and department_id:
                match = by_name.get((department_id, identity_key(record.name)))
            if match is None and lab_id:
                match = next(
                    (
                        row
                        for row in existing
                        if row.get("lab_id") == lab_id
                        and identity_key(row.get("name") or "") == identity_key(record.name)
                    ),
                    None,
                )
            db_id = self._upsert("professors", payload, match, stats, record.id)
            if db_id:
                self.professor_ids[(record.university, record.id)] = db_id

    def _seed_professor_research_areas(self) -> None:
        stats = self.result.stats["professor_research_areas"]
        existing = self._select("professor_research_areas", "professor_id, research_area_id")
        existing_pairs = {
            (row["professor_id"], row["research_area_id"])
            for row in existing
            if row.get("professor_id") and row.get("research_area_id")
        }
        for professor in self.dataset.professors:
            professor_id = self.professor_ids.get((professor.university, professor.id))
            if not professor_id:
                continue
            for area in professor.area_records():
                area_id = self.research_area_ids.get(normalize_research_area_key(area.name))
                if not area_id:
                    stats.error(f"{professor.id}: research area '{area.name}' was not seeded.")
                    continue
                pair = (professor_id, area_id)
                if pair in existing_pairs:
                    stats.skipped += 1
                    continue
                try:
                    self.client.table("professor_research_areas").insert(
                        {"professor_id": professor_id, "research_area_id": area_id}
                    ).execute()
                    stats.inserted += 1
                    existing_pairs.add(pair)
                except APIError as exc:
                    stats.error(f"{professor.id}/{area.name}: {_db_error(exc)}")

    def _seed_opportunities(self) -> None:
        stats = self.result.stats["opportunities"]
        existing = self._select(
            "opportunities",
            "id, professor_id, lab_id, university_id, title, opportunity_type, description, "
            "eligibility, international_eligible, undergraduate_eligible, funding_type, "
            "stipend_amount, tuition_coverage, accommodation_coverage, travel_coverage, "
            "application_deadline, start_date, official_url, status",
        )
        by_key = {
            identity_key(
                row.get("university_id") or "",
                row.get("professor_id") or "",
                row.get("lab_id") or "",
                row.get("opportunity_type") or "",
                row.get("title") or "",
            ): row
            for row in existing
        }
        for record in self.dataset.opportunities:
            university_id = self.university_ids.get(record.university)
            if not university_id:
                stats.error(f"{record.id or record.opportunity_type}: university '{record.university}' was not seeded.")
                continue

            professor_id = None
            if record.professor:
                professor_id = self.professor_ids.get((record.university, record.professor))
                if not professor_id:
                    stats.error(f"{record.id or record.professor}: professor was not seeded.")
                    continue

            lab_id = None
            if record.lab:
                lab_id = self.lab_ids.get((record.university, record.lab))
                if not lab_id:
                    stats.error(f"{record.id or record.lab}: lab was not seeded.")
                    continue

            payload = _payload(
                record,
                OPPORTUNITY_COLUMNS,
                professor_id=professor_id,
                lab_id=lab_id,
                university_id=university_id,
            )
            match = by_key.get(
                identity_key(
                    university_id,
                    professor_id or "",
                    lab_id or "",
                    record.opportunity_type,
                    record.title or "",
                )
            )
            self._upsert(
                "opportunities",
                payload,
                match,
                stats,
                record.id or f"{record.university}:{record.opportunity_type}",
            )

    def _upsert(
        self,
        table: str,
        payload: dict[str, Any],
        match: dict[str, Any] | None,
        stats: EntityStats,
        label: str,
    ) -> str | None:
        try:
            if match:
                if _same_payload(match, payload):
                    stats.skipped += 1
                    return match["id"]
                response = (
                    self.client.table(table)
                    .update(payload)
                    .eq("id", match["id"])
                    .execute()
                )
                stats.updated += 1
                row = (response.data or [match])[0]
                return row.get("id") or match["id"]
            response = self.client.table(table).insert(payload).execute()
            stats.inserted += 1
            if not response.data:
                stats.error(f"{label}: insert returned no row. Check table write permissions.")
                return None
            return response.data[0]["id"]
        except APIError as exc:
            stats.error(f"{label}: {_db_error(exc)}")
            return None

    def _select(self, table: str, columns: str) -> list[dict[str, Any]]:
        try:
            response = self.client.table(table).select(columns).execute()
            return response.data or []
        except APIError as exc:
            self.result.stats[table if table in self.result.stats else "universities"].error(
                f"Could not read {table}: {_db_error(exc)}"
            )
            return []


def _payload(record: Any, columns: tuple[str, ...], **overrides: Any) -> dict[str, Any]:
    data = record.model_dump() if hasattr(record, "model_dump") else dict(record)
    data.update(overrides)
    payload: dict[str, Any] = {}
    for column in columns:
        if column not in data:
            continue
        value = data[column]
        if value is None:
            continue
        if isinstance(value, date):
            value = value.isoformat()
        if column == "stipend_amount" and isinstance(value, str):
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                pass
        payload[column] = value
    return payload


def _same_payload(existing: dict[str, Any], payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        if key not in existing:
            return False
        if _normalize_compare(existing.get(key)) != _normalize_compare(value):
            return False
    return True


def _normalize_compare(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _db_error(exc: APIError) -> str:
    message = exc.message or str(exc)
    lowered = message.lower()
    if "row-level security" in lowered or "permission" in lowered or "not allowed" in lowered:
        return (
            f"{message} Write access is required. "
            "Set SUPABASE_SERVICE_ROLE_KEY in .env for seeding (API can keep using the publishable key)."
        )
    return message
