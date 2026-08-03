from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.enums import ProcessingStatus
from app.models.source import IngestionJob, UploadedFile
from app.schemas.upload import IngestionJobOut, UploadedFileOut
from app.services import storage
from app.services.audit import log_audit
from app.services.dispatch import submit_file_processing

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=UploadedFileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    source_name: str | None = Form(default=None),
    original_url: str | None = Form(default=None),
    jurisdiction: str | None = Form(default=None),
    record_type: str | None = Form(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.max_upload_size_mb} MB limit",
        )

    mime = storage.guess_mime(file.filename or "upload", file.content_type)
    if mime not in storage.ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file type. Allowed: PDF, CSV, TXT, JSON.",
        )

    file_hash = storage.sha256_hex(data)
    existing = db.execute(
        select(UploadedFile).where(
            UploadedFile.workspace_id == principal.workspace_id,
            UploadedFile.file_hash == file_hash,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Duplicate file already uploaded (id={existing.id})",
        )

    stored = storage.store_file(data, mime)
    uf = UploadedFile(
        workspace_id=principal.workspace_id,
        uploaded_by=principal.user.id,
        original_filename=file.filename or "upload",
        stored_filename=stored,
        mime_type=mime,
        file_hash=file_hash,
        size_bytes=len(data),
        processing_status=ProcessingStatus.pending,
        source_name=source_name,
        original_url=original_url,
        jurisdiction=jurisdiction,
        record_type=record_type,
    )
    db.add(uf)
    db.flush()
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="upload_file",
        target_type="uploaded_file",
        target_id=str(uf.id),
        detail={"filename": uf.original_filename, "mime": mime, "size": len(data)},
    )
    db.commit()

    submit_file_processing(uf.id)
    db.refresh(uf)
    return uf


@router.get("", response_model=list[UploadedFileOut])
def list_uploads(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    rows = db.execute(
        select(UploadedFile)
        .where(UploadedFile.workspace_id == principal.workspace_id)
        .order_by(UploadedFile.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars()
    return list(rows)


def _get_file(db: Session, principal: Principal, file_id: uuid.UUID) -> UploadedFile:
    uf = db.get(UploadedFile, file_id)
    if uf is None or uf.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return uf


@router.get("/{file_id}/status", response_model=UploadedFileOut)
def get_status(
    file_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return _get_file(db, principal, file_id)


@router.post("/{file_id}/retry", response_model=UploadedFileOut)
def retry_processing(
    file_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    uf = _get_file(db, principal, file_id)
    if uf.processing_status == ProcessingStatus.processing:
        raise HTTPException(status.HTTP_409_CONFLICT, "File is currently processing")
    uf.retry_count += 1
    uf.processing_status = ProcessingStatus.pending
    uf.processing_error = None
    db.commit()
    submit_file_processing(uf.id)
    db.refresh(uf)
    return uf


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    file_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    uf = _get_file(db, principal, file_id)
    try:
        storage.delete_file(uf.stored_filename)
    except Exception:  # noqa: BLE001
        pass
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="delete_record",
        target_type="uploaded_file",
        target_id=str(uf.id),
    )
    db.delete(uf)
    db.commit()


@router.get("/jobs", response_model=list[IngestionJobOut])
def list_jobs(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    rows = db.execute(
        select(IngestionJob)
        .where(IngestionJob.workspace_id == principal.workspace_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
    ).scalars()
    return list(rows)
