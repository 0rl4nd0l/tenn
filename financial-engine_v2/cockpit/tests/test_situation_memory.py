"""Tests for SituationMemory (BM25 + keyword fallback)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cockpit.core.research.situation_memory import SituationMemory


# ------------------------------------------------------------------
# Happy path (BM25): recall returns more relevant result ranked higher
# ------------------------------------------------------------------


def test_recall_ranks_relevant_higher(tmp_path):
    """More relevant situation is ranked higher than less relevant."""
    mem = SituationMemory(path=tmp_path / "situations.jsonl")
    mem.add("iron ore prices dropped sharply", "mining stocks fell 5%")
    mem.add("interest rates rose by 25 basis points", "bank stocks rallied")
    mem.add("iron ore demand from China increased", "BHP and RIO surged")

    results = mem.recall("iron ore market conditions")
    assert len(results) >= 2
    # Iron ore entries should score higher than interest rates
    texts = [r["situation"] for r in results]
    assert any("iron ore" in t for t in texts)
    # The first result should contain "iron ore" (most relevant)
    assert "iron ore" in results[0]["situation"]


# ------------------------------------------------------------------
# Fallback: rank_bm25 import fails — keyword fallback fires
# ------------------------------------------------------------------


def test_keyword_fallback_when_bm25_unavailable(tmp_path):
    """When _HAS_BM25 is False, keyword fallback returns results."""
    with patch("cockpit.core.research.situation_memory._HAS_BM25", False):
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("gold price surged after Fed announcement", "miners outperformed")
        mem.add("tech stocks dropped on earnings miss", "NASDAQ fell")

        results = mem.recall("gold price movement")

    assert len(results) >= 1
    assert "gold" in results[0]["situation"]
    assert "score" in results[0]


# ------------------------------------------------------------------
# Empty corpus: recall on empty memory returns empty list
# ------------------------------------------------------------------


def test_recall_empty_memory(tmp_path):
    """Recall on empty memory returns empty list, no raise."""
    mem = SituationMemory(path=tmp_path / "situations.jsonl")
    results = mem.recall("anything at all")
    assert results == []


def test_recall_empty_query(tmp_path):
    """Recall with empty query returns empty list."""
    mem = SituationMemory(path=tmp_path / "situations.jsonl")
    mem.add("some situation", "some outcome")
    results = mem.recall("   ")
    assert results == []


def test_add_empty_strings_ignored(tmp_path):
    """Adding empty situation or outcome is silently ignored."""
    mem = SituationMemory(path=tmp_path / "situations.jsonl")
    mem.add("", "outcome")
    mem.add("situation", "")
    assert mem.recall("anything") == []
