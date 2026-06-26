from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes as api_routes


MARKET_DATA_ROUTES = [
    (
        "/api/price?ticker=BHP&range=1mo&interval=1d",
        "fetch_price",
        "persist_price",
    ),
    (
        "/api/fundamentals/profile?ticker=BHP",
        "fetch_fundamentals_profile",
        "persist_fundamental",
    ),
    (
        "/api/fundamentals/summary?ticker=BHP",
        "fetch_fundamentals_summary",
        "persist_fundamental",
    ),
    (
        "/api/fundamentals/statements?ticker=BHP&statement_type=income&period=annual&limit=2",
        "fetch_fundamentals_statements",
        "persist_fundamental",
    ),
]


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(api_routes.router, prefix="/api")
    return TestClient(app)


class FakeOpenBBSidecarProvider:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def fetch_price(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("fetch_price")
        return {"kind": "price", "ticker": kwargs["ticker"]}

    def fetch_fundamentals_profile(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("fetch_fundamentals_profile")
        return {"kind": "profile", "ticker": kwargs["ticker"]}

    def fetch_fundamentals_summary(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("fetch_fundamentals_summary")
        return {"kind": "summary", "ticker": kwargs["ticker"]}

    def fetch_fundamentals_statements(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("fetch_fundamentals_statements")
        return {"kind": "statements", "ticker": kwargs["ticker"]}


def _configure_openbb_staging(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool,
) -> None:
    monkeypatch.setattr(api_routes.settings, "local_api_key", "local-secret", raising=False)
    monkeypatch.setattr(
        api_routes.settings, "market_data_mode", "openbb_sidecar", raising=False
    )
    monkeypatch.setattr(
        api_routes.settings,
        "openbb_sidecar_enable_staging_writes",
        enabled,
        raising=False,
    )


def _install_sidecar_and_persistence_spies(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
) -> None:
    monkeypatch.setattr(
        api_routes,
        "_openbb_sidecar_provider",
        lambda: FakeOpenBBSidecarProvider(calls),
    )
    monkeypatch.setattr(
        api_routes,
        "_persist_openbb_price_snapshot",
        lambda **_: calls.append("persist_price"),
    )
    monkeypatch.setattr(
        api_routes,
        "_persist_openbb_fundamental_snapshot",
        lambda **_: calls.append("persist_fundamental"),
    )


@pytest.mark.parametrize(
    ("path", "provider_call", "persist_call"),
    MARKET_DATA_ROUTES,
)
def test_market_data_get_routes_remain_public_when_staging_writes_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    provider_call: str,
    persist_call: str,
) -> None:
    _configure_openbb_staging(monkeypatch, enabled=False)
    calls: list[str] = []
    monkeypatch.setattr(
        api_routes,
        "_openbb_sidecar_provider",
        lambda: FakeOpenBBSidecarProvider(calls),
    )

    response = client.get(path)

    assert response.status_code == 200
    assert response.json()["ticker"] == "BHP"
    assert calls == [provider_call]
    assert persist_call not in calls


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
@pytest.mark.parametrize(
    ("path", "provider_call", "persist_call"),
    MARKET_DATA_ROUTES,
)
def test_openbb_staging_get_routes_reject_missing_or_wrong_key_before_refresh_or_persist(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    provider_call: str,
    persist_call: str,
    headers: dict[str, str],
) -> None:
    _configure_openbb_staging(monkeypatch, enabled=True)
    calls: list[str] = []
    _install_sidecar_and_persistence_spies(monkeypatch, calls)

    response = client.get(path, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}
    assert provider_call not in calls
    assert persist_call not in calls
    assert calls == []


@pytest.mark.parametrize(
    ("path", "provider_call", "persist_call"),
    MARKET_DATA_ROUTES,
)
def test_openbb_staging_get_routes_accept_matching_key_and_preserve_staging_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    provider_call: str,
    persist_call: str,
) -> None:
    _configure_openbb_staging(monkeypatch, enabled=True)
    calls: list[str] = []
    _install_sidecar_and_persistence_spies(monkeypatch, calls)

    response = client.get(path, headers={"X-API-Key": "local-secret"})

    assert response.status_code == 200
    assert response.json()["ticker"] == "BHP"
    assert calls == [provider_call, persist_call]
