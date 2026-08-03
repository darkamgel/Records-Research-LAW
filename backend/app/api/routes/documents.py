from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.record import Document
from app.schemas.upload import DocumentDetailOut, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    rows = db.execute(
        select(Document)
        .where(Document.workspace_id == principal.workspace_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars()
    return list(rows)


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None or doc.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc
