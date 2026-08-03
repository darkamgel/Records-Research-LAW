from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import JobStatus, ProcessingStatus
from app.schemas.common import ORMModel


class UploadedFileOut(ORMModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_hash: str
    size_bytes: int
    processing_status: ProcessingStatus
    processing_error: str | None
    retry_count: int
    source_name: str | None
    original_url: str | None
    jurisdiction: str | None
    record_type: str | None
    created_at: datetime


class IngestionJobOut(ORMModel):
    id: uuid.UUID
    source_id: uuid.UUID | None
    uploaded_file_id: uuid.UUID | None
    job_type: str
    status: JobStatus
    records_created: int
    records_failed: int
    progress: int
    error_message: str | None
    stats: dict | None
    created_at: datetime
    updated_at: datetime


class DocumentOut(ORMModel):
    id: uuid.UUID
    title: str | None
    mime_type: str | None
    page_count: int
    char_count: int
    extraction_quality: float
    ocr_used: bool
    processing_status: ProcessingStatus
    warnings: list | None


class DocumentPageOut(ORMModel):
    page_number: int
    text: str | None
    char_count: int
    ocr_used: bool


class DocumentDetailOut(DocumentOut):
    full_text: str | None
    doc_metadata: dict | None
    pages: list[DocumentPageOut] = []
