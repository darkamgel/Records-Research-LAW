"""Safe local file storage for uploads.

Files are stored under ``settings.upload_dir`` with a random, generated filename
(never the user-supplied name) to avoid path traversal and collisions. Original
filenames are kept only as metadata in the database.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from app.core.config import settings

ALLOWED_MIME = {
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".csv",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/json": ".json",
    "text/json": ".json",
}

EXT_BY_SUFFIX = {".csv": "text/csv", ".pdf": "application/pdf", ".txt": "text/plain", ".json": "application/json"}


def guess_mime(filename: str, provided: str | None) -> str | None:
    if provided in ALLOWED_MIME:
        return provided
    suffix = Path(filename).suffix.lower()
    return EXT_BY_SUFFIX.get(suffix)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_file(data: bytes, mime_type: str) -> str:
    """Write bytes to disk using a generated name. Returns the stored filename."""
    base = ensure_upload_dir()
    suffix = ALLOWED_MIME.get(mime_type, ".bin")
    stored = f"{uuid.uuid4().hex}{suffix}"
    with open(base / stored, "wb") as fh:
        fh.write(data)
    return stored


def read_file(stored_filename: str) -> bytes:
    path = Path(settings.upload_dir) / stored_filename
    # Guard against traversal via crafted stored names.
    resolved = path.resolve()
    if os.path.commonpath([resolved, Path(settings.upload_dir).resolve()]) != str(
        Path(settings.upload_dir).resolve()
    ):
        raise ValueError("Invalid file path.")
    with open(resolved, "rb") as fh:
        return fh.read()


def delete_file(stored_filename: str) -> None:
    path = Path(settings.upload_dir) / stored_filename
    if path.exists():
        path.unlink()
