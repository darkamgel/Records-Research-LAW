# Source adapters

Source adapters are the **only** way records enter the system, and each one makes its compliance
posture explicit. Adapters must prefer official APIs, bulk downloads, RSS/Atom feeds, public export
mechanisms, or user uploads over scraping — and must **never** bypass authentication, CAPTCHAs, rate
limits, or `robots.txt`, or access private/sealed/paywalled data without authorization.

## The interface

Defined in `app/source_adapters/base.py`:

```python
@runtime_checkable
class PublicRecordSourceAdapter(Protocol):
    descriptor: SourceDescriptor

    async def validate_configuration(self) -> SourceValidationResult: ...
    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]: ...
    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord: ...
```

### `SourceDescriptor` — declared, reviewable metadata

Every adapter must declare:

| Field                    | Meaning                                                      |
| ------------------------ | ----------------------------------------------------------- |
| `source_key`             | Stable adapter identifier (e.g. `csv_upload`, `json_api`).  |
| `source_name`            | Human-readable name.                                        |
| `source_type`            | `SourceType` enum (upload, api, rss, demo, …).              |
| `access_method`          | `AccessMethod` enum (user_upload, official_api, rss, …).    |
| `jurisdiction`           | Jurisdiction, if fixed.                                     |
| `base_url`               | Base URL / API root, if applicable.                         |
| `supported_record_types` | Record types the adapter can produce.                       |
| `terms_notes`            | Terms of service / access notes.                            |
| `attribution`            | Required attribution string.                                |
| `requires_auth`          | Whether the source requires credentials.                   |
| `rate_limit_per_minute`  | Politeness/rate-limit budget.                               |

The descriptor is surfaced verbatim via `GET /sources/adapters` and shown in the Import UI, so users
see access method, terms, attribution, and rate limits before importing.

### Data contract

- `fetch_records(query)` → `list[RawSourceRecord]` — raw rows with `external_id`, `payload`,
  `original_url`, and `retrieved_at` (provenance is captured at fetch time).
- `normalize_record(raw)` → `NormalizedRecord` — maps raw fields to the canonical record shape
  (title, description, jurisdiction, `filing_date`, `event_date`, `case_number`, `primary_name`,
  `address`, …) while retaining `raw_payload` and `source_accessed_at`.

`app/source_adapters/mapping.py` provides a shared helper for mapping arbitrary rows to
`NormalizedRecord`, so most adapters are small.

## Bundled MVP adapters

| Adapter               | `source_key`  | Access method | Notes                                             |
| --------------------- | ------------- | ------------- | ------------------------------------------------- |
| CSV upload            | `csv_upload`  | user_upload   | Maps CSV columns to record fields via pandas.     |
| PDF upload            | `pdf_upload`  | user_upload   | Descriptor only; text/OCR handled by the pipeline.|
| Generic JSON API      | `json_api`    | official_api  | Configurable endpoint + field mapping (no scraping). |
| Generic RSS/Atom      | `rss`         | rss           | Parses public-notice feeds offline-safely.        |
| Demonstration         | `demo`        | sample_data   | Synthetic, clearly-labeled records for testing.   |

The generic JSON API and RSS adapters are intentionally **configuration-driven** — you point them at
a compliant endpoint/feed and provide a field mapping, rather than hard-coding a specific government
website.

## Registration

Adapters are registered in one place — `app/source_adapters/registry.py`. The registry powers
`GET /sources/adapters` and the import routes.

## Adding a new adapter

1. **Create** `app/source_adapters/my_source.py`:

```python
from app.source_adapters.base import (
    SourceDescriptor, SourceValidationResult, SourceQuery,
    RawSourceRecord, NormalizedRecord,
)
from app.models.enums import SourceType, AccessMethod

class MySourceAdapter:
    descriptor = SourceDescriptor(
        source_key="my_source",
        source_name="My Public Records Source",
        source_type=SourceType.api,
        access_method=AccessMethod.official_api,
        jurisdiction="Example County, EX",
        base_url="https://api.example.gov",
        supported_record_types=["court_filing"],
        terms_notes="Official API; 60 req/min; attribution required.",
        attribution="Data courtesy of Example County Clerk.",
        requires_auth=True,
        rate_limit_per_minute=60,
    )

    async def validate_configuration(self) -> SourceValidationResult:
        return SourceValidationResult(valid=True, messages=["Configuration OK"])

    async def fetch_records(self, query: SourceQuery) -> list[RawSourceRecord]:
        # Use the official API only. Respect rate limits and auth requirements.
        ...

    async def normalize_record(self, record: RawSourceRecord) -> NormalizedRecord:
        ...
```

2. **Register** it in `registry.py`.
3. It now appears under `GET /sources/adapters` and in **Import Data**. Users create a `source` from
   it and trigger an import via `POST /sources/{id}/import`.

## Compliance checklist for new adapters

- [ ] Uses an official API, bulk download, RSS/export, or user upload — **not** scraping of a source
      that prohibits automated access.
- [ ] Honors `robots.txt`, rate limits, auth requirements, and licensing.
- [ ] Declares complete, accurate `terms_notes` and `attribution`.
- [ ] Preserves provenance (`original_url`, `retrieved_at`, `source_accessed_at`).
- [ ] Does not access private, sealed, restricted, or paywalled data without authorization.
