from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.models.enums import AccessMethod, SourceType
from app.source_adapters.base import (
    NormalizedRecord,
    RawSourceRecord,
    SourceDescriptor,
    SourceQuery,
    SourceValidationResult,
)
from app.source_adapters.mapping import normalize_row


def _dig(obj: Any, path: str | None) -> Any:
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class GenericJSONAPIAdapter:
    """Fetches records from a public JSON API endpoint.

    Compliance: only use endpoints that explicitly permit automated access. This
    adapter does not bypass auth or rate limits. Provide the endpoint URL and an
    optional ``records_path`` (dot path to the array of records) via config.
    """

    descriptor = SourceDescriptor(
        source_key="json_api",
        source_name="Generic Public JSON API",
        source_type=SourceType.json_api,
        access_method=AccessMethod.official_api,
        jurisdiction=None,
        base_url=None,
        supported_record_types=["*"],
        terms_notes=(
            "Only for endpoints that permit automated access per their terms. "
            "Respects the endpoint's own rate limits; does not bypass auth/CAPTCHA."
        ),
        attribution="Attribution per the upstream API's terms of use.",
        requires_auth=False,
        rate_limit_per_minute=30,
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        url = self._config.get("url")
        if not url:
            return SourceValidationResult(False, ["Missing 'url' in configuration."])
        if not str(url).lower().startswith(("http://", "https://")):
            return SourceValidationResult(False, ["URL must be http(s)."])
        return SourceValidationResult(
            True,
            ["Configuration looks valid."],
            notes="Ensure the endpoint's terms permit automated access.",
        )

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        cfg = {**self._config, **(query.config or {})}
        url = cfg["url"]
        params = cfg.get("params") or {}
        records_path = cfg.get("records_path")
        headers = {"User-Agent": "PublicRecordsResearchMVP/0.1 (+compliance-respecting)"}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        items = _dig(data, records_path)
        if isinstance(data, list) and items is None:
            items = data
        if not isinstance(items, list):
            items = [items] if items else []
        out: list[RawSourceRecord] = []
        for item in items[: query.limit]:
            if not isinstance(item, dict):
                item = {"value": item}
            out.append(
                RawSourceRecord(
                    external_id=str(item.get("id") or ""),
                    payload=item,
                    original_url=item.get("url"),
                )
            )
        return out

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        kw = normalize_row(
            record.payload,
            jurisdiction_default=self._config.get("jurisdiction"),
            record_type_default=self._config.get("record_type"),
            original_url=record.original_url,
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
