import os

from celery import Celery
from celery.schedules import crontab


celery = Celery(
    "financial_engine",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    # "worker_app.tasks" removed — module never existed (was worker/app/tasks.py,
    # now deprecated). Beat only needs news_tasks for scheduling.
    include=["worker_app.news_tasks", "worker_app.research_tasks"],
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
        # newspaper4k provider (default since 2026-03-27; eodhd/gdelt suspended).
        "run_daily_news_pipeline": {
            "task": "run_daily_news_pipeline",
            "schedule": crontab(hour=6, minute=0),
        },
        "sync_news_qdrant": {
            "task": "sync_news_qdrant",
            "schedule": crontab(minute=0, hour="*/2"),
            # since_hours must exceed the fetch window (36h) so articles
            # scraped by run_daily_news_pipeline are not excluded by the
            # published_at_utc filter.  48h provides headroom.
            "kwargs": {"since_hours": 48},
        },
        # Rebuild news.sqlite chunk store after daily fetch so the SQLite
        # fallback path in cockpit get_news_context stays current.
        "build_news_chunks": {
            "task": "build_news_chunks",
            "schedule": crontab(hour=7, minute=0),
        },
        "watchlist_research_scan": {
            "task": "watchlist_research_scan",
            "schedule": crontab(minute=0, hour="8,12,16"),
        },
    },
)
