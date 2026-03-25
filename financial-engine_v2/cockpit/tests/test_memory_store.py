"""Tests for MemoryStore — markdown read/write."""
from __future__ import annotations
import pytest
from cockpit.core.agent.memory.store import MemoryStore


@pytest.fixture
def tmp_store(tmp_path):
    return MemoryStore(root=tmp_path)


def test_write_and_read_session(tmp_store):
    tmp_store.append_session_turn(role="user", content="hello")
    tmp_store.append_session_turn(role="assistant", content="world")
    turns = tmp_store.read_session_turns()
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["content"] == "world"


def test_write_and_read_research(tmp_store):
    tmp_store.write_research("BHP", "BHP revenue: $55B in FY2025")
    content = tmp_store.read_research("BHP")
    assert "55B" in content


def test_append_research_does_not_overwrite(tmp_store):
    tmp_store.write_research("CSL", "Note 1")
    tmp_store.append_research("CSL", "Note 2")
    content = tmp_store.read_research("CSL")
    assert "Note 1" in content
    assert "Note 2" in content


def test_read_durable_memory(tmp_store):
    tmp_store.write_durable("User prefers concise responses")
    content = tmp_store.read_durable()
    assert "concise" in content


def test_read_missing_ticker_returns_empty(tmp_store):
    assert tmp_store.read_research("NOPE") == ""


def test_list_research_tickers(tmp_store):
    tmp_store.write_research("MIN", "data")
    tmp_store.write_research("BHP", "data")
    tickers = tmp_store.list_research_tickers()
    assert "MIN" in tickers
    assert "BHP" in tickers


def test_rotate_session(tmp_store):
    tmp_store.append_session_turn(role="user", content="hi")
    archived = tmp_store.rotate_session()
    assert archived.exists()
    turns = tmp_store.read_session_turns()
    assert turns == []
