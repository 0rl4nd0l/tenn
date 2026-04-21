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


def test_holdings_crud_api_round_trip(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/holdings",
        json={
            "ticker": "bhp",
            "quantity": 100,
            "avg_cost": 42.5,
            "account_label": "Broker",
            "note": "starter position",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["ticker"] == "BHP"
    assert created["quantity"] == 100.0
    assert created["avg_cost"] == 42.5
    assert created["account_label"] == "Broker"
    assert created["note"] == "starter position"
    holding_id = created["holding_id"]

    list_response = client.get("/api/cockpit/holdings")
    assert list_response.status_code == 200
    listed = list_response.json()["items"]
    assert len(listed) == 1
    assert listed[0]["holding_id"] == holding_id

    patch_response = client.patch(
        f"/api/cockpit/holdings/{holding_id}",
        json={
            "quantity": 125,
            "avg_cost": 41.2,
            "account_label": "Brokerage A",
            "note": "trimmed then rebuilt",
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["quantity"] == 125.0
    assert updated["avg_cost"] == 41.2
    assert updated["account_label"] == "Brokerage A"
    assert updated["note"] == "trimmed then rebuilt"

    clear_response = client.patch(
        f"/api/cockpit/holdings/{holding_id}",
        json={"note": None, "account_label": None},
    )
    assert clear_response.status_code == 200
    cleared = clear_response.json()
    assert cleared["note"] is None
    assert cleared["account_label"] is None

    delete_response = client.delete(f"/api/cockpit/holdings/{holding_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True, "holding_id": holding_id}

    after_delete = client.get("/api/cockpit/holdings")
    assert after_delete.status_code == 200
    assert after_delete.json()["items"] == []


def test_holdings_update_unknown_id_returns_404(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.patch(
        "/api/cockpit/holdings/does-not-exist",
        json={"note": "x"},
    )
    assert response.status_code == 404

