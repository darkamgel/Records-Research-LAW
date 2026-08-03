# Security & compliance controls

This document summarizes the security and compliance measures in the MVP and where they live in the
code.

## Authentication & authorization

- **Password hashing** — `app/core/security.py` uses bcrypt. Because bcrypt truncates at 72 bytes,
  passwords are pre-hashed with SHA-256 and base64-encoded first, so arbitrary-length passwords are
  handled safely.
- **JWT sessions** — signed with `APP_SECRET_KEY`; expiry via `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **Roles** — `admin`, `researcher`, `reviewer`, enforced through FastAPI dependencies
  (`app/core/deps.py`).
- **Protected routes** — every non-auth route depends on `get_current_user` and an active workspace.

## Workspace isolation (IDOR protection)

- Every workspace-scoped table has an indexed `workspace_id` FK.
- Requests carry the active workspace; services filter **every** query by it, so a user can never
  read or mutate another workspace's records, matches, projects, files, or audit entries.
- Object lookups are always scoped (`WHERE id = ? AND workspace_id = ?`), preventing insecure direct
  object references. Covered by `backend/app/tests/test_workspace_isolation.py`.

## Input validation & injection protection

- **Schema validation** — all request/response bodies use Pydantic v2 schemas.
- **SQL injection** — SQLAlchemy 2.0 parameterized queries throughout; no string-built SQL.
- **File-type & size validation** — MIME/extension allow-list and `MAX_UPLOAD_SIZE_MB` enforced in
  `app/services/storage.py` and the upload route.

## Safe file handling

- Uploaded files get **secure generated filenames** and are stored **separately** from extracted
  data (a dedicated uploads volume).
- **SHA-256 hashing** deduplicates files and detects tampering.
- **Path-traversal protection** on all storage paths.
- Imported documents are treated as **untrusted input** for the entire pipeline.

## Transport & HTTP hardening

- **Security headers** middleware (`app/core/middleware.py`) sets standard protective headers.
- **CORS** restricted to `CORS_ORIGINS` (use `*` only for local dev).
- **Rate limiting** — in-process limiter middleware for API request limits.
- **Generic error responses** — the global exception handler logs details server-side but returns a
  generic message, avoiding internal disclosure.

## Background jobs

- Long-running ingestion/document-processing jobs run with **timeouts** and record structured status
  and error messages; failed jobs are visible and retryable.

## LLM prompt-injection defenses

- System instructions are separated from document content; untrusted text is fenced via
  `wrap_untrusted` (`app/ai/prompts.py`).
- Document text can never override system instructions, request secrets, trigger tool calls, or
  change application behavior.
- All model output is Pydantic-validated before use; summary citations are validated against known
  record ids. See [`ai-workflows.md`](ai-workflows.md).

## Secret management

- All secrets come from environment variables (`app/core/config.py`).
- Only `.env.example` (placeholders) is committed; `.env` is git-ignored. No real credentials exist
  in the repository.

## Safe logging

- Structured JSON logging (`app/core/logging.py`) avoids logging passwords, tokens, or full document
  contents.

## Audit logging

- `app/services/audit.py` records imports, searches, AI operations, record reviews, and match
  decisions to `audit_logs`, viewable via `GET /audit`. Covered by
  `backend/app/tests/test_audit_permissions.py`.

## Compliance controls (product-level)

The application enforces responsible-use constraints by design:

- Operates only on **publicly available** or **user-uploaded** information.
- Source adapters must use compliant access methods and **declare** access method, terms, rate
  limit, auth requirements, and attribution (see [`source-adapters.md`](source-adapters.md)); no
  scraping of sources that prohibit automated access; no bypassing auth/CAPTCHA/rate limits.
- **Provenance preserved** for every imported record.
- AI summaries and match suggestions are **clearly labeled**.
- **No automated identity determination**; every potential match requires human review and records
  are never auto-merged.
- Not to be used for legal, employment, housing, credit, insurance, immigration, educational, or
  law-enforcement decisions; no inference of protected characteristics; no facial recognition.
- Users can **remove** imported records from their workspace.
- An in-app **compliance notice** (`ComplianceBanner`) and `GET /compliance` explain these limits.

## Recommended production hardening

See [`deployment.md`](deployment.md) — HTTPS/TLS termination, a shared rate-limit/store (Redis) for
multi-instance deployments, managed Postgres with backups, object storage + AV scanning for uploads,
secret manager, refresh-token rotation, and centralized log aggregation.
