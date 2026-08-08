from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.celery_app import celery as celery_app
from app.services.news_memo_extractor import NewsMemoExtractor
from app.services.news_memo_outcomes import NewsMemoOutcomeStore, utc_now_iso


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="extract_news_memo_task", queue="llm_gpu")
def extract_news_memo_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    task_payload = dict(payload or {})
    llm_url = task_payload.pop("llm_url", None)
    llm_model = task_payload.pop("llm_model", None)
    memos_path = task_payload.pop("memos_path", None)
    max_article_chars = task_payload.pop("max_article_chars", None)
    candidate_tickers = task_payload.pop("candidate_tickers", None)
    correlation_id = str(task_payload.pop("correlation_id", None) or "").strip()
    attempt_started_at_utc = str(
        task_payload.pop("attempt_started_at_utc", None) or ""
    ).strip()
    task_payload.pop("memo_skips_path", None)
    source_id = str(task_payload.get("source_id") or "").strip()
    task_id = str(getattr(self.request, "id", None) or "").strip()
    correlation_id = correlation_id or task_id or uuid4().hex
    attempt_started_at_utc = attempt_started_at_utc or utc_now_iso()
    outcomes = NewsMemoOutcomeStore(memos_path=memos_path)

    try:
        extractor = NewsMemoExtractor(
            llm_url=llm_url,
            llm_model=llm_model,
            memos_path=memos_path,
            max_article_chars=max_article_chars,
        )
        result = extractor.extract_and_store(
            **task_payload,
            candidate_tickers=candidate_tickers,
        )
    except Exception as exc:
        try:
            outcomes.record_terminal(
                correlation_id=correlation_id,
                source_id=source_id,
                attempt_started_at_utc=attempt_started_at_utc,
                task_id=task_id,
                terminal_state="failed",
                reason="worker_exception",
                error_class=type(exc).__name__,
            )
        except Exception:
            logger.exception(
                "failed to persist news memo worker failure outcome for %s",
                source_id,
            )
        raise
    terminal_state = (
        "needs_retry"
        if str(result.get("status") or "") == "needs_retry"
        else "completed"
    )
    outcomes.record_terminal(
        correlation_id=correlation_id,
        source_id=source_id,
        attempt_started_at_utc=attempt_started_at_utc,
        task_id=task_id,
        terminal_state=terminal_state,
        reason=str(result.get("reason") or result.get("retry_reason") or "").strip(),
    )
    return result
