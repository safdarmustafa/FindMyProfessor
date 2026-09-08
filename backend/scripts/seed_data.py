"""FindMyProfessor data ingestion CLI.

Reads verified JSON from data/, validates it, and optionally upserts into Supabase.

source_url is required in seed files and is kept as local source metadata.
It is not written to Supabase because those tables do not currently have source_url columns.

Usage (from the repository root):

    python backend/scripts/seed_data.py --report
    python backend/scripts/seed_data.py --dry-run
    python backend/scripts/seed_data.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

from app.ingestion.dataset import load_dataset
from app.ingestion.report import render_report
from app.ingestion.seeder import SeedResult, Seeder
from app.ingestion.validate import ValidationReport, validate_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and seed the 30-university dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Validate only. Do not write to Supabase.")
    parser.add_argument("--report", action="store_true", help="Show coverage for the 30 configured universities.")
    args = parser.parse_args(argv)

    dataset = load_dataset()
    report = validate_dataset(dataset)

    want_report = args.report
    want_dry_run = args.dry_run
    want_seed = not args.dry_run and not args.report

    if want_report:
        print(render_report(dataset))

    if want_dry_run or want_seed:
        _print_validation(report, dry_run=want_dry_run)

    if want_dry_run:
        _print_seed_counts(dry_run=True, report=report)
        print("Dry run complete. Supabase was not modified.")
        return 1 if report.error_count else 0

    if want_seed:
        if report.error_count:
            print("Seeding aborted because validation failed.")
            return 1
        client = _supabase_client()
        result = Seeder(client, dataset).run()
        result.print()
        print("Seed complete. Only verified local seed files were written.")
        return 1 if any(item.errors for item in result.stats.values()) else 0

    return 0


def _print_validation(report: ValidationReport, dry_run: bool) -> None:
    mode = "dry-run" if dry_run else "seed"
    print(f"Mode: {mode}")
    print()
    print("Validation")
    entities = [
        "files",
        "manifest",
        "universities",
        "departments",
        "labs",
        "research_areas",
        "professors",
        "opportunities",
    ]
    for entity in entities:
        counts = report.counts.get(entity)
        if counts is None and entity not in {"files", "manifest"}:
            print(f"  {entity}: 0 valid, 0 invalid, 0 duplicates")
            continue
        if counts is None:
            continue
        print(
            f"  {entity}: {counts.valid} valid, {counts.invalid} invalid, {counts.duplicates} duplicates"
        )
    print(f"  issues: {report.error_count}")
    for issue in report.issues:
        print(f"  - [{issue.entity}] {issue.record_id}: {issue.message}")
    print()


def _print_seed_counts(dry_run: bool, report: ValidationReport) -> None:
    result = SeedResult()
    mapping = {
        "universities": "universities",
        "departments": "departments",
        "labs": "labs",
        "research_areas": "research_areas",
        "professors": "professors",
        "opportunities": "opportunities",
    }
    for key, entity in mapping.items():
        counts = report.counts.get(entity)
        result.stats[key].errors = counts.invalid if counts else 0
        result.stats[key].skipped = counts.duplicates if counts else 0
    result.stats["professor_research_areas"].errors = 0
    result.print()
    if dry_run:
        print("inserted/updated remain 0 because this was a dry run.")
        print()


def _supabase_client():
    load_dotenv(ROOT_DIR / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit("Supabase environment variables are not configured.")
    from supabase import create_client

    return create_client(url, key)


if __name__ == "__main__":
    raise SystemExit(main())
