import os

from celery import Celery


celery = Celery(
    "financial_engine",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    include=["worker_app.tasks"],
)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
)
