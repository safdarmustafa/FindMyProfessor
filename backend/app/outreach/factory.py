from __future__ import annotations

import os

from app.outreach.deterministic import DeterministicTemplateProvider
from app.outreach.provider import EmailGenerationProvider


def get_email_provider() -> EmailGenerationProvider:
    """
    Return the appropriate email generation provider.

    If EMAIL_LLM_API_KEY (preferred) or LLM_API_KEY (shared) is set in the
    environment, return the LLM provider.  Otherwise return the zero-cost
    deterministic template provider.

    API keys are never exposed to the frontend.
    """
    api_key = os.getenv("EMAIL_LLM_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return DeterministicTemplateProvider()

    from app.outreach.llm import LlmEmailProvider  # deferred import

    return LlmEmailProvider(
        api_key=api_key,
        base_url=os.getenv("EMAIL_LLM_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("EMAIL_LLM_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
