from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.cv.extraction.provider import ExtractionProvider
from app.cv.extraction.schema import ExtractedStudentProfile


SYSTEM_PROMPT = """You extract a student research profile from CV text.
Return JSON only matching the provided schema.
Rules:
- Use only facts present in the CV text.
- Do not invent publications, projects, employers, degrees, dates, or research interests.
- Do not add information from general knowledge or the internet.
- Do not treat a generic skill (for example Python or TensorFlow) as a research interest.
- Explicit research interests belong in research_interests.
- Topics evidenced by projects, publications, or research roles belong in research_signals.
- If a field is absent or uncertain, use null or an empty list.
"""


class LlmExtractionProvider(ExtractionProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 45.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def extract(self, cv_text: str, catalog_labels: list[str]) -> ExtractedStudentProfile:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "allowed_research_area_labels": catalog_labels,
                            "cv_text": cv_text[:20000],
                            "schema": ExtractedStudentProfile.model_json_schema(),
                        }
                    ),
                },
            ],
        }
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        data = _parse_json_object(content)
        return ExtractedStudentProfile.model_validate(data)


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
