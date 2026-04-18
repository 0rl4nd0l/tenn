from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.market_memory import MarketMemoryStore


def _sector_signal(**overrides):
    payload = {
        "scope": "sector",
        "sector": "Materials",
        "type": "sector_trend",
        "statement": "Iron ore producers are showing renewed pricing discipline.",
        "confidence": 0.7,
        "materiality": 0.8,
        "persistence": "medium",
        "status": "active",
        "source": "news",
        "source_id": "sector-src-1",
        "linked_tickers": ["BHP", "RIO"],
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def _macro_signal(**overrides):
    payload = {
        "scope": "macro",
        "macro_topic": "China stimulus",
        "type": "macro_theme",
        "statement": "China stimulus expectations are supporting bulk commodity sentiment.",
        "confidence": 0.6,
        "materiality": 0.7,
        "persistence": "medium",
        "status": "active",
        "source": "commentary",
        "source_id": "macro-src-1",
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def test_insert_sector_entry_creates_change_log(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    result = store.update_market_memory(_sector_signal())

    assert result["rule"] == "insert"
    entries = store.list_sector_entries("Materials")
    assert len(entries) == 1
    assert entries[0]["status"] == "active"
    assert store.list_change_log()[-1]["event_type"] == "insert"


def test_duplicate_sector_signal_is_deduped(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(_sector_signal())

    result = store.update_market_memory(_sector_signal())

    assert result["rule"] == "dedupe"
    entries = store.list_sector_entries("Materials")
    assert len(entries) == 1
    assert entries[0]["reinforcement_count"] == 0


def test_reinforce_sector_signal_from_new_source(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(_sector_signal(confidence=0.5, materiality=0.4))

    result = store.update_market_memory(
        _sector_signal(source_id="sector-src-2", confidence=0.9, materiality=0.95)
    )

    assert result["rule"] == "reinforce"
    entries = store.list_sector_entries("Materials")
    assert entries[0]["confidence"] == pytest.approx(0.9)
    assert entries[0]["materiality"] == pytest.approx(0.95)
    assert entries[0]["reinforcement_count"] == 1


def test_supersede_macro_entry_marks_prior_state_closed(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    original = store.update_market_memory(_macro_signal())

    result = store.update_market_memory(
        _macro_signal(
            statement="China stimulus expectations have faded materially.",
            source_id="macro-src-2",
            supersedes=[original["entry"]["entry_id"]],
        )
    )

    assert result["rule"] == "supersede"
    entries = store.list_macro_entries("China stimulus")
    statuses = {entry["statement"]: entry["status"] for entry in entries}
    assert (
        statuses["China stimulus expectations are supporting bulk commodity sentiment."]
        == "superseded"
    )
    assert statuses["China stimulus expectations have faded materially."] == "active"


def test_contradict_sector_entry_marks_prior_state_contradicted(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(_sector_signal())

    result = store.update_market_memory(
        _sector_signal(
            type="sector_risk",
            statement="Iron ore producers are now competing aggressively on price.",
            source_id="sector-src-2",
            contradicts=["Iron ore producers are showing renewed pricing discipline."],
        )
    )

    assert result["rule"] == "contradict"
    entries = store.list_sector_entries("Materials")
    statuses = {entry["statement"]: entry["status"] for entry in entries}
    assert (
        statuses["Iron ore producers are showing renewed pricing discipline."]
        == "contradicted"
    )
    assert (
        statuses["Iron ore producers are now competing aggressively on price."]
        == "active"
    )


def test_expire_macro_entry_updates_existing_state_without_new_insert(
    tmp_path: Path,
) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(_macro_signal())

    result = store.update_market_memory(
        _macro_signal(status="expired", source_id="macro-expire")
    )

    assert result["rule"] == "expire"
    entries = store.list_macro_entries("China stimulus")
    assert len(entries) == 1
    assert entries[0]["status"] == "expired"


def test_add_manual_sector_entry_marks_metadata_and_uses_manual_source(
    tmp_path: Path,
) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    result = store.add_manual_entry(
        scope="sector",
        signal_type="sector_trend",
        statement="Smelter availability is tightening.",
        sector="Materials",
        linked_tickers=["BHP"],
        metadata={"operator": "alex"},
    )

    assert result["rule"] == "insert"
    entry = store.list_sector_entries("Materials")[0]
    assert entry["source"] == "backend_manual"
    assert entry["metadata"]["manual"] is True
    assert entry["metadata"]["operator"] == "alex"
    assert entry["linked_tickers"] == ["BHP"]


def test_expire_market_entry_soft_expires_by_entry_id(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    inserted = store.add_manual_entry(
        scope="macro",
        signal_type="macro_theme",
        statement="China policy support is broadening.",
        macro_topic="China stimulus",
    )

    result = store.expire_entry(
        scope="macro",
        entry_id=inserted["entry"]["entry_id"],
        reason="cleanup",
    )

    assert result["rule"] == "expire"
    entry = store.list_macro_entries("China stimulus")[0]
    assert entry["status"] == "expired"
    assert store.list_change_log()[-1]["details"]["reason"] == "cleanup"


def test_manual_market_entry_rejects_financial_metric_signals(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    with pytest.raises(ValueError, match="financial"):
        store.add_manual_entry(
            scope="sector",
            signal_type="revenue",
            statement="Sector revenue is accelerating.",
            sector="Materials",
        )


def test_retrieve_links_sector_memory_to_company_and_includes_macro_context(
    tmp_path: Path,
) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(_sector_signal())
    store.update_market_memory(_macro_signal())

    result = store.retrieve(
        query="What is the market backdrop for BHP?",
        entities={"primary_ticker": "BHP", "tickers": ["BHP"]},
        intent="market",
    )

    assert result["status"] == "ok"
    assert result["sector"] == "Materials"
    assert len(result["sector_items"]) == 1
    assert len(result["macro_items"]) == 1
    assert result["items"] == result["sector_items"] + result["macro_items"]


def test_store_rejects_financial_metric_signals(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    with pytest.raises(ValueError, match="financial"):
        store.update_market_memory(
            _sector_signal(
                type="revenue", statement="Materials revenue is accelerating."
            )
        )


def test_market_memory_connect_enables_wal_and_busy_timeout(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    with store._connect() as conn:
        journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        busy_timeout = int(conn.execute("PRAGMA busy_timeout").fetchone()[0])

    assert journal_mode == "wal"
    assert busy_timeout >= 5000


def test_market_memory_retries_transient_locked_database(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    original_connect = store._connect
    calls = {"count": 0}

    def flaky_connect():
        calls["count"] += 1
        if calls["count"] == 1:
            raise sqlite3.OperationalError("database is locked")
        return original_connect()

    store._connect = flaky_connect  # type: ignore[method-assign]

    result = store.update_market_memory(_sector_signal())

    assert result["rule"] == "insert"
    assert calls["count"] >= 2


def test_market_retrieve_filters_low_value_one_off_context(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(
        _macro_signal(
            statement="Macro setup looks interesting.",
            confidence=0.3,
            materiality=0.32,
            metadata={"specificity": 0.32, "themes": ["demand"], "theme_key": "demand"},
        )
    )
    store.update_market_memory(
        _sector_signal(
            statement="Iron ore supply discipline is improving across the sector.",
            source_id="sector-src-2",
            confidence=0.8,
            materiality=0.84,
            metadata={"specificity": 0.76, "themes": ["supply"], "theme_key": "supply"},
        )
    )

    result = store.retrieve(
        query="How is the iron ore sector trading right now?",
        entities={"primary_ticker": "BHP", "tickers": ["BHP"]},
        intent="market",
    )

    assert [item["statement"] for item in result["items"]] == [
        "Iron ore supply discipline is improving across the sector."
    ]


def test_market_retrieve_infers_sector_from_tickerless_prompt(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(
        _sector_signal(
            statement="Iron ore supply discipline is improving across the sector.",
            metadata={"specificity": 0.76, "themes": ["supply"], "theme_key": "supply"},
        )
    )

    result = store.retrieve(
        query="How is the iron ore sector trading right now?",
        entities={"primary_ticker": None, "tickers": []},
        intent="market",
    )

    assert result["sector"] == "Materials"
    assert [item["statement"] for item in result["sector_items"]] == [
        "Iron ore supply discipline is improving across the sector."
    ]


def test_market_retrieve_collapses_replaced_theme_state(tmp_path: Path) -> None:
    store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    store.update_market_memory(
        _sector_signal(
            statement="Iron ore supply discipline improved in FY2025.",
            metadata={
                "specificity": 0.7,
                "themes": ["supply"],
                "theme_key": "supply",
                "replaceable": True,
            },
        )
    )
    store.update_market_memory(
        _sector_signal(
            statement="Iron ore supply discipline is tightening further in FY2026.",
            source_id="sector-src-3",
            confidence=0.84,
            materiality=0.86,
            metadata={
                "specificity": 0.82,
                "themes": ["supply"],
                "theme_key": "supply",
                "replaceable": True,
            },
        )
    )

    result = store.retrieve(
        query="What is the market backdrop for BHP?",
        entities={"primary_ticker": "BHP", "tickers": ["BHP"]},
        intent="market",
    )

    assert [item["statement"] for item in result["sector_items"]] == [
        "Iron ore supply discipline is tightening further in FY2026."
    ]
