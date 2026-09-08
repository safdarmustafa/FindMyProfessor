from __future__ import annotations

from abc import ABC, abstractmethod

from app.cv.extraction.schema import ExtractedStudentProfile


class ExtractionProvider(ABC):
    """Turns CV text into a structured profile. Must not invent facts."""

    @abstractmethod
    def extract(self, cv_text: str, catalog_labels: list[str]) -> ExtractedStudentProfile:
        raise NotImplementedError
