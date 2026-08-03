# Architecture

## Goals

- **Keep a human in the loop.** The system automates mechanical work (ingest, extract, normalize,
  index, generate candidates, draft summaries) but never confirms an identity.
- **Run anywhere.** Full stack under Docker Compose; also runnable with zero external services
  (SQLite + inline jobs + deterministic AI) for local development and CI.
- **Explainability first.** Match scores are deterministic and transparent; the LLM only *explains*.

## High-level components

```text
┌──────────────┐     REST/JSON      ┌─────────────────────────────────────────────┐
│  Next.js UI  │ ─────────────────▶ │                 FastAPI app                  │
│ TanStack Q   │ ◀───────────────── │  middleware → routes → services → models     │
└──────────────┘                    └───────────────┬─────────────────────────────┘
                                                     │ SQLAlchemy 2.0
                             ┌───────────────────────┼───────────────────────────┐
                             ▼                       ▼                           ▼
                     ┌──────────────┐        ┌──────────────┐            ┌──────────────┐
                     │ PostgreSQL   │        │    Redis     │            │ File storage │
                     │ pgvector/FTS │        │  (broker)    │            │ (volume)     │
                     └──────────────┘        └──────┬───────┘            └──────────────┘
                                                    ▼
                                          ┌───────────────────┐
                                          │  Celery worker    │  LangGraph workflows:
                                          │  ingest + docproc │  doc-processing / match / summary
                                          └───────────────────┘         │
                                                                        ▼
                                                                 OpenAI SDK (optional)
```

## Backend layering

The backend follows a strict, thin-route layering so business logic stays testable and out of the
HTTP layer:

- **`app/api/routes/*`** — thin FastAPI routers. Parse/validate input (Pydantic), call a service,
  shape the response. No business logic.
- **`app/services/*`** — business logic: ingestion, record creation/enrichment, search, storage,
  reports, audit, dispatch.
- **`app/models/*`** — SQLAlchemy 2.0 ORM models (the repository layer). Custom portable column
  types live in `app/db/types.py`.
- **`app/schemas/*`** — Pydantic request/response models.
- **Domain packages** — `document_processing/`, `entity_resolution/`, `ai/`, `source_adapters/`,
  `workers/`.
- **`app/core/*`** — config, logging, security (hashing/JWT), dependency injection, middleware.

## Request flow (example: file upload)

1. `POST /files/upload` → `uploads` route validates auth (JWT), workspace, MIME type, and size.
2. `services/storage.py` computes a SHA-256, deduplicates, and writes the file with a secure
   generated name to the uploads volume (separate from extracted data).
3. `services/ingestion.py` creates an `UploadedFile` + `IngestionJob` row (provenance) and
   dispatches processing via `services/dispatch.py`.
4. Dispatch runs the job on the **Celery worker** if Redis is configured, otherwise **inline**
   (thread pool) so the same code path works in tests.
5. `document_processing/` extracts text (OCR fallback if needed), chunks it (page + offsets),
   `document_processing/entities.py` extracts entities, `services/normalization.py` normalizes, and
   `services/record_service.py` persists records + embeddings.
6. Every step writes to the **audit log**; job status/errors are queryable via `/files/jobs`.

## Asynchronous execution & the inline fallback

`services/dispatch.py` is the single seam between "do it now" and "queue it". In production it
enqueues Celery tasks (`app/workers/tasks.py`); when `REDIS_URL`/Celery is unavailable (local dev,
tests) it executes the same callable inline on a thread pool. This keeps behavior identical and
avoids a hard Redis dependency for development. Background jobs are bounded by timeouts.

## Database portability

Custom SQLAlchemy `TypeDecorator`s in `app/db/types.py` make the schema portable:

- `GUID` — UUIDs (native under Postgres, string under SQLite).
- `JSONType` — `JSONB` on Postgres, JSON-as-text on SQLite.
- `Embedding` — `pgvector` `Vector` on Postgres, serialized text on SQLite.
- `EnumType` — stores Python `Enum` values as strings and rehydrates them on load.

This lets the full test-suite run on SQLite while production uses PostgreSQL features (FTS,
`pgvector`, `JSONB`).

## AI orchestration

`app/ai/` wraps the OpenAI SDK behind `client.py`, which provides deterministic fallbacks (local
hash embeddings, template summaries) when no API key is set. `app/ai/workflows.py` defines LangGraph
`StateGraph`s for match analysis and research summaries. All model output is validated against
Pydantic schemas (`app/ai/schemas.py`) before it is used, and prompts (`app/ai/prompts.py`) separate
trusted system instructions from untrusted document content.

## Frontend

Next.js 14 App Router with a route group `(app)` for authenticated pages behind an `AppShell` guard.
TanStack Query manages server state and caching; React Hook Form + Zod handle forms and validation;
Tailwind provides styling. `src/lib/api.ts` centralizes authenticated fetches (JWT + workspace
header).

## Configuration & secrets

All configuration is environment-driven via `app/core/config.py` (Pydantic settings). Secrets live
only in `.env` (git-ignored); `.env.example` documents every variable with placeholders.

## Observability

`app/core/logging.py` emits structured JSON logs. The unhandled-exception handler logs details
server-side but returns a generic message to clients to avoid leaking internals. Health is exposed
at `/health`; Compose defines healthchecks for Postgres and Redis.
