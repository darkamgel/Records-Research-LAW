from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from app.models.enums import AccessMethod, SourceType
from app.services.normalization import normalize_date
from app.source_adapters.base import (
    NormalizedRecord,
    RawSourceRecord,
    SourceDescriptor,
    SourceQuery,
    SourceValidationResult,
)


class GenericRSSAdapter:
    """Reads public RSS/Atom feeds (e.g. public-notice feeds).

    RSS/Atom feeds are an explicitly public export mechanism, preferred over
    scraping. Provide the feed URL via config ``url``.
    """

    descriptor = SourceDescriptor(
        source_key="rss",
        source_name="Generic RSS/Atom Public Notice Feed",
        source_type=SourceType.rss,
        access_method=AccessMethod.rss_feed,
        jurisdiction=None,
        base_url=None,
        supported_record_types=["public_notice"],
        terms_notes="Public RSS/Atom feeds only. Honor any stated usage terms.",
        attribution="Attribution per the publishing feed's terms.",
        requires_auth=False,
        rate_limit_per_minute=20,
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        url = self._config.get("url")
        if not url:
            return SourceValidationResult(False, ["Missing 'url' in configuration."])
        return SourceValidationResult(True, ["Feed URL present."])

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        cfg = {**self._config, **(query.config or {})}
        url = cfg["url"]
        headers = {"User-Agent": "PublicRecordsResearchMVP/0.1 (+compliance-respecting)"}
        # Support inline feed content for tests / offline mode.
        content = cfg.get("_content")
        if content is None:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                content = resp.text
        parsed = feedparser.parse(content)
        out: list[RawSourceRecord] = []
        for entry in parsed.entries[: query.limit]:
            payload = dict(entry)
            out.append(
                RawSourceRecord(
                    external_id=str(entry.get("id") or entry.get("link") or ""),
                    payload={k: str(v) for k, v in payload.items() if isinstance(v, str)},
                    original_url=entry.get("link"),
                )
            )
        return out

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        p = record.payload
        published = p.get("published") or p.get("updated")
        nd = normalize_date(published) if published else None
        return NormalizedRecord(
            external_record_id=record.external_id or None,
            record_type="public_notice",
            title=p.get("title"),
            description=p.get("summary") or p.get("description"),
            jurisdiction=self._config.get("jurisdiction"),
            filing_date=nd.iso if nd else None,
            event_date=None,
            case_number=None,
            original_url=record.original_url,
            primary_name=None,
            address=None,
            raw_payload=p,
            source_accessed_at=record.retrieved_at or datetime.now(timezone.utc),
        )
