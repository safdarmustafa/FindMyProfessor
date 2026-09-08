from __future__ import annotations

from app.cv.parsers.base import CvParser, ParseError
from app.cv.parsers.doc import DocParser
from app.cv.parsers.docx import DocxParser
from app.cv.parsers.odt import OdtParser
from app.cv.parsers.pdf import PdfParser
from app.cv.parsers.rtf import RtfParser
from app.cv.parsers.txt import TxtParser

_PARSERS: dict[str, CvParser] = {
    parser.format_id: parser
    for parser in (
        PdfParser(),
        DocxParser(),
        DocParser(),
        TxtParser(),
        RtfParser(),
        OdtParser(),
    )
}


def parser_for(format_id: str) -> CvParser:
    parser = _PARSERS.get(format_id)
    if parser is None:
        raise ParseError(f"No parser is registered for '{format_id}'.")
    return parser


def extract_normalized_text(format_id: str, content: bytes) -> str:
    text = parser_for(format_id).extract_text(content)
    normalized = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))
    normalized = normalized.strip()
    if not normalized:
        raise ParseError(
            "Your CV was uploaded successfully, but we couldn't extract its text. "
            "Please upload another version."
        )
    return normalized
