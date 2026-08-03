# Deployment

## Services (Docker Compose)

`docker-compose.yml` defines:

| Service    | Image / build      | Purpose                                             | Port  |
| ---------- | ------------------ | --------------------------------------------------- | ----- |
| `db`       | `pgvector/pgvector:pg16` | PostgreSQL 16 with `pgvector` (persistent volume). | 5432  |
| `redis`    | `redis:7-alpine`   | Celery broker/result backend.                       | 6379  |
| `backend`  | `./backend`        | FastAPI API (`command: api`).                       | 8000  |
| `worker`   | `./backend`        | Celery worker (`command: worker`).                  | —     |
| `frontend` | `./frontend`       | Next.js UI.                                          | 3000  |
| `nginx`    | `nginx:1.27-alpine`| Optional reverse proxy (`--profile proxy`).         | 8080  |

Healthchecks are defined for `db` and `redis`; the backend and worker `depends_on` them with
`condition: service_healthy`. Named volumes `pgdata` (database) and `uploads` (original files)
provide persistence.

## First run

```bash
cp .env.example .env      # set APP_SECRET_KEY (and OPENAI_API_KEY if available)
docker compose up --build
```

The backend entrypoint (`backend/docker-entrypoint.sh`) waits for the database, runs
`alembic upgrade head`, seeds demo data, and then starts either uvicorn (`api`) or the Celery worker
(`worker`) based on the container command.

## Common operations

```bash
docker compose exec backend alembic upgrade head   # migrations
docker compose exec backend python -m app.seed     # (re)seed demo data
docker compose exec backend pytest                 # backend tests
docker compose exec frontend npm test              # frontend tests
docker compose logs -f                             # tail logs
docker compose down                                # stop
docker compose down -v                             # stop + wipe volumes (DESTRUCTIVE)
```

A `Makefile` wraps these (`make up`, `make migrate`, `make seed`, `make test`, …).

## Optional Nginx reverse proxy

```bash
docker compose --profile proxy up --build
```

`nginx/nginx.conf` serves the UI at `/` and proxies the API under `/api/` on port **8080**, and sets
`client_max_body_size 30m` for uploads.

## Environment configuration

See the [README](../README.md#environment-configuration) for the full variable table. Minimum for a
real deployment: a strong `APP_SECRET_KEY`, a durable `DATABASE_URL`, and `CORS_ORIGINS` locked to
your frontend origin. `OPENAI_API_KEY` is optional (deterministic mode otherwise).

## Health & readiness

- Backend: `GET /health`.
- Postgres: `pg_isready` healthcheck.
- Redis: `redis-cli ping` healthcheck.

## Running without external services

The app also runs with **no** Postgres/Redis: it falls back to SQLite and inline job execution. This
is intended for local development and CI (the test-suite uses exactly this mode), not production.

## Recommended production hardening

These are intentionally **out of scope** for the MVP but recommended before real-world use:

- **TLS/HTTPS** termination (Nginx/ALB) and HSTS.
- **Managed PostgreSQL** with automated backups and PITR; enable `pgvector` on the instance.
- **Shared rate limiting** — replace the in-process limiter with a Redis-backed limiter for
  multi-instance deployments.
- **Object storage** (e.g., S3) for uploads plus **antivirus scanning** on ingest.
- **Secret manager** (e.g., AWS Secrets Manager / Vault) instead of `.env`.
- **AuthN hardening** — refresh-token rotation, optional MFA/SSO.
- **Horizontal scaling** — multiple API and worker replicas behind a load balancer; scale Celery
  workers by queue depth.
- **Observability** — ship structured logs to a central store; add metrics/tracing and alerting.
- **CI/CD** — run `ruff`, type checks, `pytest`, and `vitest` on every change; build and scan images.
- **Backups & retention** — database backups and an uploads retention/deletion policy.
