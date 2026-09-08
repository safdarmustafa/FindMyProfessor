from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from app.cv.parsers.base import ParseError
from app.cv.parsers.registry import extract_normalized_text, parser_for
from app.cv.validation import UnsupportedCvError, detect_cv_type
from tests.builders import doc_bytes, docx_bytes, odt_bytes, pdf_bytes, rtf_bytes, txt_bytes
from tests.sample_cv import SAMPLE_CV


@pytest.mark.parametrize(
    "filename,builder,format_id",
    [
        ("cv.pdf", pdf_bytes, "pdf"),
        ("cv.docx", docx_bytes, "docx"),
        ("cv.doc", doc_bytes, "doc"),
        ("cv.txt", txt_bytes, "txt"),
        ("cv.rtf", rtf_bytes, "rtf"),
        ("cv.odt", odt_bytes, "odt"),
    ],
)
def test_detect_and_parse_supported_formats(filename, builder, format_id):
    content = builder(SAMPLE_CV)
    detected = detect_cv_type(filename, content, None)
    assert detected.format_id == format_id
    assert parser_for(format_id).format_id == format_id
    text = extract_normalized_text(format_id, content)
    assert "Alex Rivera" in text
    assert "Computer Vision" in text


def test_rejects_unsupported_extension():
    with pytest.raises(UnsupportedCvError):
        detect_cv_type("photo.png", b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png")


def test_rejects_mismatched_extension():
    content = txt_bytes(SAMPLE_CV)
    with pytest.raises(UnsupportedCvError):
        detect_cv_type("cv.pdf", content, "application/pdf")


def test_empty_file_rejected():
    with pytest.raises(UnsupportedCvError):
        detect_cv_type("cv.txt", b"", "text/plain")


def test_corrupt_pdf_fails_gracefully():
    content = b"%PDF-1.4\nthis is not a valid pdf body"
    detect_cv_type("broken.pdf", content, "application/pdf")
    with pytest.raises(ParseError):
        extract_normalized_text("pdf", content)


def test_empty_text_pdf_fails_gracefully():
    content = pdf_bytes("")
    with pytest.raises(ParseError):
        extract_normalized_text("pdf", content)


def test_whitespace_txt_fails_after_upload_validation():
    content = b"   \n\n"
    detect_cv_type("cv.txt", content, "text/plain")
    with pytest.raises(ParseError):
        extract_normalized_text("txt", content)


def test_password_protected_pdf_fails_gracefully():
    reader = PdfReader(BytesIO(pdf_bytes(SAMPLE_CV)))
    writer = PdfWriter()
    writer.append(reader)
    writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    content = buffer.getvalue()
    detect_cv_type("locked.pdf", content, "application/pdf")
    with pytest.raises(ParseError):
        extract_normalized_text("pdf", content)
