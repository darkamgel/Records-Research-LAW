#!/usr/bin/env bash
set -euo pipefail

wait_for_db() {
  echo "Waiting for database..."
  python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import settings
for i in range(60):
    try:
        e = create_engine(settings.database_url)
        with e.connect() as c:
            c.execute(text("SELECT 1"))
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"  db not ready ({exc}); retrying...")
        time.sleep(2)
print("Database did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY
}

case "${1:-api}" in
  api)
    wait_for_db
    echo "Running migrations..."
    alembic upgrade head
    echo "Seeding demo data (idempotent)..."
    python -m app.seed || echo "Seed skipped/failed (non-fatal)."
    echo "Starting API..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    wait_for_db
    echo "Starting Celery worker..."
    exec celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2
    ;;
  migrate)
    wait_for_db
    exec alembic upgrade head
    ;;
  *)
    exec "$@"
    ;;
esac
