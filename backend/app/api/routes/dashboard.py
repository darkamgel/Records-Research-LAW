from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.enums import JobStatus, ProcessingStatus, ReviewStatus
from app.models.matching import MatchCandidate
from app.models.record import Document, Record
from app.models.research import ResearchHistory
from app.models.source import IngestionJob, UploadedFile

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics")
def metrics(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    ws = principal.workspace_id
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def count(model, *conds):
        return db.scalar(
            select(func.count()).select_from(model).where(model.workspace_id == ws, *conds)
        ) or 0

    recent = list(
        db.execute(
            select(ResearchHistory)
            .where(ResearchHistory.workspace_id == ws)
            .order_by(ResearchHistory.created_at.desc())
            .limit(10)
        ).scalars()
    )

    return {
        "total_records": count(Record),
        "total_documents": count(Document),
        "records_this_week": count(Record, Record.created_at >= week_ago),
        "documents_pending": count(
            UploadedFile, UploadedFile.processing_status == ProcessingStatus.pending
        ),
        "matches_pending_review": count(
            MatchCandidate, MatchCandidate.review_status == ReviewStatus.not_reviewed
        ),
        "matches_reviewed": count(
            MatchCandidate, MatchCandidate.review_status != ReviewStatus.not_reviewed
        ),
        "failed_jobs": count(IngestionJob, IngestionJob.status == JobStatus.failed),
        "recent_activity": [
            {
                "action": r.action,
                "result_count": r.result_count,
                "created_at": r.created_at.isoformat(),
                "query": r.query,
            }
            for r in recent
        ],
    }
