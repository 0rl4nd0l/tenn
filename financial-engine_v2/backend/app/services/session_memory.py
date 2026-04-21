from __future__ import annotations

"""Backend session memory — thin wrapper over shared.session_memory_base.

Public API is unchanged so all callers in backend/app/main.py and
backend/app/services/tenn_chat.py continue to work without modification.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.session_memory_base import SessionMemoryClient

_BACKEND_CONFIG_PATH = Path("~/.openviking/backend.ov.conf").expanduser()

_OPERATOR_ACTION = (
    "To enable: copy config/openviking/backend.ov.conf.example to "
    "~/.openviking/backend.ov.conf, fill in local LLM endpoints, then restart. "
    "Or set OPENVIKING_CONFIG_FILE=/path/to/your.ov.conf"
)

_client = SessionMemoryClient(
    component_name="backend",
    config_path=_BACKEND_CONFIG_PATH,
    operator_action=_OPERATOR_ACTION,
)


# ---------------------------------------------------------------------------
# Public API — matches original module surface exactly
# ---------------------------------------------------------------------------


def _log_startup_status() -> None:
    _client.log_startup_status()


def get_relevant_session_context(
    session_id: str,
    query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return up to *limit* vector-search results relevant to *query*.

    When the vector index is empty (common case), combine with
    get_recent_turns() for direct message retrieval.
    """
    return _client.get_relevant_session_context(session_id, query, limit=limit)


def get_recent_turns(
    session_id: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return up to *limit* most-recent turns directly from the session store."""
    return _client.get_recent_turns(session_id, limit=limit)


def get_session_context(
    session_id: str,
    query: str,
    *,
    semantic_limit: int = 3,
    recent_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return semantic session context, falling back to recent turns."""
    return _client.get_session_context(
        session_id,
        query,
        semantic_limit=semantic_limit,
        recent_limit=recent_limit,
    )


def record_turn(session_id: str, payload: dict[str, Any]) -> None:
    """Persist a structured turn record to the session."""
    _client.record_turn(session_id, payload)


def _shutdown() -> None:
    """Release OpenViking resources on process shutdown."""
    _client.close()


def _build_turn_payload(
    *,
    session_id: str,
    query: str,
    answer: str,
    ticker: str | None,
    confidence: float | None,
    sources: list[dict[str, Any]] | None,
    retrieved_chunk_ids: list[str] | None,
    quality_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": session_id,
        "query": query,
        "answer": answer,
    }
    if ticker:
        payload["ticker"] = ticker
    if confidence is not None:
        payload["confidence"] = confidence
    if sources:
        payload["sources"] = [
            {
                "source_name": str(s.get("source_name") or ""),
                "source_type": str(s.get("source_type") or ""),
                "published_at": str(s.get("published_at") or ""),
            }
            for s in sources[:5]
        ]
    if retrieved_chunk_ids:
        payload["retrieved_chunk_ids"] = retrieved_chunk_ids[:10]
    if quality_metrics:
        payload["quality_metrics"] = {
            "composite_metric": quality_metrics.get("composite_metric"),
            "retrieval_precision": quality_metrics.get("retrieval_precision"),
            "session_coherence": quality_metrics.get("session_coherence"),
        }
    return payload
