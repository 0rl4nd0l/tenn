from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_home import (
    build_attention_queue_snapshot,
    build_home_narrative_snapshot,
    build_market_movers_snapshot,
)


class FakeStateStore:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def list_market_update_followups(self, *, status: str | None = None, limit: int = 100):
        self.calls.append({"status": status, "limit": limit})
        return self.rows[:limit]


def test_attention_queue_snapshot_empty_queue_is_ready() -> None:
    store = FakeStateStore([])

    snapshot = build_attention_queue_snapshot(
        store,
        now=datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc),
    )

    assert store.calls == [{"status": "queued", "limit": 50}]
    assert snapshot.data_state == "READY"
    assert snapshot.degraded is False
    assert snapshot.data_missing == []
    assert snapshot.as_of == "2026-05-07T02:00:00+00:00"
    assert snapshot.items == []


def test_attention_queue_snapshot_maps_queued_market_update_followup() -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-1",
                "report_id": "report-1",
                "ticker": "BHP",
                "action_type": "review",
                "priority_score": 0.82,
                "reason": {"reasons": ["notable price move", "alert present"], "score": 0.82},
                "status": "queued",
                "created_at": "2026-05-07T01:15:00+00:00",
            }
        ]
    )

    snapshot = build_attention_queue_snapshot(store, limit=10)

    assert store.calls == [{"status": "queued", "limit": 10}]
    assert snapshot.data_state == "READY"
    assert snapshot.as_of == "2026-05-07T01:15:00+00:00"
    assert len(snapshot.items) == 1
    item = snapshot.items[0]
    assert item.id == "market_update_followup:fu-1"
    assert item.title == "BHP: review"
    assert item.reason == "notable price move; alert present"
    assert item.status == "queued"
    assert item.priority == "high"
    assert item.source_type == "market_update_followup"
    assert item.created_at == "2026-05-07T01:15:00+00:00"
    assert item.source_id is None
    assert item.target_route == "/news"


def test_attention_queue_snapshot_maps_watchlist_followup_to_read_only_route() -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-watch",
                "report_id": "report-1",
                "ticker": "CBA",
                "action_type": "watchlist_add_proposal",
                "priority_score": 0.5,
                "reason": {"note": "review watchlist proposal"},
                "status": "queued",
                "created_at": "2026-05-07T01:30:00+00:00",
            }
        ]
    )

    snapshot = build_attention_queue_snapshot(store)

    assert snapshot.items[0].target_route == "/watchlist"


def test_attention_queue_endpoint_returns_backend_owned_operational_queue(monkeypatch) -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-2",
                "report_id": "report-2",
                "ticker": "CBA",
                "action_type": "watchlist_add_proposal",
                "priority_score": 0.5,
                "reason": {"note": "review watchlist proposal"},
                "status": "queued",
                "created_at": "2026-05-07T01:30:00+00:00",
            }
        ]
    )

    class FakeService:
        state_store = store

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(lambda: FakeService()),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")

    response = TestClient(app).get("/api/cockpit/home/attention-queue")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data_state": "READY",
        "degraded": False,
        "data_missing": [],
        "as_of": "2026-05-07T01:30:00+00:00",
        "items": [
            {
                "id": "market_update_followup:fu-2",
                "title": "CBA: watchlist add proposal",
                "reason": "review watchlist proposal",
                "status": "queued",
                "priority": "medium",
                "source_type": "market_update_followup",
                "created_at": "2026-05-07T01:30:00+00:00",
                "updated_at": "2026-05-07T01:30:00+00:00",
                "source_id": None,
                "target_route": "/watchlist",
            }
        ],
    }


def test_market_movers_snapshot_uses_backend_owned_operational_signals() -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-1",
                "report_id": "report-1",
                "ticker": "BHP",
                "action_type": "review",
                "priority_score": 0.82,
                "reason": {"reasons": ["notable price move"]},
                "status": "queued",
                "created_at": "2026-05-07T01:15:00+00:00",
            }
        ]
    )

    snapshot = build_market_movers_snapshot(store)

    assert snapshot.data_state == "PARTIAL"
    assert len(snapshot.items) == 1
    item = snapshot.items[0]
    assert item.id == "home-market-movers:market_update_followup:fu-1"
    assert item.ticker == "BHP"
    assert item.price is None
    assert item.change is None
    assert item.change_percent is None
    assert item.source_label == "operational_trace"
    assert [signal.code for signal in item.data_missing] == [
        "MARKET_MOVER_PRICE_FIELDS_MISSING"
    ]


def test_market_movers_endpoint_returns_operational_trace_payload(monkeypatch) -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-1",
                "report_id": "report-1",
                "ticker": "BHP",
                "action_type": "review",
                "priority_score": 0.82,
                "reason": {"reasons": ["notable price move"]},
                "status": "queued",
                "created_at": "2026-05-07T01:15:00+00:00",
            }
        ]
    )

    class FakeService:
        state_store = store

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(lambda: FakeService()),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")

    response = TestClient(app).get("/api/cockpit/home/market-movers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_state"] == "PARTIAL"
    assert payload["items"][0]["id"] == "home-market-movers:market_update_followup:fu-1"
    assert payload["items"][0]["ticker"] == "BHP"
    assert payload["items"][0]["source_label"] == "operational_trace"
    assert payload["items"][0]["price"] is None
    assert payload["items"][0]["data_missing"][0]["code"] == "MARKET_MOVER_PRICE_FIELDS_MISSING"


def test_home_narrative_snapshot_returns_explicit_missing_without_source() -> None:
    snapshot = build_home_narrative_snapshot(
        now=datetime(2026, 5, 7, 2, 0, tzinfo=timezone.utc),
    )

    assert snapshot.data_state == "DATA_MISSING"
    assert snapshot.session_summary is None
    assert snapshot.theme_candidates == []
    assert snapshot.tomorrow_prep == []
    assert {signal.code for signal in snapshot.data_missing} == {
        "NO_SESSION_SUMMARY_ENDPOINT",
        "NO_THEME_CANDIDATES_ENDPOINT",
        "NO_TOMORROW_PREP_ENDPOINT",
    }


def test_home_narrative_snapshot_builds_operational_session_summary_from_followups() -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-1",
                "report_id": "report-1",
                "ticker": "BHP",
                "action_type": "review",
                "priority_score": 0.82,
                "reason": {"reasons": ["notable price move"]},
                "status": "queued",
                "created_at": "2026-05-07T01:15:00+00:00",
            },
            {
                "followup_id": "fu-2",
                "report_id": "report-2",
                "ticker": "CBA",
                "action_type": "watchlist_add_proposal",
                "priority_score": 0.5,
                "reason": {"note": "review watchlist proposal"},
                "status": "queued",
                "created_at": "2026-05-07T01:30:00+00:00",
            },
        ]
    )

    snapshot = build_home_narrative_snapshot(store, limit=5)

    assert store.calls == [{"status": "queued", "limit": 5}]
    assert snapshot.data_state == "PARTIAL"
    assert snapshot.degraded is False
    assert snapshot.as_of == "2026-05-07T01:30:00+00:00"
    assert snapshot.session_summary == (
        "Cockpit has 2 queued operational follow-ups from backend market-update state: "
        "BHP: review (high priority; notable price move); "
        "CBA: watchlist add proposal (medium priority; review watchlist proposal)."
    )
    assert snapshot.theme_candidates == []
    assert snapshot.tomorrow_prep == []
    assert {signal.code for signal in snapshot.data_missing} == {
        "NO_THEME_CANDIDATES_ENDPOINT",
        "NO_TOMORROW_PREP_ENDPOINT",
    }


def test_home_narrative_endpoint_returns_explicit_missing_state(monkeypatch) -> None:
    store = FakeStateStore([])

    class FakeService:
        state_store = store

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(lambda: FakeService()),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    response = TestClient(app).get("/api/cockpit/home/narrative")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_state"] == "DATA_MISSING"
    assert payload["session_summary"] is None
    assert payload["theme_candidates"] == []
    assert payload["tomorrow_prep"] == []
    assert {signal["code"] for signal in payload["data_missing"]} == {
        "NO_SESSION_SUMMARY_ENDPOINT",
        "NO_THEME_CANDIDATES_ENDPOINT",
        "NO_TOMORROW_PREP_ENDPOINT",
    }


def test_home_narrative_endpoint_keeps_missing_state_when_source_unavailable(monkeypatch) -> None:
    def raise_unavailable():
        raise RuntimeError("state store unavailable")

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(raise_unavailable),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    response = TestClient(app).get("/api/cockpit/home/narrative")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_state"] == "DATA_MISSING"
    assert payload["degraded"] is True
    assert payload["session_summary"] is None
    assert {signal["code"] for signal in payload["data_missing"]} == {
        "NO_SESSION_SUMMARY_ENDPOINT",
        "NO_THEME_CANDIDATES_ENDPOINT",
        "NO_TOMORROW_PREP_ENDPOINT",
    }


def test_home_narrative_endpoint_wires_read_only_operational_summary(monkeypatch) -> None:
    store = FakeStateStore(
        [
            {
                "followup_id": "fu-1",
                "report_id": "report-1",
                "ticker": "BHP",
                "action_type": "review",
                "priority_score": 0.82,
                "reason": {"reasons": ["notable price move"]},
                "status": "queued",
                "created_at": "2026-05-07T01:15:00+00:00",
            }
        ]
    )

    class FakeService:
        state_store = store

    monkeypatch.setattr(
        cockpit_api.CockpitService,
        "get_instance",
        staticmethod(lambda: FakeService()),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    response = TestClient(app).get("/api/cockpit/home/narrative")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_state"] == "PARTIAL"
    assert payload["degraded"] is False
    assert payload["as_of"] == "2026-05-07T01:15:00+00:00"
    assert payload["session_summary"] == (
        "Cockpit has 1 queued operational follow-up from backend market-update state: "
        "BHP: review (high priority; notable price move)."
    )
    assert payload["theme_candidates"] == []
    assert payload["tomorrow_prep"] == []
    assert {signal["code"] for signal in payload["data_missing"]} == {
        "NO_THEME_CANDIDATES_ENDPOINT",
        "NO_TOMORROW_PREP_ENDPOINT",
    }
