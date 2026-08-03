from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "public_records",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=600,  # hard timeout for long-running ingestion jobs
    task_soft_time_limit=540,
    worker_max_tasks_per_child=100,
)

from app.workers.tasks import process_file  # noqa: E402


@celery_app.task(name="process_uploaded_file")
def process_uploaded_file_task(file_id: str) -> dict:  # pragma: no cover - worker path
    return process_file(file_id)
