from __future__ import annotations

from app.document_processing.chunking import chunk_pages
from app.document_processing.pdf import extract_pdf, extract_plain_text
from app.tests.pdf_helpers import SAMPLE_TEXT_PDF


def test_text_pdf_extraction_no_ocr():
    result = extract_pdf(SAMPLE_TEXT_PDF)
    assert len(result.pages) == 1
    assert "Rivera" in result.full_text
    assert result.ocr_used is False
    assert result.extraction_quality > 0


def test_scanned_pdf_triggers_ocr_decision():
    # An image-only PDF (built with Pillow) has no text layer -> OCR is required.
    try:
        from PIL import Image, ImageDraw
    except Exception:
        import pytest

        pytest.skip("Pillow not installed")
    import io

    img = Image.new("RGB", (800, 1000), "white")
    ImageDraw.Draw(img).text((50, 50), "Scanned page requiring OCR", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    result = extract_pdf(buf.getvalue())
    # No embedded text; quality is ~0 which is the signal OCR is needed. When OCR
    # deps are absent, a warning is recorded (OCR remains a fallback, not default).
    assert result.extraction_quality < 0.15
    assert result.ocr_used is False
    assert any("OCR" in w for w in result.warnings)


def test_plain_text_extraction():
    result = extract_plain_text(b"Hello world. Case No. 2020-CV-9.")
    assert result.pages[0].text.startswith("Hello world")
    assert result.extraction_quality == 1.0


def test_chunking_preserves_pages_and_offsets():
    pages = [(1, "a" * 2000), (2, "b" * 500)]
    chunks = chunk_pages(pages, chunk_size=800, overlap=100)
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2
    assert all(c.char_end > c.char_start for c in chunks)
