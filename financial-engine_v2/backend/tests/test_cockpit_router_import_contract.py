from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest


REQUIRED_COCKPIT_ROUTES = {
    "/api/cockpit/chat",
    "/api/cockpit/chat/readiness",
}


def _route_paths() -> set[str]:
    from app.main import app

    return {
        str(route.path)
        for route in app.router.routes
        if hasattr(route, "path") and isinstance(getattr(route, "path"), str)
    }


def test_main_registers_required_cockpit_chat_routes() -> None:
    assert REQUIRED_COCKPIT_ROUTES.issubset(_route_paths())


def test_cockpit_api_router_import_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import: Callable[..., ModuleType] = builtins.__import__
    original_main = sys.modules.pop("app.main", None)

    def fail_cockpit_api_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "app.routes.cockpit_api":
            raise ImportError("simulated transitive cockpit_api dependency failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_cockpit_api_import)

    try:
        with pytest.raises(RuntimeError, match="Required Cockpit API router"):
            importlib.import_module("app.main")
    finally:
        sys.modules.pop("app.main", None)
        if original_main is not None:
            sys.modules["app.main"] = original_main
