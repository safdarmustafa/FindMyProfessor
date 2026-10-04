from __future__ import annotations

from dataclasses import dataclass, field

from app.cv.extraction.schema import ExtractedStudentProfile, ProjectExtract, PublicationExtract
from app.matching.evidence import excerpt_for_label, labels_in_text, why_from_evidence
from app.matching.models import MatchEvidence, dedupe_evidence
from app.matching.normalize import (
    canonical_catalog_name,
    catalog_index,
    is_generic_area,
    normalize_label,
    scoring_labels,
)
from app.matching.taxonomy import RELATED_CREDIT, related_labels

MATCH_VERSION = "v2"

WEIGHTS = {
    "interests": 0.55,
    "signals": 0.20,
    "artifacts": 0.20,
    "corroboration": 0.05,
}

PRIORITY_HIGH = 80
PRIORITY_NORMAL = 50


@dataclass(frozen=True)
class ComponentScores:
    interests: float | None
    signals: float | None
    artifacts: float | None
    corroboration: float | None


@dataclass
class ProfessorMatchResult:
    score: int
    priority: str
    research_overlap: list[str]
    evidence: list[MatchEvidence]
    why: list[str]
    components: ComponentScores
    matched_areas: list[str]
    # (student label, professor label) pairs that earned partial credit as
    # close neighbours. Never part of research_overlap.
    related_areas: list[tuple[str, str]] = field(default_factory=list)


def priority_for_score(score: int) -> str:
    if score >= PRIORITY_HIGH:
        return "high"
    if score >= PRIORITY_NORMAL:
        return "normal"
    return "low"


def clamp_score(value: float) -> int:
    rounded = int(value + 0.5)
    return max(0, min(100, rounded))


def score_professor(
    *,
    student: ExtractedStudentProfile,
    professor_areas: list[str],
    catalog_names: list[str],
    research_summary: str | None = None,
) -> ProfessorMatchResult:
    catalog = catalog_index(catalog_names)
    professor_scoring = scoring_labels(professor_areas, catalog)
    professor_set = {normalize_label(name) for name in professor_scoring}
    professor_by_key = {normalize_label(name): name for name in professor_scoring}

    interest_labels = student_labels(student.research_interests, catalog_names)
    signal_labels = student_labels(student.research_signals, catalog_names)
    artifact_hits = _artifact_hits(student, catalog_names)
    artifact_labels = scoring_labels([hit.area_name for hit in artifact_hits if hit.area_name], catalog)

    interest_score = _coverage_score(interest_labels, professor_set) if interest_labels else None
    signal_score = _coverage_score(signal_labels, professor_set) if signal_labels else None
    artifact_score = _coverage_score(artifact_labels, professor_set) if artifact_labels else None

    matched = _ordered_union(
        _intersection(interest_labels, professor_set),
        _intersection(signal_labels, professor_set),
        _intersection(artifact_labels, professor_set),
    )
    related = _related_pairs(
        _ordered_union(interest_labels, signal_labels, artifact_labels),
        matched,
        professor_by_key,
    )

    corroboration_score = None
    corroborated: list[str] = []
    if matched and research_summary and research_summary.strip():
        for area in matched:
            if labels_in_text(research_summary, [area]):
                corroborated.append(area)
        corroboration_score = 100.0 * len(corroborated) / len(matched)

    components = ComponentScores(
        interests=interest_score,
        signals=signal_score,
        artifacts=artifact_score,
        corroboration=corroboration_score,
    )
    score = combine_components(components)
    evidence = _build_evidence(
        interest_labels=interest_labels,
        signal_labels=signal_labels,
        artifact_hits=artifact_hits,
        professor_set=professor_set,
        matched=matched,
        corroborated=corroborated,
        research_summary=research_summary,
    )
    overlap = _ordered_union(matched)
    why = why_from_evidence(evidence)
    for student_area, professor_area in related:
        why.append(f"{student_area} on your CV is closely related to this professor's work in {professor_area}.")
    return ProfessorMatchResult(
        score=score,
        priority=priority_for_score(score),
        research_overlap=overlap,
        evidence=evidence,
        why=why,
        components=components,
        matched_areas=matched,
        related_areas=related,
    )


def student_labels(values: list[str], catalog_names: list[str]) -> list[str]:
    """Resolve free-text student areas to catalog labels.

    An exact catalog name wins; otherwise the text is scanned for catalog
    names and aliases, so "NLP" or "LLMs for legal text" still resolve.
    Generic labels never count.
    """
    catalog = catalog_index(catalog_names)
    resolved: list[str] = []
    for value in values:
        canonical = canonical_catalog_name(value, catalog)
        resolved.extend([canonical] if canonical else labels_in_text(value, catalog_names))
    return [name for name in _ordered_union(resolved) if not is_generic_area(name)]


def combine_components(components: ComponentScores) -> int:
    available: list[tuple[str, float]] = []
    mapping = {
        "interests": components.interests,
        "signals": components.signals,
        "artifacts": components.artifacts,
        "corroboration": components.corroboration,
    }
    for name, value in mapping.items():
        if value is None:
            continue
        available.append((name, value))
    if not available:
        return 0
    weight_sum = sum(WEIGHTS[name] for name, _ in available)
    total = sum(WEIGHTS[name] / weight_sum * value for name, value in available)
    return clamp_score(total)


def _coverage_score(labels: list[str], professor_set: set[str]) -> float:
    """Share of the student's labels the professor covers.

    An exact match counts fully; a close neighbour counts RELATED_CREDIT.
    """
    if not labels:
        return 0.0
    credit = 0.0
    for name in labels:
        if normalize_label(name) in professor_set:
            credit += 1.0
        elif related_labels(name) & professor_set:
            credit += RELATED_CREDIT
    return 100.0 * credit / len(labels)


def _related_pairs(
    labels: list[str],
    matched: list[str],
    professor_by_key: dict[str, str],
) -> list[tuple[str, str]]:
    matched_keys = {normalize_label(name) for name in matched}
    pairs: list[tuple[str, str]] = []
    for name in labels:
        if normalize_label(name) in matched_keys:
            continue
        for key in sorted(related_labels(name)):
            if key in professor_by_key and key not in matched_keys:
                pairs.append((name, professor_by_key[key]))
                break
    return pairs


def _intersection(labels: list[str], professor_set: set[str]) -> list[str]:
    return [name for name in labels if normalize_label(name) in professor_set]


def _ordered_union(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for name in group:
            key = normalize_label(name)
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(name)
    return ordered


def _artifact_hits(student: ExtractedStudentProfile, catalog_names: list[str]) -> list[MatchEvidence]:
    hits: list[MatchEvidence] = []
    for project in student.projects:
        text = _project_text(project)
        for area in labels_in_text(text, catalog_names):
            hits.append(
                MatchEvidence(
                    type="artifact_research_area",
                    area_name=area,
                    student_source="project",
                    artifact_title=project.title,
                )
            )
    for publication in student.publications:
        text = _publication_text(publication)
        for area in labels_in_text(text, catalog_names):
            hits.append(
                MatchEvidence(
                    type="artifact_research_area",
                    area_name=area,
                    student_source="publication",
                    artifact_title=publication.title,
                )
            )
    return dedupe_evidence(hits)


def _project_text(project: ProjectExtract) -> str:
    parts = [project.title, project.description or "", project.research_relevance or ""]
    parts.extend(project.technologies)
    return "\n".join(part for part in parts if part)


def _publication_text(publication: PublicationExtract) -> str:
    return "\n".join(
        part
        for part in (
            publication.title,
            publication.venue or "",
            publication.publication_type or "",
        )
        if part
    )


def _build_evidence(
    *,
    interest_labels: list[str],
    signal_labels: list[str],
    artifact_hits: list[MatchEvidence],
    professor_set: set[str],
    matched: list[str],
    corroborated: list[str],
    research_summary: str | None,
) -> list[MatchEvidence]:
    items: list[MatchEvidence] = []
    for area in _intersection(interest_labels, professor_set):
        items.append(
            MatchEvidence(
                type="shared_research_area",
                area_name=area,
                student_source="interest",
                professor_source="research_area_mapping",
            )
        )
    for area in _intersection(signal_labels, professor_set):
        items.append(
            MatchEvidence(
                type="shared_research_area",
                area_name=area,
                student_source="signal",
                professor_source="research_area_mapping",
            )
        )
    for hit in artifact_hits:
        if hit.area_name and normalize_label(hit.area_name) in professor_set:
            items.append(hit)
    matched_keys = {normalize_label(name) for name in matched}
    for area in corroborated:
        if normalize_label(area) not in matched_keys:
            continue
        items.append(
            MatchEvidence(
                type="professor_summary_mentions_area",
                area_name=area,
                excerpt=excerpt_for_label(research_summary, area),
            )
        )
    return dedupe_evidence(items)
