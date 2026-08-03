"""Create and enrich Record rows from NormalizedRecord + document text.

Enrichment is deterministic (normalization + regex/heuristic entity extraction +
local embedding) so it works with no OpenAI key. When AI is enabled, an extra
LLM extraction pass can augment entities (validated against a Pydantic schema).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.ai.client import get_ai_client
from app.document_processing.entities import ExtractedEntity, deterministic_extract
from app.models.entity import Address, EntityMention, Organization, Person
from app.models.record import Record
from app.services.normalization import (
    normalize_address,
    normalize_name,
    normalize_org,
)
from app.source_adapters.base import NormalizedRecord


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date_parser.parse(value).date()
    except (ValueError, OverflowError):
        return None


def _looks_like_org(name: str | None) -> bool:
    if not name:
        return False
    low = name.lower()
    return any(tok in low for tok in ("llc", "inc", "corp", "l.l.c", "ltd", "company", "holdings"))


def build_search_text(rec: NormalizedRecord, extra: str | None = None) -> str:
    parts = [
        rec.title,
        rec.description,
        rec.primary_name,
        rec.case_number,
        rec.jurisdiction,
        rec.address,
        rec.record_type,
        extra,
    ]
    return " \n".join(p for p in parts if p)


def create_record_from_normalized(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    source_id: uuid.UUID | None,
    normalized: NormalizedRecord,
    document_id: uuid.UUID | None = None,
    document_text: str | None = None,
    is_demo: bool = False,
) -> Record:
    ai = get_ai_client()
    normalized_payload: dict = {}

    primary_name = normalized.primary_name
    norm_name_obj = normalize_name(primary_name) if primary_name else None
    is_org = _looks_like_org(primary_name)

    normalized_name = None
    normalized_last = None
    if norm_name_obj and not is_org:
        normalized_name = norm_name_obj.normalized
        normalized_last = norm_name_obj.last
        normalized_payload["person"] = {
            "first": norm_name_obj.first,
            "middle": norm_name_obj.middle,
            "last": norm_name_obj.last,
            "prefix": norm_name_obj.prefix,
            "suffix": norm_name_obj.suffix,
        }
    elif is_org and primary_name:
        no = normalize_org(primary_name)
        normalized_name = no.normalized
        normalized_payload["organization"] = {"normalized": no.normalized, "original": no.original}

    addr_obj = normalize_address(normalized.address) if normalized.address else None
    if addr_obj:
        normalized_payload["address"] = {
            "normalized": addr_obj.normalized,
            "city": addr_obj.city,
            "state": addr_obj.state,
            "zip": addr_obj.zip_code,
        }

    search_text = build_search_text(normalized, extra=document_text)
    embedding = ai.embed(search_text) if search_text.strip() else None

    record = Record(
        workspace_id=workspace_id,
        source_id=source_id,
        document_id=document_id,
        external_record_id=normalized.external_record_id,
        record_type=normalized.record_type,
        title=normalized.title,
        description=normalized.description,
        jurisdiction=normalized.jurisdiction,
        filing_date=_to_date(normalized.filing_date),
        event_date=_to_date(normalized.event_date),
        case_number=normalized.case_number,
        original_url=normalized.original_url,
        source_accessed_at=normalized.source_accessed_at,
        primary_name=primary_name,
        normalized_name=normalized_name,
        normalized_last_name=normalized_last,
        normalized_address=addr_obj.normalized if addr_obj else None,
        city=addr_obj.city if addr_obj else None,
        state=addr_obj.state if addr_obj else None,
        zip_code=addr_obj.zip_code if addr_obj else None,
        raw_payload=normalized.raw_payload,
        normalized_payload=normalized_payload,
        search_text=search_text,
        embedding=embedding,
        is_demo=is_demo,
    )
    db.add(record)
    db.flush()

    _persist_structured_entities(db, workspace_id, record, norm_name_obj, is_org, addr_obj)
    _extract_and_persist_mentions(db, workspace_id, record, document_text)

    return record


def _persist_structured_entities(db, workspace_id, record, name_obj, is_org, addr_obj):
    if name_obj and not is_org and (name_obj.first or name_obj.last):
        db.add(
            Person(
                workspace_id=workspace_id,
                record_id=record.id,
                original_name=name_obj.original,
                normalized_name=name_obj.normalized,
                first_name=name_obj.first,
                middle_name=name_obj.middle,
                last_name=name_obj.last,
                prefix=name_obj.prefix,
                suffix=name_obj.suffix,
            )
        )
    if is_org and record.primary_name:
        no = normalize_org(record.primary_name)
        db.add(
            Organization(
                workspace_id=workspace_id,
                record_id=record.id,
                original_name=no.original,
                normalized_name=no.normalized,
            )
        )
    if addr_obj and addr_obj.normalized:
        db.add(
            Address(
                workspace_id=workspace_id,
                record_id=record.id,
                original_address=addr_obj.original,
                normalized_address=addr_obj.normalized,
                street=addr_obj.street,
                unit=addr_obj.unit,
                city=addr_obj.city,
                state=addr_obj.state,
                zip_code=addr_obj.zip_code,
                components=addr_obj.components or None,
            )
        )


def _extract_and_persist_mentions(db, workspace_id, record, document_text):
    text = document_text or record.search_text or ""
    entities: list[ExtractedEntity] = deterministic_extract(text)
    for e in entities:
        db.add(
            EntityMention(
                workspace_id=workspace_id,
                record_id=record.id,
                document_id=record.document_id,
                entity_type=e.entity_type,
                value=e.value[:1024],
                normalized_value=(e.normalized_value or "")[:1024] or None,
                extraction_method=e.method,
                confidence=e.confidence,
                page_number=None,
                char_start=e.char_start,
                char_end=e.char_end,
                source_text=(e.source_text or "")[:500] or None,
            )
        )
    db.flush()
