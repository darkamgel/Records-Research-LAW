from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.db.session import get_db
from app.models.audit import AuditLog
from app.schemas.common import Page
from app.schemas.project import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditLogOut])
def list_audit(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(AuditLog).where(AuditLog.workspace_id == principal.workspace_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    rows = list(db.execute(stmt).scalars())
    return Page(items=[AuditLogOut.model_validate(r) for r in rows], total=total,
                limit=limit, offset=offset)
