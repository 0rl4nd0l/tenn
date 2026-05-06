from __future__ import annotations

from pathlib import Path

import pytest

from cockpit.storage.state import StateStore


@pytest.fixture()
def store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


def test_watchlist_starts_empty(store: StateStore) -> None:
    assert store.list_watch_tickers() == []


def test_add_watch_ticker_persists_uppercase(store: StateStore) -> None:
    inserted = store.add_watch_ticker("bhp", "2026-05-06T00:00:00+00:00")

    assert inserted is True
    assert store.list_watch_tickers() == [
        {"ticker": "BHP", "added_at": "2026-05-06T00:00:00+00:00"}
    ]


def test_add_watch_ticker_duplicate_returns_false(store: StateStore) -> None:
    assert store.add_watch_ticker("BHP", "2026-05-06T00:00:00+00:00") is True

    assert store.add_watch_ticker("bhp", "2026-05-06T01:00:00+00:00") is False
    assert store.list_watch_tickers() == [
        {"ticker": "BHP", "added_at": "2026-05-06T00:00:00+00:00"}
    ]


def test_remove_watch_ticker_returns_true_only_when_removed(
    store: StateStore,
) -> None:
    store.add_watch_ticker("BHP.AX", "2026-05-06T00:00:00+00:00")

    assert store.remove_watch_ticker("bhp.ax") is True
    assert store.remove_watch_ticker("BHP.AX") is False
    assert store.list_watch_tickers() == []
