from __future__ import annotations

"""
Deterministic outreach email writer. No external API calls, no invented facts.

The email follows the conventions of a formal academic inquiry, because that
is what professors expect and answer:
1. who the student is and exactly what they are asking for, up front;
2. why *this* professor: a topic from the professor's own research summary,
   tied to the student's specific interests;
3. the student's strongest evidence first: publications (with venue and
   status), research roles, then a relevant project in the CV's own words;
4. a clear, polite request suited to the student's level;
5. CV attached, thanks, and a full signature block.

Style rules: complete formal sentences, no contractions, no exclamation
marks, no em dashes, none of the stock phrases that mark mass-produced text.
Every sentence is optional: if a fact is missing, the sentence is dropped
rather than filled with a placeholder.
"""

import re
from datetime import date

from app.cv.extraction.schema import ExperienceExtract, ExtractedStudentProfile, PublicationExtract
from app.matching.evidence import labels_in_text
from app.outreach.provider import (
    ArtifactEvidence,
    EmailDraftOutput,
    EmailGenerationProvider,
    MatchContext,
    OpportunityContext,
    ProfessorContext,
)

GENERIC_TOPICS = frozenset({
    "machine learning", "artificial intelligence", "ai", "computer science",
    "algorithms", "theory", "applications", "research", "deep learning",
    "data science", "ai/ml", "ml",
})

# Words that mark a summary fragment as scraping metadata, not a research topic.
_META_WORDS = re.compile(
    r"\b(official|listing|listed|lists|faculty|profile|page|directory|fetched|"
    r"included|roster|table|chips?|states?|describes?|statement|website|member|"
    r"department|university|institute|school|centre|center|professor|his|her|"
    r"their|lab|group|core|people|research|interests?|works?|working|focus(?:es)?|"
    r"current(?:ly)?|aims?|including|appointment|initiatives?|associated|developing|"
    r"such|that|which|who|understand|better|laboratory|overview)\b",
    re.I,
)
_TOPIC_LEADS = re.compile(
    r"^(?:(?:(?:his|her|their|main|current|recent)\s+)?(?:research|work|works|interests?)\s+"
    r"(?:on|in|into|includes?|spans?|covers?)\s+|and\s+|or\s+|with\s+|such as\s+|e\.g\.\s+|"
    r"especially\s+|particularly\s+|on\s+|in\s+)",
    re.I,
)
_STOP_TOKENS = frozenset({
    "ai", "learning", "systems", "models", "model", "data", "and", "for", "of", "the",
    "in", "with", "methods", "analysis", "based", "computer", "natural", "processing",
    "artificial", "intelligence", "machine", "large", "human", "centered", "science",
    "deep",
})

_FIELD_MAX_WORDS = 6
_INSTITUTION_MAX_WORDS = 10
_TITLE_MAX_WORDS = 16
_PAPER_TITLE_MAX_WORDS = 28
_GENERIC_INTERESTS = frozenset({
    "artificial intelligence", "machine learning", "computer science", "data science", "deep learning",
})


# ---------------------------------------------------------------------------
# Wording. Each list is indexed by a rotating variant number, so "regenerate"
# gives a differently worded draft built from the same facts. Every variant
# keeps the same formal register.
# ---------------------------------------------------------------------------

_SUBJECTS = {
    "undergraduate": "Research Internship Inquiry: {area}",
    "masters": "Prospective PhD Student / Research Assistant Inquiry: {area}",
    "phd": "Research Collaboration Inquiry: {area}",
    "unknown": "Research Position Inquiry: {area}",
}

_PURPOSE = {
    "undergraduate": "an undergraduate research intern",
    "masters": "a research assistant or prospective PhD student",
    "phd": "a visiting researcher or collaborator",
    "unknown": "a research intern",
}

_PURPOSE_LINES = [
    "I am writing to ask whether there might be an opportunity to join your research group as {purpose}.",
    "I am writing to enquire about the possibility of joining your group as {purpose}.",
]

_REASON_WITH_TOPICS = [
    "Your group's work on {topics} is of particular interest to me, as it connects directly with my own research interest in {area}{extra}.",
    "I was particularly drawn to your research on {topics}, which relates closely to my work in {area}{extra}.",
]

_REASON_WITH_AREAS = [
    "Your research in {area} is closely related to my own interests{extra}, and it is the main reason I am contacting you.",
    "I am contacting you because your work in {area} is closely related to the direction I wish to pursue{extra}.",
]

_REASON_RELATED = [
    "My main research interest is {student_area}, and your group's work in {professor_area} is closely connected to it.",
    "I have been working mainly in {student_area}, and I am keen to extend this towards {professor_area}, which is central to your research.",
]

_REASON_GENERAL = [
    "My research interests lie in {interests}, and I would value the opportunity to learn from the work being done in your group.",
]

_ASKS = {
    "undergraduate": [
        "I would be grateful for the opportunity to contribute to ongoing projects in your group as a research intern, either remotely or in person. If no position is available at present, I would greatly appreciate any advice on how best to prepare for research in this area.",
        "If your group is able to take on an undergraduate research intern, remotely or in person, I would be glad to contribute to any ongoing project. I would also be grateful for any guidance on preparing for graduate research in this area.",
    ],
    "masters": [
        "I would be grateful to know whether you expect to have openings for research assistants or PhD students in the coming intake, and whether my background would be a suitable fit for your group.",
        "I would like to ask whether you are considering new PhD students or research assistants for the upcoming intake, and how best to apply.",
    ],
    "phd": [
        "I would welcome the opportunity to discuss possible collaboration or a visiting research position in your group.",
    ],
    "unknown": [
        "I would be grateful to know whether there may be an opportunity to contribute to your group's research, and how best to apply.",
    ],
}

_OPPORTUNITY_LINES = [
    "I also noticed that {university} offers the {opportunity}, and I would be keen to apply if it is relevant to your group.",
    "I understand that {university} offers the {opportunity}; I would be glad to apply through it if that would be appropriate.",
]

_CLOSINGS = [
    "I have attached my CV for your reference. Thank you for your time and consideration; I look forward to hearing from you.",
    "Please find my CV attached for your reference. Thank you very much for your time and consideration.",
]

_SIGN_OFFS = ["Sincerely,", "Kind regards,"]


class DeterministicTemplateProvider(EmailGenerationProvider):
    """
    Generates a formal, evidence-grounded email from structured verified data.
    No external API calls. No invented facts.
    """

    # Rotates per call so "regenerate" returns a differently worded draft.
    _variant_counter: int = 0

    def generate(
        self,
        *,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        email_type: str,
        opportunity: OpportunityContext | None = None,
    ) -> EmailDraftOutput:
        DeterministicTemplateProvider._variant_counter += 1
        v = DeterministicTemplateProvider._variant_counter

        usable_opportunity = (
            opportunity
            if email_type == "research_opportunity" and opportunity and opportunity.status != "closed"
            else None
        )
        subject = self._subject(student, match, usable_opportunity)
        body = self._body(student, professor, match, usable_opportunity, v)
        evidence = self._evidence_lines(student, professor, match, opportunity)

        return EmailDraftOutput(
            subject=subject,
            body=body,
            evidence_used=evidence,
            generation_provider="deterministic",
        )

    # ------------------------------------------------------------------
    # Subject
    # ------------------------------------------------------------------

    def _subject(
        self,
        student: ExtractedStudentProfile,
        match: MatchContext,
        opportunity: OpportunityContext | None,
    ) -> str:
        area = _focus_area(match, student)
        if opportunity and opportunity.title and area:
            subject = f"Inquiry regarding the {_clean_title(opportunity.title)}: {area}"
            if len(subject) <= 95:
                return subject
        if not area:
            return "Research Position Inquiry from a Prospective Student"
        subject = _SUBJECTS[_student_level(student)].format(area=area)
        credentials = _short_credentials(student)
        if credentials and len(subject) + len(credentials) + 3 <= 95:
            subject += f" | {credentials}"
        return subject

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    def _body(
        self,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        opportunity: OpportunityContext | None,
        v: int,
    ) -> str:
        name = _clean_student_name(student.identity.name, student)
        level = _student_level(student)

        intro = _who_i_am(student, name)
        purpose = _PURPOSE_LINES[v % len(_PURPOSE_LINES)].format(purpose=_PURPOSE[level])
        paragraphs = [" ".join(s for s in (intro, purpose) if s)]

        paragraphs.append(_why_this_professor(student, professor, match, v))

        research = _research_paragraph(student, match)
        projects = _projects_paragraph(student, match, has_research=bool(research))
        practical = _practical_paragraph(student)
        paragraphs += [p for p in (research, projects, practical) if p]

        ask = _contribution_line(match, research, projects, practical)
        ask = f"{ask} {_ASKS[level][v % len(_ASKS[level])]}".strip()
        if opportunity:
            ask += " " + _opportunity_line(opportunity, professor, v)
        paragraphs.append(ask)

        paragraphs.append(_CLOSINGS[v % len(_CLOSINGS)])

        signature = [_SIGN_OFFS[v % len(_SIGN_OFFS)]]
        if name:
            signature.append(name)
        credentials = _full_credentials(student)
        if credentials:
            signature.append(credentials)
        email = (student.identity.email or "").strip()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            signature.append(email)

        return "\n\n".join([_greeting(professor), *paragraphs, "\n".join(signature)])

    # ------------------------------------------------------------------
    # Evidence list (human-readable)
    # ------------------------------------------------------------------

    def _evidence_lines(
        self,
        student: ExtractedStudentProfile,
        professor: ProfessorContext,
        match: MatchContext,
        opportunity: OpportunityContext | None,
    ) -> list[str]:
        lines: list[str] = []
        for area in match.shared_interest_areas:
            lines.append(f"{area} — explicit research interest match")
        for ev in match.artifact_evidence:
            lines.append(f'Your {ev.kind} "{ev.title}" — {ev.area_name} evidence')
        for area in match.corroborated_areas:
            lines.append(f"{area} — corroborated by professor research summary")
        for student_area, professor_area in match.related_areas:
            lines.append(f"{student_area} — closely related to the professor's {professor_area} research")
        if opportunity:
            uni = opportunity.university_name or professor.university_name or "university"
            lines.append(
                f"University opportunity: {opportunity.title or opportunity.opportunity_type} "
                f"at {uni} (university-wide, not professor-specific)"
            )
        return lines


# ---------------------------------------------------------------------------
# Paragraph builders
# ---------------------------------------------------------------------------

def _greeting(professor: ProfessorContext) -> str:
    last = _last_name(professor.name)
    if not last:
        return "Dear Professor,"
    title = (professor.title or "").lower()
    if title and "professor" not in title and re.search(r"lecturer|researcher|scientist|fellow|reader", title):
        return f"Dear Dr. {last},"
    return f"Dear Professor {last},"


def _who_i_am(student: ExtractedStudentProfile, name: str | None) -> str:
    degree = _degree_display(student)
    edu = student.education[0] if student.education else None
    field_of_study = _clean_phrase(edu.field_of_study, _FIELD_MAX_WORDS) if edu else None
    institution = _clean_phrase(edu.institution, _INSTITUTION_MAX_WORDS) if edu else None
    final_year = _is_final_year(student)

    role = ""
    if degree or field_of_study or institution:
        role = " ".join(p for p in ("final-year" if final_year else "", degree or "", "student") if p)
        role = f"{_article(role)} {role}"
        if field_of_study:
            role += f" in {field_of_study}"
        if institution:
            role += f" at {institution}"
        year = edu.graduation_year if edu else None
        if year and not final_year and date.today().year <= year <= date.today().year + 6:
            role += f", expecting to graduate in {year}"

    if name and role:
        return f"My name is {name}, and I am {role}."
    if name:
        return f"My name is {name}."
    if role:
        return f"I am {role}."
    return ""


def _is_final_year(student: ExtractedStudentProfile) -> bool:
    edu = student.education[0] if student.education else None
    semester = re.match(r"(\d{1,2})", (edu.current_semester or "").strip()) if edu else None
    if semester and _student_level(student) == "undergraduate" and int(semester.group(1)) >= 7:
        return True  # 7th/8th semester of a four-year degree
    year = edu.graduation_year if edu else None
    if not year:
        return False
    today = date.today()
    # Academic years run roughly July-June.
    return year == (today.year + 1 if today.month >= 7 else today.year)


def _why_this_professor(
    student: ExtractedStudentProfile,
    professor: ProfessorContext,
    match: MatchContext,
    v: int,
) -> str:
    """Why this professor in particular, then the student's own research focus."""
    shared = _specific_first(match.research_overlap)[:2]
    mentioned = {a.casefold() for a in shared}
    sentence = ""
    if shared:
        for area in shared:
            topics = summary_topics(professor.research_summary, [area], known_areas=shared)
            if topics:
                template = _REASON_WITH_TOPICS[v % len(_REASON_WITH_TOPICS)]
                sentence = template.format(topics=_join(topics), area=_area_text(area), extra="")
                break
        if not sentence:
            sentence = _REASON_WITH_AREAS[v % len(_REASON_WITH_AREAS)].format(
                area=_join([_area_text(a) for a in shared]), extra=""
            )
    elif match.related_areas:
        student_area, professor_area = match.related_areas[0]
        mentioned |= {student_area.casefold(), professor_area.casefold()}
        template = _REASON_RELATED[v % len(_REASON_RELATED)]
        sentence = template.format(student_area=_area_text(student_area), professor_area=_area_text(professor_area))
    else:
        prof_areas = [
            a for a in _specific_first(professor.research_areas) if a.casefold() not in {"computer science"}
        ][:2]
        if prof_areas:
            sentence = (
                f"I am particularly interested in your research on {_join([_area_text(a) for a in prof_areas])}, "
                "and I would value the opportunity to learn from the work being carried out in your group."
            )
        else:
            sentence = "I would value the opportunity to learn from the research being carried out in your group."

    focus = [a for a in _student_focus(student) if a.casefold() not in mentioned][:3]
    if focus:
        lead = "More broadly, my research interests centre on" if v % 2 else "My broader research interests include"
        sentence += f" {lead} {_join([_area_text(a) for a in focus])}."
    return sentence


def _student_focus(student: ExtractedStudentProfile) -> list[str]:
    """The student's own specific areas: stated interests first, then areas evidenced by their work."""
    seen: set[str] = set()
    ordered: list[str] = []
    for area in _specific_first(list(student.research_interests)) + _specific_first(list(student.research_signals)):
        key = area.casefold()
        if key in seen or key in _GENERIC_INTERESTS or key == "computer science" or not _clean_phrase(area, 5):
            continue
        seen.add(key)
        ordered.append(area)
    return ordered


def _research_paragraph(student: ExtractedStudentProfile, match: MatchContext) -> str:
    papers = [p for p in student.publications if _clean_title(p.title, _PAPER_TITLE_MAX_WORDS)]
    role = _research_role_sentence(student)
    if not papers:
        return role.replace("I have also served", "In terms of research experience, I have served") if role else ""

    relevance: dict[str, int] = {}
    for artifact in match.artifact_evidence:
        if artifact.kind == "publication":
            score = 2 if artifact.area_name.casefold() not in _GENERIC_INTERESTS else 1
            key = artifact.title.casefold()
            relevance[key] = max(relevance.get(key, 0), score)
    ranked = sorted(papers, key=lambda p: (-relevance.get(p.title.casefold(), 0), not _is_published(p)))
    chosen, rest = ranked[0], ranked[1:]
    title = _clean_title(chosen.title, _PAPER_TITLE_MAX_WORDS)
    status = _publication_status(chosen)

    if len(papers) == 1:
        sentences = [f'In terms of research experience, I am a co-author of the paper "{title}"{status}.']
    elif relevance.get(chosen.title.casefold()):
        sentences = [
            f"In terms of research experience, I have co-authored {_number_word(len(papers))} research papers. "
            f'The one most relevant to your work is "{title}"{status}.'
        ]
    else:
        sentences = [
            f"In terms of research experience, I have co-authored {_number_word(len(papers))} research papers, "
            f'including "{title}"{status}.'
        ]
    second = next((p for p in rest if _clean_title(p.title, 20)), None)
    if second:
        sentences.append(f'I have also contributed to "{_clean_title(second.title, 20)}"{_publication_status(second)}.')
    if role:
        sentences.append(role.replace("I have also served", "In addition, I have served"))
    return " ".join(sentences)


def _projects_paragraph(student: ExtractedStudentProfile, match: MatchContext, *, has_research: bool) -> str:
    relevant_titles = [a.title for a in match.artifact_evidence if a.kind == "project"]
    area_by_title = {a.title: a.area_name for a in match.artifact_evidence if a.kind == "project"}
    ordered = sorted(student.projects, key=lambda p: p.title not in relevant_titles)
    sentences: list[str] = []
    for project in ordered:
        if len(sentences) >= 2:
            break
        if project.title not in relevant_titles and (sentences or not _RESEARCHY.search(
            f"{project.title} {project.description or ''} {' '.join(project.technologies)}"
        )):
            continue  # unrelated, non-research projects add length without adding relevance
        title = _project_title(project.title)
        clause = _first_sentence_as_clause(project.description)
        if not title or not clause:
            continue
        if not sentences:
            opener = "Alongside my research, in my project" if has_research else "In my project"
            sentences.append(f"{opener} {title}, I {clause}.")
            area = area_by_title.get(project.title)
            if area and area.casefold() not in _GENERIC_INTERESTS:
                sentences.append(f"This work is closely related to your research in {_area_text(area)}.")
        else:
            sentences.append(f"In another project, {title}, I {clause}.")
    return " ".join(sentences)


_RESEARCHY = re.compile(
    r"(?i)\b(ai|ml|machine learning|deep[- ]learning|neural|llms?|nlp|computer vision|vision|"
    r"tensorflow|pytorch|model(?:s|ing)?|prediction|classification|detection|dataset|research|agents?)\b"
)


def _project_title(title: str | None) -> str | None:
    """'Agro 360 – Smart AI-Powered Farming Assistant' -> 'Agro 360 (Smart AI-Powered Farming Assistant)'."""
    if not title:
        return None
    text = re.sub(r"\s+", " ", title).strip(" .,|-–—")
    parts = re.split(r"\s+[–—|]\s+|\s+-\s+|:\s+", text, maxsplit=1)
    if len(parts) == 2 and parts[1].strip().lower() in {"app", "application", "website"}:
        text = f"{parts[0]} {parts[1].strip().title()}"
    elif len(parts) == 2 and parts[1] and len(parts[1].split()) <= 8:
        text = f"{parts[0]} ({parts[1]})"
    else:
        text = parts[0]
    if len(text.split()) > 14:
        return None
    return text


def _practical_paragraph(student: ExtractedStudentProfile) -> str:
    sentences: list[str] = []
    job = next(
        (e for e in student.experience if e.kind in ("internship", "work") and _clean_phrase(e.role, 6) and e.organization),
        None,
    )
    if job:
        role = _role_text(_clean_phrase(job.role, 6))
        org = re.sub(r"\s+", " ", job.organization).strip(" ,.;:-")
        if org and len(org.split()) <= 8:
            clause = _first_sentence_as_clause(job.description)
            if clause:
                sentences.append(f"My practical experience includes working as {_article(role)} {role} at {org}, where I {clause}.")
            else:
                sentences.append(f"My practical experience includes working as {_article(role)} {role} at {org}.")
    skills = _skills_list(student)
    if len(skills) >= 2:
        sentences.append(f"I am proficient in {_join(skills)}.")
    return " ".join(sentences)


def _skills_list(student: ExtractedStudentProfile) -> list[str]:
    languages = [s.name for s in student.skills if s.category == "language" and s.name not in {"SQL", "R"}]
    tools = [s.name for s in student.skills if s.category == "ml_tool"]
    return (languages[:2] + tools[:2]) if tools else languages[:3]


def _contribution_line(match: MatchContext, research: str, projects: str, practical: str) -> str:
    area = _specific_first(match.research_overlap)[0] if match.research_overlap else None
    if not area or not (research or projects or practical):
        return ""
    if research and (projects or practical):
        basis = "this combination of research and practical experience"
    elif research:
        basis = "this research experience"
    else:
        basis = "this experience"
    return f"I believe {basis} would allow me to contribute meaningfully to your group's work in {_area_text(area)}."


def _is_published(paper: PublicationExtract) -> bool:
    kind = (paper.publication_type or "").lower()
    return kind in {"published", "accepted"} or bool(paper.venue and kind not in {"under review", "preprint"})


def _publication_status(paper: PublicationExtract) -> str:
    kind = (paper.publication_type or "").lower()
    venue = _clean_venue(paper.venue)
    if kind == "under review":
        return ", which is currently under review"
    if kind == "preprint":
        return ", available as a preprint"
    if venue:
        verb = "accepted at" if kind == "accepted" else "published at"
        needs_the = re.search(r"(?i)\b(conference|workshop|symposium|proceedings|international|annual)\b", venue)
        if needs_the and not venue.lower().startswith("the "):
            return f", {verb} the {venue}"
        return f", {verb} {venue}"
    return ""


def _clean_venue(venue: str | None) -> str | None:
    if not venue:
        return None
    text = re.sub(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{1,2},?\s*(?:19|20)\d{2}\b", "", venue, flags=re.I)
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    text = re.sub(r",?\s*(?:19|20)\d{2}\s*$", "", text).strip(" .,;:")
    if not text or len(text.split()) > 10:
        return None
    return text


def _research_role_sentence(student: ExtractedStudentProfile) -> str:
    role = next((e for e in student.experience if e.kind == "research" and _clean_phrase(e.role, 6)), None)
    if not role:
        return ""
    title = _clean_phrase(role.role, 6)
    title_text = _role_text(title)
    org = re.sub(r"\s+", " ", role.organization or "").strip(" ,.;:-") or None
    if org and len(org.split()) > 8:
        org = None
    preposition = "for" if re.search(r"review|referee|editor|judge", title, re.I) else "at"
    article = _article(title_text)
    if org:
        return f"I have also served as {article} {title_text} {preposition} {org}."
    return f"I have also served as {article} {title_text}."


_ROLE_WORDS = frozenset({
    "peer", "reviewer", "research", "researcher", "assistant", "associate", "intern", "trainee",
    "software", "developer", "engineer", "engineering", "scientist", "analyst", "designer", "data",
    "machine", "learning", "web", "backend", "frontend", "full", "stack", "student", "member",
    "lead", "manager", "teaching", "volunteer", "consultant", "and", "ethics", "program", "committee",
})


def _role_text(role: str) -> str:
    """'Android Developer Intern' -> 'Android developer intern' (proper nouns kept)."""
    return " ".join(w.lower() if w.lower() in _ROLE_WORDS and re.fullmatch(r"[A-Z][a-z]+", w) else w for w in role.split())


_PAST_VERBS = re.compile(
    r"^(built|developed|designed|implemented|created|trained|led|wrote|proposed|analysed|analyzed|"
    r"applied|integrated|deployed|evaluated|improved|optimized|optimised|engineered|researched|"
    r"collected|fine-tuned|benchmarked|studied|investigated)\b",
    re.I,
)


_DETERMINERS = frozenset({
    "a", "an", "the", "my", "our", "their", "its", "this", "these", "those", "and", "several", "multiple",
    "two", "three", "four", "five", "various", "new", "end-to-end",
})
_SINGULAR_THINGS = re.compile(
    r"(?i)^(?:[\w\-]+\s+){0,3}?(app|application|system|tool|model|pipeline|platform|website|dashboard|"
    r"chatbot|bot|framework|service|panel|api|engine|library|prototype|interface)\b"
)


def _first_sentence_as_clause(description: str | None) -> str | None:
    """'Built an app with X.' -> 'built an app with X' (only if it reads as the student's action)."""
    if not description:
        return None
    sentence = re.split(r"(?<=[.!?])\s+", description.strip())[0].strip().rstrip(".")
    if not _PAST_VERBS.match(sentence) or len(sentence.split()) > 30:
        return None
    # CV bullets often drop articles: "Built production Android app ..." ->
    # "built a production Android app ...".
    verb, _, rest = sentence.partition(" ")
    first_word = rest.split(" ", 1)[0].lower() if rest else ""
    if rest and first_word not in _DETERMINERS and _SINGULAR_THINGS.match(rest):
        rest = f"{_article(rest)} {rest}"
    sentence = f"{verb} {rest}".strip()
    return sentence[0].lower() + sentence[1:]


def _opportunity_line(opportunity: OpportunityContext, professor: ProfessorContext, v: int) -> str:
    university = opportunity.university_name or professor.university_name or "the university"
    name = _clean_title(opportunity.title or "") or (
        f"{opportunity.opportunity_type} programme" if opportunity.opportunity_type else "research programme"
    )
    line = _OPPORTUNITY_LINES[v % len(_OPPORTUNITY_LINES)].format(university=university, opportunity=name)
    if university.casefold() in name.casefold():
        line = line.replace(f"that {university} offers", "that the university offers").replace(
            f"that {university} offers", "that the university offers"
        ).replace(f"{university} offers", "the university offers")
    return line


def _short_credentials(student: ExtractedStudentProfile) -> str:
    """'B.Tech, Jamia Hamdard' for the subject line."""
    edu = student.education[0] if student.education else None
    degree = _degree_display(student)
    institution = _clean_phrase(edu.institution, 5) if edu else None
    if degree in {"bachelor's", "master's"}:
        degree = None
    return ", ".join(p for p in (degree, institution) if p)


def _full_credentials(student: ExtractedStudentProfile) -> str:
    """'B.Tech in Computer Science, Jamia Hamdard' for the signature."""
    edu = student.education[0] if student.education else None
    if not edu:
        return ""
    degree = _degree_display(student)
    field_of_study = _clean_phrase(edu.field_of_study, _FIELD_MAX_WORDS)
    institution = _clean_phrase(edu.institution, _INSTITUTION_MAX_WORDS)
    if degree in {"bachelor's", "master's"}:
        degree = degree.capitalize() + " student"
    head = " in ".join(p for p in (degree, field_of_study) if p)
    return ", ".join(p for p in (head, institution) if p)


def _number_word(n: int) -> str:
    return {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}.get(n, str(n))


# ---------------------------------------------------------------------------
# Professor research-summary topics
# ---------------------------------------------------------------------------

def summary_topics(
    summary: str | None,
    focus_areas: list[str],
    limit: int = 2,
    known_areas: list[str] | None = None,
) -> list[str]:
    """
    Short topic phrases from the professor's own summary that relate to the
    shared areas, e.g. "dialogue systems" or "3D computer vision".

    Returns [] when nothing clean and relevant is found, so the caller falls
    back to naming the shared area. Never paraphrases or invents.
    """
    if not summary or not focus_areas:
        return []
    focus_tokens: set[str] = set()
    focus_names: set[str] = set()
    for area in focus_areas:
        focus_names.add(area.casefold())
        focus_tokens |= _content_tokens(area)
    known_tokens = set(focus_tokens)
    for area in known_areas or []:
        known_tokens |= _content_tokens(area)

    picked: list[str] = []
    seen: set[str] = set()
    for fragment in re.split(r"[,;:()]|\.\s|\.$", summary):
        topic = _clean_topic(fragment)
        if not topic:
            continue
        key = topic.casefold()
        if key in seen or key in GENERIC_TOPICS or key in focus_names:
            continue
        # Relevant if it names a shared area (or a known alias of one), or
        # shares a distinctive word with it ("3D computer vision" -> vision).
        tokens = _content_tokens(topic)
        if not (labels_in_text(topic, focus_areas) or tokens & focus_tokens):
            continue
        # ...and it must say something the area name alone doesn't, otherwise
        # the email just repeats itself ("your work on computer vision").
        if not tokens - known_tokens:
            continue
        seen.add(key)
        picked.append(_area_text(topic))
        if len(picked) >= limit:
            break
    return picked


def _clean_topic(fragment: str) -> str | None:
    text = re.sub(r"\s+", " ", fragment).strip(" .-–—\"'")
    text = _TOPIC_LEADS.sub("", text)
    if not text or _META_WORDS.search(text):
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 \-+']*", text):
        return None
    if re.match(r"(?:the|a|an|to|of|for|from|by)\b", text, re.I) or not _content_tokens(text):
        return None
    words = text.split()
    if any(len(w) == 1 and w.isalpha() for w in words):  # "v alidation" typos in source data
        return None
    if not 1 <= len(words) <= 6 or len(text) < 4:
        return None
    return text


def _content_tokens(text: str) -> set[str]:
    tokens = {
        t for t in re.split(r"[^a-z0-9]+", text.casefold())
        if len(t) > 2 or (len(t) == 2 and any(c.isdigit() for c in t))
    }
    return tokens - _STOP_TOKENS


# ---------------------------------------------------------------------------
# Helpers (also used by the LLM provider)
# ---------------------------------------------------------------------------

def _last_name(full_name: str) -> str:
    """Last real token of a name, ignoring honorifics and post-nominals."""
    if not full_name:
        return full_name
    tokens = [t.strip(",") for t in full_name.strip().split()]
    tokens = [
        t for t in tokens
        if t and t.lower().rstrip(".") not in {"dr", "prof", "professor", "phd", "jr", "sr", "ii", "iii", "frs", "md"}
    ]
    return tokens[-1] if tokens else full_name


def _degree_phrase(student: ExtractedStudentProfile) -> str:
    """e.g. "BS student in Computer Science at University of Example"."""
    degree = _degree_display(student)
    edu = student.education[0] if student.education else None
    parts = [f"{degree} student" if degree else "student"]
    if edu:
        field_of_study = _clean_phrase(edu.field_of_study, _FIELD_MAX_WORDS)
        institution = _clean_phrase(edu.institution, _INSTITUTION_MAX_WORDS)
        if field_of_study:
            parts.append(f"in {field_of_study}")
        if institution:
            parts.append(f"at {institution}")
    if len(parts) == 1 and not degree:
        return "research student"
    return " ".join(parts)


def _interests_phrase(overlap: list[str], raw_interests: list[str]) -> str:
    """Use the verified overlap areas; fall back to raw interests if none."""
    areas = overlap or raw_interests
    if not areas:
        return "research"
    return _join(list(areas))


def _best_artifact(
    artifacts: list[ArtifactEvidence],
    overlap: list[str],
) -> ArtifactEvidence | None:
    """Prefer artifacts in the overlap set, then publications, then clean titles."""
    overlap_set = {a.lower() for a in overlap}
    in_overlap = [a for a in artifacts if a.area_name.lower() in overlap_set]
    ranked = in_overlap or artifacts
    usable = [a for a in ranked if _clean_title(a.title)] or ranked
    pubs = [a for a in usable if a.kind == "publication"]
    projs = [a for a in usable if a.kind == "project"]
    return (pubs + projs + [None])[0]


def _specific_first(areas: list[str]) -> list[str]:
    """Broad labels (Machine Learning, AI) only lead when nothing narrower is shared."""
    breadth = {"artificial intelligence": 2, "machine learning": 2, "computer science": 2,
               "deep learning": 1, "data science": 1}
    return sorted(areas, key=lambda a: breadth.get(a.casefold(), 0))


def _focus_area(match: MatchContext, student: ExtractedStudentProfile) -> str | None:
    if match.research_overlap:
        return _specific_first(match.research_overlap)[0]
    if match.related_areas:
        return match.related_areas[0][0]
    for interest in student.research_interests:
        cleaned = _clean_phrase(interest, 5)
        if cleaned:
            return cleaned
    return None


def _student_level(student: ExtractedStudentProfile) -> str:
    edu = student.education[0] if student.education else None
    text = " ".join(filter(None, [edu.degree, edu.current_semester] if edu else [])).lower()
    compact = re.sub(r"[.\s']", "", text)
    if re.search(r"phd|doctor", compact):
        return "phd"
    if re.search(r"^m|master|mtech|msc|meng|mphil|mba|\bms\b", compact):
        return "masters"
    if re.search(r"^b|bachelor|undergrad|btech|bsc|beng", compact):
        return "undergraduate"
    return "unknown"


def _level_label(level: str) -> str:
    return {
        "undergraduate": "Undergraduate",
        "masters": "Master's",
        "phd": "PhD",
    }.get(level, "")


_DEGREE_NAMES = {
    "bs": "BS", "bsc": "BSc", "btech": "B.Tech", "be": "BE", "beng": "BEng", "ba": "BA",
    "bba": "BBA", "bcs": "BCS", "bse": "BSE",
    "ms": "MS", "msc": "MSc", "mtech": "M.Tech", "meng": "MEng", "mba": "MBA",
    "mphil": "MPhil", "ma": "MA", "mcs": "MCS",
    "phd": "PhD", "dphil": "DPhil",
}


def _degree_display(student: ExtractedStudentProfile) -> str | None:
    edu = student.education[0] if student.education else None
    raw = (edu.degree or "").strip() if edu else ""
    if not raw:
        return None
    compact = re.sub(r"[.\s]", "", raw).lower()
    if compact in _DEGREE_NAMES:
        return _DEGREE_NAMES[compact]
    lowered = raw.lower()
    spelled = {
        "bachelor of technology": "B.Tech", "bachelor of engineering": "BE", "bachelor of science": "BS",
        "bachelor of arts": "BA", "bachelor of computer applications": "BCA",
        "master of technology": "M.Tech", "master of engineering": "MEng", "master of science": "MS",
        "master of arts": "MA", "master of computer applications": "MCA", "master of philosophy": "MPhil",
    }
    for prefix, short in spelled.items():
        if lowered.startswith(prefix):
            return short
    if lowered.startswith("bachelor"):
        return "bachelor's"
    if lowered.startswith("master"):
        return "master's"
    if "doctor" in lowered or "ph.d" in lowered or "phd" in lowered:
        return "PhD"
    if len(raw.split()) <= 3 and not re.search(r"\d", raw):
        return raw.rstrip(".")
    return None


def _article(phrase: str) -> str:
    first = phrase.split()[0] if phrase.split() else phrase
    if first[:1].lower() in "aeiou" and not first.isupper():
        return "an"
    # Acronyms read letter by letter: "an MS", "an MSc", "a BS".
    if first[:1] in "AEFHILMNORSX" and (first.isupper() or re.match(r"^[A-Z]{1,2}[a-z]", first)):
        return "an"
    return "a"


def _clean_student_name(raw: str | None, student: ExtractedStudentProfile | None = None) -> str | None:
    if not raw:
        return None
    if re.search(r"(?i)\b(university|institute|college|school|academy|page)\b", raw):
        return None
    institution = (student.education[0].institution or "") if student and student.education else ""
    if institution and (raw.strip().casefold() in institution.casefold() or institution.casefold() in raw.casefold()):
        return None  # a letterhead parsed as the name
    name = re.sub(r"\s+", " ", raw).strip()
    if not name or len(name) > 60 or re.search(r"[,;:|/@\d]", name) or len(name.split()) > 5:
        return None
    if name.isupper():
        name = name.title()
    return name


def _clean_phrase(value: str | None, max_words: int) -> str | None:
    if not value:
        return None
    text = re.sub(r"\s+", " ", value).strip(" ,.;:-")
    if not text or re.search(r"\d", text) or len(text.split()) > max_words:
        return None
    return text


def _clean_title(title: str | None, max_words: int = _TITLE_MAX_WORDS) -> str | None:
    """A project or paper title that is short enough to quote."""
    if not title:
        return None
    text = re.sub(r"\s+", " ", title).strip(" .,-–—\"'“”")
    # Drop trailing dates, "| Python, PyTorch", "- 2024" and similar tails.
    text = re.split(r"\s+[|–—]\s+|\s+-\s+|\s*\(\s*(?:19|20)\d{2}", text)[0].strip(" .,-")
    text = re.sub(r",?\s*(?:19|20)\d{2}$", "", text).strip(" .,")
    # Drop a trailing venue: "..., MICCAI" or "..., Proceedings of ACL".
    text = re.sub(
        r",\s*(?:[A-Z][A-Za-z0-9&\-]*\s*){1,3}$|,\s*[^,]*\b(?:Conference|Journal|Workshop|Proceedings|arXiv|Transactions)\b[^,]*$",
        "",
        text,
    ).strip(" .,")
    if not text or len(text.split()) > max_words:
        return None
    return text


def _area_text(label: str) -> str:
    """Write a catalog label the way it reads mid-sentence: "medical AI"."""
    words = []
    for word in label.split():
        if re.fullmatch(r"[A-Z][a-z]+(?:-[A-Z]?[a-z]+)*", word):
            words.append(word.lower())
        else:
            words.append(word)
    return " ".join(words)


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
