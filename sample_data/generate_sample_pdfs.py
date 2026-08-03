"""Generate demonstration PDFs.

Creates:
- ``sample_text_filing.pdf``  : a text-based PDF (extractable without OCR).
- ``sample_scanned_filing.pdf``: an image-only PDF (no text layer) that triggers
  the OCR fallback path.

The text PDF is built by hand (no third-party dependency). The scanned PDF is
generated with Pillow when available; otherwise it is skipped with a note.

Run:  python sample_data/generate_sample_pdfs.py
"""

from __future__ import annotations

import pathlib

HERE = pathlib.Path(__file__).parent

TEXT_LINES = [
    "DEMONSTRATION COURT FILING (SYNTHETIC DATA - NOT A REAL RECORD)",
    "",
    "IN THE DISTRICT COURT OF DEMO COUNTY, STATE OF DX",
    "",
    "Case No. 2023-CV-004821",
    "",
    "Plaintiff: Jonathan A. Rivera",
    "Address: 482 Maple Street, Springfield, DX 55011",
    "Filed: March 14, 2023",
    "",
    "NATURE OF ACTION: Breach of contract. The plaintiff Jonathan A. Rivera",
    "alleges that the defendant failed to perform under a written agreement",
    "dated January 5, 2023. This is fictional demonstration content.",
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_text_pdf(lines: list[str]) -> bytes:
    content_parts = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for i, line in enumerate(lines):
        if i == 0:
            content_parts.append(f"({_escape(line)}) Tj")
        else:
            content_parts.append("T*")
            content_parts.append(f"({_escape(line)}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n"
    pdf += f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_pos}\n".encode()
    pdf += b"%%EOF"
    return bytes(pdf)


def build_scanned_pdf() -> bytes | None:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    img = Image.new("RGB", (1000, 1300), "white")
    draw = ImageDraw.Draw(img)
    text = (
        "DEMONSTRATION SCANNED FILING (SYNTHETIC)\n\n"
        "IN THE PROBATE COURT OF DEMO COUNTY, DX\n\n"
        "Estate of Harold Winters\n"
        "Case No. 2020-PR-000871\n"
        "58 Cedar Court, Baytown, DX 55402\n\n"
        "This page is rendered as an image with no text layer,\n"
        "so extraction requires OCR (Tesseract)."
    )
    y = 80
    for line in text.split("\n"):
        draw.text((80, y), line, fill="black")
        y += 40
    import io

    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


def main() -> None:
    text_pdf = build_text_pdf(TEXT_LINES)
    (HERE / "sample_text_filing.pdf").write_bytes(text_pdf)
    print(f"Wrote sample_text_filing.pdf ({len(text_pdf)} bytes)")

    scanned = build_scanned_pdf()
    if scanned:
        (HERE / "sample_scanned_filing.pdf").write_bytes(scanned)
        print(f"Wrote sample_scanned_filing.pdf ({len(scanned)} bytes)")
    else:
        print("Pillow not installed; skipped scanned PDF. Install extras: pip install '.[ocr]'")


if __name__ == "__main__":
    main()
