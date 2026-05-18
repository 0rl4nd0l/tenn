"""Route parity contract tests for NVMe2 validated profile."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _route_paths() -> list[str]:
    return sorted(
        path
        for route in app.router.routes
        if hasattr(route, "path") and isinstance(getattr(route, "path"), str)
        for path in [str(route.path)]
    )


def test_backend_reported_route_inventory_matches_expected_profile() -> None:
    paths = _route_paths()

    assert "/api/cockpit/home" not in paths
    assert "/api/news/status" not in paths

    assert "/api/cockpit/home/market-session" in paths
    assert "/api/cockpit/home/portfolio" in paths
    assert "/api/cockpit/home/attention-queue" in paths
    assert "/api/cockpit/home/market-movers" in paths
    assert "/api/cockpit/home/narrative" in paths


def test_backend_direct_aggregate_routes_are_not_required_for_home_or_news_status() -> None:
    client = TestClient(app)

    assert client.get("/api/cockpit/home").status_code == 404
    assert client.get("/api/news/status").status_code == 404
