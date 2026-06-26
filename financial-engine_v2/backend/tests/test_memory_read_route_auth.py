from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api import context as context_api


READ_ROUTE_PATHS = (
    "/memory",
    "/memory/index",
    "/thesis",
    "/company_dump",
)


def _route(path: str) -> APIRoute:
    for route in context_api.router.routes:
        if isinstance(route, APIRoute) and route.path == path:
            return route
    raise AssertionError(f"route not found: {path}")


def _has_api_key_dependency(path: str) -> bool:
    return any(
        getattr(dependency, "dependency", None) is context_api.require_api_key
        or getattr(dependency, "call", None) is context_api.require_api_key
        for dependency in _route(path).dependencies
    )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(context_api.router, prefix="/api/context")
    return TestClient(app, raise_server_exceptions=False)


def _minimal_company_memory() -> dict[str, Any]:
    return {
        "entries": [],
        "entries_total": 0,
        "change_log": [],
        "change_log_total": 0,
    }


def _minimal_market_memory() -> dict[str, Any]:
    return {
        "items": [],
        "items_total": 0,
        "sector": None,
    }


def _minimal_user_thesis_memory() -> dict[str, Any]:
    return {
        "entries": [],
        "entries_total": 0,
        "proposals": [],
        "proposals_total": 0,
    }


def _minimal_ticker_context() -> dict[str, Any]:
    return {
        "ticker": "BHP",
        "docs": [],
        "financials": [],
        "latest_financial_snapshot": None,
        "announcement_context": [],
        "extraction_failures": [],
        "low_confidence_financials": [],
        "errors": [],
    }


def _patch_memory_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context_api,
        "_load_company_memory",
        lambda *args, **kwargs: (_minimal_company_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "_load_company_memory_index",
        lambda *args, **kwargs: (_minimal_company_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "_load_market_memory",
        lambda *args, **kwargs: (_minimal_market_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "_load_market_memory_index",
        lambda *args, **kwargs: (_minimal_market_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "_load_user_thesis_memory",
        lambda *args, **kwargs: (_minimal_user_thesis_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "_load_user_thesis_memory_index",
        lambda *args, **kwargs: (_minimal_user_thesis_memory(), None),
    )
    monkeypatch.setattr(
        context_api,
        "get_ticker_context",
        lambda *args, **kwargs: _minimal_ticker_context(),
    )
    monkeypatch.setattr(context_api, "_run_query", lambda *args, **kwargs: ([], None))
    monkeypatch.setattr(
        context_api,
        "_load_price_context_1y",
        lambda *args, **kwargs: ({}, [], {"points": 0}, None),
    )


def _patch_memory_fail_if_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise AssertionError("memory read route work must not run before API-key auth")

    for name in (
        "_load_company_memory",
        "_load_company_memory_index",
        "_load_market_memory",
        "_load_market_memory_index",
        "_load_user_thesis_memory",
        "_load_user_thesis_memory_index",
        "get_ticker_context",
        "_run_query",
        "_load_price_context_1y",
    ):
        monkeypatch.setattr(context_api, name, fail)


def _route_url(path: str) -> str:
    params = {
        "/memory": "ticker=BHP",
        "/memory/index": "",
        "/thesis": "ticker=BHP",
        "/company_dump": "ticker=BHP",
    }[path]
    suffix = f"?{params}" if params else ""
    return f"/api/context{path}{suffix}"


def test_memory_read_routes_register_api_key_dependency() -> None:
    for path in READ_ROUTE_PATHS:
        assert _has_api_key_dependency(path), f"{path} must depend on require_api_key"


@pytest.mark.parametrize("path", READ_ROUTE_PATHS)
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-API-Key": "wrong-key"},
    ],
)
def test_memory_read_routes_reject_missing_or_wrong_key_before_work(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    headers: dict[str, str],
) -> None:
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)
    _patch_memory_fail_if_called(monkeypatch)

    response = _client().get(_route_url(path), headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


@pytest.mark.parametrize("path", READ_ROUTE_PATHS)
def test_memory_read_routes_accept_matching_key(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(context_api.settings, "local_api_key", "local-secret", raising=False)
    _patch_memory_success(monkeypatch)

    response = _client().get(
        _route_url(path),
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize("path", READ_ROUTE_PATHS)
def test_memory_read_routes_preserve_no_key_local_dev(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(context_api.settings, "local_api_key", "", raising=False)
    _patch_memory_success(monkeypatch)

    response = _client().get(_route_url(path))

    assert response.status_code == 200
