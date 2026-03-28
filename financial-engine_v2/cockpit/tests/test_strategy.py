"""Tests for StrategyService — user-defined investment criteria and decisions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cockpit.core.strategy import StrategyService
from cockpit.storage.state import StateStore


@pytest.fixture()
def svc(tmp_path):
    """Create a StrategyService backed by a fresh SQLite state store."""
    db_path = str(tmp_path / "state.db")
    store = StateStore(db_path)
    return StrategyService(store)


# ------------------------------------------------------------------
# Happy path: add + retrieve global criterion
# ------------------------------------------------------------------


def test_add_global_criterion(svc):
    result = svc.add_global("Must have positive FCF for 2 consecutive periods", category="quality", priority=3)
    assert result["id"] is not None
    assert result["criterion"] == "Must have positive FCF for 2 consecutive periods"
    assert result["category"] == "quality"
    assert result["priority"] == 3

    criteria = svc.get_global()
    assert len(criteria) == 1
    assert criteria[0]["criterion"] == "Must have positive FCF for 2 consecutive periods"


# ------------------------------------------------------------------
# Add + retrieve ticker-specific criterion
# ------------------------------------------------------------------


def test_add_ticker_criterion(svc):
    result = svc.add_ticker("BHP", "Acceptable through iron ore cycle", category="risk")
    assert result["ticker"] == "BHP"
    assert result["category"] == "risk"

    criteria = svc.get_ticker("BHP")
    assert len(criteria) == 1
    assert criteria[0]["criterion"] == "Acceptable through iron ore cycle"

    # Case-insensitive ticker
    criteria_lower = svc.get_ticker("bhp")
    assert len(criteria_lower) == 1


# ------------------------------------------------------------------
# Decision recording and retrieval
# ------------------------------------------------------------------


def test_get_decision(svc):
    svc.record_decision("BHP", "watchlist", "Waiting for FCF inflection")
    decision = svc.get_decision("BHP")
    assert decision is not None
    assert decision["decision"] == "watchlist"
    assert decision["decision_rationale"] == "Waiting for FCF inflection"


# ------------------------------------------------------------------
# Context block: global only
# ------------------------------------------------------------------


def test_build_context_block_global_only(svc):
    svc.add_global("Positive FCF", category="quality")
    svc.add_global("Low net debt", category="risk")

    block = svc.build_context_block("CSL")
    assert "## Investment Strategy" in block
    assert "### Global criteria" in block
    assert "Positive FCF" in block
    assert "Low net debt" in block
    # No ticker-specific section
    assert "CSL-specific" not in block


# ------------------------------------------------------------------
# Context block: with ticker criteria
# ------------------------------------------------------------------


def test_build_context_block_with_ticker(svc):
    svc.add_global("Positive FCF")
    svc.add_ticker("BHP", "Iron ore moat justifies lower yield threshold", category="valuation")

    block = svc.build_context_block("BHP")
    assert "### Global criteria" in block
    assert "### BHP-specific criteria" in block
    assert "Iron ore moat" in block
    assert "Positive FCF" in block


# ------------------------------------------------------------------
# Context block: empty when no criteria
# ------------------------------------------------------------------


def test_build_context_block_empty(svc):
    block = svc.build_context_block("BHP")
    assert block == ""

    block_none = svc.build_context_block(None)
    assert block_none == ""


# ------------------------------------------------------------------
# Context block: staleness warning
# ------------------------------------------------------------------


def test_build_context_block_staleness(svc):
    # Insert a criterion with an old updated_at
    old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    conn = svc._store.conn
    conn.execute(
        "INSERT INTO global_strategy (criterion, category, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("Old criterion", "general", 5, old_date, old_date),
    )
    conn.commit()

    block = svc.build_context_block("BHP")
    assert "[stale:" in block
    assert "Old criterion" in block


# ------------------------------------------------------------------
# Priority ordering
# ------------------------------------------------------------------


def test_priority_ordering(svc):
    svc.add_global("Nice to have", priority=8)
    svc.add_global("Must have", priority=1)
    svc.add_global("Normal", priority=5)

    criteria = svc.get_global()
    priorities = [c["priority"] for c in criteria]
    assert priorities == [1, 5, 8]


# ------------------------------------------------------------------
# Ticker override precedence — separate blocks
# ------------------------------------------------------------------


def test_ticker_override_precedence(svc):
    svc.add_global("FCF yield > 5%", category="valuation")
    svc.add_ticker("BHP", "FCF yield > 3% acceptable", category="valuation")

    block = svc.build_context_block("BHP")
    # Both blocks must be present and separate
    global_idx = block.index("### Global criteria")
    ticker_idx = block.index("### BHP-specific criteria")
    assert global_idx < ticker_idx


# ------------------------------------------------------------------
# Delete criterion
# ------------------------------------------------------------------


def test_delete_criterion(svc):
    result = svc.add_global("To be removed")
    row_id = result["id"]

    assert svc.delete(row_id) is True
    assert len(svc.get_global()) == 0

    # Deleting again returns False
    assert svc.delete(row_id) is False
