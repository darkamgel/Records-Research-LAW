"""Background-job dispatch seam.

Prefers Celery (via Redis) when a broker is reachable, otherwise processes
inline so the application remains fully functional without a running worker
(local dev without docker, and the test-suite). This keeps a single call-site
for background processing.
"""

from __future__ import annotations

import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.workers.tasks import process_file

logger = get_logger(__name__)


def _redis_available() -> bool:
    if settings.celery_task_always_eager:
        return False
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        client.ping()
        return True
    except Exception:
        return False


def submit_file_processing(file_id: uuid.UUID) -> str:
    """Enqueue or inline-run document processing. Returns dispatch mode."""
    if _redis_available():
        try:
            from app.workers.celery_app import process_uploaded_file_task

            process_uploaded_file_task.delay(str(file_id))
            return "celery"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Celery dispatch failed, running inline: %s", exc)
    process_file(str(file_id))
    return "inline"
