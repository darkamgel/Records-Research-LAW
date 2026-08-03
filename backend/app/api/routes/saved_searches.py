from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.research import SavedSearch
from app.schemas.project import (
    SavedSearchCreate,
    SavedSearchExecuteOut,
    SavedSearchOut,
    SavedSearchUpdate,
)
from app.schemas.record import RecordOut
from app.schemas.search import SearchQuery
from app.services.audit import log_audit
from app.services.search import search_records

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.post("", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create(
    body: SavedSearchCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    ss = SavedSearch(
        workspace_id=principal.workspace_id,
        user_id=principal.user.id,
        name=body.name,
        query=body.query,
    )
    db.add(ss)
    log_audit(db, workspace_id=principal.workspace_id, user_id=principal.user.id,
              action="save_search", target_type="saved_search")
    db.commit()
    db.refresh(ss)
    return ss


@router.get("", response_model=list[SavedSearchOut])
def list_saved(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = db.execute(
        select(SavedSearch)
        .where(SavedSearch.workspace_id == principal.workspace_id,
               SavedSearch.user_id == principal.user.id)
        .order_by(SavedSearch.created_at.desc())
    ).scalars()
    return list(rows)


def _get(db, principal, ss_id) -> SavedSearch:
    ss = db.get(SavedSearch, ss_id)
    if ss is None or ss.workspace_id != principal.workspace_id or ss.user_id != principal.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved search not found")
    return ss


@router.get("/{ss_id}", response_model=SavedSearchOut)
def get_one(ss_id: uuid.UUID, principal: Principal = Depends(get_principal),
            db: Session = Depends(get_db)):
    return _get(db, principal, ss_id)


@router.put("/{ss_id}", response_model=SavedSearchOut)
def update(ss_id: uuid.UUID, body: SavedSearchUpdate,
           principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    ss = _get(db, principal, ss_id)
    if body.name is not None:
        ss.name = body.name
    if body.query is not None:
        ss.query = body.query
    db.commit()
    db.refresh(ss)
    return ss


@router.delete("/{ss_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(ss_id: uuid.UUID, principal: Principal = Depends(get_principal),
           db: Session = Depends(get_db)):
    ss = _get(db, principal, ss_id)
    db.delete(ss)
    db.commit()


@router.post("/{ss_id}/execute", response_model=SavedSearchExecuteOut)
def execute(ss_id: uuid.UUID, principal: Principal = Depends(get_principal),
            db: Session = Depends(get_db)):
    ss = _get(db, principal, ss_id)
    query = SearchQuery.model_validate(ss.query)
    items, total = search_records(db, principal.workspace_id, query)
    new_ids = [r.id for r in items]
    prev_ids = set(ss.last_result_ids or [])
    new_set = {str(i) for i in new_ids}
    added = [i for i in new_ids if str(i) not in prev_ids]
    removed = [uuid.UUID(i) for i in prev_ids if i not in new_set]

    ss.last_executed_at = datetime.now(timezone.utc)
    ss.last_result_count = total
    ss.last_result_ids = [str(i) for i in new_ids]
    db.commit()

    return SavedSearchExecuteOut(
        result_count=total,
        new_result_ids=added,
        removed_result_ids=removed,
        items=[RecordOut.model_validate(r) for r in items],
    )
