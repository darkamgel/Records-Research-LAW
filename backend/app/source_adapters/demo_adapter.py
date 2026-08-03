from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.enums import AccessMethod, SourceType
from app.source_adapters.base import (
    NormalizedRecord,
    RawSourceRecord,
    SourceDescriptor,
    SourceQuery,
    SourceValidationResult,
)
from app.source_adapters.mapping import normalize_row
from app.source_adapters.sample_data import SAMPLE_RECORDS


class DemoDataAdapter:
    """Serves clearly-labeled fictional demonstration records.

    All data is synthetic and marked ``is_demo``. Safe for offline use and tests.
    """

    descriptor = SourceDescriptor(
        source_key="demo",
        source_name="Demonstration Public Records (Synthetic)",
        source_type=SourceType.demo,
        access_method=AccessMethod.sample_data,
        jurisdiction="Demo County, DX",
        base_url=None,
        supported_record_types=[
            "court_filing",
            "probate_notice",
            "public_notice",
            "property_record",
            "organization_filing",
        ],
        terms_notes="Fictional demonstration data generated locally. No real persons.",
        attribution="Synthetic sample data (this project).",
        requires_auth=False,
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        return SourceValidationResult(True, ["Demo adapter ready.", "Data is synthetic."])

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        return [
            RawSourceRecord(external_id=str(r.get("id")), payload=dict(r), original_url=r.get("url"))
            for r in SAMPLE_RECORDS[: query.limit or len(SAMPLE_RECORDS)]
        ]

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        kw = normalize_row(record.payload, jurisdiction_default=self.descriptor.jurisdiction)
        return NormalizedRecord(
            external_record_id=kw["external_record_id"] or record.external_id,
            record_type=kw["record_type"],
            title=kw["title"],
            description=kw["description"],
            jurisdiction=kw["jurisdiction"],
            filing_date=kw["filing_date"],
            event_date=kw["event_date"],
            case_number=kw["case_number"],
            original_url=kw["original_url"],
            primary_name=kw["primary_name"],
            address=kw["address"],
            raw_payload=kw["raw_payload"],
            source_accessed_at=datetime.now(timezone.utc),
        )
