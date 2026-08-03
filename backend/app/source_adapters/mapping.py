"""Flexible field mapping used by CSV/JSON adapters to build NormalizedRecord."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.normalization import normalize_date

# Candidate source keys for each canonical field (case-insensitive contains).
FIELD_ALIASES: dict[str, list[str]] = {
    "primary_name": ["name", "party", "defendant", "petitioner", "owner", "decedent", "full_name"],
    "case_number": ["case_number", "case_no", "case", "docket", "cause_no"],
    "record_type": ["record_type", "type", "category", "filing_type"],
    "title": ["title", "subject", "caption"],
    "description": ["description", "summary", "notes", "details"],
    "jurisdiction": ["jurisdiction", "county", "court", "state"],
    "filing_date": ["filing_date", "filed", "date_filed", "file_date", "date"],
    "event_date": ["event_date", "hearing_date", "recorded_date"],
    "address": ["address", "property_address", "mailing_address", "street"],
    "original_url": ["url", "link", "source_url", "document_url"],
    "external_id": ["id", "record_id", "external_id", "instrument_number"],
}


def _find(row: dict[str, Any], canonical: str) -> Any:
    lowered = {str(k).lower().strip(): v for k, v in row.items()}
    for alias in FIELD_ALIASES.get(canonical, []):
        for key, val in lowered.items():
            if key == alias or alias in key:
                if val not in (None, ""):
                    return val
    return None


def normalize_row(
    row: dict[str, Any],
    *,
    jurisdiction_default: str | None = None,
    record_type_default: str | None = None,
    original_url: str | None = None,
    mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return kwargs suitable for building a NormalizedRecord/Record."""
    mapping = mapping or {}

    def value(field: str) -> Any:
        if field in mapping and mapping[field] in row:
            return row[mapping[field]]
        return _find(row, field)

    filing_raw = value("filing_date")
    event_raw = value("event_date")
    filing = normalize_date(str(filing_raw)) if filing_raw else None
    event = normalize_date(str(event_raw)) if event_raw else None

    return {
        "external_record_id": (str(value("external_id")) if value("external_id") else None),
        "record_type": (value("record_type") or record_type_default),
        "title": value("title") or value("primary_name"),
        "description": value("description"),
        "jurisdiction": value("jurisdiction") or jurisdiction_default,
        "filing_date": filing.iso if filing else None,
        "event_date": event.iso if event else None,
        "case_number": (str(value("case_number")) if value("case_number") else None),
        "original_url": value("original_url") or original_url,
        "primary_name": (str(value("primary_name")) if value("primary_name") else None),
        "address": (str(value("address")) if value("address") else None),
        "raw_payload": {str(k): v for k, v in row.items()},
        "source_accessed_at": datetime.now(timezone.utc),
    }
