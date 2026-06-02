from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

import app.core.config as config
import app.main as main
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
        ("/api/ingest/transcript", "POST"),
        ("/api/ingest/book", "POST"),
        ("/api/cockpit/claims/verify", "POST"),
        ("/ingest/transcript", "POST"),
        ("/ingest/book", "POST"),
        ("/rag/query", "POST"),
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
