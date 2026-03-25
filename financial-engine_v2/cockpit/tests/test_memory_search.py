"""Tests for MemorySearch — SQLite-vec semantic search.
These tests use a stub embed function to avoid requiring Ollama.
"""
from __future__ import annotations
import pytest
from cockpit.core.agent.memory.search import MemorySearch


def _stub_embed(text: str) -> list[float]:
    """Fake embedding: hash of first char repeated to 4 dims."""
    seed = ord(text[0]) if text else 0
    return [float(seed % 10) / 10] * 4


@pytest.fixture
def search(tmp_path):
    return MemorySearch(db_path=tmp_path / "memory.db", embed_fn=_stub_embed, dims=4)


def test_index_and_search(search):
    search.index("BHP revenue is $55B", source="research/BHP")
    search.index("CSL R&D spend is high", source="research/CSL")
    results = search.query("BHP revenue", top_k=1)
    assert len(results) == 1
    assert results[0]["source"] == "research/BHP"


def test_empty_search_returns_empty(search):
    results = search.query("anything", top_k=5)
    assert results == []


def test_top_k_limits_results(search):
    for i in range(5):
        search.index(f"note {i}", source=f"research/T{i}")
    results = search.query("note", top_k=2)
    assert len(results) <= 2


def test_reindex_updates_chunk(search):
    search.index("old content", source="research/BHP")
    search.reindex_source("research/BHP", "new content about revenue")
    results = search.query("revenue", top_k=1)
    assert results[0]["source"] == "research/BHP"
