from __future__ import annotations

"""
Tie-breaking for professors with the same research score.

The displayed score stays a plain coverage percentage. Ranking inside a score
band prefers, in order:
  1. specificity — shared areas that few professors list (e.g. Medical AI)
     outrank ones almost everyone lists (Machine Learning);
  2. focus — the shared areas make up more of the professor's own profile;
  3. corroboration — the professor's research summary confirms the overlap.
"""

import math
from collections import Counter
from typing import Iterable

from app.matching.normalize import is_generic_area, normalize_label
from app.matching.scoring import ProfessorMatchResult
from app.matching.taxonomy import RELATED_CREDIT


def area_frequencies(area_lists: Iterable[list[str]]) -> Counter[str]:
    """How many professors list each (normalized) area."""
    counts: Counter[str] = Counter()
    for areas in area_lists:
        counts.update({normalize_label(name) for name in areas if name})
    return counts


def tiebreak(
    result: ProfessorMatchResult,
    professor_areas: list[str],
    frequencies: Counter[str],
    total_professors: int,
) -> tuple[float, float, int]:
    def rarity(name: str) -> float:
        seen = frequencies.get(normalize_label(name), 0)
        return math.log((total_professors + 1) / (seen + 1))

    specificity = sum(rarity(name) for name in result.matched_areas)
    specificity += RELATED_CREDIT * sum(rarity(prof) for _, prof in result.related_areas)

    own = {normalize_label(name) for name in professor_areas if name and not is_generic_area(name)}
    focus = len(result.matched_areas) / len(own) if own else 0.0

    corroborated = sum(1 for item in result.evidence if item.type == "professor_summary_mentions_area")
    return (round(specificity, 6), round(focus, 6), corroborated)


def rank_key(
    result: ProfessorMatchResult,
    professor_areas: list[str],
    frequencies: Counter[str],
    total_professors: int,
    name: str,
) -> tuple:
    specificity, focus, corroborated = tiebreak(result, professor_areas, frequencies, total_professors)
    return (-result.score, -specificity, -focus, -corroborated, name.lower())
