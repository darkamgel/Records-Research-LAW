"""Ingestion + document-processing orchestration.

``process_uploaded_file`` implements the file-based ingestion path (CSV / PDF /
TXT / JSON). ``run_source_import`` implements the pull-based path for JSON API /
RSS / demo adapters. Both create an IngestionJob for tracking and preserve full
provenance on every record.
"""

from __future__ import annotations

import asyncio
import json
import uuid

from sqlalchemy.orm import Session

from app.ai.client import get_ai_client
from app.core.logging import get_logger
from app.document_processing.chunking import chunk_pages
from app.document_processing.pdf import extract_pdf, extract_plain_text
from app.models.enums import JobStatus, ProcessingStatus
from app.models.record import Document, DocumentChunk, DocumentPage
from app.models.source import IngestionJob, Source, UploadedFile
from app.services import storage
from app.services.audit import log_audit
from app.services.record_service import create_record_from_normalized
from app.source_adapters.base import NormalizedRecord, RawSourceRecord, SourceQuery
from app.source_adapters.csv_adapter import CSVUploadAdapter
from app.source_adapters.registry import get_adapter

logger = get_logger(__name__)


def _new_job(db: Session, *, workspace_id, user_id, job_type, uploaded_file_id=None, source_id=None):
    job = IngestionJob(
        workspace_id=workspace_id,
        created_by=user_id,
        job_type=job_type,
        uploaded_file_id=uploaded_file_id,
        source_id=source_id,
        status=JobStatus.running,
        progress=0,
    )
    db.add(job)
    db.flush()
    return job


def process_uploaded_file(db: Session, file_id: uuid.UUID) -> IngestionJob:
    uf = db.get(UploadedFile, file_id)
    if uf is None:
        raise ValueError("Uploaded file not found")

    job = _new_job(
        db,
        workspace_id=uf.workspace_id,
        user_id=uf.uploaded_by,
        job_type=f"upload:{uf.mime_type}",
        uploaded_file_id=uf.id,
    )
    uf.processing_status = ProcessingStatus.processing
    db.flush()

    try:
        data = storage.read_file(uf.stored_filename)
        if uf.mime_type in ("text/csv", "application/csv", "application/vnd.ms-excel"):
            created, failed = _process_csv(db, uf, data)
        elif uf.mime_type == "application/json":
            created, failed = _process_json(db, uf, data)
        elif uf.mime_type == "application/pdf":
            created, failed = _process_document(db, uf, data, is_pdf=True)
        elif uf.mime_type == "text/plain":
            created, failed = _process_document(db, uf, data, is_pdf=False)
        else:
            raise ValueError(f"Unsupported mime type: {uf.mime_type}")

        job.records_created = created
        job.records_failed = failed
        job.progress = 100
        job.status = JobStatus.completed if failed == 0 else JobStatus.partial
        uf.processing_status = ProcessingStatus.completed
        uf.processing_error = None
        log_audit(
            db,
            workspace_id=uf.workspace_id,
            user_id=uf.uploaded_by,
            action="import_records",
            target_type="uploaded_file",
            target_id=str(uf.id),
            detail={"created": created, "failed": failed, "mime": uf.mime_type},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Processing failed for file %s", file_id)
        job.status = JobStatus.failed
        job.error_message = str(exc)
        uf.processing_status = ProcessingStatus.failed
        uf.processing_error = str(exc)
    db.commit()
    return job


def _run(coro):
    """Run a coroutine to completion whether or not an event loop is active.

    The upload endpoint is ``async`` (needs ``await file.read()``), so inline
    processing executes inside a running loop; ``asyncio.run`` would fail there.
    In that case we run the coroutine on a dedicated worker thread.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _process_csv(db: Session, uf: UploadedFile, data: bytes) -> tuple[int, int]:
    adapter = CSVUploadAdapter(data=data, config={
        "jurisdiction": uf.jurisdiction, "record_type": uf.record_type
    })
    validation = _run(adapter.validate_configuration())
    if not validation.valid:
        raise ValueError("; ".join(validation.messages))
    raws = _run(adapter.fetch_records(SourceQuery(limit=100000)))
    created = failed = 0
    for raw in raws:
        try:
            normalized = _run(adapter.normalize_record(raw))
            create_record_from_normalized(
                db,
                workspace_id=uf.workspace_id,
                source_id=None,
                normalized=_apply_provenance(normalized, uf),
            )
            created += 1
        except Exception:  # noqa: BLE001
            failed += 1
    return created, failed


def _process_json(db: Session, uf: UploadedFile, data: bytes) -> tuple[int, int]:
    parsed = json.loads(data.decode("utf-8", errors="replace"))
    items = parsed if isinstance(parsed, list) else parsed.get("records", [parsed])
    adapter = get_adapter("json_api", config={
        "jurisdiction": uf.jurisdiction, "record_type": uf.record_type
    })
    created = failed = 0
    for item in items:
        try:
            raw = RawSourceRecord(external_id=str(item.get("id", "")), payload=item)
            normalized = _run(adapter.normalize_record(raw))
            create_record_from_normalized(
                db,
                workspace_id=uf.workspace_id,
                source_id=None,
                normalized=_apply_provenance(normalized, uf),
            )
            created += 1
        except Exception:  # noqa: BLE001
            failed += 1
    return created, failed


def _process_document(db: Session, uf: UploadedFile, data: bytes, *, is_pdf: bool) -> tuple[int, int]:
    result = extract_pdf(data) if is_pdf else extract_plain_text(data)

    document = Document(
        workspace_id=uf.workspace_id,
        uploaded_file_id=uf.id,
        title=uf.original_filename,
        mime_type=uf.mime_type,
        page_count=len(result.pages),
        char_count=len(result.full_text),
        extraction_quality=result.extraction_quality,
        ocr_used=result.ocr_used,
        processing_status=ProcessingStatus.completed,
        full_text=result.full_text,
        doc_metadata=result.metadata,
        warnings=result.warnings,
    )
    db.add(document)
    db.flush()

    for page in result.pages:
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                char_count=len(page.text or ""),
                ocr_used=page.ocr_used,
            )
        )

    ai = get_ai_client()
    chunks = chunk_pages([(p.page_number, p.text) for p in result.pages])
    for ch in chunks:
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=ch.chunk_index,
                page_number=ch.page_number,
                char_start=ch.char_start,
                char_end=ch.char_end,
                text=ch.text,
                embedding=ai.embed(ch.text) if ch.text.strip() else None,
            )
        )
    db.flush()

    normalized = NormalizedRecord(
        external_record_id=None,
        record_type=uf.record_type or "document",
        title=uf.original_filename,
        description=(result.full_text[:500] or None),
        jurisdiction=uf.jurisdiction,
        filing_date=None,
        event_date=None,
        case_number=None,
        original_url=uf.original_url,
        primary_name=None,
        address=None,
        raw_payload={"document_id": str(document.id), "ocr_used": result.ocr_used},
        source_accessed_at=uf.created_at,
    )
    create_record_from_normalized(
        db,
        workspace_id=uf.workspace_id,
        source_id=None,
        normalized=normalized,
        document_id=document.id,
        document_text=result.full_text,
    )
    return 1, 0


def _apply_provenance(normalized: NormalizedRecord, uf: UploadedFile) -> NormalizedRecord:
    if uf.original_url and not normalized.original_url:
        normalized.original_url = uf.original_url
    if uf.jurisdiction and not normalized.jurisdiction:
        normalized.jurisdiction = uf.jurisdiction
    if uf.source_name:
        normalized.raw_payload = {**(normalized.raw_payload or {}), "_source_name": uf.source_name}
    return normalized


def run_source_import(
    db: Session,
    *,
    source: Source,
    config: dict | None,
    limit: int,
    user_id: uuid.UUID | None,
) -> IngestionJob:
    job = _new_job(
        db,
        workspace_id=source.workspace_id,
        user_id=user_id,
        job_type=f"source:{source.source_key}",
        source_id=source.id,
    )
    try:
        merged = {**(source.configurations[0].config if source.configurations else {} or {}),
                  **(config or {})}
        adapter = get_adapter(source.source_key, config=merged)
        validation = _run(adapter.validate_configuration())
        if not validation.valid:
            raise ValueError("; ".join(validation.messages))
        raws = _run(adapter.fetch_records(SourceQuery(config=merged, limit=limit)))
        created = failed = 0
        for raw in raws:
            try:
                normalized = _run(adapter.normalize_record(raw))
                create_record_from_normalized(
                    db,
                    workspace_id=source.workspace_id,
                    source_id=source.id,
                    normalized=normalized,
                    is_demo=(source.source_key == "demo"),
                )
                created += 1
            except Exception:  # noqa: BLE001
                failed += 1
        job.records_created = created
        job.records_failed = failed
        job.progress = 100
        job.status = JobStatus.completed if failed == 0 else JobStatus.partial
        log_audit(
            db,
            workspace_id=source.workspace_id,
            user_id=user_id,
            action="import_records",
            target_type="source",
            target_id=str(source.id),
            detail={"created": created, "failed": failed, "source_key": source.source_key},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Source import failed for %s", source.id)
        job.status = JobStatus.failed
        job.error_message = str(exc)
    db.commit()
    return job
