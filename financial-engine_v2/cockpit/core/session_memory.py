from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ov_instance: Any = None
_ov_init_attempted: bool = False
_ov_init_error: str = ""
_status_logged: bool = False

_MAX_CONTENT_CHARS = 400

_OPERATOR_ACTION = (
    "To enable: copy config/openviking/cockpit.ov.conf.example to "
    "~/.openviking/cockpit.ov.conf, fill in local LLM endpoints, then restart cockpit. "
    "Or set OPENVIKING_CONFIG_FILE=/path/to/your.ov.conf"
)


def _ov_config_present() -> bool:
    env_path = os.environ.get("OPENVIKING_CONFIG_FILE")
    if env_path:
        return Path(env_path).expanduser().exists()
    if Path("~/.openviking/ov.conf").expanduser().exists():
        return True
    return Path("/etc/openviking/ov.conf").exists()


def _get_ov() -> Any | None:
    """Attempt OpenViking init once; capture error. Does not log — call _log_startup_status()."""
    global _ov_instance, _ov_init_attempted, _ov_init_error
    if _ov_init_attempted:
        return _ov_instance
    _ov_init_attempted = True
    try:
        from openviking import SyncOpenViking  # type: ignore[import]

        ov = SyncOpenViking()
        ov.initialize()
        _ov_instance = ov
    except Exception as exc:
        _ov_init_error = f"{type(exc).__name__}: {exc}"
    return _ov_instance


def _log_startup_status() -> None:
    """Emit exactly one startup log per process: enabled or degraded with operator action."""
    global _status_logged
    if _status_logged:
        return
    _status_logged = True
    ov = _get_ov()
    if ov is not None:
        config_path = os.environ.get("OPENVIKING_CONFIG_FILE") or "~/.openviking/ov.conf"
        logger.info("cockpit.session_memory: OpenViking enabled (config: %s)", config_path)
    elif _ov_config_present():
        logger.warning(
            "cockpit.session_memory: OpenViking init failed — cockpit running stateless. "
            "Root cause: %s",
            _ov_init_error,
        )
    else:
        logger.warning(
            "cockpit.session_memory: OpenViking config not found — cockpit running stateless. %s",
            _OPERATOR_ACTION,
        )


def get_relevant_session_context(
    session_id: str,
    query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return up to *limit* structured prior-turn records relevant to *query*.

    Returns an empty list on any failure — callers must treat this as
    best-effort augmentation only.
    """
    ov = _get_ov()
    if not ov:
        return []
    try:
        raw_results = ov.search(query, session_id=session_id, limit=limit)
        items: list[dict[str, Any]] = []
        for r in raw_results or []:
            content: str = ""
            if isinstance(r, dict):
                content = str(r.get("content") or r.get("text") or "").strip()
            elif isinstance(r, str):
                content = r.strip()
            if not content:
                continue
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    items.append(parsed)
                    continue
            except (json.JSONDecodeError, ValueError):
                pass
            items.append({"text": content[:_MAX_CONTENT_CHARS]})
        return items[:limit]
    except Exception as exc:
        logger.warning(
            "cockpit.session_memory.get_relevant_session_context failed — returning empty context. "
            "%s: %s",
            type(exc).__name__,
            exc,
        )
        return []


def record_turn(session_id: str, payload: dict[str, Any]) -> None:
    """Persist a structured turn record to the session.

    Fails open — callers must not depend on this succeeding.
    """
    ov = _get_ov()
    if not ov:
        return
    try:
        query = str(payload.get("query") or "").strip()
        if query:
            ov.add_message(session_id, "user", content=query)
        answer_json = json.dumps(payload, ensure_ascii=False, default=str)
        ov.add_message(session_id, "assistant", content=answer_json)
    except Exception as exc:
        logger.warning(
            "cockpit.session_memory.record_turn failed — turn not persisted. "
            "%s: %s",
            type(exc).__name__,
            exc,
        )


def build_turn_payload(
    *,
    session_id: str,
    thread_id: str,
    query: str,
    answer: str,
    ticker: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": session_id,
        "thread_id": thread_id,
        "query": query,
        "answer": answer,
    }
    if ticker:
        payload["ticker"] = ticker
    return payload
