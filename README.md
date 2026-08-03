# Public Records Research MVP

A research-productivity platform for the **lawful** collection, organization, search, matching, and
summarization of **publicly available** government records and **user-uploaded** documents.

> **This is a research tool, not an identity service.** It may suggest that records *could* be
> related and produces explainable confidence scores, but it **never makes a final identity
> determination**. Every potential match is subject to human review. See the
> [Compliance and Responsible-Use Notice](#compliance-and-responsible-use-notice).

> **New here?** For a hands-on, step-by-step walkthrough of running and using the app, see
> [`HOWTO.md`](HOWTO.md).

---

## What this project does

Public records live in dozens of scattered places — court dockets, probate notices, public notices,
property records, and organization filings — in many different formats (CSV, PDF, JSON, RSS). Pulling
them together, making them searchable, and figuring out which records *might* describe the same
person or organization is slow, manual, and error-prone.

This application automates that mechanical work while keeping a human in charge of every judgment. In
practice, it lets a researcher:

1. **Import** records from approved public sources or by uploading **PDF / CSV / TXT / JSON** files.
2. **Extract & normalize** the text and metadata — names, organizations, dates, addresses,
   cities/counties/states/ZIPs, case & parcel numbers — with OCR as a fallback for scanned PDFs.
3. **Search & filter** everything with keyword, full-text, semantic, exact/fuzzy name, address, and
   case-number search.
4. **Find potential matches** — records that may refer to the same person, organization, address,
   case, or property — using a transparent, rule-based engine.
5. **See an explainable confidence score (0–100)** for each suggestion, with the supporting and
   conflicting evidence and a plain-language rationale.
6. **Review every match** side by side and confirm, reject, defer, or flag it — nothing is ever
   merged or decided automatically.
7. **Assemble research projects** and generate **cited, exportable summaries** (Markdown / JSON /
   CSV / printable HTML).
8. **Save searches, keep a research history, and track an audit log** of imports, searches, AI
   operations, reviews, and decisions.

**What it is not:** it is *not* an identity, background-check, or surveillance service. It only works
on **public or user-uploaded** data, it **clearly labels** AI-generated output, and it **never
confirms an identity** — the confidence scores are review guidance, not determinations. It runs fully
even with **no OpenAI key** (in a deterministic mode). See the
[Compliance and Responsible-Use Notice](#compliance-and-responsible-use-notice).

---

## Table of contents

- [What this project does](#what-this-project-does)
- [Project purpose](#project-purpose)
- [Main features](#main-features)
- [Architecture overview](#architecture-overview)
- [Technology stack](#technology-stack)
- [Quick start (Docker)](#quick-start-docker)
- [Local installation (without Docker)](#local-installation-without-docker)
- [Environment configuration](#environment-configuration)
- [Database migrations](#database-migrations)
- [Running tests](#running-tests)
- [Demo login / setup](#demo-login--setup)
- [OpenAI configuration](#openai-configuration)
- [OCR configuration](#ocr-configuration)
- [Adding a new source adapter](#adding-a-new-source-adapter)
- [API overview](#api-overview)
- [Known MVP limitations](#known-mvp-limitations)
- [Compliance and responsible-use notice](#compliance-and-responsible-use-notice)
- [Further documentation](#further-documentation)

---

## Project purpose

Researchers, journalists, genealogists, and analysts frequently need to gather public records from
many places (court dockets, probate notices, public notices, property records, organization
filings), normalize them, search across them, and identify records that *might* refer to the same
person, organization, address, case, or property. Doing this by hand is slow and error-prone.

This application automates the **mechanical** parts of that workflow — ingestion, extraction,
normalization, indexing, candidate generation, and drafting cited summaries — while keeping a human
firmly in the loop for every consequential judgment.

## Main features

- **Authentication & workspaces** — email/password auth, JWT sessions, `admin` / `researcher` /
  `reviewer` roles, and hard workspace isolation on every query.
- **Modular source adapters** — CSV upload, PDF upload, generic public JSON API, generic RSS/Atom
  public-notice feed, and a synthetic demonstration adapter. Each adapter declares its access
  method, terms, rate limit, auth requirements, and attribution.
- **File upload & ingestion** — PDF/CSV/TXT/JSON with type & size validation, SHA-256 duplicate
  detection, secure generated filenames, background processing, and per-job status/retry.
- **Document processing** — embedded-text extraction with an **OCR fallback** (Tesseract) only when
  quality is low, page-number preservation, chunking with character offsets, and metadata capture.
- **Hybrid entity extraction** — regex identifiers (case/parcel/ZIP), address parsing, optional
  spaCy NER, and optional schema-validated LLM extraction, with a text span for every entity.
- **Deterministic normalization** — names, addresses, dates (exact/partial/range/unknown), and
  organizations, always preserving the original value.
- **Search** — keyword, PostgreSQL full-text, semantic (pgvector), exact & fuzzy name, address, and
  case-number search, plus jurisdiction / source / record-type / date / review-status filters.
- **Explainable entity resolution** — blocking → deterministic features → transparent weighted
  score (0–100) with categories, supporting/conflicting evidence, missing-info list, and a
  plain-language rationale. **The LLM never controls the number.**
- **Human review workflow** — side-by-side record comparison; confirm / reject / needs-more-info /
  duplicate / not-reviewed. Records are **never merged automatically**.
- **AI workflows (LangGraph)** — document processing, match-evidence explanation, and cited research
  summaries. Runs in a **deterministic mode** when no OpenAI key is present.
- **Research projects & reports** — group records, generate cited summaries, export as Markdown /
  JSON / CSV / printable HTML.
- **Saved searches & history** — save, re-run, and see what changed since the last run.
- **Audit log** — imports, searches, AI operations, reviews, and match decisions are recorded.
- **Compliance UI** — an in-app notice explaining what the tool does and does not do.

## Architecture overview

```text
                 ┌──────────────┐        ┌──────────────────────────┐
  Browser  ─────▶│  Next.js UI  │──REST─▶│        FastAPI API        │
                 │ (TanStack Q) │        │  routes → services → repo │
                 └──────────────┘        └───────────┬──────────────┘
                                                     │
                          ┌──────────────────────────┼───────────────────────────┐
                          ▼                           ▼                           ▼
                   ┌────────────┐            ┌────────────────┐          ┌────────────────┐
                   │ PostgreSQL │            │     Redis      │          │  Local file    │
                   │ + pgvector │            │  (broker)      │          │  storage       │
                   │ + FTS      │            └───────┬────────┘          └────────────────┘
                   └────────────┘                    │
                                                     ▼
                                            ┌────────────────┐   LangGraph workflows
                                            │ Celery worker  │──▶ (doc processing, match
                                            │ (ingest/docproc)│   analysis, summaries) ──▶ OpenAI*
                                            └────────────────┘   * optional; deterministic fallback
```

The backend is layered: **API routes** (thin) → **services** (business logic) → **models/repository**
(SQLAlchemy). Long-running work (ingestion, PDF/OCR, embeddings) is dispatched to a Celery worker,
with an inline/thread-pool fallback so everything also runs without Redis for local dev and tests.
See [`docs/architecture.md`](docs/architecture.md).

## Technology stack

| Layer            | Technology                                                                    |
| ---------------- | ----------------------------------------------------------------------------- |
| Backend          | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic                     |
| Database         | PostgreSQL 16 + `pgvector`, PostgreSQL full-text search (SQLite for tests)     |
| Async / jobs     | Redis + Celery (inline fallback)                                               |
| Documents        | pypdf / PyMuPDF, Tesseract OCR, pandas, spaCy (optional)                       |
| AI               | LangGraph, OpenAI Python SDK (optional; deterministic fallback)                |
| Frontend         | Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack Query, React Hook Form + Zod |
| Deployment       | Docker, Docker Compose, optional Nginx reverse proxy                           |
| Testing          | pytest (backend), Vitest + Testing Library (frontend)                          |

## Quick start (Docker)

Prerequisites: Docker and Docker Compose.

```bash
cp .env.example .env          # then edit APP_SECRET_KEY (and OPENAI_API_KEY if you have one)
docker compose up --build
```

The stack starts Postgres, Redis, the API, a background worker, and the frontend. On first boot the
backend entrypoint waits for the database, runs Alembic migrations, and seeds the demo user + data.

| Service         | URL                                            |
| --------------- | ---------------------------------------------- |
| Frontend        | http://localhost:3000                          |
| API (OpenAPI)   | http://localhost:8000/docs                     |
| API health      | http://localhost:8000/health                   |
| Compliance      | http://localhost:8000/compliance               |

Optional Nginx reverse proxy (serves UI at `/` and API at `/api/` on port 8080):

```bash
docker compose --profile proxy up --build
```

Common operations (see the `Makefile` for more):

```bash
docker compose exec backend alembic upgrade head   # run migrations
docker compose exec backend python -m app.seed     # (re)seed demo data
docker compose exec backend pytest                 # backend tests
docker compose exec frontend npm test              # frontend tests
```

## Local installation (without Docker)

The application is designed to also run with **no external services** — it falls back to SQLite,
inline task execution, and deterministic (no-key) AI.

**Backend**

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
# Uses a local SQLite DB and inline jobs by default when DATABASE_URL/REDIS are unset.
python -m app.seed                 # create demo user + demo records
uvicorn app.main:app --reload      # http://localhost:8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

## Environment configuration

Copy `.env.example` to `.env`. Key variables:

| Variable                 | Purpose                                                                 |
| ------------------------ | ---------------------------------------------------------------------- |
| `APP_SECRET_KEY`         | **Required.** Signing key for JWTs. Use a long random string.          |
| `DATABASE_URL`           | SQLAlchemy URL. Empty → local SQLite (dev/tests).                      |
| `REDIS_URL`              | Celery broker/result URL. Empty → inline task execution.              |
| `OPENAI_API_KEY`         | Optional. Empty → deterministic mode (imports/search/matching still work). |
| `OPENAI_BASE_URL`        | Optional. Base URL of an OpenAI-compatible server. Empty → official OpenAI API. |
| `OPENAI_MODEL`           | Chat model (default `gpt-4o-mini`).                                     |
| `OPENAI_EMBEDDING_MODEL` | Embedding model (default `text-embedding-3-small`).                     |
| `NEXT_PUBLIC_API_URL`    | Frontend → backend base URL.                                           |
| `MAX_UPLOAD_SIZE_MB`     | Upload size limit (default 25).                                        |
| `OCR_ENABLED`            | Enable Tesseract OCR fallback.                                         |
| `CORS_ORIGINS`           | Comma-separated allowed origins.                                       |
| `LOG_LEVEL`              | `INFO`, `DEBUG`, etc.                                                   |

**Never commit a real `.env`.** Only `.env.example` (with placeholders) is tracked.

## Database migrations

Migrations are managed with Alembic (`backend/alembic`).

```bash
# Docker
docker compose exec backend alembic upgrade head

# Local
cd backend && alembic upgrade head
```

The Docker entrypoint runs `alembic upgrade head` automatically on startup.

## Running tests

Both suites run **without a live OpenAI API key** (the client is mocked / falls back deterministically).

```bash
# Backend (pytest, SQLite, mocked OpenAI)
cd backend && pytest -q

# Frontend (Vitest + Testing Library, mocked API)
cd frontend && npm test
```

Latest local results: **backend 36 passing**, **frontend 15 passing**.

## Demo login / setup

After seeding (automatic in Docker, or `python -m app.seed` locally):

```
Email:    demo@example.com
Password: demopassword123
```

The seed creates a workspace and a set of clearly-labeled **synthetic** demonstration records,
including strong-match pairs, uncertain pairs, similar-but-different people, conflicting addresses,
and incomplete dates. You can also load demo data from the UI: **Import Data → Import demo records**.

## OpenAI configuration

Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL` / `OPENAI_EMBEDDING_MODEL`). When a key is
present, the app uses real embeddings and LLM-assisted match explanations and research summaries —
all outputs are schema-validated with Pydantic before use, and prompt-injection defenses separate
system instructions from untrusted document content.

To use an **OpenAI-compatible** server (self-hosted vLLM, a gateway, or a custom-OpenAI endpoint)
instead of the official API, also set `OPENAI_BASE_URL` to that server's base URL — the value before
`/chat/completions` in the provider's example, usually ending in `/v1` — and set `OPENAI_MODEL` to a
model the endpoint actually serves. If the endpoint has no embeddings model, semantic search
automatically falls back to the local deterministic embedding.

When **no** key is present, the app runs in deterministic mode:

- Imports, search, entity extraction, normalization, and matching all work.
- Embeddings use a local deterministic hashing fallback.
- AI summaries and match explanations use a deterministic template and are clearly labeled.

## OCR configuration

OCR is a **fallback**, not the default. The pipeline extracts embedded text first, estimates
extraction quality, and only runs Tesseract OCR when quality is poor (e.g., scanned PDFs). Toggle
with `OCR_ENABLED`. The Docker image installs `tesseract-ocr` and `poppler-utils`; for local runs
install Tesseract via your package manager (e.g. `brew install tesseract` / `apt-get install
tesseract-ocr`).

## Adding a new source adapter

Adapters implement a small `Protocol` and are registered in one place. In short:

1. Create `backend/app/source_adapters/my_source.py` implementing `validate_configuration`,
   `fetch_records`, and `normalize_record`, and declaring its metadata (name, type, jurisdiction,
   access method, terms, rate limit, auth, attribution).
2. Register it in `backend/app/source_adapters/registry.py`.
3. It automatically appears under `GET /sources/adapters` and in the Import UI.

Only use **compliant** access methods (official APIs, bulk downloads, RSS, public exports). Do not
add scrapers for sources that prohibit automated access. Full walkthrough:
[`docs/source-adapters.md`](docs/source-adapters.md).

## API overview

Interactive OpenAPI docs are served at `/docs`. Route groups:

`/auth`, `/sources`, `/files`, `/documents`, `/records`, `/matches`, `/projects`,
`/saved-searches`, `/dashboard`, `/audit`, plus `/health` and `/compliance`. Full reference:
[`docs/api.md`](docs/api.md).

## Known MVP limitations

- Auth is email/password with JWTs; no refresh-token rotation, MFA, or SSO.
- No production object storage — uploaded files are stored on a local/mounted volume.
- Semantic search uses `pgvector` in Postgres; under SQLite (tests/local) it degrades to a
  deterministic in-Python similarity.
- spaCy NER and LLM extraction are optional; the default deterministic extractor is intentionally
  conservative.
- Saved searches are on-demand (no scheduled monitoring/alerts).
- Rate limiting is a simple in-process limiter suitable for a single instance.
- PDF export of reports is not included (Markdown/JSON/CSV/HTML are).
- Only the five MVP adapters ship; real government adapters must be added per their terms.

See [`docs/deployment.md`](docs/deployment.md) for recommended production hardening.

## Compliance and responsible-use notice

This platform operates **only** on publicly available or user-uploaded information. It is designed
to respect the law and source terms of service. It does **not**, and must not be used to:

- Bypass authentication, CAPTCHAs, rate limits, or access controls.
- Scrape sources that prohibit automated access, or access private, sealed, restricted, or paywalled
  data without authorization.
- Make legal, employment, housing, credit, insurance, immigration, educational, or law-enforcement
  decisions.
- Infer protected characteristics or perform facial recognition.
- Present uncertain matches as confirmed identities.

Every imported record preserves its **source provenance**. AI-generated summaries and match
suggestions are **clearly labeled**. All potential matches require **human review**, and records are
never merged automatically. An **audit log** records imports, searches, AI operations, reviews, and
decisions. Users can remove imported records from their workspace. See [`docs/security.md`](docs/security.md).

## Further documentation

- [`HOWTO.md`](HOWTO.md) — step-by-step guide to running and using the app
- **In-app User Guide** — after login, open **User Guide** in the sidebar (`/guide`)
- [`docs/architecture.md`](docs/architecture.md) — system architecture & request flow
- [`docs/database-schema.md`](docs/database-schema.md) — tables, keys, and indexes
- [`docs/source-adapters.md`](docs/source-adapters.md) — the adapter framework & how to add one
- [`docs/entity-resolution.md`](docs/entity-resolution.md) — blocking, features, scoring, review
- [`docs/ai-workflows.md`](docs/ai-workflows.md) — LangGraph workflows & fallbacks
- [`docs/security.md`](docs/security.md) — security & compliance controls
- [`docs/api.md`](docs/api.md) — REST API reference
- [`docs/deployment.md`](docs/deployment.md) — Docker & production notes
- [`docs/user-guide.md`](docs/user-guide.md) — end-to-end usage walkthrough

## License

See [`LICENSE`](LICENSE). Demonstration data is fictional and provided for testing only.
