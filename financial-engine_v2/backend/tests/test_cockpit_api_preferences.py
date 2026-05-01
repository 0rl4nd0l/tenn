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


def test_preferences_defaults_and_patch_round_trip(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    initial = client.get("/api/cockpit/preferences")
    assert initial.status_code == 200
    assert initial.json() == {
        "api_default_enabled": False,
        "marketplace_prefer_cloud_routing": False,
        "chat_routing_policy_override": "config_default",
    }

    patched = client.patch(
        "/api/cockpit/preferences",
        json={
            "api_default_enabled": True,
            "marketplace_prefer_cloud_routing": True,
            "chat_routing_policy_override": "local_preferred",
        },
    )
    assert patched.status_code == 200
    assert patched.json() == {
        "api_default_enabled": True,
        "marketplace_prefer_cloud_routing": True,
        "chat_routing_policy_override": "local_preferred",
    }

    after = client.get("/api/cockpit/preferences")
    assert after.status_code == 200
    assert after.json() == {
        "api_default_enabled": True,
        "marketplace_prefer_cloud_routing": True,
        "chat_routing_policy_override": "local_preferred",
    }


def test_preferences_reject_invalid_chat_routing_policy(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.patch(
        "/api/cockpit/preferences",
        json={"chat_routing_policy_override": "bad_policy"},
    )

    assert response.status_code == 400
    assert "Invalid chat_routing_policy_override" in response.json()["detail"]
