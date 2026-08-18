"""Regression tests for DbReader's retired financial compatibility surface."""
from __future__ import annotations

from cockpit.integrations.db_reader import DbReader


def test_legacy_financial_methods_are_query_free_empty_stubs(monkeypatch):
    reader = DbReader("sqlite:///:memory:")

    def reject_query(*args, **kwargs):
        raise AssertionError("retired financial table must never be queried")

    monkeypatch.setattr(reader, "_run_read_query", reject_query)

    assert reader.get_financials("BHP", limit=10) == []
    assert reader.get_latest_financial_snapshot("BHP") is None
    assert reader.get_low_confidence_financials(
        threshold=0.4,
        limit=10,
        ticker="BHP",
    ) == []
    assert reader.get_low_confidence_financials(threshold=0.4, limit=10) == []
