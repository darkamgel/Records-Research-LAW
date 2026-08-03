"""Source adapter framework.

Every adapter declares its access method, usage limitations, and attribution so
compliance is explicit and reviewable. Adapters must prefer official APIs, bulk
downloads, RSS/exports, or user uploads over scraping. Adapters MUST NOT bypass
authentication, CAPTCHAs, rate limits, or robots.txt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from app.models.enums import AccessMethod, SourceType


@dataclass
class SourceDescriptor:
    source_key: str
    source_name: str
    source_type: SourceType
    access_method: AccessMethod
    jurisdiction: str | None
    base_url: str | None
    supported_record_types: list[str]
    terms_notes: str
    attribution: str
    requires_auth: bool = False
    rate_limit_per_minute: int | None = None


@dataclass
class SourceValidationResult:
    valid: bool
    messages: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class SourceQuery:
    config: dict[str, Any] = field(default_factory=dict)
    limit: int = 50


@dataclass
class RawSourceRecord:
    external_id: str | None
    payload: dict[str, Any]
    original_url: str | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NormalizedRecord:
    external_record_id: str | None
    record_type: str | None
    title: str | None
    description: str | None
    jurisdiction: str | None
    filing_date: str | None
    event_date: str | None
    case_number: str | None
    original_url: str | None
    primary_name: str | None
    address: str | None
    raw_payload: dict[str, Any]
    source_accessed_at: datetime


@runtime_checkable
class PublicRecordSourceAdapter(Protocol):
    descriptor: SourceDescriptor

    async def validate_configuration(self) -> SourceValidationResult: ...

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]: ...

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord: ...
