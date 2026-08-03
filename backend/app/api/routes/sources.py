from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.source import Source, SourceConfiguration
from app.schemas.source import (
    AdapterDescriptorOut,
    SourceCreate,
    SourceImportRequest,
    SourceOut,
    SourceValidationOut,
)
from app.schemas.upload import IngestionJobOut
from app.services.ingestion import run_source_import
from app.source_adapters.registry import descriptor_to_dict, get_adapter, list_descriptors

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/adapters", response_model=list[AdapterDescriptorOut])
def list_adapters(_: Principal = Depends(get_principal)):
    return [AdapterDescriptorOut(**descriptor_to_dict(d)) for d in list_descriptors()]


@router.get("", response_model=list[SourceOut])
def list_sources(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Source).where(Source.workspace_id == principal.workspace_id)
    ).scalars()
    return list(rows)


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    body: SourceCreate,
    principal: Principal = Depends(require_roles(UserRole.admin, UserRole.researcher)),
    db: Session = Depends(get_db),
):
    source = Source(
        workspace_id=principal.workspace_id,
        source_key=body.source_key,
        source_name=body.source_name,
        source_type=body.source_type,
        jurisdiction=body.jurisdiction,
        base_url=body.base_url,
        access_method=body.access_method,
        supported_record_types=body.supported_record_types,
        terms_notes=body.terms_notes,
        attribution=body.attribution,
        rate_limit_per_minute=body.rate_limit_per_minute,
        requires_auth=body.requires_auth,
    )
    db.add(source)
    db.flush()
    if body.config is not None:
        db.add(SourceConfiguration(source_id=source.id, name="default", config=body.config))
    db.commit()
    db.refresh(source)
    return source


def _get_source(db: Session, principal: Principal, source_id: uuid.UUID) -> Source:
    source = db.get(Source, source_id)
    if source is None or source.workspace_id != principal.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    return source


@router.post("/{source_id}/validate", response_model=SourceValidationOut)
def validate_source(
    source_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    source = _get_source(db, principal, source_id)
    cfg = source.configurations[0].config if source.configurations else {}
    adapter = get_adapter(source.source_key, config=cfg)
    result = asyncio.run(adapter.validate_configuration())
    return SourceValidationOut(
        valid=result.valid,
        messages=result.messages,
        access_method=source.access_method.value,
        requires_auth=source.requires_auth,
        notes=result.notes,
    )


@router.post("/{source_id}/enable", response_model=SourceOut)
def toggle_source(
    source_id: uuid.UUID,
    enabled: bool = True,
    principal: Principal = Depends(require_roles(UserRole.admin, UserRole.researcher)),
    db: Session = Depends(get_db),
):
    source = _get_source(db, principal, source_id)
    source.enabled = enabled
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/import", response_model=IngestionJobOut)
def import_source(
    source_id: uuid.UUID,
    body: SourceImportRequest,
    principal: Principal = Depends(require_roles(UserRole.admin, UserRole.researcher)),
    db: Session = Depends(get_db),
):
    source = _get_source(db, principal, source_id)
    if not source.enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source is disabled")
    job = run_source_import(
        db, source=source, config=body.config, limit=body.limit, user_id=principal.user.id
    )
    return job
