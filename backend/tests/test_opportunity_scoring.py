from __future__ import annotations

from uuid import uuid4

from app.cv.extraction.schema import EducationExtract, ExtractedStudentProfile
from app.opportunities.models import OpportunityRecord
from app.opportunities.scoring import is_clearly_undergraduate, score_university_opportunities
from app.services.matching import opportunities_for_professor


def _opp(**kwargs) -> OpportunityRecord:
    defaults = {
        "id": str(uuid4()),
        "university_id": "uni-1",
        "professor_id": None,
        "lab_id": None,
        "title": "Program",
        "opportunity_type": "phd",
        "status": "open",
    }
    defaults.update(kwargs)
    return OpportunityRecord(**defaults)


def test_open_opportunity_fit():
    result = score_university_opportunities([_opp(status="open")])
    assert result.score == 100
    assert result.best_opportunity is not None
    assert 0 <= result.score <= 100


def test_upcoming_opportunity_fit():
    assert score_university_opportunities([_opp(status="upcoming")]).score == 80


def test_unknown_opportunity_fit():
    assert score_university_opportunities([_opp(status="unknown")]).score == 50
    assert score_university_opportunities([_opp(status=None)]).score == 50


def test_closed_opportunity_gives_zero():
    result = score_university_opportunities([_opp(status="closed")])
    assert result.score == 0
    assert result.best_opportunity is None
    assert result.non_closed_opportunity_count == 0


def test_international_eligibility_bonus():
    base = score_university_opportunities([_opp(status="upcoming")])
    bonus = score_university_opportunities(
        [_opp(status="upcoming", international_eligible=True)]
    )
    assert bonus.score == base.score + 5
    assert "International eligibility is confirmed." in bonus.why


def test_undergraduate_bonus_only_when_clear():
    undergrad = ExtractedStudentProfile(
        education=[EducationExtract(degree="B.Tech", field_of_study="Computer Science")]
    )
    graduate = ExtractedStudentProfile(
        education=[EducationExtract(degree="M.S.", field_of_study="Computer Science")]
    )
    empty = ExtractedStudentProfile()
    mixed = ExtractedStudentProfile(
        education=[
            EducationExtract(degree="B.S."),
            EducationExtract(degree="Master of Science"),
        ]
    )
    assert is_clearly_undergraduate(undergrad) is True
    assert is_clearly_undergraduate(graduate) is False
    assert is_clearly_undergraduate(empty) is False
    assert is_clearly_undergraduate(mixed) is False

    opportunity = [_opp(status="open", undergraduate_eligible=True)]
    with_bonus = score_university_opportunities(opportunity, student_is_undergraduate=True)
    without = score_university_opportunities(opportunity, student_is_undergraduate=False)
    assert with_bonus.score == 100
    assert without.score == 100
    upcoming = [_opp(status="upcoming", undergraduate_eligible=True)]
    assert score_university_opportunities(upcoming, student_is_undergraduate=True).score == 90
    assert score_university_opportunities(upcoming, student_is_undergraduate=False).score == 80


def test_multiple_opportunities_do_not_stack():
    stacked = score_university_opportunities(
        [
            _opp(status="open", international_eligible=True),
            _opp(status="open", international_eligible=True),
            _opp(status="upcoming"),
        ]
    )
    single = score_university_opportunities(
        [_opp(status="open", international_eligible=True)]
    )
    assert stacked.score == single.score
    assert stacked.non_closed_opportunity_count == 3


def test_professor_id_null_is_university_wide():
    item = _opp(professor_id=None, lab_id=None)
    assert item.not_professor_specific is True


def test_lab_id_null_does_not_invent_lab_link():
    item = _opp(lab_id=None)
    assert item.lab_id is None


def test_professor_specific_opportunity_only_matches_that_professor():
    professor_id = str(uuid4())
    other_id = str(uuid4())
    university_id = str(uuid4())
    specific = _opp(university_id=university_id, professor_id=professor_id, title="Advisor opening")
    uni_wide = _opp(university_id=university_id, professor_id=None, title="University PhD")
    row = {
        "id": professor_id,
        "lab_id": None,
        "departments": {
            "university_id": university_id,
            "universities": {"id": university_id, "name": "Example"},
        },
    }
    other = {
        "id": other_id,
        "lab_id": None,
        "departments": {
            "university_id": university_id,
            "universities": {"id": university_id, "name": "Example"},
        },
    }
    mine = opportunities_for_professor([specific, uni_wide], row)
    theirs = opportunities_for_professor([specific, uni_wide], other)
    assert {item.title for item in mine} == {"Advisor opening", "University PhD"}
    assert {item.title for item in theirs} == {"University PhD"}
    assert specific.not_professor_specific is False
    assert uni_wide.not_professor_specific is True


def test_deterministic_repeated_runs():
    opps = [
        _opp(id="b", status="upcoming", international_eligible=True),
        _opp(id="a", status="upcoming", international_eligible=True),
    ]
    first = score_university_opportunities(opps)
    second = score_university_opportunities(opps)
    assert first == second


def test_scores_remain_in_range():
    result = score_university_opportunities(
        [
            _opp(
                status="open",
                international_eligible=True,
                undergraduate_eligible=True,
            )
        ],
        student_is_undergraduate=True,
    )
    assert result.score == 100
