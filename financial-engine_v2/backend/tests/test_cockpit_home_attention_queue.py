from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_home import build_attention_queue_snapshot


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
