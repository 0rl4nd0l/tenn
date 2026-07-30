"""Tests for deterministic financial_snapshot_v0 export."""
from __future__ import annotations

import uuid
from datetime import date

from app.services.analysis.periodic_snapshot_export import (
    SCHEMA_VERSION,
    build_financial_snapshot_v0,
    build_financial_snapshot_v0_from_rows,
    write_financial_snapshot_v0,
)


def test_build_financial_snapshot_v0_empty_ticker_rows():
    out = build_financial_snapshot_v0_from_rows("EMPTY", [], period_type="A", max_periods=5)
    assert out["schema_version"] == SCHEMA_VERSION
    assert out["ticker"] == "EMPTY"
    assert out["warnings"] == [
        "No accepted financial-observation projection rows for EMPTY."
    ]
    assert out["source_table"] == "accepted_financial_observation_projection"
    assert out["periodic_rows"] == []


def test_build_financial_snapshot_v0_is_deterministic():
    d1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
    d2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
    raw = [
        {
            "ticker": "TST",
            "period_end": date(2023, 6, 30),
            "period_type": "A",
            "revenue": 200.0,
            "ebit": 40.0,
            "np_attributable": 30.0,
            "operating_cf": 50.0,
            "investing_cf": None,
            "financing_cf": None,
            "capex": -5.0,
            "cash_end": 50.0,
            "net_debt": 10.0,
            "shares_outstanding": 1_000_000.0,
            "period_start": None,
            "currency": "AUD",
            "source_document_id": d1,
            "confidence_metrics": 0.9,
            "updated_at": None,
        },
        {
            "ticker": "TST",
            "period_end": date(2024, 6, 30),
            "period_type": "A",
            "revenue": 220.0,
            "ebit": 44.0,
            "np_attributable": 33.0,
            "operating_cf": 55.0,
            "investing_cf": None,
            "financing_cf": None,
            "capex": -5.0,
            "cash_end": 55.0,
            "net_debt": 9.0,
            "shares_outstanding": 1_000_000.0,
            "period_start": None,
            "currency": "AUD",
            "source_document_id": d2,
            "confidence_metrics": 0.9,
            "updated_at": None,
        },
    ]
    a = build_financial_snapshot_v0_from_rows("TST", raw, period_type="A", max_periods=5)
    b = build_financial_snapshot_v0_from_rows("TST", list(raw), period_type="A", max_periods=5)
    assert a == b
    assert len(a["periodic_rows"]) == 2
    assert a["metrics_summary"]["period_count"] == 2
    assert a["periodic_rows"][0]["period_end"] == "2023-06-30"
    assert a["periodic_rows"][1]["period_end"] == "2024-06-30"
    assert a["periodic_rows"][0]["source_document_id"] == str(d1)
    assert a["periodic_rows"][1]["source_document_id"] == str(d2)


def test_write_financial_snapshot_v0_roundtrip(tmp_path):
    raw = [
        {
            "ticker": "TST",
            "period_end": date(2024, 6, 30),
            "period_type": "A",
            "revenue": 100.0,
            "ebit": 20.0,
            "np_attributable": 15.0,
            "operating_cf": 25.0,
            "investing_cf": None,
            "financing_cf": None,
            "capex": -5.0,
            "cash_end": 50.0,
            "net_debt": 10.0,
            "shares_outstanding": 1_000_000.0,
            "period_start": None,
            "currency": "AUD",
            "source_document_id": uuid.uuid4(),
            "confidence_metrics": 0.9,
            "updated_at": None,
        },
    ]
    payload = build_financial_snapshot_v0_from_rows("TST", raw)
    path = tmp_path / "financial_snapshot_v0.json"
    write_financial_snapshot_v0(path, payload)
    text = path.read_text(encoding="utf-8")
    assert "financial_snapshot_v0" in text
    assert text.endswith("\n")


def test_snapshot_uses_accepted_projected_rows_not_legacy_query(monkeypatch):
    projected = (
        {
            "ticker": "TST",
            "period_end": date(2024, 6, 30),
            "period_type": "A",
            "revenue": "220",
            "source_document_id": str(uuid.uuid4()),
        },
    )

    class _NoLegacyQuery:
        def query(self, *args, **kwargs):
            raise AssertionError("stale legacy financials must not be queried")

    monkeypatch.setattr(
        "app.services.analysis.periodic_snapshot_export.stable_financial_profile",
        lambda db, *, ticker: projected,
    )

    payload = build_financial_snapshot_v0(" tst ", _NoLegacyQuery())

    assert payload["periodic_rows"][0]["revenue"] == 220.0
    assert payload["source_table"] == "accepted_financial_observation_projection"
