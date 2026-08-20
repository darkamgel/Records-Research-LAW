from __future__ import annotations

import asyncio
import json

from app.source_adapters.base import SourceQuery
from app.source_adapters.federal_register_adapter import FederalRegisterAdapter

SAMPLE_RESPONSE = {
    "count": 1,
    "results": [
        {
            "title": "Agency Information Collection Activities",
            "type": "Notice",
            "abstract": "Comment request on proposed collection.",
            "document_number": "2026-15733",
            "html_url": "https://www.federalregister.gov/documents/2026/08/03/2026-15733/example",
            "publication_date": "2026-08-03",
            "agencies": [
                {"name": "Federal Communications Commission", "id": 128},
            ],
        }
    ],
}


def test_federal_register_adapter_offline_parsing():
    adapter = FederalRegisterAdapter(
        config={"document_type": "NOTICE", "_content": json.dumps(SAMPLE_RESPONSE)}
    )
    raws = asyncio.run(adapter.fetch_records(SourceQuery(limit=10)))
    assert len(raws) == 1
    assert raws[0].external_id == "2026-15733"

    normalized = asyncio.run(adapter.normalize_record(raws[0]))
    assert normalized.record_type == "public_notice"
    assert normalized.external_record_id == "2026-15733"
    assert normalized.case_number == "2026-15733"
    assert normalized.filing_date == "2026-08-03"
    assert normalized.jurisdiction == "United States"
    assert "Communications" in (normalized.primary_name or "")
    assert normalized.original_url == SAMPLE_RESPONSE["results"][0]["html_url"]


def test_federal_register_import_skips_duplicates(client, auth):
    inline = json.dumps(SAMPLE_RESPONSE)
    src = client.post(
        "/sources",
        headers=auth,
        json={
            "source_key": "federal_register",
            "source_name": "Federal Register Test",
            "source_type": "json_api",
            "access_method": "official_api",
            "config": {"document_type": "NOTICE", "_content": inline},
        },
    )
    assert src.status_code == 201, src.text
    sid = src.json()["id"]

    first = client.post(f"/sources/{sid}/import", headers=auth, json={"limit": 10})
    assert first.status_code == 200, first.text
    assert first.json()["records_created"] == 1
    assert first.json()["stats"]["records_skipped"] == 0

    second = client.post(f"/sources/{sid}/import", headers=auth, json={"limit": 10})
    assert second.status_code == 200, second.text
    assert second.json()["records_created"] == 0
    assert second.json()["stats"]["records_skipped"] == 1


def test_federal_register_listed_as_adapter(client, auth):
    adapters = client.get("/sources/adapters", headers=auth).json()
    fr = next(a for a in adapters if a["source_key"] == "federal_register")
    assert fr["requires_auth"] is False
    assert fr["access_method"] == "official_api"
    assert "Federal Register" in fr["source_name"]
