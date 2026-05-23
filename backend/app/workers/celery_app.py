from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "querymind",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.profile_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Schema profiling can take a while on large databases. The hard ceiling
    # guards a runaway task; the soft limit gives it a chance to clean up.
    task_time_limit=600,
    task_soft_time_limit=540,
)
