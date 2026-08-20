"""Federal Register official JSON API adapter (free, no API key).

Docs: https://www.federalregister.gov/developers/documentation/api/v1
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

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

API_BASE = "https://www.federalregister.gov/api/v1"
DOCUMENTS_URL = f"{API_BASE}/documents.json"
USER_AGENT = "PublicRecordsResearchMVP/0.1 (+compliance-respecting; research tool)"


def _agency_names(agencies: Any) -> str | None:
    if not isinstance(agencies, list):
        return None
    names = [a.get("name") for a in agencies if isinstance(a, dict) and a.get("name")]
    return "; ".join(names) if names else None


def _record_type_from_doc(doc_type: str | None) -> str:
    if not doc_type:
        return "public_notice"
    low = doc_type.lower()
    if "notice" in low:
        return "public_notice"
    if "rule" in low:
        return "regulatory_rule"
    return "public_notice"


class FederalRegisterAdapter:
    """Pulls documents from the free, keyless Federal Register REST API."""

    descriptor = SourceDescriptor(
        source_key="federal_register",
        source_name="Federal Register (Official API)",
        source_type=SourceType.json_api,
        access_method=AccessMethod.official_api,
        jurisdiction="United States",
        base_url=API_BASE,
        supported_record_types=["public_notice", "regulatory_rule"],
        terms_notes=(
            "Uses the official Federal Register API (federalregister.gov/api/v1). "
            "No API key required. Be polite with request volume (roughly ≤10 req/s)."
        ),
        attribution="Data courtesy of the U.S. Federal Register / National Archives.",
        requires_auth=False,
        rate_limit_per_minute=30,
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def validate_configuration(self) -> SourceValidationResult:
        document_type = self._config.get("document_type")
        if document_type is not None and document_type not in (
            "NOTICE",
            "RULE",
            "PROPOSED RULE",
            "PRESIDENTIAL",
            None,
            "",
        ):
            return SourceValidationResult(
                False,
                [
                    "document_type must be one of: NOTICE, RULE, PROPOSED RULE, PRESIDENTIAL, "
                    "or omitted for all types."
                ],
            )
        return SourceValidationResult(
            True,
            ["Federal Register API configuration is valid."],
            notes="Live requests go to the official Federal Register API.",
        )

    def _build_params(self, limit: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            "per_page": min(max(limit, 1), 1000),
            "order": self._config.get("order") or "newest",
            "fields[]": [
                "title",
                "type",
                "abstract",
                "document_number",
                "html_url",
                "publication_date",
                "agencies",
                "excerpts",
            ],
        }
        document_type = self._config.get("document_type")
        if document_type:
            params["conditions[type][]"] = document_type
        return params

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        cfg = {**self._config, **(query.config or {})}
        self._config = cfg
        limit = query.limit or 50

        inline = cfg.get("_content")
        if inline is not None:
            data = json.loads(inline) if isinstance(inline, str) else inline
        else:
            params = self._build_params(limit)
            headers = {"User-Agent": USER_AGENT}
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(DOCUMENTS_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

        items = data.get("results") if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        out: list[RawSourceRecord] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            doc_no = item.get("document_number")
            out.append(
                RawSourceRecord(
                    external_id=str(doc_no or item.get("id") or ""),
                    payload=item,
                    original_url=item.get("html_url"),
                )
            )
        return out

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        p = record.payload
        pub = p.get("publication_date")
        nd = normalize_date(str(pub)) if pub else None
        agencies = _agency_names(p.get("agencies"))
        abstract = (p.get("abstract") or "").strip()
        excerpts = p.get("excerpts")
        if not abstract and isinstance(excerpts, str):
            abstract = excerpts.strip()
        description = abstract or None
        if agencies and description:
            description = f"{agencies}\n\n{description}"
        elif agencies:
            description = agencies

        return NormalizedRecord(
            external_record_id=str(p.get("document_number") or record.external_id or "") or None,
            record_type=_record_type_from_doc(p.get("type")),
            title=p.get("title"),
            description=description,
            jurisdiction=self._config.get("jurisdiction") or "United States",
            filing_date=nd.iso if nd else None,
            event_date=None,
            case_number=str(p.get("document_number")) if p.get("document_number") else None,
            original_url=p.get("html_url") or record.original_url,
            primary_name=agencies.split(";")[0].strip() if agencies else None,
            address=None,
            raw_payload={str(k): v for k, v in p.items()},
            source_accessed_at=record.retrieved_at or datetime.now(timezone.utc),
        )
