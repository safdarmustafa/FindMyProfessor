from __future__ import annotations

import re

from app.matching.models import MatchEvidence, dedupe_evidence
from app.matching.normalize import catalog_index, is_generic_area, normalize_label


def labels_in_text(text: str | None, catalog_names: list[str]) -> list[str]:
    if not text or not text.strip():
        return []
    catalog = catalog_index(catalog_names)
    found: list[str] = []
    seen: set[str] = set()
    for canonical in sorted(catalog.values(), key=lambda name: len(name), reverse=True):
        if not _label_occurs(text, canonical):
            continue
        key = normalize_label(canonical)
        if key in seen:
            continue
        seen.add(key)
        found.append(canonical)
    return found


def excerpt_for_label(text: str | None, label: str, max_len: int = 180) -> str | None:
    if not text or not label:
        return None
    match = _label_search(text, label)
    if not match:
        return None
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    snippet = text[start:end].strip()
    snippet = re.sub(r"\s+", " ", snippet)
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1].rstrip() + "…"
    return snippet


def _label_occurs(text: str, label: str) -> bool:
    return _label_search(text, label) is not None


def _label_search(text: str, label: str) -> re.Match[str] | None:
    pattern = r"(?<!\w)" + re.escape(label.strip()) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE)


def why_from_evidence(evidence: list[MatchEvidence]) -> list[str]:
    lines: list[str] = []
    for item in dedupe_evidence(evidence):
        if item.type == "shared_research_area" and item.area_name:
            if item.student_source == "interest":
                lines.append(f"{item.area_name} matches your explicit research interest.")
            elif item.student_source == "signal":
                lines.append(f"{item.area_name} matches a research signal from your CV.")
        elif item.type == "artifact_research_area" and item.area_name:
            kind = "project" if item.student_source == "project" else "publication"
            title = item.artifact_title or "an item on your CV"
            lines.append(f'Your {kind} "{title}" provides additional {item.area_name} evidence.')
        elif item.type == "professor_summary_mentions_area" and item.area_name:
            lines.append(f"Professor research summary also references {item.area_name}.")
        elif item.type == "university_opportunity" and item.title:
            status = item.status or "unknown"
            lines.append(
                f"University-wide opportunity (not professor-specific): {item.title} "
                f"(status: {status})."
            )
    return lines


def filter_generic_labels(names: list[str]) -> list[str]:
    return [name for name in names if not is_generic_area(name)]
