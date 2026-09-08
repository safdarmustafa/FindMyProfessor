from __future__ import annotations

import re
from io import BytesIO

from app.cv.parsers.base import CvParser, ParseError
from app.cv.parsers.docx import DocxParser


class DocParser(CvParser):
    format_id = "doc"

    def extract_text(self, content: bytes) -> str:
        if content.startswith(b"PK"):
            try:
                return DocxParser().extract_text(content)
            except ParseError:
                pass
        if content.startswith(b"\xd0\xcf\x11\xe0"):
            extracted = _extract_ole_strings(content)
            if extracted.strip():
                return extracted
        raise ParseError(
            "This legacy Word (.doc) file could not be read. "
            "Please export it to .docx or PDF and upload again."
        )


def _extract_ole_strings(content: bytes) -> str:
    try:
        import olefile
    except ImportError as exc:
        raise ParseError("Legacy Word support is unavailable.") from exc
    try:
        ole = olefile.OleFileIO(BytesIO(content))
    except Exception as exc:
        raise ParseError("The Word document could not be opened.") from exc
    chunks: list[bytes] = []
    try:
        for stream in ole.listdir():
            name = "/".join(stream)
            if name.lower() in {"worddocument", "1table", "0table"} or "text" in name.lower():
                chunks.append(ole.openstream(stream).read())
    finally:
        ole.close()
    text_parts: list[str] = []
    for chunk in chunks or [content]:
        text_parts.append(_printable_utf16(chunk))
        text_parts.append(_printable_ascii(chunk))
    return "\n".join(part for part in text_parts if part.strip())


def _printable_utf16(chunk: bytes) -> str:
    try:
        decoded = chunk.decode("utf-16le", errors="ignore")
    except Exception:
        return ""
    return "\n".join(_clean_runs(decoded))


def _printable_ascii(chunk: bytes) -> str:
    matches = re.findall(rb"[\t\r\n\x20-\x7e]{5,}", chunk)
    return "\n".join(m.decode("ascii", errors="ignore") for m in matches)


def _clean_runs(text: str) -> list[str]:
    lines = []
    current = []
    for char in text:
        if char == "\x00":
            continue
        if char.isprintable() or char in "\n\t":
            current.append(char)
        else:
            if current:
                lines.append("".join(current).strip())
                current = []
    if current:
        lines.append("".join(current).strip())
    return [line for line in lines if len(line) >= 3]
