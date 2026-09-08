from __future__ import annotations

import os

from app.cv.extraction.heuristic import HeuristicExtractionProvider
from app.cv.extraction.provider import ExtractionProvider
from app.cv.extraction.llm import LlmExtractionProvider


def get_extraction_provider() -> ExtractionProvider:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return HeuristicExtractionProvider()
    return LlmExtractionProvider(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
