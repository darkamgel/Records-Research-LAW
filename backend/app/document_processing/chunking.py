"""Text chunking that preserves page numbers and character offsets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_index: int
    page_number: int | None
    char_start: int
    char_end: int
    text: str


def chunk_pages(
    pages: list[tuple[int, str]], chunk_size: int = 1200, overlap: int = 150
) -> list[Chunk]:
    """Chunk per page so each chunk carries an accurate page number and offsets.

    ``pages`` is a list of ``(page_number, text)``. Offsets are relative to the
    concatenated full text (pages joined by ``\n``) to match stored full_text.
    """
    chunks: list[Chunk] = []
    idx = 0
    global_offset = 0
    for page_number, text in pages:
        start = 0
        text = text or ""
        n = len(text)
        if n == 0:
            global_offset += 1  # account for the join newline
            continue
        while start < n:
            end = min(start + chunk_size, n)
            piece = text[start:end]
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    page_number=page_number,
                    char_start=global_offset + start,
                    char_end=global_offset + end,
                    text=piece,
                )
            )
            idx += 1
            if end >= n:
                break
            start = end - overlap
        global_offset += n + 1  # +1 for the newline used when joining pages
    return chunks
