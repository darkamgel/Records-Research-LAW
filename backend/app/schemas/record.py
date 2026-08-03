from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class EntityMentionOut(ORMModel):
    id: uuid.UUID
    entity_type: str
    value: str
    normalized_value: str | None
    extraction_method: str
    confidence: float
    page_number: int | None
    char_start: int | None
    char_end: int | None
    source_text: str | None


class RecordOut(ORMModel):
    id: uuid.UUID
    source_id: uuid.UUID | None
    document_id: uuid.UUID | None
    external_record_id: str | None
    record_type: str | None
    title: str | None
    description: str | None
    jurisdiction: str | None
    filing_date: date | None
    event_date: date | None
    case_number: str | None
    original_url: str | None
    source_accessed_at: datetime | None
    primary_name: str | None
    normalized_name: str | None
    normalized_address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    is_demo: bool
    created_at: datetime


class RecordDetailOut(RecordOut):
    raw_payload: dict | None
    normalized_payload: dict | None
    entities: list[EntityMentionOut] = []


class RecordNotesUpdate(BaseModel):
    body: str


class NoteOut(ORMModel):
    id: uuid.UUID
    record_id: uuid.UUID | None
    project_id: uuid.UUID | None
    body: str
    created_at: datetime
