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


def test_route_alias_api_confirmation_gate_round_trip(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    proposed_response = client.post(
        "/api/cockpit/preferences/route-aliases",
        json={
            "source_utterance": "my stonks means my portfolio",
            "alias_phrase": "my stonks",
            "canonical_intent": "holdings",
            "scope": "user",
            "provenance_message_id": "msg-1",
        },
    )
    assert proposed_response.status_code == 200
    proposed = proposed_response.json()
    assert proposed["confirmation_status"] == "proposed"
    assert proposed["enabled"] is False

    active_before = client.get(
        "/api/cockpit/preferences/route-aliases",
        params={"active_only": True},
    )
    assert active_before.status_code == 200
    assert active_before.json()["items"] == []

    confirmed_response = client.post(
        f"/api/cockpit/preferences/route-aliases/{proposed['preference_id']}/confirm"
    )
    assert confirmed_response.status_code == 200
    confirmed = confirmed_response.json()
    assert confirmed["confirmation_status"] == "confirmed"
    assert confirmed["enabled"] is True

    active_after = client.get(
        "/api/cockpit/preferences/route-aliases",
        params={"active_only": True},
    )
    assert active_after.status_code == 200
    assert active_after.json()["items"][0]["preference_id"] == proposed["preference_id"]
    assert fake_service.state_store.get_preferences() == {}


def test_route_alias_api_reject_disable_and_delete_deactivate(
    tmp_path,
    monkeypatch,
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    def propose(alias: str) -> dict:
        response = client.post(
            "/api/cockpit/preferences/route-aliases",
            json={
                "source_utterance": f"{alias} means my portfolio",
                "alias_phrase": alias,
                "canonical_intent": "holdings",
            },
        )
        assert response.status_code == 200
        return response.json()

    rejected = propose("holdies")
    disabled = propose("bags")
    deleted = propose("folio")

    assert client.post(
        f"/api/cockpit/preferences/route-aliases/{rejected['preference_id']}/reject"
    ).json()["enabled"] is False
    assert client.post(
        f"/api/cockpit/preferences/route-aliases/{disabled['preference_id']}/confirm"
    ).json()["enabled"] is True
    assert client.post(
        f"/api/cockpit/preferences/route-aliases/{disabled['preference_id']}/disable"
    ).json()["enabled"] is False
    delete_response = client.delete(
        f"/api/cockpit/preferences/route-aliases/{deleted['preference_id']}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "ok": True,
        "preference_id": deleted["preference_id"],
    }

    active_after = client.get(
        "/api/cockpit/preferences/route-aliases",
        params={"active_only": True},
    )
    assert active_after.status_code == 200
    assert active_after.json()["items"] == []
