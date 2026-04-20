from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from cockpit.storage.state import StateStore


def _fake_service(tmp_path: Path) -> SimpleNamespace:
    state_store = StateStore(str(tmp_path / "state.db"))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        state_store=state_store,
        artifact_store=SimpleNamespace(logs_dir=logs_dir),
    )


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
