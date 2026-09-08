from __future__ import annotations

from striprtf.striprtf import rtf_to_text

from app.cv.parsers.base import CvParser, ParseError


class RtfParser(CvParser):
    format_id = "rtf"

    def extract_text(self, content: bytes) -> str:
        raw = content.decode("latin-1", errors="ignore")
        try:
            text = rtf_to_text(raw)
        except Exception as exc:
            raise ParseError("The RTF document could not be parsed.") from exc
        return text.replace("\r\n", "\n").replace("\r", "\n")
