from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cockpit.storage.state import StateStore


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_list_chat_sessions_returns_latest_first(store: StateStore) -> None:
    store.add_chat_message("session-a", "user", "first question", _now_iso())
    store.add_chat_message("session-a", "assistant", "first answer", _now_iso())
    store.add_chat_message("session-b", "user", "new question", _now_iso())
    store.add_chat_message("session-b", "assistant", "new answer", _now_iso())

    sessions = store.list_chat_sessions(limit=10)
    assert [row["thread_id"] for row in sessions] == ["session-b", "session-a"]
    assert int(sessions[0]["message_count"]) == 2
    assert sessions[0]["title_seed"] == "new question"
    assert sessions[0]["last_message"] == "new answer"


def test_get_chat_messages_with_ids_is_chronological(store: StateStore) -> None:
    store.add_chat_message("session-c", "user", "hello", _now_iso())
    store.add_chat_message("session-c", "assistant", "world", _now_iso())

    rows = store.get_chat_messages_with_ids("session-c", limit=20)
    assert len(rows) == 2
    assert rows[0]["content"] == "hello"
    assert rows[1]["content"] == "world"
    assert int(rows[0]["id"]) < int(rows[1]["id"])


def test_delete_chat_session_removes_only_target(store: StateStore) -> None:
    store.add_chat_message("session-1", "user", "u1", _now_iso())
    store.add_chat_message("session-1", "assistant", "a1", _now_iso())
    store.add_chat_message("session-2", "user", "u2", _now_iso())

    deleted = store.delete_chat_session("session-1")
    assert deleted == 2
    assert store.get_chat_messages("session-1", limit=10) == []
    assert len(store.get_chat_messages("session-2", limit=10)) == 1


def test_ensure_chat_session_creates_empty_listable_session(store: StateStore) -> None:
    created = store.ensure_chat_session("session-empty")
    assert created is True

    sessions = store.list_chat_sessions(limit=10)
    assert len(sessions) == 1
    assert sessions[0]["thread_id"] == "session-empty"
    assert int(sessions[0]["message_count"]) == 0
    assert sessions[0]["last_message"] is None
