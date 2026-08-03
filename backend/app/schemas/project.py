from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.record import RecordOut


class ProjectCreate(BaseModel):
    name: str
    objective: str | None = None


class ProjectOut(ORMModel):
    id: uuid.UUID
    name: str
    objective: str | None
    created_at: datetime


class ProjectDetailOut(ProjectOut):
    records: list[RecordOut] = []


class ProjectRecordsRequest(BaseModel):
    record_ids: list[uuid.UUID]


class SavedSearchCreate(BaseModel):
    name: str
    query: dict


class SavedSearchUpdate(BaseModel):
    name: str | None = None
    query: dict | None = None


class SavedSearchOut(ORMModel):
    id: uuid.UUID
    name: str
    query: dict
    last_executed_at: datetime | None
    last_result_count: int | None
    created_at: datetime


class SavedSearchExecuteOut(BaseModel):
    result_count: int
    new_result_ids: list[uuid.UUID]
    removed_result_ids: list[uuid.UUID]
    items: list[RecordOut]


class ReportRequest(BaseModel):
    title: str | None = None
    use_ai: bool = True


class ReportOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    summary_markdown: str | None
    content: dict | None
    ai_generated: bool
    created_at: datetime


class AuditLogOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict | None
    created_at: datetime
