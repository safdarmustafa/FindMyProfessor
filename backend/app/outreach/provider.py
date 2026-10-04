from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.cv.extraction.schema import ExtractedStudentProfile


@dataclass(frozen=True)
class ProfessorContext:
    """Verified professor data passed to the email generation provider."""
    professor_id: str
    name: str
    title: str | None
    email: str | None
    university_name: str | None
    department_name: str | None
    lab_name: str | None
    research_areas: list[str]
    research_summary: str | None


@dataclass(frozen=True)
class MatchContext:
    """Deterministic Phase 3.2 match evidence — never recalculated here."""
    research_score: int
    research_overlap: list[str]          # verified shared areas only
    shared_interest_areas: list[str]     # from explicit research_interests
    artifact_evidence: list[ArtifactEvidence]  # projects / publications
    corroborated_areas: list[str]        # professor summary confirmed these
    # (student area, professor area) close neighbours — not shared areas
    related_areas: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactEvidence:
    kind: str   # "project" | "publication"
    title: str
    area_name: str


@dataclass(frozen=True)
class OpportunityContext:
    """University-level opportunity info — only included when explicitly requested."""
    opportunity_id: str
    title: str | None
    opportunity_type: str | None
    status: str
    university_name: str | None
    not_professor_specific: bool  # always True for current data


@dataclass
class EmailDraftOutput:
    subject: str
    body: str
    evidence_used: list[str]        # human-readable list of evidence lines
    generation_provider: str


class EmailGenerationProvider(ABC):
    """
    Abstract email-generation provider.

    Implementations must:
    - Use ONLY the supplied verified facts.
    - Not invent research topics, publications, papers, openings, or deadlines.
    - Not add claims about reading a professor's work unless a specific
      artifact_evidence entry with that title is supplied.
    """

    @abstractmethod
    def generate(
        self,
        *,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        opportunity: OpportunityContext | None = None,
    ) -> EmailDraftOutput:
        raise NotImplementedError
