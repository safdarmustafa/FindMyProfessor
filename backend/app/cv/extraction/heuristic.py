from __future__ import annotations

"""
Rule-based CV parser used when no LLM is configured.

Real CVs exported from Word/LaTeX/Canva vary a lot, so the parser is
deliberately tolerant about layout:
- section headings in many wordings ("RESEARCH INTEREST", "PUBLICATIONS /
  CONFERENCES", "Skills & Interests"), any case, with or without a colon;
- bullets from symbol fonts (U+F0B7 "", "●", "➢", ...) as well as "-", "*";
- entries that wrap over several lines (a wrapped line is joined back onto
  the bullet it belongs to instead of becoming a new "project");
- numbered citations whose quoted title spans lines.
It never invents anything: a field it cannot read stays empty.
"""

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
from app.matching.evidence import labels_in_text

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}(?!\w)"
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_RANGE_RE = re.compile(
    rf"(?:{_MONTH}\s+)?(?:19|20)\d{{2}}"
    rf"(?:\s*(?:-|–|—|to)\s*(?:(?:{_MONTH}\s+)?(?:19|20)\d{{2}}|present|current|now|ongoing))?",
    re.I,
)

# Bullet glyphs seen in exported CVs, including private-use symbol-font ones.
BULLET_RE = re.compile(
    "^[\\-*•●○◦▪▫■□►▶➢➤✓✔·‣⁃\uf0b7\uf0a7\uf0d8\uf076\uf0fc\uf0a8\uf02d\uf06e]+\\s*"
)
NUMBERED_RE = re.compile(r"^\(?\d{1,2}[.)]\s+")

SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (key, re.compile(rf"(?:{pattern})", re.I))
    for key, pattern in [
        ("research interests", r"(?:research )?(?:interests?|areas? of interests?|research areas?|research focus)"),
        ("skills", r"(?:technical |key |core )?skills?(?: (?:and )?(?:interests?|tools|technologies|abilities|expertise))?"
                   r"|technologies|tools(?: and technologies)?|technical expertise"),
        ("education", r"(?:education(?:al)?(?: background| details| qualifications?)?|academics?"
                      r"|academic (?:background|qualifications?|details)|qualifications?)"),
        ("experience", r"(?:(?:work|professional|research|industry|relevant|internship) )?experiences?"
                       r"(?: (?:and )?internships?)?|internships?(?: (?:and )?(?:work )?experiences?)?"
                       r"|employment(?: history)?|work history"),
        ("projects", r"(?:(?:academic|personal|selected|key|research|technical|major) )?projects?"),
        ("publications", r"(?:selected |research |conference )?(?:publications?|papers)"
                         r"(?: (?:and )?(?:conferences?|presentations?|preprints?))?"),
        ("certifications", r"certifications?|certificates?|courses|licen[cs]es(?: and certifications)?"
                           r"|online courses"),
        ("other", r"(?:awards?|honou?rs|achievements?|scholarships?)(?: (?:and )?(?:awards?|achievements?|honou?rs))?"
                  r"|volunt\w*.*|leadership.*|extra ?curricular.*|activities|references?|referees?"
                  r"|details of referees?|languages?|hobbies|positions? of responsibility|community.*"
                  r"|other details|additional (?:details|information)|personal (?:details|information)"),
        ("summary", r"summary|profile|objective|about(?: me)?|professional summary|career objective"),
        ("contact", r"contact(?: details| information)?"),
    ]
]

DEGREE_RE = re.compile(
    r"\b(?:(?:Bachelor|Master)(?:'s)?\s+of\s+[A-Z][a-z]+(?:\s+(?:in\s+)?[A-Z][a-z]+)?|"
    r"Ph\.?D\.?|M\.?S\.?|M\.?Sc\.?|M\.?Tech\.?|M\.?Eng\.?|MBA|"
    r"B\.?S\.?|B\.?Sc\.?|B\.?Tech\.?|B\.?Eng\.?|B\.?A\.?|B\.?E\.?|"
    r"Bachelor(?:'s)?|Master(?:'s)?|Doctorate)(?![\w])",
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


# Bump whenever parsing rules change: stored CVs parsed by an older version
# (and not edited by hand) are re-read automatically (services/cv.py).
PARSER_VERSION = 3


class HeuristicExtractionProvider(ExtractionProvider):
    def extract(self, cv_text: str, catalog_labels: list[str]) -> ExtractedStudentProfile:
        lines = [_normalize_line(line) for line in cv_text.splitlines()]
        sections = _split_sections(lines)
        identity = _identity(lines)
        education = _education(sections.get("education", []))
        interests = _explicit_interests(
            [_strip_bullet(line) for line in sections.get("research interests", [])],
            catalog_labels,
        )
        skills = _skills("\n".join(sections.get("skills", [])) or cv_text)
        experience = _experience(sections.get("experience", []))
        projects = _projects(sections.get("projects", []))
        publications = _publications(sections.get("publications", []))
        certifications = _certs(sections.get("certifications", []))
        signal_text = "\n".join(
            sections.get("projects", [])
            + sections.get("publications", [])
            + sections.get("experience", [])
            + [_profile_summary(lines)]
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


# ---------------------------------------------------------------------------
# Lines, bullets, sections
# ---------------------------------------------------------------------------

def _normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ").replace("_", " ").strip()
    # Symbol/Wingdings fonts export as private-use code points. A leading one
    # is a bullet glyph; inside text, U+F020-F07E are just ASCII shifted by
    # 0xF000 ("\uf049\uf042\uf04d" is "IBM"); anything else is dropped.
    if line and "\ue000" <= line[0] <= "\uf8ff":
        line = "\u2022 " + line[1:]
    if re.fullmatch(r"[\s\u2022\u25cf\u25cb\u25e6\u25aa\u25a0\u25ba\u27a2\u27a4\u2713\u2714\u00b7*-]*", line):
        return ""  # a bullet glyph on its own line
    line = "".join(
        chr(ord(c) - 0xF000) if "\uf020" <= c <= "\uf07e" else ("" if "\ue000" <= c <= "\uf8ff" else c)
        for c in line
    )
    return re.sub(r"[ \t]+", " ", line).strip()


def _join_bullets(bullets: list[str]) -> str:
    """Join bullet points into prose, keeping each one a separate sentence."""
    parts = [b.strip() for b in bullets if b.strip()]
    return _fix_spacing(" ".join(p if p.endswith((".", "!", "?", ";")) else p + "." for p in parts))


def _is_bullet(line: str) -> bool:
    return bool(BULLET_RE.match(line)) and bool(_strip_bullet(line))


def _strip_bullet(line: str) -> str:
    return BULLET_RE.sub("", line, count=1).strip()


def _profile_summary(lines: list[str]) -> str:
    """
    The short professional summary that follows the name/contact block
    ("B.Tech in CS with experience in AI/ML ... AI agents on top of LLMs").
    """
    email_index = next((i for i, line in enumerate(lines) if EMAIL_RE.search(line)), None)
    if email_index is None:
        return ""
    collected: list[str] = []
    for line in lines[email_index + 1:email_index + 15]:
        if not line:
            continue
        if _heading_key(line):
            break
        if _CONTACT_LINE_RE.search(line) or PHONE_RE.search(line):
            continue
        collected.append(line)
    return " ".join(collected)


def _heading_key(line: str) -> str | None:
    raw = line.strip().rstrip(":").strip()
    if not raw or len(raw) > 60 or ":" in raw or raw.endswith("."):
        return None
    words = re.findall(r"[A-Za-z]+", raw)
    if not 1 <= len(words) <= 6:
        return None
    text = " ".join(w.lower() for w in words)
    for key, pattern in SECTION_PATTERNS:
        if pattern.fullmatch(text):
            return key
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"summary": []}
    current = "summary"
    for line in lines:
        if not line:
            continue
        key = _heading_key(line)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _entries(lines: list[str]) -> list[dict[str, list[str]]]:
    """
    Group a section into entries of header lines followed by bullets.

    A non-bullet line after bullets is treated as the wrapped tail of the last
    bullet unless it clearly starts a new entry (it carries dates, or it is a
    short title followed by a bullet).
    """
    entries: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] | None = None
    for index, line in enumerate(lines):
        if _is_bullet(line) or (NUMBERED_RE.match(line) and current and current["bullets"]):
            if current is None:
                current = {"header": [], "bullets": []}
                entries.append(current)
            current["bullets"].append(_strip_bullet(NUMBERED_RE.sub("", line)))
            continue
        if current and current["bullets"] and _continues_bullet(line, lines, index, current["bullets"][-1]):
            current["bullets"][-1] = f"{current['bullets'][-1]} {line}"
            continue
        if current is None or current["bullets"]:
            current = {"header": [], "bullets": []}
            entries.append(current)
        current["header"].append(line)
    return entries


def _continues_bullet(line: str, lines: list[str], index: int, previous: str) -> bool:
    if DATE_RANGE_RE.search(line) and not line[:1].islower():
        return False
    # "Title | Kotlin · Compose  Github || Play Store Link" is an entry header.
    if re.search(r"\s\|\s|\|\||·|\b(?:github|play store)\b", line, re.I) and not line[:1].islower():
        return False
    if line[:1].islower() or line.endswith("."):
        return True
    if re.search(r"[,&(/\-]$|\b(?:and|or|of|for|with|the|to|in|using|on|a|an)$", previous.strip(), re.I):
        return True
    next_is_bullet = index + 1 < len(lines) and _is_bullet(lines[index + 1])
    if next_is_bullet and len(line.split()) <= 8:
        return False
    return not previous.rstrip().endswith((".", "!", "?"))


def _clean_dates(text: str) -> str:
    text = DATE_RANGE_RE.sub("", text)
    return re.sub(r"\s*[|,–—\-]\s*$", "", re.sub(r"\s{2,}", " ", text)).strip(" |,-–—")


def _fix_spacing(text: str) -> str:
    # PDF text often has "LLM -Driven", "high -fidelity", "i nternational".
    text = re.sub(r"(\w) -(?=\w)", r"\1-", text)
    text = re.sub(r"(\d)- (?=[a-z])", r"\1-", text)  # "1- day trial" -> "1-day trial"
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


_CONTACT_LINE_RE = re.compile(r"@|https?://|www\.|linkedin|github|^\s*(?:e-?mail|phone|mobile|tel|address)\b", re.I)


def _identity(lines: list[str]) -> IdentityExtract:
    # Two-column templates put the contact block anywhere, so search it all.
    blob = "\n".join(lines)
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

    # Strongest signal: the name sits directly above the contact details.
    # (University letterheads like "JAMIA HAMDARD" often come first.)
    email_index = next((i for i, line in enumerate(lines) if EMAIL_RE.search(line)), None)
    if email_index is not None:
        i = email_index - 1
        while i >= 0 and (not lines[i] or _CONTACT_LINE_RE.search(lines[i]) or PHONE_RE.search(lines[i])):
            i -= 1
        if i >= 0 and _looks_like_name(lines[i]):
            return IdentityExtract(name=lines[i], email=email, phone=phone)

    name = None
    for line in lines[:8]:
        if not line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        heading = _heading_key(line)
        if heading:
            # A name sits above the body of the CV, never inside a section.
            if heading in {"contact", "summary"}:
                continue
            break
        if _looks_like_name(line):
            name = line
            break
    return IdentityExtract(name=name, email=email, phone=phone)


NAME_TOKEN_RE = re.compile(r"^[^\W\d_][^\W\d_.'\-]*(?:[.'\-][^\W\d_]*)*\.?$")


def _looks_like_name(line: str) -> bool:
    """One to five word-only tokens, no punctuation lists, no degree words."""
    if len(line) > 60 or DEGREE_RE.search(line) or re.search(r"[,;:|/@\d]", line):
        return False
    if re.search(r"\b(curriculum|vitae|resume|résumé|cv|university|institute|college|school|academy)\b", line, re.I):
        return False
    tokens = line.split()
    return 1 <= len(tokens) <= 5 and all(NAME_TOKEN_RE.match(token) for token in tokens)


def _education(lines: list[str]) -> list[EducationExtract]:
    """The first (most recent) degree entry: degree, field, institution, year."""
    if not lines:
        return []
    lines = [_strip_bullet(line) for line in lines]
    start = next((i for i, line in enumerate(lines) if DEGREE_RE.search(line)), None)
    if start is None:
        return []
    entry = [lines[start]]
    for line in lines[start + 1:start + 4]:
        if DEGREE_RE.search(line) or re.search(
            r"\b(?:A|O)-?Levels?\b|secondary|cbse|high school|class (?:10|12|x|xii)\b|percentage", line, re.I
        ):
            break
        entry.append(line)

    degree_line = lines[start]
    degree = DEGREE_RE.search(degree_line).group(0).strip()
    after_degree = degree_line[degree_line.find(degree) + len(degree):]

    field = None
    field_match = (
        re.search(r"\b(?:major|specialization|specialisation|branch|stream)\s*[:\-]\s*([^|,(\n]+)", degree_line, re.I)
        or re.search(r"\bin\s+([A-Z][^|,(\n]+)", after_degree)
        or re.search(r"^\s*(?:[—–:|]|-\s)\s*([A-Za-z][^|,(\n]+)", after_degree)
    )
    if field_match:
        field = _clean_dates(field_match.group(1)).strip(" .,:;-—–") or None

    # Institution: look line by line (never across the degree line, which
    # would turn "... Engineering" + "Jamia Hamdard University" into one name).
    institution = None
    uni_re = re.compile(
        r"(?:\b[A-Z][\w.&'\-]*\s+){0,4}(?:University|Institute|College|École|Ecole|School of [A-Z]\w+)[^,|\n]{0,80}"
    )
    for line in entry[1:] + entry[:1]:
        uni_match = uni_re.search(line if line is not degree_line else after_degree)
        if uni_match:
            institution = _clean_dates(uni_match.group(0)).strip(" .,")
            break
    if not institution:
        # Otherwise the line under the degree is usually "Institution, City".
        for line in entry[1:]:
            candidate = re.split(r"\s*[,|]\s*", line)[0].strip()
            if candidate and not re.search(r"\d|gpa|cgpa|grade|percentage|%", line, re.I) and len(candidate.split()) <= 8:
                institution = candidate
                break

    # "2023 – Present" means still studying: that start year is not a
    # graduation year.
    entry_text = " ".join(entry)
    years = [int(m.group(0)) for m in YEAR_RE.finditer(entry_text)]
    ongoing = re.search(r"\b(?:present|current|ongoing|pursuing|expected)\b", entry_text, re.I)
    graduation_year = max(years) if years else None
    if ongoing and graduation_year and not re.search(r"expected", entry_text, re.I):
        from datetime import date
        if graduation_year <= date.today().year and len(set(years)) == 1:
            graduation_year = None

    semester = None
    sem = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+sem(?:ester)?\b|\bsem(?:ester)?\s*(\d{1,2})\b", entry_text, re.I)
    if sem:
        number = sem.group(1) or sem.group(2)
        suffix = {"1": "st", "2": "nd", "3": "rd"}.get(number[-1], "th") if number not in {"11", "12", "13"} else "th"
        semester = f"{number}{suffix} semester"

    return [
        EducationExtract(
            degree=degree,
            field_of_study=field,
            institution=institution,
            graduation_year=graduation_year,
            current_semester=semester,
        )
    ]


def _explicit_interests(lines: list[str], catalog_labels: list[str]) -> list[str]:
    if not lines:
        return []
    blob = "\n".join(lines)
    found = labels_in_text(blob, catalog_labels)
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
    return labels_in_text(text, catalog_labels)


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
    for entry in _entries(lines):
        header = entry["header"]
        if not header:
            continue
        header_text = " ".join(header)
        # Drop date-only lines ("March 2026 – Present 2026").
        named = [line for line in header if re.search(r"[A-Za-z]{3,}", _clean_dates(re.sub(r"(?i)\bpresent\b", "", line)))]
        if not named:
            continue
        role = _clean_dates(named[0])[:120] or None
        organization = None
        if len(named) > 1:
            organization = re.sub(r"\s*\([^)]*\)", "", re.split(r"\s*[|,]\s*", named[1])[0]).strip() or None
        elif role and re.search(r",| at | \| ", role):
            # "Android Developer Intern, Square Nova tech | Hybrid"
            parts = re.split(r"\s*,\s*|\s+at\s+|\s*\|\s*", role)
            role, organization = parts[0].strip() or None, (parts[1].strip() if len(parts) > 1 else None) or None
        lowered = header_text.lower()
        kind = None
        if "intern" in lowered:
            kind = "internship"
        if re.search(r"research|reviewer|scholar|fellow", lowered):
            kind = "research"
        years = sorted({int(m.group(0)) for m in YEAR_RE.finditer(header_text)})
        description = _join_bullets(entry["bullets"]) or None
        items.append(
            ExperienceExtract(
                role=role,
                organization=organization,
                kind=kind,  # type: ignore[arg-type]
                description=description,
                start_year=min(years) if years else None,
                end_year=max(years) if len(years) > 1 else None,
            )
        )
        if len(items) >= 8:
            break
    return items


_TECH_PREFIX = re.compile(r"^(?:skills? learnt|skills? learned|tech(?:nologies)?(?: stack)?|tools(?: used)?|built with)\s*:\s*", re.I)


def _projects(lines: list[str]) -> list[ProjectExtract]:
    items: list[ProjectExtract] = []
    for entry in _entries(lines):
        header, bullets = entry["header"], entry["bullets"]
        if not header:
            continue
        if not bullets:
            # Plain list of project names.
            for line in header:
                items.append(ProjectExtract(title=_fix_spacing(_clean_dates(line))[:160]))
            continue
        # "Title | Kotlin · Compose · Supabase  Github || Play Store Link" and
        # any further header lines carry the tech stack, not more projects.
        title_part, _, tech_part = header[0].partition("|")
        title = _fix_spacing(_clean_dates(title_part)).strip(" |:-–—")
        tech_text = " ".join([tech_part, *header[1:]])
        technologies = [
            t.strip(" .·")
            for t in re.split(r"[,|·•](?![^()]*\))", re.sub(r"(?i)\b(?:github|play store|app store|demo|live|link)\b", "", tech_text))
            if len(t.strip(" .·")) > 1
        ]
        description: list[str] = []
        for bullet in bullets:
            if _TECH_PREFIX.match(bullet):
                # Split on commas/pipes that are not inside brackets.
                bullet_tech = _TECH_PREFIX.sub("", bullet)
                technologies += [
                    t.strip(" .") for t in re.split(r"[,|](?![^()]*\))", bullet_tech) if t.strip(" .")
                ]
            else:
                description.append(bullet)
        items.append(
            ProjectExtract(
                title=title[:160],
                description=_join_bullets(description) or None,
                technologies=technologies[:15],
            )
        )
        if len(items) >= 8:
            break
    return [item for item in items if item.title][:8]


_QUOTED_TITLE = re.compile(r"[\"“”]([^\"“”]{8,300})[\"“”]")


def _publications(lines: list[str]) -> list[PublicationExtract]:
    if not lines:
        return []
    grouped = any(NUMBERED_RE.match(line) or _is_bullet(line) for line in lines)
    raw_entries: list[str] = []
    for line in lines:
        starts_entry = bool(NUMBERED_RE.match(line) or _is_bullet(line))
        text = _strip_bullet(NUMBERED_RE.sub("", line))
        if not grouped or starts_entry or not raw_entries:
            raw_entries.append(text)
        else:
            raw_entries[-1] = f"{raw_entries[-1]} {text}"

    items: list[PublicationExtract] = []
    for raw in raw_entries:
        entry = _fix_spacing(raw)
        if len(entry) < 8:
            continue
        years = [int(m.group(0)) for m in YEAR_RE.finditer(entry)]
        status = None
        if re.search(r"under review|submitted|in review|preprint", entry, re.I):
            status = "under review"
        elif re.search(r"published|accepted|proceedings|in press", entry, re.I):
            status = "published"
        quoted = _QUOTED_TITLE.search(entry)
        if quoted:
            title = quoted.group(1).strip(" .")
            authors = entry[:quoted.start()]
            authors = re.sub(r"\(\s*(?:19|20)\d{2}\s*\)\.?\s*$", "", authors).strip(" .,") or None
            venue = re.split(r"\[", entry[quoted.end():])[0].strip(" .,") or None
        else:
            title, authors, venue = entry[:300], None, None
        items.append(
            PublicationExtract(
                title=title,
                venue=venue[:200] if venue else None,
                year=years[0] if years else None,
                authors=authors[:300] if authors else None,
                publication_type=status,
            )
        )
        if len(items) >= 8:
            break
    return items


def _certs(lines: list[str]) -> list[CertificationExtract]:
    # With bullets, a line without one is the wrapped end of the previous item.
    if any(_is_bullet(line) for line in lines):
        merged: list[str] = []
        for line in lines:
            if _is_bullet(line) or not merged:
                merged.append(line)
            else:
                merged[-1] = f"{merged[-1]} {line}"
        lines = merged
    items: list[CertificationExtract] = []
    for line in lines:
        text = _strip_bullet(line).strip(" .")
        if len(text) < 3:
            continue
        years = [int(m.group(0)) for m in YEAR_RE.finditer(text)]
        issuer = None
        parts = re.split(r"\s+[–—-]\s+", text, maxsplit=1)
        if len(parts) == 2 and len(parts[0].split()) <= 4:
            issuer, text = parts[0].strip(), parts[1].strip()
        items.append(CertificationExtract(name=text[:160], issuer=issuer, year=years[-1] if years else None))
        if len(items) >= 8:
            break
    return items
