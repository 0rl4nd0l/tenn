from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cockpit.storage.state import SQLITE_BUSY_TIMEOUT_MS, StateStore


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


def test_chat_message_metadata_round_trips_for_session_reload(store: StateStore) -> None:
    metadata = {
        "routing_metadata": {
            "source_label_taxonomy_version": "source_label_semantics_v1",
            "evidence_labels": ["claim_verified", "local_news_context"],
            "source_label_counts": {"claim_verified": 1, "local_news_context": 1},
            "claim_verified_source_count": 1,
            "source_coverage_status": "claim_verified",
        },
        "sources": [
            {
                "title": "A2M recall article",
                "evidence_labels": ["claim_verified", "local_news_context"],
                "claim_verified": True,
            }
        ],
    }
    store.add_chat_message(
        "session-labels",
        "assistant",
        "A2M answer.",
        _now_iso(),
        metadata=metadata,
    )

    rows = store.get_chat_messages_with_ids("session-labels", limit=20)

    assert rows[0]["metadata"]["routing_metadata"]["source_coverage_status"] == "claim_verified"
    assert rows[0]["metadata"]["sources"][0]["evidence_labels"] == [
        "claim_verified",
        "local_news_context",
    ]


def test_replace_latest_chat_message_updates_metadata(store: StateStore) -> None:
    store.add_chat_message("session-labels", "assistant", "draft answer", _now_iso())

    updated = store.replace_latest_chat_message(
        "session-labels",
        "assistant",
        "delivered answer",
        metadata={
            "routing_metadata": {
                "evidence_labels": ["context_only"],
                "claim_verified_source_count": 0,
                "source_coverage_status": "context_only",
            }
        },
    )

    rows = store.get_chat_messages_with_ids("session-labels", limit=20)
    assert updated is True
    assert rows[0]["content"] == "delivered answer"
    assert rows[0]["metadata"]["routing_metadata"]["evidence_labels"] == ["context_only"]


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


def test_state_store_configures_sqlite_busy_timeout(store: StateStore) -> None:
    row = store.conn.execute("PRAGMA busy_timeout").fetchone()

    assert row is not None
    assert int(row[0]) == SQLITE_BUSY_TIMEOUT_MS
