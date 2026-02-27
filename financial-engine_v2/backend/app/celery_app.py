from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery = Celery(
    "financial_engine",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker_tasks"],
)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
