"""Route-auth tests for TradingView alert endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api import routes
from app.core import config
from app.routes import cockpit_api


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(cockpit_api.settings, "data_root", str(tmp_path), raising=False)
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "", raising=False)
    monkeypatch.setattr(cockpit_api.settings, "tv_webhook_token", "", raising=False)
    monkeypatch.delenv("TV_WEBHOOK_TOKEN", raising=False)

    app = FastAPI()
    app.include_router(cockpit_api.router, prefix="/api/cockpit")
    with TestClient(app) as test_client:
        yield test_client


def _route(path: str, method: str) -> APIRoute:
    for candidate in cockpit_api.router.routes:
        if (
            isinstance(candidate, APIRoute)
            and candidate.path == path
            and method in candidate.methods
        ):
            return candidate
    raise AssertionError(f"route not found: {method} {path}")


def _has_api_key_dependency(route: APIRoute) -> bool:
    return any(
        dependency.call is routes.require_api_key
        for dependency in route.dependant.dependencies
    )


def _payload() -> dict[str, Any]:
    return {
        "ticker": "BHP",
        "action": "buy",
        "price": 42.0,
        "message": "breakout",
    }


def _payload_with_token(token: str) -> dict[str, Any]:
    return {
        **_payload(),
        "webhook_token": token,
    }


def _alerts_path(tmp_path: Path) -> Path:
    return tmp_path / "tv_alerts.json"


def test_receive_tv_alert_fails_closed_when_webhook_token_unset(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post("/api/cockpit/tv/alert", json=_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "TradingView webhook token is not configured"}
    assert not _alerts_path(tmp_path).exists()


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-TradingView-Webhook-Token": "wrong-secret"}],
)
def test_receive_tv_alert_rejects_missing_or_wrong_token_before_persistence(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    monkeypatch.setenv("TV_WEBHOOK_TOKEN", "tv-secret")

    response = client.post("/api/cockpit/tv/alert", json=_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid webhook token"}
    assert not _alerts_path(tmp_path).exists()


def test_receive_tv_alert_accepts_matching_webhook_token(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TV_WEBHOOK_TOKEN", "tv-secret")

    response = client.post(
        "/api/cockpit/tv/alert",
        json=_payload(),
        headers={"X-TradingView-Webhook-Token": "tv-secret"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    alerts = json.loads(_alerts_path(tmp_path).read_text())
    assert len(alerts) == 1
    assert alerts[0]["ticker"] == "BHP"
    assert "webhook_token" not in alerts[0]


def test_receive_tv_alert_accepts_body_webhook_token(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TV_WEBHOOK_TOKEN", "tv-secret")

    response = client.post(
        "/api/cockpit/tv/alert",
        json=_payload_with_token("tv-secret"),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    alerts = json.loads(_alerts_path(tmp_path).read_text())
    assert len(alerts) == 1
    assert alerts[0]["ticker"] == "BHP"
    assert "webhook_token" not in alerts[0]


def test_receive_tv_alert_rejects_wrong_body_webhook_token_before_persistence(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TV_WEBHOOK_TOKEN", "tv-secret")

    response = client.post(
        "/api/cockpit/tv/alert",
        json=_payload_with_token("wrong-secret"),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid webhook token"}
    assert not _alerts_path(tmp_path).exists()


def test_receive_tv_alert_accepts_settings_webhook_token(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TV_WEBHOOK_TOKEN", raising=False)
    monkeypatch.setattr(
        cockpit_api.settings,
        "tv_webhook_token",
        "settings-secret",
        raising=False,
    )

    response = client.post(
        "/api/cockpit/tv/alert",
        json=_payload(),
        headers={"X-TradingView-Webhook-Token": "settings-secret"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    alerts = json.loads(_alerts_path(tmp_path).read_text())
    assert len(alerts) == 1
    assert alerts[0]["ticker"] == "BHP"
    assert "webhook_token" not in alerts[0]


def test_settings_loads_tv_webhook_token_from_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TV_WEBHOOK_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("TV_WEBHOOK_TOKEN=env-file-secret\n")

    loaded = config.Settings(_env_file=str(env_file))

    assert loaded.tv_webhook_token == "env-file-secret"


def test_get_tv_alerts_registers_api_key_dependency() -> None:
    assert _has_api_key_dependency(_route("/tv/alerts", "GET"))


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
def test_get_tv_alerts_rejects_missing_or_wrong_key_when_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)

    response = client.get("/api/cockpit/tv/alerts", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_get_tv_alerts_accepts_matching_api_key(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)
    _alerts_path(tmp_path).write_text(
        json.dumps([{"received_at": "2026-06-26T00:00:00Z", "ticker": "BHP"}])
    )

    response = client.get(
        "/api/cockpit/tv/alerts",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["alerts"][0]["ticker"] == "BHP"
