from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.ingestion import process_uploaded_file

logger = get_logger(__name__)


def process_file(file_id: str) -> dict:
    """Plain function used by both the Celery task and the inline fallback."""
    db = SessionLocal()
    try:
        job = process_uploaded_file(db, uuid.UUID(file_id))
        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "records_created": job.records_created,
        }
    finally:
        db.close()
