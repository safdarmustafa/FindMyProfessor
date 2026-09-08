from __future__ import annotations

from abc import ABC, abstractmethod


class ParseError(ValueError):
    pass


class CvParser(ABC):
    format_id: str

    @abstractmethod
    def extract_text(self, content: bytes) -> str:
        """Return normalized CV text or raise ParseError."""
