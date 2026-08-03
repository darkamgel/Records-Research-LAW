# REST API reference

Interactive OpenAPI docs are served at **`/docs`** (Swagger UI) and **`/openapi.json`**.

## Conventions

- **Auth** — send `Authorization: Bearer <jwt>` (from `/auth/login` or `/auth/register`).
- **Workspace** — send the active workspace via the `X-Workspace-Id` header. All data is scoped to it.
- **Content type** — JSON, except `POST /files/upload` (multipart/form-data).
- **Pagination** — list/search endpoints returning `Page<T>` accept `limit` and `offset` and return
  `{ items, total, limit, offset }`. Filtering/sorting is provided via the search body.
- **Errors** — consistent shape `{ "detail": "<message>" }` with appropriate HTTP status codes
  (`400/401/403/404/409/422/429/500`). Unexpected errors return a generic `500`.

## System

| Method | Path          | Description                                  |
| ------ | ------------- | -------------------------------------------- |
| GET    | `/`           | Service metadata + links.                    |
| GET    | `/health`     | Health check.                                |
| GET    | `/compliance` | Machine-readable compliance/responsible-use notice. |

## Authentication — `/auth`

| Method | Path             | Description                          |
| ------ | ---------------- | ------------------------------------ |
| POST   | `/auth/register` | Create account (returns a token).    |
| POST   | `/auth/login`    | Log in (returns a token).            |
| POST   | `/auth/logout`   | Log out.                             |
| GET    | `/auth/me`       | Current user + workspace membership. |

## Sources — `/sources`

| Method | Path                        | Description                                        |
| ------ | --------------------------- | ------------------------------------------------- |
| GET    | `/sources/adapters`         | List available adapters + declared metadata.      |
| GET    | `/sources`                  | List configured sources.                          |
| POST   | `/sources`                  | Create a source from an adapter.                  |
| POST   | `/sources/{id}/validate`    | Validate a source configuration.                  |
| POST   | `/sources/{id}/enable`      | Enable/disable a source.                          |
| POST   | `/sources/{id}/import`      | Run an import (creates an ingestion job).         |

## Files & documents — `/files`, `/documents`

| Method | Path                     | Description                                    |
| ------ | ------------------------ | ---------------------------------------------- |
| POST   | `/files/upload`          | Upload PDF/CSV/TXT/JSON (multipart).           |
| GET    | `/files`                 | List uploads.                                  |
| GET    | `/files/jobs`            | List ingestion jobs.                           |
| GET    | `/files/{id}/status`     | Processing status for an upload.               |
| POST   | `/files/{id}/retry`      | Retry processing.                              |
| DELETE | `/files/{id}`            | Delete an uploaded file.                       |
| GET    | `/documents`             | List processed documents.                      |
| GET    | `/documents/{id}`        | Document detail (pages, chunks, metadata).     |

## Records — `/records`

| Method | Path                       | Description                                            |
| ------ | -------------------------- | ----------------------------------------------------- |
| POST   | `/records/search`          | Search + filter (paginated). See modes below.         |
| GET    | `/records/{id}`            | Record detail (entities, page refs, matches, notes).  |
| PUT    | `/records/{id}/notes`      | Update record notes.                                  |
| GET    | `/records/{id}/related`    | Related/candidate records for a record.               |
| DELETE | `/records/{id}`            | Remove a record from the workspace.                  |
| POST   | `/records/export`          | Export records (e.g. CSV).                            |

**Search body** supports: `q`, `mode` (`keyword` / `fulltext` / `semantic` / `exact_name` /
`fuzzy_name` / `address` / `case_number`), and filters for jurisdiction, source, record type, date
range, and review status, plus `limit`/`offset`.

## Matches — `/matches`

| Method | Path                          | Description                                        |
| ------ | ----------------------------- | ------------------------------------------------- |
| POST   | `/matches/generate`           | Generate candidates (blocking + scoring).         |
| GET    | `/matches`                    | List candidates.                                  |
| GET    | `/matches/{id}`               | Candidate detail (both records + evidence).       |
| POST   | `/matches/{id}/review`        | Record a decision (`confirmed`/`rejected`/`needs_more_info`/`duplicate`) + notes. |
| POST   | `/matches/{id}/approve`       | Shortcut: confirm.                                |
| POST   | `/matches/{id}/reject`        | Shortcut: reject.                                 |
| POST   | `/matches/{id}/needs-info`    | Shortcut: needs more information.                 |

## Research projects — `/projects`

| Method | Path                                   | Description                                   |
| ------ | -------------------------------------- | --------------------------------------------- |
| POST   | `/projects`                            | Create a project.                             |
| GET    | `/projects`                            | List projects.                                |
| GET    | `/projects/{id}`                       | Project detail (with records).                |
| POST   | `/projects/{id}/records`               | Add records to the project.                   |
| DELETE | `/projects/{id}/records/{record_id}`   | Remove a record from the project.             |
| POST   | `/projects/{id}/report`                | Generate a cited research summary.            |
| GET    | `/projects/{id}/reports`               | List generated reports.                       |
| GET    | `/projects/reports/{report_id}`        | Get a report.                                 |
| GET    | `/projects/reports/{report_id}/export` | Export report (`?fmt=markdown|json|csv|html`). |

## Saved searches — `/saved-searches`

| Method | Path                          | Description                                     |
| ------ | ----------------------------- | ----------------------------------------------- |
| POST   | `/saved-searches`             | Create.                                         |
| GET    | `/saved-searches`             | List.                                           |
| GET    | `/saved-searches/{id}`        | Read.                                           |
| PUT    | `/saved-searches/{id}`        | Update.                                         |
| DELETE | `/saved-searches/{id}`        | Delete.                                         |
| POST   | `/saved-searches/{id}/execute`| Re-run; returns results + new/removed since last run. |

## Dashboard & audit

| Method | Path                 | Description                               |
| ------ | -------------------- | ----------------------------------------- |
| GET    | `/dashboard/metrics` | Aggregate metrics for the dashboard.      |
| GET    | `/audit`             | List workspace audit events (paginated).  |

## Example

```bash
# Register and capture the token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","password":"a-strong-password","full_name":"Me"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Search records (keyword mode)
curl -s -X POST http://localhost:8000/records/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"q":"Rivera","mode":"keyword","limit":25,"offset":0}'
```
