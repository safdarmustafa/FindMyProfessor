from __future__ import annotations

import re

from app.cv.extraction.provider import ExtractionProvider
from app.cv.extraction.schema import (
    CertificationExtract,
    EducationExtract,
    ExperienceExtract,
    ExtractedStudentProfile,
    IdentityExtract,
    ProjectExtract,
    PublicationExtract,
    SkillExtract,
)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}(?!\w)"
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

HEADING_RE = re.compile(
    r"^(education|academic|research interests|interests|skills|technical skills|"
    r"experience|work experience|research experience|internships|"
    r"projects|publications|papers|certifications|certificates|"
    r"summary|profile|contact)\b[:\s]*$",
    re.I,
)

DEGREE_RE = re.compile(
    r"\b(Ph\.?D\.?|M\.?S\.?|M\.?Sc\.?|M\.?Tech\.?|M\.?Eng\.?|MBA|"
    r"B\.?S\.?|B\.?Sc\.?|B\.?Tech\.?|B\.?Eng\.?|B\.?A\.?|"
    r"Bachelor(?:'s)?|Master(?:'s)?|Doctorate)\b",
    re.I,
)

SKILL_CATALOG: list[tuple[str, str]] = [
    ("Python", "language"),
    ("Java", "language"),
    ("Kotlin", "language"),
    ("C++", "language"),
    ("C#", "language"),
    ("JavaScript", "language"),
    ("TypeScript", "language"),
    ("Go", "language"),
    ("Rust", "language"),
    ("R", "language"),
    ("MATLAB", "language"),
    ("SQL", "language"),
    ("TensorFlow", "ml_tool"),
    ("PyTorch", "ml_tool"),
    ("Keras", "ml_tool"),
    ("scikit-learn", "ml_tool"),
    ("Hugging Face", "ml_tool"),
    ("OpenCV", "ml_tool"),
    ("Pandas", "framework"),
    ("NumPy", "framework"),
    ("React", "framework"),
    ("FastAPI", "framework"),
    ("Django", "framework"),
    ("PostgreSQL", "database"),
    ("MySQL", "database"),
    ("MongoDB", "database"),
    ("AWS", "cloud"),
    ("GCP", "cloud"),
    ("Azure", "cloud"),
    ("Docker", "cloud"),
    ("Kubernetes", "cloud"),
    ("Git", "other"),
    ("Linux", "other"),
]


class HeuristicExtractionProvider(ExtractionProvider):
    def extract(self, cv_text: str, catalog_labels: list[str]) -> ExtractedStudentProfile:
        lines = [line.strip() for line in cv_text.splitlines()]
        sections = _split_sections(lines)
        identity = _identity(lines)
        education = _education(sections.get("education", []))
        interests = _explicit_interests(
            sections.get("research interests", []) + sections.get("interests", []),
            catalog_labels,
        )
        skills = _skills("\n".join(sections.get("skills", []) + sections.get("technical skills", [])) or cv_text)
        experience = _experience(
            sections.get("experience", [])
            + sections.get("work experience", [])
            + sections.get("research experience", [])
            + sections.get("internships", [])
        )
        projects = _projects(sections.get("projects", []))
        publications = _publications(sections.get("publications", []) + sections.get("papers", []))
        certifications = _certs(sections.get("certifications", []) + sections.get("certificates", []))
        signal_text = "\n".join(
            sections.get("projects", [])
            + sections.get("publications", [])
            + sections.get("experience", [])
            + sections.get("research experience", [])
        )
        signals = _catalog_mentions(signal_text, catalog_labels)
        signals = [item for item in signals if item not in interests]
        return ExtractedStudentProfile(
            identity=identity,
            education=education,
            research_interests=interests,
            research_signals=signals,
            skills=skills,
            experience=experience,
            projects=projects,
            publications=publications,
            certifications=certifications,
        )


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "summary"
    sections[current] = []
    for line in lines:
        if not line:
            continue
        match = HEADING_RE.match(line.lower().rstrip(":"))
        if match:
            current = match.group(1).lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _identity(lines: list[str]) -> IdentityExtract:
    blob = "\n".join(lines[:40])
    email = None
    found = EMAIL_RE.search(blob)
    if found:
        email = found.group(0)
    phone = None
    for match in PHONE_RE.finditer(blob):
        digits = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits) <= 15:
            phone = match.group(0).strip()
            break
    name = None
    for line in lines[:8]:
        if not line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if HEADING_RE.match(line.lower().rstrip(":")):
            continue
        if len(line) <= 80 and not DEGREE_RE.search(line):
            name = line
            break
    return IdentityExtract(name=name, email=email, phone=phone)


def _education(lines: list[str]) -> list[EducationExtract]:
    if not lines:
        return []
    blob = " ".join(lines)
    degree = None
    match = DEGREE_RE.search(blob)
    if match:
        degree = match.group(0)
    years = [int(y.group(0)) for y in YEAR_RE.finditer(blob)]
    field = None
    field_match = re.search(
        r"in ([A-Za-z][A-Za-z0-9&/\-\s]{2,60})",
        blob,
        re.I,
    )
    if field_match:
        field = field_match.group(1).strip(" .,")
    institution = None
    uni_match = re.search(
        r"(University|Institute|College|École|Ecole)[^,\n]{0,80}",
        blob,
        re.I,
    )
    if uni_match:
        institution = uni_match.group(0).strip(" .,")
    return [
        EducationExtract(
            degree=degree,
            field_of_study=field,
            institution=institution,
            graduation_year=max(years) if years else None,
        )
    ]


def _explicit_interests(lines: list[str], catalog_labels: list[str]) -> list[str]:
    if not lines:
        return []
    blob = "\n".join(lines)
    found: list[str] = []
    for label in catalog_labels:
        if _contains_label(blob, label) and label not in found:
            found.append(label)
    if found:
        return found
    items: list[str] = []
    for line in lines:
        for part in re.split(r"[,;•|/]| and ", line):
            item = part.strip(" -•\t")
            if 2 <= len(item) <= 60 and item.lower() not in {"research interests", "interests"}:
                items.append(item)
    return items[:12]


def _catalog_mentions(text: str, catalog_labels: list[str]) -> list[str]:
    found: list[str] = []
    for label in catalog_labels:
        if _contains_label(text, label) and label not in found:
            found.append(label)
    return found


def _contains_label(text: str, label: str) -> bool:
    if not text or not label:
        return False
    pattern = r"(?<!\w)" + re.escape(label) + r"(?!\w)"
    return re.search(pattern, text, re.I) is not None


def _skills(text: str) -> list[SkillExtract]:
    found: list[SkillExtract] = []
    seen: set[str] = set()
    for name, category in SKILL_CATALOG:
        if name.lower() == "r":
            if not re.search(r"(?<!\w)R(?!\w)", text):
                continue
        elif not _contains_label(text, name):
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        found.append(SkillExtract(name=name, category=category))  # type: ignore[arg-type]
    return found


def _experience(lines: list[str]) -> list[ExperienceExtract]:
    items: list[ExperienceExtract] = []
    for line in lines:
        if len(line) < 4:
            continue
        kind = None
        lower = line.lower()
        if "intern" in lower:
            kind = "internship"
        elif "research" in lower:
            kind = "research"
        years = [int(m.group(0)) for m in YEAR_RE.finditer(line)]
        items.append(
            ExperienceExtract(
                role=line[:120],
                kind=kind,  # type: ignore[arg-type]
                description=line,
                start_year=min(years) if years else None,
                end_year=max(years) if len(years) > 1 else None,
            )
        )
        if len(items) >= 8:
            break
    return items


def _projects(lines: list[str]) -> list[ProjectExtract]:
    items: list[ProjectExtract] = []
    current: ProjectExtract | None = None
    for line in lines:
        if not line:
            continue
        if line.startswith(("-", "•", "*")) and current:
            extra = line.lstrip("-•* ").strip()
            current.description = (
                f"{current.description} {extra}".strip() if current.description else extra
            )
            continue
        if current:
            items.append(current)
        current = ProjectExtract(title=line[:160], description=None)
        if len(items) >= 8:
            break
    if current and len(items) < 8:
        items.append(current)
    return items


def _publications(lines: list[str]) -> list[PublicationExtract]:
    items: list[PublicationExtract] = []
    for line in lines:
        if len(line) < 8:
            continue
        years = [int(m.group(0)) for m in YEAR_RE.finditer(line)]
        items.append(PublicationExtract(title=line[:300], year=years[-1] if years else None))
        if len(items) >= 8:
            break
    return items


def _certs(lines: list[str]) -> list[CertificationExtract]:
    items: list[CertificationExtract] = []
    for line in lines:
        if len(line) < 3:
            continue
        years = [int(m.group(0)) for m in YEAR_RE.finditer(line)]
        items.append(CertificationExtract(name=line[:160], year=years[-1] if years else None))
        if len(items) >= 8:
            break
    return items
