from __future__ import annotations

from app.cv.parsers.base import CvParser, ParseError


class TxtParser(CvParser):
    format_id = "txt"

    def extract_text(self, content: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                text = None
        if text is None:
            raise ParseError("The text file could not be decoded.")
        return text.replace("\r\n", "\n").replace("\r", "\n")
