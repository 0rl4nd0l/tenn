from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_home import (
    MarketSessionSnapshot,
    build_market_session_snapshot,
)


def test_market_session_snapshot_reports_open_session() -> None:
    snapshot = build_market_session_snapshot(
        datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc)
    )

    assert snapshot.exchange == "ASX"
    assert snapshot.timezone == "Australia/Melbourne"
    assert snapshot.session == "OPEN"
    assert snapshot.session_date == "2026-05-07"
    assert snapshot.next_event_label == "ASX close"
    assert snapshot.next_event_at == "2026-05-07T06:00:00+00:00"


def test_market_session_snapshot_reports_pre_market_same_local_session() -> None:
    snapshot = build_market_session_snapshot(
        datetime(2026, 5, 7, 23, 0, tzinfo=timezone.utc)
    )

    assert snapshot.session == "PRE_MARKET"
    assert snapshot.session_date == "2026-05-08"
    assert snapshot.next_event_label == "ASX open"
    assert snapshot.next_event_at == "2026-05-08T00:00:00+00:00"


def test_market_session_endpoint_returns_backend_owned_calendar_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "build_market_session_snapshot",
        lambda: MarketSessionSnapshot(
            exchange="ASX",
            timezone="Australia/Melbourne",
            session="POST_MARKET",
            session_date="2026-05-07",
            next_event_label="ASX open",
            next_event_at="2026-05-08T00:00:00+00:00",
            as_of="2026-05-07T08:00:00+00:00",
        ),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")

    response = TestClient(app).get("/api/cockpit/home/market-session")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "exchange": "ASX",
        "timezone": "Australia/Melbourne",
        "session": "POST_MARKET",
        "session_date": "2026-05-07",
        "next_event_label": "ASX open",
        "next_event_at": "2026-05-08T00:00:00+00:00",
        "as_of": "2026-05-07T08:00:00+00:00",
    }
