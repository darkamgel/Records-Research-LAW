from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.models.enums import AccessMethod, SourceType
from app.source_adapters.base import (
    NormalizedRecord,
    RawSourceRecord,
    SourceDescriptor,
    SourceQuery,
    SourceValidationResult,
)
from app.source_adapters.mapping import normalize_row


class CSVUploadAdapter:
    """Ingests user-uploaded CSV files. Access is user-upload only."""

    descriptor = SourceDescriptor(
        source_key="csv_upload",
        source_name="CSV Upload",
        source_type=SourceType.file_upload,
        access_method=AccessMethod.user_upload,
        jurisdiction=None,
        base_url=None,
        supported_record_types=["*"],
        terms_notes=(
            "Processes only files the user uploads. The user is responsible for "
            "ensuring they have the right to use uploaded data."
        ),
        attribution="User-provided upload.",
        requires_auth=False,
        rate_limit_per_minute=None,
    )

    def __init__(self, data: bytes | None = None, config: dict[str, Any] | None = None) -> None:
        self._data = data
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        if self._data is None:
            return SourceValidationResult(False, ["No CSV data provided."])
        try:
            self._read_df()
        except Exception as exc:
            return SourceValidationResult(False, [f"CSV parse error: {exc}"])
        return SourceValidationResult(True, ["CSV parsed successfully."])

    def _read_df(self) -> pd.DataFrame:
        assert self._data is not None
        df = pd.read_csv(io.BytesIO(self._data), dtype=str, keep_default_na=False)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        df = self._read_df()
        limit = query.limit or len(df)
        records: list[RawSourceRecord] = []
        for _, row in df.head(limit).iterrows():
            payload = {k: (None if v == "" else v) for k, v in row.to_dict().items()}
            records.append(
                RawSourceRecord(
                    external_id=str(payload.get("id") or payload.get("case_number") or ""),
                    payload=payload,
                )
            )
        return records

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        kw = normalize_row(
            record.payload,
            jurisdiction_default=self._config.get("jurisdiction"),
            record_type_default=self._config.get("record_type"),
            mapping=self._config.get("mapping"),
        )
        return NormalizedRecord(
            external_record_id=kw["external_record_id"] or record.external_id or None,
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
            source_accessed_at=kw["source_accessed_at"] or datetime.now(timezone.utc),
        )
