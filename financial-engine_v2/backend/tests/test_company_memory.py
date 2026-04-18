from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.company_memory import CompanyMemoryStore


def _signal(**overrides):
    payload = {
        "type": "risk",
        "statement": "Customer concentration remains elevated.",
        "entity_id": "BHP",
        "confidence": 0.7,
        "materiality": 0.8,
        "persistence": "medium",
        "status": "active",
        "source": "commentary",
        "source_id": "src-1",
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def test_insert_creates_active_entry_and_change_log(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")

    result = store.update_company_memory("BHP", _signal())

    assert result["rule"] == "insert"
    entries = store.list_entries("BHP")
    assert len(entries) == 1
    assert entries[0]["status"] == "active"
    change_log = store.list_change_log("BHP")
    assert change_log[-1]["event_type"] == "insert"


def test_duplicate_signal_is_deduped_by_source_id(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory("BHP", _signal())

    result = store.update_company_memory("BHP", _signal())

    assert result["rule"] == "dedupe"
    entries = store.list_entries("BHP")
    assert len(entries) == 1
    assert entries[0]["reinforcement_count"] == 0


def test_matching_signal_from_new_source_reinforces_existing_entry(
    tmp_path: Path,
) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory("BHP", _signal(confidence=0.6, materiality=0.5))

    result = store.update_company_memory(
        "BHP",
        _signal(source_id="src-2", confidence=0.9, materiality=0.9),
    )

    assert result["rule"] == "reinforce"
    entries = store.list_entries("BHP")
    assert len(entries) == 1
    assert entries[0]["confidence"] == pytest.approx(0.9)
    assert entries[0]["materiality"] == pytest.approx(0.9)
    assert entries[0]["reinforcement_count"] == 1


def test_supersede_marks_prior_entry_inactive_and_inserts_new_one(
    tmp_path: Path,
) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    original = store.update_company_memory(
        "BHP",
        _signal(type="strategy", statement="Management is prioritising volume growth."),
    )

    result = store.update_company_memory(
        "BHP",
        _signal(
            type="strategy",
            statement="Management is now prioritising free cash flow.",
            source_id="src-2",
            supersedes=[original["entry"]["entry_id"]],
        ),
    )

    assert result["rule"] == "supersede"
    entries = store.list_entries("BHP")
    statuses = {entry["statement"]: entry["status"] for entry in entries}
    assert statuses["Management is prioritising volume growth."] == "superseded"
    assert statuses["Management is now prioritising free cash flow."] == "active"


def test_contradict_marks_prior_entry_contradicted_and_inserts_new_one(
    tmp_path: Path,
) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory(
        "BHP",
        _signal(
            type="catalyst", statement="Copper expansion should complete on schedule."
        ),
    )

    result = store.update_company_memory(
        "BHP",
        _signal(
            type="risk",
            statement="Copper expansion schedule now looks at risk.",
            source_id="src-2",
            contradicts=["Copper expansion should complete on schedule."],
        ),
    )

    assert result["rule"] == "contradict"
    entries = store.list_entries("BHP")
    statuses = {entry["statement"]: entry["status"] for entry in entries}
    assert statuses["Copper expansion should complete on schedule."] == "contradicted"
    assert statuses["Copper expansion schedule now looks at risk."] == "active"


def test_expire_marks_existing_entry_without_inserting_new_one(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory(
        "BHP",
        _signal(
            type="context", statement="Temporary rail outage is constraining exports."
        ),
    )

    result = store.update_company_memory(
        "BHP",
        _signal(
            type="context",
            statement="Temporary rail outage is constraining exports.",
            status="expired",
            source_id="src-expire",
        ),
    )

    assert result["rule"] == "expire"
    entries = store.list_entries("BHP")
    assert len(entries) == 1
    assert entries[0]["status"] == "expired"


def test_add_manual_entry_marks_metadata_and_uses_manual_source(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")

    result = store.add_manual_entry(
        "BHP",
        signal_type="risk",
        statement="Contractor availability remains tight.",
        metadata={"operator": "alex"},
    )

    assert result["rule"] == "insert"
    entry = store.list_entries("BHP")[0]
    assert entry["source"] == "backend_manual"
    assert entry["metadata"]["manual"] is True
    assert entry["metadata"]["operator"] == "alex"


def test_expire_entry_soft_expires_by_entry_id(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    inserted = store.add_manual_entry(
        "BHP",
        signal_type="risk",
        statement="Manual risk entry.",
    )

    result = store.expire_entry("BHP", inserted["entry"]["entry_id"], reason="cleanup")

    assert result["rule"] == "expire"
    entry = store.list_entries("BHP")[0]
    assert entry["status"] == "expired"
    assert store.list_change_log("BHP")[-1]["details"]["reason"] == "cleanup"


def test_manual_entry_rejects_financial_metric_signals(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")

    with pytest.raises(ValueError, match="financial"):
        store.add_manual_entry(
            "BHP",
            signal_type="revenue",
            statement="Revenue is rising.",
        )


def test_store_rejects_financial_metric_signals(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")

    with pytest.raises(ValueError, match="financial"):
        store.update_company_memory(
            "BHP",
            _signal(type="revenue", statement="Revenue was AUD 55 billion."),
        )


def test_company_memory_connect_enables_wal_and_busy_timeout(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")

    with store._connect() as conn:
        journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        busy_timeout = int(conn.execute("PRAGMA busy_timeout").fetchone()[0])

    assert journal_mode == "wal"
    assert busy_timeout >= 5000


def test_company_memory_retries_transient_locked_database(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    original_connect = store._connect
    calls = {"count": 0}

    def flaky_connect():
        calls["count"] += 1
        if calls["count"] == 1:
            raise sqlite3.OperationalError("database is locked")
        return original_connect()

    store._connect = flaky_connect  # type: ignore[method-assign]

    result = store.update_company_memory("BHP", _signal())

    assert result["rule"] == "insert"
    assert calls["count"] >= 2


def test_retrieve_filters_out_weak_one_off_signals(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory(
        "BHP",
        _signal(
            type="interpretation",
            statement="The setup looks interesting.",
            confidence=0.32,
            materiality=0.3,
            metadata={"specificity": 0.32, "themes": ["growth"], "theme_key": "growth"},
        ),
    )
    store.update_company_memory(
        "BHP",
        _signal(
            type="risk",
            statement="Customer concentration remains elevated in the steel segment.",
            source_id="src-2",
            confidence=0.78,
            materiality=0.82,
            metadata={"specificity": 0.72, "themes": ["demand"], "theme_key": "demand"},
        ),
    )

    result = store.retrieve(
        query="What are the risks for BHP?",
        entities={"primary_ticker": "BHP"},
        intent="risk_catalyst",
    )

    assert [item["statement"] for item in result["items"]] == [
        "Customer concentration remains elevated in the steel segment."
    ]
    assert result["items"][0]["active_score"] >= 0.56


def test_retrieve_collapses_replaced_time_bounded_claims_by_theme(
    tmp_path: Path,
) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory(
        "BHP",
        _signal(
            type="management_guidance",
            statement="BHP guides FY2025 copper growth to the low end.",
            confidence=0.68,
            materiality=0.74,
            metadata={
                "specificity": 0.72,
                "themes": ["growth"],
                "theme_key": "growth",
                "time_refs": ["fiscal_year"],
                "replaceable": True,
            },
        ),
    )
    store.update_company_memory(
        "BHP",
        _signal(
            type="management_guidance",
            statement="BHP guides FY2026 copper growth higher.",
            source_id="src-2",
            confidence=0.84,
            materiality=0.82,
            metadata={
                "specificity": 0.82,
                "themes": ["growth"],
                "theme_key": "growth",
                "time_refs": ["fiscal_year"],
                "replaceable": True,
            },
        ),
    )

    result = store.retrieve(
        query="What is BHP management guiding for growth?",
        entities={"primary_ticker": "BHP"},
        intent="strategy",
    )

    assert [item["statement"] for item in result["items"]] == [
        "BHP guides FY2026 copper growth higher."
    ]


def test_retrieve_prefers_current_contradicting_signal(tmp_path: Path) -> None:
    store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    store.update_company_memory(
        "BHP",
        _signal(
            type="management_guidance",
            statement="Copper expansion should complete on schedule.",
            metadata={"specificity": 0.7, "themes": ["growth"], "theme_key": "growth"},
        ),
    )
    store.update_company_memory(
        "BHP",
        _signal(
            type="risk",
            statement="Copper expansion timing is now at risk.",
            source_id="src-2",
            contradicts=["Copper expansion should complete on schedule."],
            confidence=0.82,
            materiality=0.86,
            metadata={"specificity": 0.78, "themes": ["growth"], "theme_key": "growth"},
        ),
    )

    result = store.retrieve(
        query="What are the risks for BHP?",
        entities={"primary_ticker": "BHP"},
        intent="risk_catalyst",
    )

    assert [item["statement"] for item in result["items"]] == [
        "Copper expansion timing is now at risk."
    ]
