from __future__ import annotations

from io import BytesIO

from odf import teletype, text
from odf.opendocument import load

from app.cv.parsers.base import CvParser, ParseError


class OdtParser(CvParser):
    format_id = "odt"

    def extract_text(self, content: bytes) -> str:
        try:
            document = load(BytesIO(content))
        except Exception as exc:
            raise ParseError("The OpenDocument file could not be opened.") from exc
        parts: list[str] = []
        for element in document.getElementsByType(text.P) + document.getElementsByType(text.H):
            parts.append(teletype.extractText(element))
        return "\n".join(parts)
