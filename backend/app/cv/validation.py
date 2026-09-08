from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_CV_BYTES = 10 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".txt": "txt",
    ".rtf": "rtf",
    ".odt": "odt",
}

SUPPORTED_MIME_ALIASES = {
    "application/pdf": "pdf",
    "application/x-pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "application/vnd.ms-word": "doc",
    "text/plain": "txt",
    "text/rtf": "rtf",
    "application/rtf": "rtf",
    "application/vnd.oasis.opendocument.text": "odt",
}


class UnsupportedCvError(ValueError):
    pass


class CvTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class DetectedCvType:
    format_id: str
    extension: str
    mime_type: str | None


def validate_size(size: int) -> None:
    if size <= 0:
        raise UnsupportedCvError("The uploaded file is empty.")
    if size > MAX_CV_BYTES:
        raise CvTooLargeError(
            f"The CV is larger than the {MAX_CV_BYTES // (1024 * 1024)} MB limit."
        )


def detect_cv_type(
    filename: str,
    content: bytes,
    declared_mime: str | None = None,
) -> DetectedCvType:
    validate_size(len(content))
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedCvError(
            "Unsupported file type. Please upload a PDF, Word (.doc/.docx), "
            "text, RTF, or OpenDocument (.odt) CV."
        )
    expected = SUPPORTED_EXTENSIONS[suffix]
    sniffed = _sniff_format(content)
    mime_hint = None
    if declared_mime:
        mime_hint = SUPPORTED_MIME_ALIASES.get(declared_mime.split(";")[0].strip().lower())

    if sniffed is None:
        raise UnsupportedCvError(
            "The file contents do not match a supported CV format. "
            "Please upload another version."
        )
    if sniffed != expected:
        raise UnsupportedCvError(
            "The file extension does not match the file contents. "
            "Please upload another version."
        )
    if mime_hint and mime_hint not in {expected, sniffed}:
        # Some browsers send application/octet-stream; ignore unknown MIME.
        if declared_mime and declared_mime.split(";")[0].strip().lower() not in {
            "application/octet-stream",
            "binary/octet-stream",
        }:
            raise UnsupportedCvError(
                "The reported file type does not match a supported CV format."
            )
    mime = declared_mime.split(";")[0].strip() if declared_mime else None
    return DetectedCvType(format_id=sniffed, extension=suffix, mime_type=mime)


def _sniff_format(content: bytes) -> str | None:
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.lstrip().startswith(b"{\\rtf"):
        return "rtf"
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "doc"
    if content.startswith(b"PK"):
        return _sniff_zip_document(content)
    if _looks_like_plain_text(content):
        return "txt"
    return None


def _sniff_zip_document(content: bytes) -> str | None:
    try:
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "word/document.xml" in names:
                return "docx"
            if "mimetype" in names:
                mime = archive.read("mimetype").decode("utf-8", errors="ignore").strip()
                if mime == "application/vnd.oasis.opendocument.text":
                    return "odt"
            if "content.xml" in names and "META-INF/manifest.xml" in names:
                return "odt"
    except zipfile.BadZipFile:
        return None
    return None


def _looks_like_plain_text(content: bytes) -> bool:
    if not content:
        return False
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
            return True
        except UnicodeDecodeError:
            return False
