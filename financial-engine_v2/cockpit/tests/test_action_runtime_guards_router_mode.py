from __future__ import annotations

import json

import urllib.request

from cockpit.core import action_runtime_guards as guards
from cockpit.integrations import llamacpp_manager as manager


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _patch_models_response(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: _FakeResponse(payload),
    )


def test_check_extraction_endpoint_returns_ready_when_model_already_loaded(monkeypatch):
    _patch_models_response(
        monkeypatch,
        {
            "data": [
                {"id": "qwen2.5-14b-instruct", "status": {"value": "loaded"}},
            ]
        },
    )

    ok, message = guards.check_extraction_endpoint("metric_extraction", {})

    assert ok is True
    assert "Extraction ready" in message


def test_check_extraction_endpoint_auto_loads_when_router_active(monkeypatch):
    _patch_models_response(
        monkeypatch,
        {
            "data": [
                {"id": "qwen2.5-14b-instruct", "status": {"value": "unloaded"}},
            ]
        },
    )
    monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
    monkeypatch.setattr(
        manager,
        "find_all_llama_server_processes",
        lambda: [
            {
                "pid": 222,
                "binary": "/usr/bin/llama-server",
                "port": "8002",
                "router_mode": True,
            }
        ],
    )
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: True)
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": True)
    load_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        manager,
        "load_model_api",
        lambda host, port, model_name, api_key="", timeout=120.0, on_status=None: load_calls.append(
            (host, port, model_name)
        )
        or True,
    )

    ok, message = guards.check_extraction_endpoint("metric_extraction", {})

    assert ok is True
    assert "Auto-loaded extraction model" in message
    assert load_calls == [("127.0.0.1", "8002", "qwen2.5-14b-instruct")]


def test_check_extraction_endpoint_blocks_auto_load_when_router_unavailable(monkeypatch):
    _patch_models_response(
        monkeypatch,
        {
            "data": [
                {"id": "qwen2.5-14b-instruct", "status": {"value": "unloaded"}},
            ]
        },
    )
    monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
    monkeypatch.setattr(
        manager,
        "find_all_llama_server_processes",
        lambda: [
            {
                "pid": 222,
                "binary": "/usr/bin/llama-server",
                "port": "8002",
                "router_mode": False,
            }
        ],
    )
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: False)

    ok, message = guards.check_extraction_endpoint("metric_extraction", {})

    assert ok is False
    assert "Auto-load unavailable" in message
    assert "binary missing models dir support" in message


def test_check_extraction_endpoint_blocks_auto_load_for_ambiguous_extraction_topology(monkeypatch):
    _patch_models_response(
        monkeypatch,
        {
            "data": [
                {"id": "qwen2.5-14b-instruct", "status": {"value": "unloaded"}},
            ]
        },
    )
    monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
    monkeypatch.setattr(
        manager,
        "find_all_llama_server_processes",
        lambda: [
            {"pid": 111, "binary": "/usr/bin/llama-server", "port": "8002", "router_mode": True},
            {"pid": 222, "binary": "/usr/bin/llama-server", "port": "8002", "router_mode": True},
        ],
    )

    ok, message = guards.check_extraction_endpoint("metric_extraction", {})

    assert ok is False
    assert "Auto-load blocked" in message
    assert "multiple runtime candidates on port 8002" in message


def test_check_extraction_endpoint_surfaces_auto_load_failure(monkeypatch):
    _patch_models_response(
        monkeypatch,
        {
            "data": [
                {"id": "qwen2.5-14b-instruct", "status": {"value": "unloaded"}},
            ]
        },
    )
    monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
    monkeypatch.setattr(
        manager,
        "find_all_llama_server_processes",
        lambda: [
            {
                "pid": 222,
                "binary": "/usr/bin/llama-server",
                "port": "8002",
                "router_mode": True,
            }
        ],
    )
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: True)
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": True)
    monkeypatch.setattr(
        manager,
        "load_model_api",
        lambda host, port, model_name, api_key="", timeout=120.0, on_status=None: False,
    )

    ok, message = guards.check_extraction_endpoint("metric_extraction", {})

    assert ok is False
    assert "Failed to auto-load extraction model" in message
