"""Route-auth tests for /research endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api import routes
from app.core import config
from app.routes import research


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(research.router, prefix="/research")
    with TestClient(app) as test_client:
        yield test_client


def _route(path: str, method: str) -> APIRoute:
    for candidate in research.router.routes:
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
        "focus": "latest operational update",
        "gathered_sources": {"news": [{"title": "BHP update"}]},
    }


def test_research_synthesis_route_registers_api_key_dependency():
    assert _has_api_key_dependency(_route("/synthesize", "POST"))


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
def test_research_synthesis_rejects_missing_or_wrong_key_before_synthesis(
    client,
    monkeypatch,
    headers,
):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    called = False

    def fake_synthesize_research(**_: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"summary": "should not run"}

    monkeypatch.setattr(research, "synthesize_research", fake_synthesize_research)

    resp = client.post("/research/synthesize", json=_payload(), headers=headers)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid or missing API key"}
    assert called is False


def test_research_synthesis_accepts_matching_key(client, monkeypatch):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    call: dict[str, Any] = {}

    def fake_synthesize_research(**kwargs: Any) -> dict[str, Any]:
        call.update(kwargs)
        return {
            "summary": "BHP synthesis",
            "key_metrics": {"score": 1},
            "recent_developments": ["development"],
            "sentiment": "positive",
            "confidence": 0.7,
            "risks": [],
            "catalysts": [],
            "data_gaps": [],
        }

    monkeypatch.setattr(research, "synthesize_research", fake_synthesize_research)

    resp = client.post(
        "/research/synthesize",
        json=_payload(),
        headers={"X-API-Key": "local-secret"},
    )

    assert resp.status_code == 200
    assert resp.json()["summary"] == "BHP synthesis"
    assert call == {
        "ticker": "BHP",
        "gathered_sources": {"news": [{"title": "BHP update"}]},
        "focus": "latest operational update",
    }
