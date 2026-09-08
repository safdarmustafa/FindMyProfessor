from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.cv.parsers.base import CvParser, ParseError


class PdfParser(CvParser):
    format_id = "pdf"

    def extract_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
        except PdfReadError as exc:
            raise ParseError("The PDF could not be read. It may be corrupted.") from exc
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ParseError(
                    "This PDF is password-protected. Please upload an unlocked version."
                ) from exc
        pages: list[str] = []
        try:
            for page in reader.pages:
                pages.append(page.extract_text() or "")
        except FileNotDecryptedError as exc:
            raise ParseError(
                "This PDF is password-protected. Please upload an unlocked version."
            ) from exc
        except Exception as exc:
            raise ParseError("The PDF text could not be extracted.") from exc
        return "\n".join(pages)
