"""Minimal text-PDF builder for tests (no third-party dependency)."""

from __future__ import annotations


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

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n" + f"0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n" + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n" + f"{xref_pos}\n".encode() + b"%%EOF"
    return bytes(pdf)


SAMPLE_TEXT_PDF = build_text_pdf(
    [
        "DEMONSTRATION COURT FILING (SYNTHETIC DATA)",
        "Case No. 2023-CV-004821",
        "Plaintiff: Jonathan A. Rivera",
        "Address: 482 Maple Street, Springfield, DX 55011",
        "Filed: March 14, 2023. Breach of contract. Fictional content.",
    ]
)
