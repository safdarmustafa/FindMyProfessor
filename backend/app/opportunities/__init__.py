from app.opportunities.models import OpportunityRecord, UniversityFitResult
from app.opportunities.scoring import is_clearly_undergraduate, score_university_opportunities

__all__ = [
    "OpportunityRecord",
    "UniversityFitResult",
    "is_clearly_undergraduate",
    "score_university_opportunities",
]
