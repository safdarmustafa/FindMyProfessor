from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


StudentSource = Literal["interest", "signal", "project", "publication"]
ProfessorSource = Literal["research_area_mapping"]


class MatchEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "shared_research_area",
        "artifact_research_area",
        "professor_summary_mentions_area",
        "university_opportunity",
    ]
    area_name: str | None = None
    student_source: StudentSource | None = None
    professor_source: ProfessorSource | None = None
    artifact_title: str | None = None
    excerpt: str | None = None
    opportunity_id: str | None = None
    title: str | None = None
    opportunity_type: str | None = None
    status: str | None = None
    university: str | None = None
    not_professor_specific: bool | None = None


def evidence_key(item: MatchEvidence) -> tuple[Any, ...]:
    return (
        item.type,
        item.area_name,
        item.student_source,
        item.professor_source,
        item.artifact_title,
        item.opportunity_id,
    )


def dedupe_evidence(items: list[MatchEvidence]) -> list[MatchEvidence]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[MatchEvidence] = []
    for item in items:
        key = evidence_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
