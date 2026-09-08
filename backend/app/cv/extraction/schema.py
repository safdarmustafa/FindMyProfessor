from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IdentityExtract(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class EducationExtract(BaseModel):
    degree: str | None = None
    field_of_study: str | None = None
    institution: str | None = None
    country: str | None = None
    graduation_year: int | None = None
    current_semester: str | None = None


class SkillExtract(BaseModel):
    name: str
    category: Literal[
        "language",
        "framework",
        "ml_tool",
        "database",
        "cloud",
        "other",
    ] = "other"


class ExperienceExtract(BaseModel):
    role: str | None = None
    organization: str | None = None
    kind: Literal["internship", "research", "work", "other"] | None = None
    description: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class ProjectExtract(BaseModel):
    title: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    research_relevance: str | None = None


class PublicationExtract(BaseModel):
    title: str
    venue: str | None = None
    year: int | None = None
    authors: str | None = None
    publication_type: str | None = None


class CertificationExtract(BaseModel):
    name: str
    issuer: str | None = None
    year: int | None = None


class ExtractedStudentProfile(BaseModel):
    identity: IdentityExtract = Field(default_factory=IdentityExtract)
    education: list[EducationExtract] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    research_signals: list[str] = Field(default_factory=list)
    skills: list[SkillExtract] = Field(default_factory=list)
    experience: list[ExperienceExtract] = Field(default_factory=list)
    projects: list[ProjectExtract] = Field(default_factory=list)
    publications: list[PublicationExtract] = Field(default_factory=list)
    certifications: list[CertificationExtract] = Field(default_factory=list)
