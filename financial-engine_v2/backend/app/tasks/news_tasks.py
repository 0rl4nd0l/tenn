from __future__ import annotations

from typing import Any

from app.celery_app import celery as celery_app
from app.services.news_memo_extractor import NewsMemoExtractor


@celery_app.task(name="extract_news_memo_task", queue="llm_gpu")
def extract_news_memo_task(payload: dict[str, Any]) -> dict[str, Any]:
    task_payload = dict(payload or {})
    llm_url = task_payload.pop("llm_url", None)
    llm_model = task_payload.pop("llm_model", None)
    memos_path = task_payload.pop("memos_path", None)

    extractor = NewsMemoExtractor(
        llm_url=llm_url,
        llm_model=llm_model,
        memos_path=memos_path,
    )
    return extractor.extract_and_store(**task_payload)
