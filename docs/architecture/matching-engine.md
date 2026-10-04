# Matching Engine & Opportunity Scoring

> Part of the [FindMyProfessor Architecture Documentation](../ARCHITECTURE.md).

This is the core "product logic" of FindMyProfessor: given a student's confirmed profile, rank professors by research fit, optionally filtered/re-ranked by concrete funded opportunities. **It is entirely deterministic and rule-based — there is no ML model, no embeddings, no vector search, and no LLM anywhere in this engine.** That is a deliberate, verifiable design choice (see §7).

## 1. Endpoint

**`GET /matching/professors`** — `backend/app/routers/matching.py:14-34`, delegating to `match_professors()` in `backend/app/services/matching.py:30`.

| Param | Type | Meaning |
|---|---|---|
| `profile_id` | via `auth.require_profile_id` | Whose confirmed CV profile to score against |
| `mode` | `"research"` \| `"opportunity"` \| `"both"` (default `research`) | See §5 |
| `limit` | int, 1–100, default 25 | Result cap after ranking |
| `university_id` | UUID, optional | Filters to one university |
| `min_score` | int 0–100, default 0 | Drop professors below this research score |
| `email_only` | bool, default false | Only professors with a listed email |
| `opportunity_type` | string, optional | `internship`/`ra`/`masters`/`phd` |
| `opportunity_status` | string, optional | `open`/`upcoming`/`unknown`/`closed` |

## 2. Inputs

**Student signals** come from the confirmed CV profile (`_confirmed_student()`, `services/matching.py:111-129` — requires a confirmed CV or returns HTTP 400): `research_interests`, `research_signals`, and free text from `projects`/`publications` (title + description scanned for catalog-label hits). See [CV Pipeline §11](cv-pipeline.md#11-what-matching-actually-consumes-vs-whats-extracted-but-unused) for the full extracted-vs-used breakdown — notably, `skills` are never used here.

**Professor signals** are `professor_research_areas` (structured tags joined from the `research_areas` catalog, `services/matching.py:160-175`) and `research_summary` (free text) — but the free text plays a strictly *corroborating* role, never a matching one (proven by `tests/test_matching_scoring.py:191-202`, `test_professor_summary_cannot_create_new_match`).

## 3. The scoring formula — `backend/app/matching/scoring.py`

```python
WEIGHTS = {
    "interests":      0.55,
    "signals":        0.20,
    "artifacts":      0.20,   # projects + publications
    "corroboration":  0.05,   # research_summary text backing up a match
}
PRIORITY_HIGH   = 80
PRIORITY_NORMAL = 50
```

**Per-component coverage score** (`_coverage_score`, `scoring.py:136-140`):

```
coverage(component) = 0                         if student has no labels in this component
                     = 100 * |student ∩ prof| / |student|    otherwise
```

The denominator is the **student's** label count, not the professor's. This is a deliberate anti-bias choice: a professor listing many unrelated research areas does not dilute their score just for having a broad profile — proven by `test_area_count_bias_avoided` (`tests/test_matching_scoring.py:362-373`).

Corroboration is computed only if there is at least one matched area *and* the professor has a `research_summary`: `100 * (matched areas that also textually appear in the summary) / (total matched areas)` (`scoring.py:81-87`).

**Combining components — the renormalization that matters most:**

```python
def combine_components(components: dict[str, float | None]) -> float:
    available = {k: v for k, v in components.items() if v is not None}
    total_weight = sum(WEIGHTS[k] for k in available)
    return sum(WEIGHTS[k] * v for k, v in available.items()) / total_weight
```

Weights are **renormalized across whichever components actually have data**, not applied against a fixed 100% denominator. A student with *only* explicit `research_interests` populated (no signals, no projects/publications, no professor summary to corroborate against) gets their `interests` component's weight treated as 100% of the final score, not capped at 55% — proven directly by `test_unavailable_components_renormalize` (`tests/test_matching_scoring.py:376-380`): `interests=100` alone yields a final score of `100`, not `55`. **This is the single most surprising implementation detail in the whole matching engine** — it means the "55/20/20/5" split is better described as *relative* priority weighting than a literal fixed formula.

**Final score:** round-half-up, then clamp to `[0, 100]` (`scoring.py:50-52`).

**Priority label:** `score >= 80 → "high"`, `score >= 50 → "normal"`, else `"low"` (`scoring.py:42-47`, thresholds confirmed by `tests/test_matching_scoring.py:337-343`).

## 4. Text normalization and the "generic terms" list

`normalize_label()` (`backend/app/matching/normalize.py:9-13`) lowercases and collapses whitespace for every label comparison on both sides.

`GENERIC_RESEARCH_AREAS = frozenset({"computer science"})` (`normalize.py:6`) — **this is a single hardcoded entry, not a broad stopword list.** It's stripped from both the student's and the professor's label sets before scoring (`scoring_labels()`, `normalize.py:49-50`), so matching purely on "Computer Science" contributes nothing to the score (proven by `test_computer_science_does_not_inflate_score`, `tests/test_matching_scoring.py:86-104`). If you were expecting a curated list of dozens of overly-generic terms — there isn't one; it's exactly this one string.

## 5. Research vs. Opportunity vs. Both mode

All three modes compute the **identical** research score described above for every candidate professor. They differ only in filtering and sort order (`services/matching.py:75-76, 292-300`):

| Mode | Filtering | Sort key |
|---|---|---|
| `research` | None (opportunity data not required) | `(-research_score, name, id)` |
| `opportunity` | Drops any professor with no usable, non-closed opportunity attached (`fit.score <= 0` or no `best_opportunity`) | `(-fit_score, -research_score, name, id)` |
| `both` | Same universe as `research` (opportunities attached but not filtering) | `(-research_score, -fit_score, name, id)` |

## 6. Filters — implementation notes

- `min_score`: a **strict `<`** drop after scoring — a professor scoring exactly the threshold is kept, not dropped (`services/matching.py:67-68`).
- `email_only`: a pure presence filter on `professors.email` at candidate-load time — proven not to influence the score itself (`test_email_only_is_filter_not_score`).
- `university_id`: an inner-join filter through `departments.university_id`.
- `opportunity_type`/`opportunity_status`: filter the opportunity record set *before* it's attached to a professor (`services/matching.py:214-229`), so these only affect which opportunity is considered "attached," not the research score.

## 7. Opportunity scoring — `backend/app/opportunities/scoring.py`

```python
STATUS_BASE = {"open": 100, "upcoming": 80, "unknown": 50}
```

`closed` opportunities are **filtered out entirely** before scoring even runs (`scoring.py:51`) — they never appear as a candidate's "best opportunity."

**Bonuses** (`scoring.py:74-94`):
- `+5` if `international_eligible is True` — applied **unconditionally**, regardless of the actual student's nationality (there is no nationality field checked against it).
- `+10` if `undergraduate_eligible is True` **and** the student is detected as clearly undergraduate via a regex-based check on their education text (`is_clearly_undergraduate`, `scoring.py:26-43` — a graduate-degree regex match short-circuits this to `False` even for a student with a mixed/ambiguous education history).

Each opportunity's score is capped at `min(100, score)`.

**University-level aggregation** (`score_university_opportunities`, `scoring.py:46-71`) picks only the **single best-scoring** non-closed opportunity for a given professor/lab/university — multiple good opportunities do not stack or add up (`test_multiple_opportunities_do_not_stack`). The result type's own docstring is explicit that this is university-level context, never a professor-specific claim: *"University-level context only. Never a professor-specific opportunity score."* (`backend/app/schemas/matching.py:90-93`).

## 8. Opportunity ↔ professor/lab/university relationship

`backend/migrations/20260908_opportunities_nullable_professor_lab.sql` exists specifically to drop `NOT NULL` on `professor_id`/`lab_id` "so university-wide (and lab-only) opportunities can be stored without fabricating a professor." Association resolution (`opportunities_for_professor`, `services/matching.py:232-253`) is a **strict priority chain**: if the opportunity has a `professor_id`, match on that; else if it has a `lab_id`, match on that; else fall through to `university_id`. An opportunity is checked against exactly one tier, based on whichever foreign key is actually populated — it is never simultaneously "this professor's" and "this university's."

## 9. Worked example (real numbers, not invented)

From `tests/test_matching_scoring.py:76-84`:

- Student `research_interests = ["Computer Vision", "Medical AI", "Edge AI"]`
- Professor `research_areas = ["Computer Vision", "Medical AI", "Robotics"]`
- No `research_signals`, no `projects`/`publications`, no professor `research_summary`

**Step by step:**
1. Intersection = `{"Computer Vision", "Medical AI"}` → 2 of the student's 3 interests.
2. `interest_score = 100 * 2 / 3 = 66.667`
3. Only the `interests` component has data (weight 0.55); everything else is `None`.
4. `combine_components` renormalizes: `(0.55 / 0.55) * 66.667 = 66.667` — the weight cancels out entirely because it's the only available component.
5. `clamp_score(66.667)` → round-half-up → `67`.
6. **Final research score = 67**, matching the test's exact assertion (`test_matching_scoring.py:83`).
7. `priority_for_score(67)` → `"normal"` (below the 80 "high" threshold).
8. `research_overlap = ["Computer Vision", "Medical AI"]` is surfaced to the frontend as the human-readable "why this match" evidence.

## 10. Limitations (evidenced by code)

- Purely exact-label rule matching — no embeddings, no fuzzy/semantic similarity, no ML model of any kind. "Computer Vision" and "CV" would not match each other unless both are already normalized to the same catalog label upstream.
- The generic-terms exclusion list is exactly one entry (`"computer science"`) — many other genuinely generic terms (e.g. "machine learning," "artificial intelligence" as standalone tags) are not excluded and would inflate scores if broadly tagged.
- No feedback/learning loop — every score is a pure, deterministic function of the current data; running the same inputs twice always produces the same output (verified by determinism tests in the matching test suite).
- `skills` are entirely excluded from research matching (see [CV Pipeline §11](cv-pipeline.md#11-what-matching-actually-consumes-vs-whats-extracted-but-unused)).
- The international-student bonus ignores the student's actual nationality — it fires purely off the opportunity's `international_eligible` flag.
- Opportunity fit scoring has **no topical relevance component at all** — a student's research match score and their opportunity fit score are computed completely independently and only combined by sort order in `both`/`opportunity` mode, never blended into one number.
- Best-opportunity aggregation discards information about how many good opportunities a professor/university actually has.
- No deadline-proximity or recency weighting anywhere in the scoring math.

## 11. Conceptual vs. implementation — a note for interviews

**Conceptually**, describe it as: "a weighted similarity score across four signal types — explicit interests, inferred signals, project/publication evidence, and free-text corroboration — normalized so a thinner CV isn't unfairly penalized for missing signal types." **Precisely**, the mechanism is: intersection-over-student-cardinality per component, weights renormalized across whatever components have data, rounded and clamped to 0–100. Both descriptions are accurate; the first is what you'd say to a non-technical interviewer, the second is what you'd say if asked to whiteboard it.
