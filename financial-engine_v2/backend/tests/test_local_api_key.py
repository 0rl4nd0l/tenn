from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.core.config as config
import app.main as main
from app.api import commentary
from app.api import routes


def _route(path: str, method: str) -> APIRoute:
    for candidate in main.app.routes:
        if isinstance(candidate, APIRoute) and candidate.path == path and method in candidate.methods:
            return candidate
    raise AssertionError(f"route not found: {method} {path}")


def _has_api_key_dependency(route: APIRoute) -> bool:
    return any(dependency.call is routes.require_api_key for dependency in route.dependant.dependencies)


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/backfill/asx20", "POST"),
        ("/api/backfill/ticker/{ticker}", "POST"),
        ("/api/system/capabilities", "GET"),
        ("/api/system/proposals/apply", "POST"),
        ("/api/system/status", "GET"),
        ("/api/cockpit/docs", "GET"),
        ("/api/cockpit/pulse", "GET"),
        ("/api/cockpit/matrix", "GET"),
        ("/api/commentary/transcripts/pending", "GET"),
        ("/chat", "POST"),
        ("/api/chat", "POST"),
        ("/api/ingest/transcript", "POST"),
        ("/api/ingest/book", "POST"),
        ("/ingest/transcript", "POST"),
        ("/ingest/book", "POST"),
        ("/rag/query", "POST"),
        ("/api/cockpit/marketplace/missions", "GET"),
        ("/api/cockpit/marketplace/missions", "POST"),
        ("/api/cockpit/marketplace/missions/{mission_id}", "GET"),
        ("/api/cockpit/marketplace/missions/{mission_id}", "PATCH"),
        ("/api/cockpit/marketplace/missions/{mission_id}", "DELETE"),
        ("/api/cockpit/marketplace/missions/{mission_id}/link-product", "POST"),
        ("/api/cockpit/marketplace/missions/{mission_id}/link-product", "DELETE"),
        ("/api/cockpit/marketplace/matches", "GET"),
        ("/api/cockpit/marketplace/matches/{match_id}", "GET"),
        ("/api/cockpit/marketplace/matches/{match_id}", "PATCH"),
        ("/api/cockpit/marketplace/matches/{match_id}/feedback", "PATCH"),
        ("/api/cockpit/marketplace/matches/{match_id}/benchmark-review", "PATCH"),
        ("/api/cockpit/marketplace/alerts", "GET"),
        ("/api/cockpit/marketplace/alerts/{alert_id}", "PATCH"),
    ],
)
def test_protected_routes_register_api_key_dependency(path, method):
    assert _has_api_key_dependency(_route(path, method))


def test_health_route_stays_unprotected():
    assert not _has_api_key_dependency(_route("/api/health", "GET"))


def test_require_api_key_allows_local_dev_when_unconfigured(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "", raising=False)

    assert routes.require_api_key(None) is None
    assert routes.require_api_key("anything") is None


def test_require_api_key_rejects_missing_or_wrong_key_when_configured(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    with pytest.raises(HTTPException) as missing_exc:
        routes.require_api_key(None)
    assert missing_exc.value.status_code == 401
    assert missing_exc.value.detail == "Invalid or missing API key"

    with pytest.raises(HTTPException) as wrong_exc:
        routes.require_api_key("wrong-secret")
    assert wrong_exc.value.status_code == 401
    assert wrong_exc.value.detail == "Invalid or missing API key"


def test_require_api_key_accepts_matching_key(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)

    assert routes.require_api_key("local-secret") is None


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
def test_pending_transcripts_rejects_missing_or_wrong_api_key_before_loading_index(
    monkeypatch, headers
):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    load_index = Mock(side_effect=AssertionError("pending index should not load"))
    monkeypatch.setattr(commentary, "_load_index", load_index)

    response = TestClient(main.app).get(
        "/api/commentary/transcripts/pending",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    load_index.assert_not_called()


def test_pending_transcripts_accepts_matching_api_key(monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    monkeypatch.setattr(
        commentary,
        "_load_index",
        lambda: {
            "src-001": {
                "staged_at": "2026-06-01T00:00:00Z",
                "path": "/tmp/src-001.jsonl",
            }
        },
    )

    response = TestClient(main.app).get(
        "/api/commentary/transcripts/pending",
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["pending"][0]["source_id"] == "src-001"
