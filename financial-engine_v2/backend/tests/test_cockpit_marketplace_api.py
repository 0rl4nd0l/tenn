from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from app.services.marketplace_mission_service import MarketplaceMissionService
from cockpit.storage.state import StateStore


def _fake_service(tmp_path: Path) -> SimpleNamespace:
    state_store = StateStore(str(tmp_path / "state.db"))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        state_store=state_store,
        artifact_store=SimpleNamespace(logs_dir=logs_dir),
    )


def test_marketplace_api_supports_missions_matches_and_alerts(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api.check_marketplace_browser_health",
        lambda: {
            "status": "ready",
            "cdp_url": "http://127.0.0.1:9222",
            "browser_family": "chrome",
            "profile_path": "/tmp/profile",
            "logged_in": True,
            "challenge_detected": False,
            "last_checked_at": "2026-04-18T10:00:00Z",
        },
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api._launch_marketplace_scan_job",
        lambda service, mission_id=None: {
            "ok": True,
            "action_id": "marketplace_scan",
            "result": "Queued marketplace scan job",
            "exit_code": 0,
            "job_id": "scan-1",
            "status": "queued",
            "queued": True,
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Dual-cab ute",
            "brief": "Find a reliable 4x4 dual cab under 25k.",
            "hard_filters": {"include_keywords": ["4x4", "dual cab"], "price_max": 25000},
        },
    )
    assert create_response.status_code == 200
    mission = create_response.json()

    assert client.get("/api/cockpit/marketplace/missions").json()["items"][0]["mission_id"] == mission["mission_id"]
    assert client.get("/api/cockpit/marketplace/browser-health").json()["status"] == "ready"

    scan_response = client.post("/api/cockpit/marketplace/scans", json={"mission_id": mission["mission_id"]})
    assert scan_response.status_code == 200
    assert scan_response.json()["job_id"] == "scan-1"

    match = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "123",
            "listing_url": "https://www.facebook.com/marketplace/item/123/",
            "title": "2014 Toyota Hilux SR5 4x4",
            "price": "$22,500",
            "captured_at": "2026-04-18T10:00:00Z",
            "score": 89,
            "decision_band": "strong_match",
            "reasons_for": ["Below local median"],
            "reasons_against": ["High kilometres"],
            "raw_text_snapshot": "Visible listing text",
        }
    )
    alert = mission_service.create_alert(
        mission_id=mission["mission_id"],
        match_id=match["match_id"],
        trigger_reason="new_listing",
    )

    matches_response = client.get("/api/cockpit/marketplace/matches")
    assert matches_response.status_code == 200
    assert matches_response.json()["items"][0]["match_id"] == match["match_id"]
    single_match_response = client.get(
        f"/api/cockpit/marketplace/matches/{match['match_id']}"
    )
    assert single_match_response.status_code == 200
    assert single_match_response.json()["title"] == "2014 Toyota Hilux SR5 4x4"

    alert_response = client.get("/api/cockpit/marketplace/alerts")
    assert alert_response.status_code == 200
    assert alert_response.json()["items"][0]["alert_id"] == alert["alert_id"]

    update_match_response = client.patch(
        f"/api/cockpit/marketplace/matches/{match['match_id']}",
        json={"status": "reviewed"},
    )
    assert update_match_response.status_code == 200
    assert update_match_response.json()["status"] == "reviewed"

    update_alert_response = client.patch(
        f"/api/cockpit/marketplace/alerts/{alert['alert_id']}",
        json={"status": "acknowledged"},
    )
    assert update_alert_response.status_code == 200
    assert update_alert_response.json()["status"] == "acknowledged"


def test_marketplace_scheduler_tick_queues_due_mission(tmp_path, monkeypatch) -> None:
    from app.routes.cockpit_api import _run_marketplace_scheduler_tick

    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    mission = mission_service.create_mission(
        {
            "name": "Dual-cab ute",
            "brief": "Find a reliable 4x4 dual cab under 25k.",
            "hard_filters": {"include_keywords": ["4x4", "dual cab"], "price_max": 25000},
        }
    )

    monkeypatch.setattr(
        "app.routes.cockpit_api.check_marketplace_browser_health",
        lambda: {
            "status": "ready",
            "cdp_url": "http://127.0.0.1:9222",
            "browser_family": "chrome",
            "profile_path": "/tmp/profile",
            "logged_in": True,
            "challenge_detected": False,
            "last_checked_at": "2026-04-18T10:00:00Z",
        },
    )
    launches: list[tuple[str | None, str]] = []
    monkeypatch.setattr(
        "app.routes.cockpit_api._launch_marketplace_scan_job",
        lambda service, mission_id=None, trigger_source="cockpit": launches.append(
            (mission_id, trigger_source)
        )
        or {
            "ok": True,
            "job_id": "scan-scheduled-1",
            "status": "queued",
        },
    )

    launched = _run_marketplace_scheduler_tick(fake_service)

    assert launches == [(mission["mission_id"], "scheduler")]
    assert launched == [{"mission_id": mission["mission_id"], "job_id": "scan-scheduled-1"}]


def test_marketplace_scan_detail_returns_tail_and_progress(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    stdout_path = fake_service.artifact_store.logs_dir / "scan-1.out.log"
    stdout_path.write_text("line one\nline two\nline three\n", encoding="utf-8")
    fake_service.state_store.add_job(
        {
            "job_id": "scan-1",
            "action_id": "marketplace_scan",
            "args": {"mission_id": "mission-1"},
            "started_at": "2026-04-20T01:00:00Z",
            "ended_at": None,
            "status": "running",
            "exit_code": None,
            "stdout_path": str(stdout_path),
            "stderr_path": str(fake_service.artifact_store.logs_dir / "scan-1.err.log"),
            "artifacts": [],
        }
    )
    fake_service.state_store.update_job_progress("scan-1", "Collecting cards", 42.5)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/marketplace/scans/scan-1?tail=2")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "scan-1"
    assert body["progress_stage"] == "Collecting cards"
    assert body["progress_pct"] == 42.5
    assert body["result"] == "line two\nline three"


def test_marketplace_stop_job_sets_runtime_cancel_flag(tmp_path, monkeypatch) -> None:
    from app.routes.cockpit_api import (
        QueuedActionJobRuntime,
        _forget_queued_action_job,
        _register_queued_action_job,
    )

    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    runtime = QueuedActionJobRuntime(
        job_id="scan-stop-1",
        action_id="marketplace_scan",
        started_at="2026-04-21T00:00:00Z",
    )
    _register_queued_action_job(runtime)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    try:
        response = client.post("/api/cockpit/action/jobs/scan-stop-1/stop")
        assert response.status_code == 200
        assert response.json() == {
            "ok": True,
            "job_id": "scan-stop-1",
            "status": "cancelling",
        }
        assert runtime.stop_event.is_set() is True
    finally:
        _forget_queued_action_job("scan-stop-1")
