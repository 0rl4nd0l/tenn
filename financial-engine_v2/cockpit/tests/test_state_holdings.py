"""Tests for holdings_items persistence in cockpit StateStore.

P1 of the cockpit verbal market updates plus holdings v1.

Holdings are cockpit-local portfolio state (NOT financial truth, NOT memory
reasoning). Per SYSTEM_CONTRACT §1.2 they live in the cockpit SQLite next to
watchlist and update_events.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from cockpit.storage.state import StateStore


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


# ---------------------------------------------------------------------------
# add_holding / list_holdings
# ---------------------------------------------------------------------------


def test_add_holding_persists_and_lists(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="bhp", quantity=100.0, avg_cost=42.5)
    assert isinstance(holding_id, str) and holding_id

    rows = store.list_holdings()
    assert len(rows) == 1
    row = rows[0]
    assert row["holding_id"] == holding_id
    assert row["ticker"] == "BHP"  # normalised to uppercase
    assert row["quantity"] == 100.0
    assert row["avg_cost"] == 42.5
    assert row["status"] == "active"
    assert row["updated_at"]  # populated automatically


def test_add_holding_normalises_ticker_to_uppercase(store: StateStore) -> None:
    store.add_holding(ticker="cba")
    rows = store.list_holdings()
    assert rows[0]["ticker"] == "CBA"


def test_add_holding_accepts_optional_fields(store: StateStore) -> None:
    holding_id = store.add_holding(
        ticker="WES",
        account_label="super",
        thesis_bucket="quality_compounder",
        quantity=50.0,
        avg_cost=72.10,
        cost_currency="AUD",
        opened_at="2024-01-15",
        note="long term hold",
    )
    row = store.get_holding(holding_id)
    assert row is not None
    assert row["account_label"] == "super"
    assert row["thesis_bucket"] == "quality_compounder"
    assert row["cost_currency"] == "AUD"
    assert row["opened_at"] == "2024-01-15"
    assert row["note"] == "long term hold"


def test_add_holding_optional_fields_default_to_none(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="NAB")
    row = store.get_holding(holding_id)
    assert row is not None
    assert row["account_label"] is None
    assert row["thesis_bucket"] is None
    assert row["quantity"] is None
    assert row["avg_cost"] is None
    assert row["cost_currency"] is None
    assert row["opened_at"] is None
    assert row["note"] is None


def test_multiple_holdings_same_ticker_allowed_per_account(store: StateStore) -> None:
    """Same ticker across accounts is intentional (super vs. brokerage)."""
    h1 = store.add_holding(ticker="VAS", account_label="super", quantity=200.0)
    h2 = store.add_holding(ticker="VAS", account_label="brokerage", quantity=50.0)
    assert h1 != h2

    rows = store.list_holdings()
    tickers = sorted([(r["ticker"], r["account_label"]) for r in rows])
    assert tickers == [("VAS", "brokerage"), ("VAS", "super")]


def test_list_holdings_orders_alphabetically_by_ticker(store: StateStore) -> None:
    store.add_holding(ticker="ZIP")
    store.add_holding(ticker="ANZ")
    store.add_holding(ticker="MIN")

    rows = store.list_holdings()
    assert [r["ticker"] for r in rows] == ["ANZ", "MIN", "ZIP"]


def test_list_holdings_can_filter_by_ticker(store: StateStore) -> None:
    store.add_holding(ticker="BHP")
    store.add_holding(ticker="RIO")

    rows = store.list_holdings(ticker="bhp")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "BHP"


# ---------------------------------------------------------------------------
# get_holding
# ---------------------------------------------------------------------------


def test_get_holding_returns_dict(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="CSL")
    row = store.get_holding(holding_id)
    assert row is not None
    assert row["ticker"] == "CSL"


def test_get_holding_returns_none_when_missing(store: StateStore) -> None:
    assert store.get_holding("does-not-exist") is None


# ---------------------------------------------------------------------------
# update_holding
# ---------------------------------------------------------------------------


def test_update_holding_modifies_fields(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="WBC", quantity=10.0, avg_cost=20.0)
    original = store.get_holding(holding_id)
    assert original is not None
    original_updated_at = original["updated_at"]

    time.sleep(0.01)  # ensure updated_at timestamp advances
    ok = store.update_holding(
        holding_id,
        quantity=15.0,
        avg_cost=22.5,
        note="averaged down",
    )
    assert ok is True

    refreshed = store.get_holding(holding_id)
    assert refreshed is not None
    assert refreshed["quantity"] == 15.0
    assert refreshed["avg_cost"] == 22.5
    assert refreshed["note"] == "averaged down"
    assert refreshed["ticker"] == "WBC"  # untouched fields preserved
    assert refreshed["updated_at"] >= original_updated_at


def test_update_holding_partial_update_preserves_other_fields(store: StateStore) -> None:
    holding_id = store.add_holding(
        ticker="MQG", quantity=5.0, avg_cost=180.0, account_label="super"
    )
    store.update_holding(holding_id, note="post results review")

    row = store.get_holding(holding_id)
    assert row is not None
    assert row["quantity"] == 5.0
    assert row["avg_cost"] == 180.0
    assert row["account_label"] == "super"
    assert row["note"] == "post results review"


def test_update_holding_returns_false_when_missing(store: StateStore) -> None:
    assert store.update_holding("does-not-exist", quantity=1.0) is False


def test_update_holding_with_no_fields_is_noop(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="STO")
    assert store.update_holding(holding_id) is False


# ---------------------------------------------------------------------------
# archive_holding / remove_holding
# ---------------------------------------------------------------------------


def test_archive_holding_flips_status_and_excludes_from_default_list(
    store: StateStore,
) -> None:
    holding_id = store.add_holding(ticker="QAN")
    assert store.archive_holding(holding_id) is True

    row = store.get_holding(holding_id)
    assert row is not None
    assert row["status"] == "archived"

    # default list excludes archived
    assert store.list_holdings() == []
    # opt-in to see them
    archived = store.list_holdings(include_archived=True)
    assert len(archived) == 1
    assert archived[0]["status"] == "archived"


def test_archive_holding_returns_false_when_missing(store: StateStore) -> None:
    assert store.archive_holding("does-not-exist") is False


def test_remove_holding_hard_deletes_row(store: StateStore) -> None:
    holding_id = store.add_holding(ticker="TLS")
    assert store.remove_holding(holding_id) is True
    assert store.get_holding(holding_id) is None
    assert store.list_holdings(include_archived=True) == []


def test_remove_holding_returns_false_when_missing(store: StateStore) -> None:
    assert store.remove_holding("does-not-exist") is False
