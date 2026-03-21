from __future__ import annotations

import os

from celery import Celery
from kombu import Queue

from app.core.config import settings
from app.services.router import route_request


_SPECIALIZED_QUEUES = ("ingest", "embed", "score", "llm_gpu", "llm_cpu")

# Celery resolves broker/result URLs from CELERY_* env vars with higher precedence
# than app-provided config values. Force normalized runtime values into env first.
os.environ["CELERY_BROKER_URL"] = settings.celery_broker_url
os.environ["CELERY_RESULT_BACKEND"] = settings.celery_result_backend


def _resolve_task_route(
    name: str,
    args: tuple,
    kwargs: dict,
    options: dict,
    task=None,
    **_: object,
) -> dict[str, str] | None:
    if name in {"backfill_ticker", "download_pdf"}:
        queue = "ingest"
    elif name == "process_document":
        queue = "llm_gpu"
    elif name == "llm_embed_texts":
        queue = "embed"
    elif name == "llm_generate_json":
        prompt = str((kwargs or {}).get("prompt") or (args[0] if args else "") or "")
        metadata = (kwargs or {}).get("metadata")
        if not isinstance(metadata, dict) and len(args) > 1 and isinstance(args[1], dict):
            metadata = args[1]
        decision = route_request(prompt, metadata if isinstance(metadata, dict) else None)
        queue = decision.execution_queue
    else:
        return None
    return {"queue": queue, "routing_key": queue}


celery = Celery(
    "financial_engine",
    include=["app.worker_tasks", "app.tasks.commentary_tasks"],
)
celery.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_soft_time_limit=900,
    task_time_limit=960,
    result_expires=86400,
    task_default_queue="ingest",
    task_default_exchange="celery",
    task_default_routing_key="ingest",
    task_create_missing_queues=False,
    task_queues=tuple(Queue(name, routing_key=name) for name in _SPECIALIZED_QUEUES),
    task_routes=(_resolve_task_route,),
)
