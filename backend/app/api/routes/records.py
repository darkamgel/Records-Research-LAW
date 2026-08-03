from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.entity import EntityMention
from app.models.matching import MatchCandidate
from app.models.record import Record
from app.models.research import Note, ResearchHistory
from app.schemas.common import Page
from app.schemas.record import (
    EntityMentionOut,
    NoteOut,
    RecordDetailOut,
    RecordNotesUpdate,
    RecordOut,
)
from app.schemas.search import SearchQuery
from app.services.audit import log_audit
from app.services.search import search_records

router = APIRouter(prefix="/records", tags=["records"])


@router.post("/search", response_model=Page[RecordOut])
def search(
    body: SearchQuery,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    items, total = search_records(db, principal.workspace_id, body)
    db.add(
        ResearchHistory(
            workspace_id=principal.workspace_id,
            user_id=principal.user.id,
            action="search",
            query=body.model_dump(mode="json"),
            result_count=total,
        )
    )
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="search",
        detail={"mode": body.mode, "q": body.q, "results": total},
    )
    db.commit()
    return Page(items=[RecordOut.model_validate(r) for r in items], total=total,
                limit=body.limit, offset=body.offset)


def _get_record(db: Session, principal: Principal, record_id: uuid.UUID) -> Record:
    rec = db.get(Record, record_id)
    if rec is None or rec.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
    return rec


@router.get("/{record_id}", response_model=RecordDetailOut)
def get_record(
    record_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    rec = _get_record(db, principal, record_id)
    mentions = db.execute(
        select(EntityMention).where(EntityMention.record_id == rec.id)
    ).scalars()
    detail = RecordDetailOut.model_validate(rec)
    detail.entities = [EntityMentionOut.model_validate(m) for m in mentions]
    return detail


@router.put("/{record_id}/notes", response_model=NoteOut)
def add_note(
    record_id: uuid.UUID,
    body: RecordNotesUpdate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    rec = _get_record(db, principal, record_id)
    note = Note(
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        record_id=rec.id,
        body=body.body,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{record_id}/related", response_model=list[RecordOut])
def related_records(
    record_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    rec = _get_record(db, principal, record_id)
    candidates = db.execute(
        select(MatchCandidate).where(
            MatchCandidate.workspace_id == principal.workspace_id,
            (MatchCandidate.record_a_id == rec.id) | (MatchCandidate.record_b_id == rec.id),
        )
    ).scalars()
    related_ids = set()
    for c in candidates:
        related_ids.add(c.record_b_id if c.record_a_id == rec.id else c.record_a_id)
    if not related_ids:
        return []
    rows = db.execute(select(Record).where(Record.id.in_(related_ids))).scalars()
    return list(rows)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    rec = _get_record(db, principal, record_id)
    log_audit(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        action="delete_record",
        target_type="record",
        target_id=str(rec.id),
    )
    db.delete(rec)
    db.commit()


@router.post("/export")
def export_records(
    body: SearchQuery,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    body.limit = min(body.limit, 5000)
    items, _ = search_records(db, principal.workspace_id, body)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "title", "record_type", "primary_name", "case_number",
                     "filing_date", "jurisdiction", "city", "state", "zip_code", "original_url"])
    for r in items:
        writer.writerow([
            r.id, r.title, r.record_type, r.primary_name, r.case_number,
            r.filing_date, r.jurisdiction, r.city, r.state, r.zip_code, r.original_url,
        ])
    out.seek(0)
    return StreamingResponse(
        iter([out.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=records.csv"},
    )
