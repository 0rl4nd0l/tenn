from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from cockpit.storage.state import StateStore


class _WatchlistOnlyService(SimpleNamespace):
    def __getattr__(self, name: str):
        if name in {
            "company_memory",
            "market_memory",
            "user_thesis_memory",
            "financial_truth_provider",
        }:
            raise AssertionError(f"watchlist API must not touch {name}")
        raise AttributeError(name)


def _fake_service(tmp_path: Path) -> _WatchlistOnlyService:
    state_store = StateStore(str(tmp_path / "state.db"))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return _WatchlistOnlyService(
        state_store=state_store,
        artifact_store=SimpleNamespace(logs_dir=logs_dir),
    )


def _client(tmp_path: Path, monkeypatch) -> tuple[TestClient, _WatchlistOnlyService]:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService,
        "get_instance",
        classmethod(lambda cls: fake_service),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    return TestClient(app), fake_service


def test_watchlist_list_empty(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)

    response = client.get("/api/cockpit/watchlist")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "items": []}


def test_watchlist_add_valid_ticker(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/cockpit/watchlist",
        json={"ticker": "bhp", "name": "BHP Group", "note": "optional"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["item"]["ticker"] == "BHP"
    assert body["item"]["source"] == "cockpit_state"
    assert body["item"]["name"] is None
    assert body["item"]["notes"] is None
    assert body["item"]["added_at"]

    listed = client.get("/api/cockpit/watchlist").json()
    assert [item["ticker"] for item in listed["items"]] == ["BHP"]


def test_watchlist_add_duplicate_returns_409(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)

    first = client.post("/api/cockpit/watchlist", json={"ticker": "BHP"})
    duplicate = client.post("/api/cockpit/watchlist", json={"ticker": "bhp"})

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert "already on watchlist" in duplicate.json()["detail"]


def test_watchlist_remove_existing_ticker(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)
    client.post("/api/cockpit/watchlist", json={"ticker": "BHP.AX"})

    response = client.delete("/api/cockpit/watchlist/bhp.ax")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "removed": True, "ticker": "BHP.AX"}
    assert client.get("/api/cockpit/watchlist").json()["items"] == []


def test_watchlist_remove_missing_ticker_returns_404(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)

    response = client.delete("/api/cockpit/watchlist/BHP")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_watchlist_rejects_invalid_ticker(tmp_path, monkeypatch) -> None:
    client, _service = _client(tmp_path, monkeypatch)

    post_response = client.post("/api/cockpit/watchlist", json={"ticker": "!!!"})
    delete_response = client.delete("/api/cockpit/watchlist/!!!")

    assert post_response.status_code == 400
    assert delete_response.status_code == 400


def test_watchlist_does_not_write_preferences_or_other_state(
    tmp_path,
    monkeypatch,
) -> None:
    client, service = _client(tmp_path, monkeypatch)

    response = client.post("/api/cockpit/watchlist", json={"ticker": "BHP"})

    assert response.status_code == 200
    assert service.state_store.get_preferences() == {}
    assert service.state_store.list_holdings() == []
