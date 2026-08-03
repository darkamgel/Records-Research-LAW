"""PDF text extraction with OCR fallback.

Primary extraction uses ``pypdf`` (pure-python, always available). ``PyMuPDF`` is
used when installed for higher-quality extraction. OCR (``pytesseract`` +
``PyMuPDF`` rasterization) is only invoked when embedded text is missing or very
sparse, so OCR is a fallback rather than the default.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PageResult:
    page_number: int
    text: str
    ocr_used: bool = False


@dataclass
class PdfExtractionResult:
    pages: list[PageResult] = field(default_factory=list)
    full_text: str = ""
    ocr_used: bool = False
    extraction_quality: float = 0.0
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _quality_score(text: str, page_count: int) -> float:
    """Rough 0..1 score: characters-per-page relative to a typical text page."""
    if page_count <= 0:
        return 0.0
    chars_per_page = len(text) / page_count
    # ~1500+ chars/page is a healthy text page.
    return max(0.0, min(1.0, chars_per_page / 1500.0))


def _extract_pypdf(data: bytes) -> tuple[list[str], dict, list[str]]:
    import io

    from pypdf import PdfReader

    warnings: list[str] = []
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            warnings.append("PDF is encrypted; extraction may be incomplete.")
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"pypdf page error: {exc}")
            pages.append("")
    meta = {}
    try:
        if reader.metadata:
            meta = {k[1:] if k.startswith("/") else k: str(v) for k, v in reader.metadata.items()}
    except Exception:
        pass
    return pages, meta, warnings


def _ocr_pages(data: bytes, page_texts: list[str]) -> tuple[list[str], bool, list[str]]:
    """OCR only the pages that look empty. Returns updated texts."""
    warnings: list[str] = []
    if not settings.ocr_enabled:
        return page_texts, False, ["OCR disabled by configuration."]
    try:  # pragma: no cover - optional dependency path
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except Exception:
        return page_texts, False, ["OCR dependencies not installed; skipped OCR fallback."]

    import io

    ocr_used = False
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # pragma: no cover
        return page_texts, False, [f"Could not open PDF for OCR: {exc}"]

    for i, existing in enumerate(page_texts):
        if len(existing.strip()) >= 40:
            continue
        try:
            page = doc[i]
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
            if text.strip():
                page_texts[i] = text
                ocr_used = True
        except Exception as exc:  # pragma: no cover
            warnings.append(f"OCR failed on page {i + 1}: {exc}")
    return page_texts, ocr_used, warnings


def extract_pdf(data: bytes) -> PdfExtractionResult:
    result = PdfExtractionResult()
    try:
        page_texts, meta, warnings = _extract_pypdf(data)
    except Exception as exc:
        result.warnings.append(f"PDF parse failed: {exc}")
        return result

    result.metadata = meta
    result.warnings.extend(warnings)

    joined = "\n".join(page_texts)
    quality = _quality_score(joined, len(page_texts))

    # Decide whether OCR is necessary: low quality or empty pages present.
    needs_ocr = quality < 0.15 or any(len(p.strip()) < 40 for p in page_texts)
    if needs_ocr:
        page_texts, ocr_used, ocr_warnings = _ocr_pages(data, page_texts)
        result.ocr_used = ocr_used
        result.warnings.extend(ocr_warnings)
        joined = "\n".join(page_texts)
        quality = _quality_score(joined, len(page_texts))

    result.pages = [
        PageResult(page_number=i + 1, text=t, ocr_used=result.ocr_used and len(t.strip()) > 0)
        for i, t in enumerate(page_texts)
    ]
    result.full_text = joined
    result.extraction_quality = round(quality, 3)
    return result


def extract_plain_text(data: bytes) -> PdfExtractionResult:
    text = data.decode("utf-8", errors="replace")
    result = PdfExtractionResult()
    result.pages = [PageResult(page_number=1, text=text)]
    result.full_text = text
    result.extraction_quality = 1.0 if text.strip() else 0.0
    return result
