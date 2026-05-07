from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_home import build_portfolio_snapshot


class FakeStateStore:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def list_holdings(self, *, include_archived: bool = False):
        self.calls.append({"include_archived": include_archived})
        return self.rows


def test_portfolio_snapshot_empty_holdings_is_ready() -> None:
    snapshot = build_portfolio_snapshot(
        [],
        now=datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc),
    )

    assert snapshot.data_state == "READY"
    assert snapshot.degraded is False
    assert snapshot.data_missing == []
    assert snapshot.total_value == 0.0
    assert snapshot.currency is None
    assert snapshot.day_change == 0.0
    assert snapshot.day_change_percent == 0.0
    assert snapshot.coverage_percent == 100.0
    assert snapshot.holdings_count == 0
    assert snapshot.priced_holdings_count == 0
    assert snapshot.day_change_priced_holdings_count == 0
    assert snapshot.source_label == "local_personal_data"


def test_portfolio_snapshot_aggregates_same_currency_total_and_day_change() -> None:
    snapshot = build_portfolio_snapshot(
        [
            {
                "ticker": "BHP",
                "quantity": 10,
                "current_price": 100,
                "previous_close": 98,
                "price_currency": "AUD",
                "price_as_of": "2026-05-07T01:00:00+00:00",
                "market_value": 1000,
            },
            {
                "ticker": "CBA",
                "quantity": 2,
                "current_price": 50,
                "previous_close": 55,
                "price_currency": "AUD",
                "price_as_of": "2026-05-07T01:30:00+00:00",
                "market_value": 100,
            },
        ]
    )

    assert snapshot.data_state == "READY"
    assert snapshot.data_missing == []
    assert snapshot.total_value == 1100.0
    assert snapshot.currency == "AUD"
    assert snapshot.day_change == 10.0
    assert snapshot.day_change_percent == 0.92
    assert snapshot.coverage_percent == 100.0
    assert snapshot.holdings_count == 2
    assert snapshot.priced_holdings_count == 2
    assert snapshot.day_change_priced_holdings_count == 2
    assert snapshot.as_of == "2026-05-07T01:30:00+00:00"


def test_portfolio_snapshot_keeps_mixed_currency_total_ambiguous() -> None:
    snapshot = build_portfolio_snapshot(
        [
            {
                "ticker": "BHP",
                "quantity": 10,
                "current_price": 100,
                "previous_close": 99,
                "price_currency": "AUD",
                "market_value": 1000,
            },
            {
                "ticker": "AAPL",
                "quantity": 2,
                "current_price": 200,
                "previous_close": 190,
                "price_currency": "USD",
                "market_value": 400,
            },
        ],
        now=datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc),
    )

    assert snapshot.data_state == "PARTIAL"
    assert snapshot.total_value is None
    assert snapshot.currency is None
    assert snapshot.day_change is None
    assert snapshot.day_change_percent is None
    assert {item.code for item in snapshot.data_missing} == {
        "PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS",
        "PORTFOLIO_DAY_CHANGE_CURRENCY_AMBIGUOUS",
    }


def test_portfolio_snapshot_exposes_partial_day_change_with_coverage() -> None:
    snapshot = build_portfolio_snapshot(
        [
            {
                "ticker": "BHP",
                "quantity": 10,
                "current_price": 100,
                "previous_close": 98,
                "price_currency": "AUD",
                "market_value": 1000,
            },
            {
                "ticker": "CBA",
                "quantity": 2,
                "current_price": 50,
                "previous_close": None,
                "price_currency": "AUD",
                "market_value": 100,
            },
        ],
        now=datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc),
    )

    assert snapshot.data_state == "PARTIAL"
    assert snapshot.total_value == 1100.0
    assert snapshot.currency == "AUD"
    assert snapshot.day_change == 20.0
    assert snapshot.day_change_percent == 2.04
    assert snapshot.day_change_priced_holdings_count == 1
    assert [item.code for item in snapshot.data_missing] == ["PORTFOLIO_DAY_CHANGE_PARTIAL"]


def test_home_portfolio_endpoint_returns_local_personal_snapshot(monkeypatch) -> None:
    store = FakeStateStore([{"ticker": "BHP", "quantity": 10}])

    class FakeService:
        state_store = store

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(lambda: FakeService()),
    )
    monkeypatch.setattr(
        cockpit_api,
        "_enrich_holdings_with_live_prices",
        lambda rows: [
            {
                **rows[0],
                "current_price": 100,
                "previous_close": 99,
                "price_currency": "AUD",
                "price_as_of": "2026-05-07T01:00:00+00:00",
                "market_value": 1000,
            }
        ],
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")

    response = TestClient(app).get("/api/cockpit/home/portfolio")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data_state": "READY",
        "degraded": False,
        "data_missing": [],
        "as_of": "2026-05-07T01:00:00+00:00",
        "source_label": "local_personal_data",
        "total_value": 1000.0,
        "currency": "AUD",
        "day_change": 10.0,
        "day_change_percent": 1.01,
        "coverage_percent": 100.0,
        "holdings_count": 1,
        "priced_holdings_count": 1,
        "day_change_priced_holdings_count": 1,
    }
    assert store.calls == [{"include_archived": False}]


def test_holdings_enrichment_preserves_previous_close_for_day_change(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_live_price_snapshot_for_holding",
        lambda ticker, market_exchange: {
            "current_price": 50,
            "previous_close": 48,
            "price_currency": "AUD",
            "price_as_of": "2026-05-07T01:00:00+00:00",
            "market_exchange": market_exchange or "ASX",
        },
    )

    rows = cockpit_api._enrich_holdings_with_live_prices(
        [{"ticker": "BHP", "quantity": 100, "market_exchange": "ASX"}]
    )

    assert rows[0]["current_price"] == 50
    assert rows[0]["previous_close"] == 48
    assert rows[0]["market_value"] == 5000
    assert rows[0]["day_change"] == 200
    assert round(rows[0]["day_change_percent"], 2) == 4.17
