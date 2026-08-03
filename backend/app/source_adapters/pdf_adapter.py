from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.enums import AccessMethod, SourceType
from app.source_adapters.base import (
    NormalizedRecord,
    RawSourceRecord,
    SourceDescriptor,
    SourceQuery,
    SourceValidationResult,
)


class PDFUploadAdapter:
    """Descriptor + normalization for user-uploaded PDF documents.

    The heavy lifting (text extraction, OCR, chunking, entity extraction) is done
    by the document-processing pipeline; this adapter records provenance and
    produces a single record per document.
    """

    descriptor = SourceDescriptor(
        source_key="pdf_upload",
        source_name="PDF / Document Upload",
        source_type=SourceType.file_upload,
        access_method=AccessMethod.user_upload,
        jurisdiction=None,
        base_url=None,
        supported_record_types=["*"],
        terms_notes=(
            "Processes only user-uploaded documents. OCR is used as a fallback "
            "for scanned pages only."
        ),
        attribution="User-provided upload.",
        requires_auth=False,
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        return SourceValidationResult(True, ["PDF upload adapter ready."])

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        return []

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        p = record.payload
        return NormalizedRecord(
            external_record_id=record.external_id,
            record_type=self._config.get("record_type") or "document",
            title=p.get("title"),
            description=p.get("description"),
            jurisdiction=self._config.get("jurisdiction"),
            filing_date=p.get("filing_date"),
            event_date=None,
            case_number=p.get("case_number"),
            original_url=record.original_url,
            primary_name=p.get("primary_name"),
            address=p.get("address"),
            raw_payload=p,
            source_accessed_at=record.retrieved_at or datetime.now(timezone.utc),
        )
