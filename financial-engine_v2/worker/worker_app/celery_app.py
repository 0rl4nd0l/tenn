import os

from celery import Celery
from celery.schedules import crontab


celery = Celery(
    "financial_engine",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    include=["worker_app.tasks", "worker_app.news_tasks"],
)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_soft_time_limit=900,
    task_time_limit=960,
    result_expires=86400,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "run_daily_news_pipeline": {
            "task": "run_daily_news_pipeline",
            "schedule": crontab(hour=6, minute=0),
        },
        "sync_news_qdrant": {
            "task": "sync_news_qdrant",
            "schedule": crontab(minute=0, hour="*/2"),
        },
    },
)
