from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.enums import AccessMethod, SourceType
from app.schemas.common import ORMModel


class SourceCreate(BaseModel):
    source_key: str
    source_name: str
    source_type: SourceType
    jurisdiction: str | None = None
    base_url: str | None = None
    access_method: AccessMethod = AccessMethod.user_upload
    supported_record_types: list[str] | None = None
    terms_notes: str | None = None
    attribution: str | None = None
    rate_limit_per_minute: int | None = None
    requires_auth: bool = False
    config: dict | None = None


class SourceOut(ORMModel):
    id: uuid.UUID
    source_key: str
    source_name: str
    source_type: SourceType
    jurisdiction: str | None
    base_url: str | None
    access_method: AccessMethod
    supported_record_types: list | None
    terms_notes: str | None
    attribution: str | None
    rate_limit_per_minute: int | None
    requires_auth: bool
    enabled: bool


class SourceValidationOut(BaseModel):
    valid: bool
    messages: list[str]
    access_method: str
    requires_auth: bool
    notes: str | None = None


class SourceImportRequest(BaseModel):
    config: dict | None = None
    limit: int = 50


class AdapterDescriptorOut(BaseModel):
    source_key: str
    source_name: str
    source_type: str
    access_method: str
    jurisdiction: str | None
    supported_record_types: list[str]
    terms_notes: str
    attribution: str
    requires_auth: bool
    rate_limit_per_minute: int | None
