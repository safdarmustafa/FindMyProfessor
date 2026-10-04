from __future__ import annotations

import re
from functools import lru_cache

from app.matching.models import MatchEvidence, dedupe_evidence
from app.matching.normalize import is_generic_area
from app.matching.taxonomy import label_patterns


def labels_in_text(text: str | None, catalog_names: list[str]) -> list[str]:
    """Catalog labels mentioned in `text`, by name or by a known alias.

    Ordered by where they first appear, so the student's own emphasis is kept.
    """
    if not text or not text.strip():
        return []
    return list(_labels_in_text(text, tuple(catalog_names)))


@lru_cache(maxsize=4096)
def _labels_in_text(text: str, catalog_names: tuple[str, ...]) -> tuple[str, ...]:
    hits: list[tuple[int, int, str]] = []
    for name, pattern in label_patterns(catalog_names):
        match = pattern.search(text)
        if match:
            hits.append((match.start(), -len(name), name))
    hits.sort()
    return tuple(name for _, _, name in hits)


def excerpt_for_label(text: str | None, label: str, max_len: int = 180) -> str | None:
    if not text or not label:
        return None
    match = _label_search(text, label)
    if not match:
        pattern = dict(label_patterns((label,))).get(label)
        match = pattern.search(text) if pattern else None
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
