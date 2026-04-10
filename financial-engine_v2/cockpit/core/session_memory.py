from __future__ import annotations

"""Cockpit session memory — thin wrapper over shared.session_memory_base.

Public API is unchanged so all callers in cockpit/core/chat.py continue to
work without modification.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.session_memory_base import SessionMemoryClient

_COCKPIT_CONFIG_PATH = Path("~/.openviking/cockpit.ov.conf").expanduser()

_OPERATOR_ACTION = (
    "To enable: copy config/openviking/cockpit.ov.conf.example to "
    "~/.openviking/cockpit.ov.conf, fill in local LLM endpoints, then restart cockpit. "
    "Or set OPENVIKING_CONFIG_FILE=/path/to/your.ov.conf"
)

_client = SessionMemoryClient(
    component_name="cockpit",
    config_path=_COCKPIT_CONFIG_PATH,
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


def record_turn(session_id: str, payload: dict[str, Any]) -> None:
    """Persist a structured turn record to the session."""
    _client.record_turn(session_id, payload)


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
