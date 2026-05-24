from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.source_registry import RESEARCH_MEMORY_ROOT

MEMORY_EVENTS_ROOT = RESEARCH_MEMORY_ROOT
DEFAULT_MEMORY_WRITE_EVENT_LOG_PATH = MEMORY_EVENTS_ROOT / "memory_write_events.jsonl"
DEFAULT_MEMORY_READ_EVENT_LOG_PATH = MEMORY_EVENTS_ROOT / "memory_read_events.jsonl"
_SUPPRESS_MEMORY_READ_EVENTS: ContextVar[bool] = ContextVar(
    "suppress_memory_read_events",
    default=False,
)


@contextmanager
def suppress_memory_read_events() -> Iterator[None]:
    token = _SUPPRESS_MEMORY_READ_EVENTS.set(True)
    try:
        yield
    finally:
        _SUPPRESS_MEMORY_READ_EVENTS.reset(token)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        # Observability must never break the primary read/write path.
        return


def emit_memory_write_event(
    *,
    memory_class: str,
    event_type: str,
    payload: dict[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": f"mwe_{uuid.uuid4().hex}",
        "recorded_at": _utc_now(),
        "memory_class": str(memory_class or "").strip(),
        "event_type": str(event_type or "").strip(),
        "payload": dict(payload or {}),
    }
    _append_jsonl(Path(path or DEFAULT_MEMORY_WRITE_EVENT_LOG_PATH), event)
    return event


def emit_memory_read_event(
    *,
    mode: str,
    query_type: str,
    query: str,
    entities: dict[str, Any],
    source_plan: list[str],
    considered_counts: dict[str, int],
    selected_counts: dict[str, int],
    filtered_counts: dict[str, int],
    path: str | Path | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": f"mre_{uuid.uuid4().hex}",
        "recorded_at": _utc_now(),
        "mode": str(mode or "chat").strip() or "chat",
        "query_type": str(query_type or "mixed").strip() or "mixed",
        "query": str(query or "").strip(),
        "entities": dict(entities or {}),
        "source_plan": list(source_plan or []),
        "considered_counts": {
            str(key): int(value) for key, value in dict(considered_counts or {}).items()
        },
        "selected_counts": {
            str(key): int(value) for key, value in dict(selected_counts or {}).items()
        },
        "filtered_counts": {
            str(key): int(value) for key, value in dict(filtered_counts or {}).items()
        },
    }
    if _SUPPRESS_MEMORY_READ_EVENTS.get():
        event["suppressed"] = True
        event["suppression_reason"] = "stateless_chat_smoke"
        return event
    _append_jsonl(Path(path or DEFAULT_MEMORY_READ_EVENT_LOG_PATH), event)
    return event
