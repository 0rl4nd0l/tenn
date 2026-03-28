from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock

from cockpit.integrations import llamacpp_manager as manager


def test_is_router_mode_detects_status_objects(monkeypatch):
    monkeypatch.setattr(
        manager,
        "_api_request",
        lambda url, api_key="": {
            "data": [
                {
                    "id": "qwen2.5-coder-14b",
                    "status": {"value": "loaded"},
                }
            ]
        },
    )

    assert manager.is_router_mode("127.0.0.1", "8001") is True


def test_is_router_mode_returns_false_for_single_model_shape(monkeypatch):
    monkeypatch.setattr(
        manager,
        "_api_request",
        lambda url, api_key="": {
            "data": [
                {
                    "id": "qwen2.5-coder-14b",
                }
            ]
        },
    )

    assert manager.is_router_mode("127.0.0.1", "8001") is False


def test_list_models_api_normalizes_failed_loading_state(monkeypatch):
    monkeypatch.setattr(
        manager,
        "_api_request",
        lambda url, api_key="": {
            "data": [
                {
                    "id": "deepseek-r1",
                    "status": {"value": "loading", "failed": True},
                },
                {
                    "id": "qwen2.5-coder-14b",
                    "status": {"value": "loaded", "failed": False},
                },
            ]
        },
    )

    models = manager.list_models_api("127.0.0.1", "8001")

    assert models == [
        {"name": "deepseek-r1", "state": "failed"},
        {"name": "qwen2.5-coder-14b", "state": "loaded"},
    ]


def test_load_model_api_returns_true_when_target_becomes_loaded(monkeypatch):
    states = iter(
        [
            [{"name": "qwen2.5-coder-14b", "state": "loading"}],
            [{"name": "qwen2.5-coder-14b", "state": "loaded"}],
        ]
    )
    monkeypatch.setattr(manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock())
    monkeypatch.setattr(manager, "list_models_api", lambda host, port, api_key="": next(states))
    monkeypatch.setattr(manager.time, "sleep", lambda _: None)

    messages: list[str] = []
    ok = manager.load_model_api(
        "127.0.0.1",
        "8001",
        "qwen2.5-coder-14b",
        on_status=messages.append,
        timeout=5.0,
    )

    assert ok is True
    assert any("loaded successfully" in message for message in messages)


def test_load_model_api_returns_false_on_terminal_failure(monkeypatch):
    monkeypatch.setattr(manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock())
    monkeypatch.setattr(
        manager,
        "list_models_api",
        lambda host, port, api_key="": [{"name": "qwen2.5-coder-14b", "state": "failed"}],
    )
    monkeypatch.setattr(manager.time, "sleep", lambda _: None)

    messages: list[str] = []
    ok = manager.load_model_api(
        "127.0.0.1",
        "8001",
        "qwen2.5-coder-14b",
        on_status=messages.append,
        timeout=5.0,
    )

    assert ok is False
    assert any("failed to load" in message for message in messages)


def test_load_model_api_detects_stalled_loading_child(monkeypatch):
    monkeypatch.setattr(manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock())
    monkeypatch.setattr(
        manager,
        "list_models_api",
        lambda host, port, api_key="": [{"name": "qwen2.5-coder-14b", "state": "loading"}],
    )
    monkeypatch.setattr(manager.time, "sleep", lambda _: None)
    now = {"value": 100.0}

    def _monotonic():
        now["value"] += 61.0
        return now["value"]

    monkeypatch.setattr(manager.time, "monotonic", _monotonic)
    monkeypatch.setattr(manager, "_is_loading_stalled", lambda host, port, model_name, api_key="": True)

    messages: list[str] = []
    ok = manager.load_model_api(
        "127.0.0.1",
        "8001",
        "qwen2.5-coder-14b",
        on_status=messages.append,
        timeout=180.0,
    )

    assert ok is False
    assert any("child process appears dead" in message for message in messages)


def test_switch_model_uses_router_path_when_router_detected(monkeypatch):
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": True)
    warm_calls: list[str] = []
    load_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(manager, "_warm_page_cache", lambda model_path, on_status=None: warm_calls.append(model_path))
    monkeypatch.setattr(
        manager,
        "load_model_api",
        lambda host, port, model_name, api_key="", timeout=600.0, on_status=None: load_calls.append(
            (host, port, model_name)
        )
        or True,
    )

    ok = manager.switch_model(
        {"router_mode": False},
        "qwen2.5-coder-14b",
        "/models/qwen2.5-coder-14b.gguf",
        host="127.0.0.1",
        port="8001",
    )

    assert ok is True
    assert warm_calls == ["/models/qwen2.5-coder-14b.gguf"]
    assert load_calls == [("127.0.0.1", "8001", "qwen2.5-coder-14b")]


def test_switch_model_uses_restart_path_when_router_not_detected(monkeypatch):
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": False)
    restart_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        manager,
        "restart_with_model",
        lambda proc_info, new_model_path, new_model_alias, startup_timeout=600.0, on_status=None, mmap_disabled=None: restart_calls.append(
            (new_model_path, new_model_alias)
        )
        or True,
    )

    ok = manager.switch_model(
        {"router_mode": False},
        "qwen2.5-coder-14b",
        "/models/qwen2.5-coder-14b.gguf",
        host="127.0.0.1",
        port="8001",
    )

    assert ok is True
    assert restart_calls == [("/models/qwen2.5-coder-14b.gguf", "qwen2.5-coder-14b")]


def test_probe_router_capability_reports_supported_but_not_active(monkeypatch):
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: True)
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": False)

    state = manager.probe_router_capability(
        {
            "pid": 123,
            "binary": "/usr/bin/llama-server",
            "port": "8001",
            "router_mode": False,
        },
        candidate_processes=[{"pid": 123}],
    )

    assert state.active_mode == "router_mode_available_not_active"
    assert state.router_supported is True
    assert state.router_api_reachable is False
    assert state.reason == "router_supported_but_single_model_running"


def test_probe_router_capability_reports_router_degraded(monkeypatch):
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: True)
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": False)

    state = manager.probe_router_capability(
        {
            "pid": 123,
            "binary": "/usr/bin/llama-server",
            "port": "8001",
            "router_mode": True,
        },
        candidate_processes=[{"pid": 123}],
    )

    assert state.active_mode == "router_mode_degraded"
    assert state.reason == "router_process_detected_but_api_shape_missing"


def test_probe_router_capability_reports_unavailable_without_process(monkeypatch):
    monkeypatch.setenv("LLAMA_SERVER_ROUTER_MODE", "1")

    state = manager.probe_router_capability(None, candidate_processes=[])

    assert state.active_mode == "router_mode_unavailable"
    assert state.router_configured is True
    assert state.reason == "llama_server_not_running"


def test_load_model_api_surfaces_http_error_body(monkeypatch):
    class _HttpError(urllib.error.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="http://127.0.0.1:8001/models/load",
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=None,
            )

        def read(self) -> bytes:
            return b'{"error":"backend unavailable"}'

    def _raise_http_error(req, timeout=30):
        raise _HttpError()

    monkeypatch.setattr(manager.urllib.request, "urlopen", _raise_http_error)

    messages: list[str] = []
    ok = manager.load_model_api(
        "127.0.0.1",
        "8001",
        "qwen2.5-coder-14b",
        on_status=messages.append,
        timeout=5.0,
    )

    assert ok is False
    assert any("HTTP 503" in message for message in messages)
