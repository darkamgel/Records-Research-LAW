# Database schema

PostgreSQL 16 with the `pgvector` extension and native full-text search. All primary keys are UUIDs
(`GUID` type — native under Postgres, string under SQLite). All timestamps use a `created_at` /
`updated_at` mixin. Every workspace-scoped table carries an indexed `workspace_id` foreign key with
`ON DELETE CASCADE`, which is the backbone of workspace isolation.

Portable column types (`app/db/types.py`): `GUID`, `JSONType` (`JSONB`/text), `Embedding`
(`pgvector`/text), `EnumType` (enum-as-string). This allows the same models to run on PostgreSQL in
production and SQLite in tests.

## Tables

### Identity & access
- **users** — `email` (unique, indexed), `hashed_password` (bcrypt over SHA-256 pre-hash), `role`
  (`admin`/`researcher`/`reviewer`), profile fields.
- **workspaces** — `slug` (unique), name, owner.
- **workspace_members** — join of `workspace_id` × `user_id` with a role, enabling shared workspaces.

### Sources & ingestion
- **sources** — a configured instance of an adapter: `source_key` (adapter id), name, type,
  jurisdiction, base URL, access method, terms, rate limit, auth requirements, enabled flag.
- **source_configurations** — per-source key/value configuration (endpoints, field mappings).
- **ingestion_jobs** — one row per import/upload run: `status` (`pending`/`running`/`completed`/
  `failed`), counters, error message, timestamps.
- **uploaded_files** — original file provenance: original filename, secure stored name, `file_hash`
  (SHA-256, indexed for dedup), MIME type, size, uploading user, `processing_status`.

### Records & documents
- **records** — the central entity. Provenance (`source_id`, `external_record_id`, `original_url`,
  `source_accessed_at`), classification (`record_type`, `jurisdiction`), dates (`filing_date`,
  `event_date`), identifiers (`case_number`), denormalized search/matching fields (`primary_name`,
  `normalized_name`, `normalized_last_name`, `normalized_address`, `city`, `state`, `zip_code`),
  `raw_payload` and `normalized_payload` (JSON), and a chunk `embedding` for semantic search.
- **documents** — a processed file linked to records: page count, extraction method, OCR-used flag,
  quality score, warnings.
- **document_pages** — per-page extracted text (preserves page numbers).
- **document_chunks** — searchable chunks with page number, character offsets, and an embedding.

### Entities
- **entities** / **entity_mentions** — canonical entities and their mentions in records, each mention
  carrying `entity_type`, value, normalized value, confidence, and the source text span
  (page + offsets).
- **people**, **organizations**, **addresses** — normalized structured entities with the indexed
  fields used by matching (e.g., `normalized_name`, `last_name`, `normalized_address`, `city`,
  `state`, `zip_code`).

### Matching & review
- **record_relationships** — user-affirmed relationships between records.
- **match_candidates** — a generated candidate pair (`record_a_id`, `record_b_id`) with
  `confidence_score` (indexed), `category`, `rationale`, evidence, missing-info, and `review_status`
  (indexed).
- **match_evidence** — per-feature evidence rows (feature, score, weight, kind, detail).
- **review_decisions** — the human decision on a candidate with reviewer notes and timestamp.

### Research & workspace artifacts
- **research_projects** / **project_records** — projects and their member records.
- **saved_searches** — named queries with last-execution metadata (time, result count, result ids)
  used to compute "what changed since last run".
- **research_history** — a log of executed searches.
- **notes** — free-text notes attached to a workspace or a specific record.
- **generated_reports** — persisted research summaries (markdown + structured payload, AI flag).

### Audit
- **audit_logs** — `action` (indexed), actor (`user_id`), target, and a JSON detail payload for
  imports, searches, AI operations, reviews, and match decisions.

## Indexing strategy

Indexes exist to support the required access patterns:

- **Workspace isolation** — `workspace_id` on every scoped table.
- **Names** — `primary_name`, `normalized_name`, `normalized_last_name`, and `people.last_name`
  (exact/fuzzy/blocking).
- **Addresses & geography** — `normalized_address`, `city`, `state`, `zip_code`.
- **Dates** — `filing_date`, `event_date`.
- **Identifiers** — `case_number`, `external_record_id`, `uploaded_files.file_hash`.
- **Classification** — `record_type`, `jurisdiction`, `source_id`.
- **Matching/review** — `match_candidates.confidence_score`, `match_candidates.review_status`,
  `ingestion_jobs.status`, `uploaded_files.processing_status`.
- **Full-text search** — a PostgreSQL FTS expression over record title/description/normalized fields.
- **Vector similarity** — `pgvector` index on chunk/record embeddings for semantic search.

## Migrations

Alembic manages schema evolution (`backend/alembic`). Apply with `alembic upgrade head` (run
automatically by the Docker entrypoint). The initial migration creates the `vector` extension and
all tables and indexes above.
