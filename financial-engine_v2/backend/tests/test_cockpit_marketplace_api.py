from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from app.services.marketplace_mission_service import MarketplaceMissionService
from app.services.marketplace_price_intelligence import MarketplacePriceIntelligenceService
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
            "hard_filters": {
                "include_keywords": ["4x4", "dual cab"],
                "price_max": 25000,
                "location_names": ["Melbourne"],
            },
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


def test_marketplace_mission_delete_blocks_active_scan_then_deletes(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Delete me",
            "brief": "Find an RTX 3090 around Melbourne.",
            "hard_filters": {"include_keywords": ["rtx 3090"]},
        },
    )
    assert create_response.status_code == 200
    mission_id = create_response.json()["mission_id"]

    fake_service.state_store.add_job(
        {
            "job_id": "scan-active-1",
            "action_id": "marketplace_scan",
            "args": {"mission_id": mission_id},
            "started_at": "2026-04-22T12:00:00Z",
            "ended_at": None,
            "status": "running",
            "exit_code": None,
            "stdout_path": str(fake_service.artifact_store.logs_dir / "scan-active-1.out.log"),
            "stderr_path": str(fake_service.artifact_store.logs_dir / "scan-active-1.err.log"),
            "artifacts": [],
        }
    )

    blocked = client.delete(f"/api/cockpit/marketplace/missions/{mission_id}")
    assert blocked.status_code == 409

    fake_service.state_store.update_job_status(
        "scan-active-1",
        status="cancelled",
        exit_code=130,
        ended_at="2026-04-22T12:01:00Z",
    )
    deleted = client.delete(f"/api/cockpit/marketplace/missions/{mission_id}")
    assert deleted.status_code == 200
    payload = deleted.json()
    assert payload["ok"] is True
    assert payload["mission_id"] == mission_id
    assert payload["status"] == "deleted"

    lookup = client.get(f"/api/cockpit/marketplace/missions/{mission_id}")
    assert lookup.status_code == 404


def test_marketplace_mission_patch_preserves_existing_filters_when_omitted(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Location sensitive mission",
            "brief": "Find RTX 4090 listings in Melbourne.",
            "hard_filters": {
                "include_keywords": ["RTX 4090"],
                "location_names": ["Melbourne"],
            },
        },
    )
    assert create_response.status_code == 200
    mission_id = create_response.json()["mission_id"]

    patch_response = client.patch(
        f"/api/cockpit/marketplace/missions/{mission_id}",
        json={"status": "paused"},
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["status"] == "paused"
    assert payload["hard_filters"]["include_keywords"] == ["RTX 4090"]
    assert payload["hard_filters"]["location_names"] == ["Melbourne"]


def test_marketplace_mission_get_does_not_prepare_requirement_candidates(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
            "search_config": {"max_queries_per_run": 4},
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get(f"/api/cockpit/marketplace/missions/{mission['mission_id']}")

    assert response.status_code == 200
    assert response.json()["candidate_products"] == []
    assert mission_service.list_mission_candidate_products(mission["mission_id"]) == []
    assert (
        fake_service.state_store.conn.execute(
            "SELECT COUNT(*) FROM marketplace_tracked_products"
        ).fetchone()[0]
        == 0
    )


def test_marketplace_mission_link_product_and_value_context(
    tmp_path,
    monkeypatch,
) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    price_service = MarketplacePriceIntelligenceService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    product = price_service.create_tracked_product(
        {
            "category": "gpu",
            "brand": "NVIDIA",
            "model_family": "RTX 4070",
            "variant": "SUPER 12GB",
        }
    )
    for idx, price in enumerate([620, 640, 660, 680, 700]):
        price_service.ingest_observation(
            {
                "tracked_product_id": product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"api-value-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = price_service.rebuild_benchmark_snapshot(product["tracked_product_id"])
    mission = mission_service.create_mission(
        {
            "name": "GPU value mission",
            "brief": "Find a used RTX 4070 Super in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {
                "include_keywords": ["rtx 4070 super"],
                "location_names": ["Melbourne"],
            },
        }
    )
    match = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "gpu-value-1",
            "listing_url": "https://www.facebook.com/marketplace/item/gpu-value-1/",
            "title": "NVIDIA RTX 4070 Super 12GB",
            "price": "$610",
            "price_value": 610,
            "captured_at": "2026-04-22T01:00:00Z",
            "score": 42,
            "decision_band": "candidate",
            "reasons_for": ["Search match"],
            "reasons_against": [],
            "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    link_response = client.post(
        f"/api/cockpit/marketplace/missions/{mission['mission_id']}/link-product",
        json={"tracked_product_id": product["tracked_product_id"]},
    )
    assert link_response.status_code == 200
    linked = link_response.json()
    assert (
        linked["primary_tracked_product"]["tracked_product"]["tracked_product_id"]
        == product["tracked_product_id"]
    )
    assert linked["benchmark_state"]["snapshot_id"] == snapshot["snapshot_id"]

    match_response = client.get(f"/api/cockpit/marketplace/matches/{match['match_id']}")
    assert match_response.status_code == 200
    payload = match_response.json()
    assert payload["score"] == 42
    assert payload["value_context"]["state"] == "scored"
    assert payload["value_context"]["benchmark_snapshot_id"] == snapshot["snapshot_id"]
    assert payload["value_context"]["value_score"] is not None

    unlink_response = client.delete(
        f"/api/cockpit/marketplace/missions/{mission['mission_id']}/link-product"
    )
    assert unlink_response.status_code == 200
    assert unlink_response.json()["primary_tracked_product"] is None


def test_requirement_mission_uses_matched_candidate_for_value_context(
    tmp_path,
    monkeypatch,
) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    price_service = MarketplacePriceIntelligenceService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    wrong_primary = price_service.create_tracked_product(
        {
            "category": "gpu",
            "brand": "NVIDIA",
            "model_family": "RTX 4070",
            "variant": "SUPER 12GB",
        }
    )
    for idx, price in enumerate([560, 590, 620]):
        price_service.ingest_observation(
            {
                "tracked_product_id": wrong_primary["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-1{idx}T10:00:00+00:00",
                "source_listing_id": f"rtx-4070-value-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    wrong_snapshot = price_service.rebuild_benchmark_snapshot(
        wrong_primary["tracked_product_id"]
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Inference GPU",
            "brief": "24GB GPU for local inference in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
        },
    )
    assert create_response.status_code == 200
    mission = create_response.json()
    assert mission["requirement_profile"]["mode"] == "requirement_driven"
    candidate_keys = {candidate["candidate_key"] for candidate in mission["candidate_products"]}
    assert "gpu-nvidia-rtx-3090-24gb" in candidate_keys
    assert "gpu-nvidia-rtx-4070-ti-super-16gb" not in candidate_keys

    rtx_3090 = next(
        candidate["tracked_product"]
        for candidate in mission["candidate_products"]
        if candidate["candidate_key"] == "gpu-nvidia-rtx-3090-24gb"
    )
    for idx, price in enumerate([900, 940, 980, 1020, 1060]):
        price_service.ingest_observation(
            {
                "tracked_product_id": rtx_3090["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"rtx-3090-value-{idx}",
                "title": f"RTX 3090 24GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = price_service.rebuild_benchmark_snapshot(rtx_3090["tracked_product_id"])

    link_response = client.post(
        f"/api/cockpit/marketplace/missions/{mission['mission_id']}/link-product",
        json={"tracked_product_id": wrong_primary["tracked_product_id"]},
    )
    assert link_response.status_code == 200
    assert (
        link_response.json()["primary_tracked_product"]["tracked_product"]["tracked_product_id"]
        == wrong_primary["tracked_product_id"]
    )

    good_match = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "rtx-3090-local",
            "listing_url": "https://www.facebook.com/marketplace/item/rtx-3090-local/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$920",
            "price_value": 920,
            "captured_at": "2026-04-22T01:00:00Z",
            "score": 51,
            "decision_band": "candidate",
            "reasons_for": ["Search match"],
            "reasons_against": [],
            "raw_text_snapshot": "Used RTX 3090 24GB working condition.",
        }
    )
    good_response = client.get(f"/api/cockpit/marketplace/matches/{good_match['match_id']}")
    assert good_response.status_code == 200
    good_payload = good_response.json()
    assert good_payload["score"] == 51
    assert good_payload["value_context"]["value_source"] == "matched_candidate_benchmark"
    assert (
        good_payload["value_context"]["linked_tracked_product_id"]
        == rtx_3090["tracked_product_id"]
    )
    assert good_payload["value_context"]["benchmark_snapshot_id"] == snapshot["snapshot_id"]

    mismatch = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "rtx-4070-mismatch",
            "listing_url": "https://www.facebook.com/marketplace/item/rtx-4070-mismatch/",
            "title": "NVIDIA RTX 4070 Super 12GB",
            "price": "$610",
            "price_value": 610,
            "captured_at": "2026-04-22T02:00:00Z",
            "score": 49,
            "decision_band": "candidate",
            "reasons_for": ["Search match"],
            "reasons_against": [],
            "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
        }
    )
    mismatch_response = client.get(
        f"/api/cockpit/marketplace/matches/{mismatch['match_id']}"
    )
    assert mismatch_response.status_code == 200
    mismatch_context = mismatch_response.json()["value_context"]
    assert mismatch_context["state"] == "candidate_unmatched"
    assert mismatch_context["value_source"] == "none"
    assert mismatch_context["benchmark_snapshot_id"] is None
    assert mismatch_context["benchmark_snapshot_id"] != wrong_snapshot["snapshot_id"]


def test_marketplace_scan_trigger_allows_ready_health_without_login_state(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
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
            "challenge_detected": False,
            "last_checked_at": "2026-04-18T10:00:00Z",
            "detail": "Marketplace browser profile is ready.",
        },
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api._launch_marketplace_scan_job",
        lambda service, mission_id=None: {
            "ok": True,
            "action_id": "marketplace_scan",
            "result": "Queued marketplace scan job",
            "exit_code": 0,
            "job_id": "scan-login-not-required",
            "status": "queued",
            "queued": True,
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    mission_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Any GPU",
            "brief": "Find any suitable GPU listing in Melbourne.",
        },
    )
    assert mission_response.status_code == 200
    mission_id = mission_response.json()["mission_id"]

    scan_response = client.post("/api/cockpit/marketplace/scans", json={"mission_id": mission_id})

    assert scan_response.status_code == 200
    assert scan_response.json()["job_id"] == "scan-login-not-required"


def test_marketplace_scan_trigger_checks_in_progress_before_health(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api._marketplace_scan_in_progress",
        lambda service: True,
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api.check_marketplace_browser_health",
        lambda: (_ for _ in ()).throw(AssertionError("health check should not run")),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    mission_response = client.post(
        "/api/cockpit/marketplace/missions",
        json={
            "name": "Any GPU",
            "brief": "Find any suitable GPU listing in Melbourne.",
        },
    )
    assert mission_response.status_code == 200
    mission_id = mission_response.json()["mission_id"]

    scan_response = client.post("/api/cockpit/marketplace/scans", json={"mission_id": mission_id})

    assert scan_response.status_code == 409
    assert "already in progress" in scan_response.json()["detail"].lower()


def test_marketplace_scheduler_tick_queues_due_mission(tmp_path, monkeypatch) -> None:
    from app.routes.cockpit_api import _run_marketplace_scheduler_tick

    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    mission = mission_service.create_mission(
        {
            "name": "Dual-cab ute",
            "brief": "Find a reliable 4x4 dual cab under 25k.",
            "hard_filters": {
                "include_keywords": ["4x4", "dual cab"],
                "price_max": 25000,
                "location_names": ["Melbourne"],
            },
        }
    )

    monkeypatch.setattr(
        "app.routes.cockpit_api.check_marketplace_browser_health",
        lambda: {
            "status": "ready",
            "cdp_url": "http://127.0.0.1:9222",
            "browser_family": "chrome",
            "profile_path": "/tmp/profile",
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


def test_terminal_marketplace_jobs_do_not_block_new_scan(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    mission = mission_service.create_mission(
        {
            "name": "GPU mission",
            "brief": "Find used RTX cards in Melbourne.",
            "hard_filters": {"include_keywords": ["rtx"], "location_names": ["Melbourne"]},
        }
    )
    fake_service.state_store.add_job(
        {
            "job_id": "old-scan-1",
            "action_id": "marketplace_scan",
            "args": {"mission_id": mission["mission_id"]},
            "started_at": "2026-04-22T00:00:00Z",
            "ended_at": "2026-04-22T00:01:00Z",
            "status": "cancelled",
            "exit_code": 130,
            "stdout_path": str(fake_service.artifact_store.logs_dir / "old-scan-1.out.log"),
            "stderr_path": str(fake_service.artifact_store.logs_dir / "old-scan-1.err.log"),
            "artifacts": [],
        }
    )
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
            "challenge_detected": False,
            "last_checked_at": "2026-04-18T10:00:00Z",
        },
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api._launch_marketplace_scan_job",
        lambda service, mission_id=None, trigger_source="cockpit": {
            "ok": True,
            "action_id": "marketplace_scan",
            "result": "Queued marketplace scan job",
            "exit_code": 0,
            "job_id": "scan-new-1",
            "status": "queued",
            "queued": True,
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/marketplace/scans",
        json={"mission_id": mission["mission_id"]},
    )
    assert response.status_code == 200
    assert response.json()["job_id"] == "scan-new-1"


def test_marketplace_scheduler_tick_allows_ready_health_without_login_state(tmp_path, monkeypatch) -> None:
    from app.routes.cockpit_api import _run_marketplace_scheduler_tick

    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    mission = mission_service.create_mission(
        {
            "name": "GPU mission",
            "brief": "Find a suitable GPU in Melbourne.",
            "hard_filters": {"location_names": ["Melbourne"]},
        }
    )

    monkeypatch.setattr(
        "app.routes.cockpit_api.check_marketplace_browser_health",
        lambda: {
            "status": "ready",
            "cdp_url": "http://127.0.0.1:9222",
            "browser_family": "chrome",
            "profile_path": "/tmp/profile",
            "challenge_detected": False,
            "last_checked_at": "2026-04-18T10:00:00Z",
            "detail": "Marketplace browser profile is ready.",
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
            "job_id": "scan-scheduled-login-1",
            "status": "queued",
        },
    )

    launched = _run_marketplace_scheduler_tick(fake_service)

    assert launches == [(mission["mission_id"], "scheduler")]
    assert launched == [{"mission_id": mission["mission_id"], "job_id": "scan-scheduled-login-1"}]


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


def test_marketplace_benchmark_refresh_and_overlay(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    mission = mission_service.create_mission(
        {
            "name": "GPU benchmark",
            "brief": "Compare GPU listings against Centre Com",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
        }
    )
    match = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "gpu-123",
            "listing_url": "https://www.facebook.com/marketplace/item/gpu-123/",
            "title": "MSI GeForce RTX 4080 SUPER 16GB",
            "price": "$1,600",
            "captured_at": "2026-04-22T01:00:00Z",
            "score": 92,
            "decision_band": "strong_match",
            "reasons_for": ["Price is below comparable retail"],
            "reasons_against": [],
            "raw_text_snapshot": "NVIDIA RTX 4080 SUPER 16GB in excellent condition.",
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    refresh_response = client.post("/api/cockpit/marketplace/benchmarks/refresh")
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["ok"] is True
    assert set(refresh_payload["categories"]) == {"cpu", "gpu", "nvme_m2", "ram_kit"}

    match_response = client.get(f"/api/cockpit/marketplace/matches/{match['match_id']}")
    assert match_response.status_code == 200
    benchmark = match_response.json()["benchmark"]
    assert benchmark is not None
    assert benchmark["source"] == "centre_com"
    assert benchmark["wording"] == "new retail benchmark"
    assert benchmark["matched_product"]
    assert isinstance(benchmark["confidence"], float)
    second_match_response = client.get(f"/api/cockpit/marketplace/matches/{match['match_id']}")
    assert second_match_response.status_code == 200
    assert (
        fake_service.state_store.conn.execute(
            "SELECT COUNT(*) FROM listing_benchmark_scores WHERE match_id = ?",
            (match["match_id"],),
        ).fetchone()[0]
        == 0
    )


def test_marketplace_low_confidence_match_requires_manual_review(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    mission_service = MarketplaceMissionService(fake_service.state_store)
    monkeypatch.setattr(
        "app.routes.cockpit_api._ensure_marketplace_scan_scheduler",
        lambda service: None,
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    mission = mission_service.create_mission(
        {
            "name": "RAM benchmark review",
            "brief": "Review uncertain RAM-kit matches",
            "category_hint": "ram_kit",
            "hard_filters": {"location_names": ["Melbourne"]},
        }
    )
    match = mission_service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "ram-789",
            "listing_url": "https://www.facebook.com/marketplace/item/ram-789/",
            "title": "DDR5 32GB memory kit",
            "price": "$130",
            "captured_at": "2026-04-22T02:00:00Z",
            "score": 70,
            "decision_band": "candidate",
            "reasons_for": ["Likely DDR5 kit"],
            "reasons_against": ["Incomplete SKU details"],
            "raw_text_snapshot": "Unknown brand DDR5 32GB memory kit.",
        }
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    initial = client.get(f"/api/cockpit/marketplace/matches/{match['match_id']}")
    assert initial.status_code == 200
    initial_benchmark = initial.json()["benchmark"]
    assert initial_benchmark is not None
    assert initial_benchmark["low_confidence"] is True
    assert initial_benchmark["review_status"] == "pending_review"
    assert initial_benchmark["warning"]

    review = client.patch(
        f"/api/cockpit/marketplace/matches/{match['match_id']}/benchmark-review",
        json={"review_status": "accepted", "note": "validated manually"},
    )
    assert review.status_code == 200
    reviewed_benchmark = review.json()["benchmark"]
    assert reviewed_benchmark["review_status"] == "accepted"
    assert reviewed_benchmark["warning"] is None
