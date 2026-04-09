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
    monkeypatch.setattr(
        manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock()
    )
    monkeypatch.setattr(
        manager, "list_models_api", lambda host, port, api_key="": next(states)
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

    assert ok is True
    assert any("loaded successfully" in message for message in messages)


def test_load_model_api_returns_false_on_terminal_failure(monkeypatch):
    monkeypatch.setattr(
        manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock()
    )
    monkeypatch.setattr(
        manager,
        "list_models_api",
        lambda host, port, api_key="": [
            {"name": "qwen2.5-coder-14b", "state": "failed"}
        ],
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
    monkeypatch.setattr(
        manager.urllib.request, "urlopen", lambda req, timeout=30: MagicMock()
    )
    monkeypatch.setattr(
        manager,
        "list_models_api",
        lambda host, port, api_key="": [
            {"name": "qwen2.5-coder-14b", "state": "loading"}
        ],
    )
    monkeypatch.setattr(manager.time, "sleep", lambda _: None)

    # Simulate time advancing 2s per call — enough for stall detection (>60s)
    # but well within the 600s timeout.
    call_count = {"n": 0}

    def _monotonic():
        call_count["n"] += 1
        return 100.0 + call_count["n"] * 2.0

    monkeypatch.setattr(manager.time, "monotonic", _monotonic)
    monkeypatch.setattr(
        manager, "_is_loading_stalled", lambda host, port, model_name, api_key="": True
    )

    messages: list[str] = []
    ok = manager.load_model_api(
        "127.0.0.1",
        "8001",
        "qwen2.5-coder-14b",
        on_status=messages.append,
        timeout=600.0,
    )

    assert ok is False
    assert any("child process appears dead" in message for message in messages)


def test_switch_model_uses_router_path_when_router_detected(monkeypatch):
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": True)
    warm_calls: list[str] = []
    load_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        manager,
        "_warm_page_cache",
        lambda model_path, on_status=None: warm_calls.append(model_path),
    )
    monkeypatch.setattr(
        manager,
        "load_model_api",
        lambda host, port, model_name, api_key="", timeout=600.0, on_status=None: (
            load_calls.append((host, port, model_name)) or True
        ),
    )

    result = manager.switch_model(
        {"router_mode": False},
        "qwen2.5-coder-14b",
        "/models/qwen2.5-coder-14b.gguf",
        host="127.0.0.1",
        port="8001",
    )

    assert result.ok is True
    assert result.path == "router_hot_switch"
    assert result.target_model == "qwen2.5-coder-14b"
    assert warm_calls == ["/models/qwen2.5-coder-14b.gguf"]
    assert load_calls == [("127.0.0.1", "8001", "qwen2.5-coder-14b")]


def test_switch_model_uses_restart_path_when_router_not_detected(monkeypatch):
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": False)
    restart_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        manager,
        "restart_with_model",
        lambda proc_info, new_model_path, new_model_alias, startup_timeout=600.0, on_status=None, mmap_disabled=None: (
            restart_calls.append((new_model_path, new_model_alias)) or True
        ),
    )

    result = manager.switch_model(
        {"router_mode": False},
        "qwen2.5-coder-14b",
        "/models/qwen2.5-coder-14b.gguf",
        host="127.0.0.1",
        port="8001",
    )

    assert result.ok is True
    assert result.path == "restart"
    assert result.target_model == "qwen2.5-coder-14b"
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


def test_probe_router_capability_trusts_live_router_even_if_binary_probe_fails(
    monkeypatch,
):
    monkeypatch.setattr(manager, "_binary_supports_models_dir", lambda binary: False)
    monkeypatch.setattr(manager, "is_router_mode", lambda host, port, api_key="": True)

    state = manager.probe_router_capability(
        {
            "pid": 123,
            "binary": "/usr/bin/llama-server",
            "port": "8001",
            "router_mode": True,
        },
        candidate_processes=[{"pid": 123, "port": "8001", "router_mode": True}],
    )

    assert state.active_mode == "router_mode_active"
    assert state.router_supported is True
    assert state.router_api_reachable is True
    assert state.reason == ""


def test_probe_router_capability_reports_unavailable_without_process(monkeypatch):
    monkeypatch.setenv("LLAMA_SERVER_ROUTER_MODE", "1")

    state = manager.probe_router_capability(None, candidate_processes=[])

    assert state.active_mode == "router_mode_unavailable"
    assert state.router_configured is True
    assert state.reason == "no_llama_server_processes"


def test_resolve_llama_server_topology_prefers_chat_port_when_extraction_also_present():
    topology = manager.resolve_llama_server_topology(
        [
            {"pid": 101, "port": "8002", "router_mode": False},
            {"pid": 202, "port": "8001", "router_mode": True},
        ]
    )

    assert topology.ambiguous is False
    assert topology.selected_process == {
        "pid": 202,
        "port": "8001",
        "router_mode": True,
    }
    assert topology.reason == "chat_runtime_selected_with_extraction_runtime_present"


def test_resolve_llama_server_topology_blocks_multiple_chat_candidates():
    topology = manager.resolve_llama_server_topology(
        [
            {"pid": 101, "port": "8001", "router_mode": False},
            {"pid": 202, "port": "8001", "router_mode": True},
        ]
    )

    assert topology.ambiguous is True
    assert topology.selected_process is None
    assert topology.reason == "multiple_chat_runtime_candidates"


def test_resolve_llama_server_topology_blocks_extraction_only_runtime():
    topology = manager.resolve_llama_server_topology(
        [
            {"pid": 101, "port": "8002", "router_mode": False},
        ]
    )

    assert topology.ambiguous is True
    assert topology.selected_process is None
    assert topology.reason == "only_extraction_runtime_detected"


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


def test_check_gpu_process_topology_treats_router_child_worker_as_authorised(
    monkeypatch,
):
    router_proc = {
        "pid": 100,
        "binary": "/usr/bin/llama-server",
        "port": "8001",
        "router_mode": True,
    }
    child_proc = {
        "pid": 200,
        "binary": "/usr/bin/llama-server",
        "port": "48039",
        "router_mode": False,
    }
    monkeypatch.setattr(
        manager, "find_all_llama_server_processes", lambda: [router_proc, child_proc]
    )
    monkeypatch.setattr(
        manager, "_is_router_owned_child_process", lambda pid: pid == 200
    )

    topology = manager.check_gpu_process_topology()

    assert topology["clean"] is True
    assert topology["rogue"] == []
    assert topology["authorised"] == [router_proc, child_proc]


def test_check_gpu_process_topology_keeps_unrelated_ephemeral_server_as_rogue(
    monkeypatch,
):
    router_proc = {
        "pid": 100,
        "binary": "/usr/bin/llama-server",
        "port": "8001",
        "router_mode": True,
    }
    rogue_proc = {
        "pid": 300,
        "binary": "/usr/bin/llama-server",
        "port": "48039",
        "router_mode": False,
    }
    monkeypatch.setattr(
        manager, "find_all_llama_server_processes", lambda: [router_proc, rogue_proc]
    )
    monkeypatch.setattr(manager, "_is_router_owned_child_process", lambda pid: False)

    topology = manager.check_gpu_process_topology()

    assert topology["clean"] is False
    assert topology["authorised"] == [router_proc]
    assert topology["rogue"] == [rogue_proc]


def test_check_chat_gpu_preemption_allows_selected_chat_runtime_only(monkeypatch):
    router_proc = {
        "pid": 100,
        "binary": "/usr/bin/llama-server",
        "port": "8001",
        "router_mode": True,
    }
    child_proc = {
        "pid": 200,
        "binary": "/usr/bin/llama-server",
        "port": "48039",
        "router_mode": False,
    }
    monkeypatch.setattr(
        manager,
        "resolve_llama_server_port_topology",
        lambda port: manager.LlamaServerTopology(router_proc, [router_proc], False, ""),
    )
    monkeypatch.setattr(
        manager, "find_all_llama_server_processes", lambda: [router_proc, child_proc]
    )
    monkeypatch.setattr(
        manager,
        "_is_descended_from",
        lambda pid, ancestors: pid == 200 and ancestors == {100},
    )
    monkeypatch.setattr(
        manager, "_list_gpu_compute_processes", lambda: [{"pid": 100}, {"pid": 200}]
    )

    state = manager.check_chat_gpu_preemption("8001")

    assert state == {"should_defer": False, "reason": "", "competing_processes": []}


def test_check_chat_gpu_preemption_defers_for_other_llama_runtime(monkeypatch):
    router_proc = {
        "pid": 100,
        "binary": "/usr/bin/llama-server",
        "port": "8001",
        "router_mode": True,
    }
    extraction_proc = {
        "pid": 300,
        "binary": "/usr/bin/llama-server",
        "port": "8002",
        "router_mode": False,
    }
    monkeypatch.setattr(
        manager,
        "resolve_llama_server_port_topology",
        lambda port: manager.LlamaServerTopology(router_proc, [router_proc], False, ""),
    )
    monkeypatch.setattr(
        manager,
        "find_all_llama_server_processes",
        lambda: [router_proc, extraction_proc],
    )
    monkeypatch.setattr(manager, "_is_descended_from", lambda pid, ancestors: False)
    monkeypatch.setattr(manager, "_list_gpu_compute_processes", lambda: [])

    state = manager.check_chat_gpu_preemption("8001")

    assert state["should_defer"] is True
    assert state["reason"] == "higher_priority_llama_runtime_present"
    assert state["competing_processes"] == [extraction_proc]


def test_check_chat_gpu_preemption_defers_for_other_gpu_compute_process(monkeypatch):
    router_proc = {
        "pid": 100,
        "binary": "/usr/bin/llama-server",
        "port": "8001",
        "router_mode": True,
    }
    gpu_proc = {"pid": 555, "process_name": "python", "used_memory_mb": 4096}
    monkeypatch.setattr(
        manager,
        "resolve_llama_server_port_topology",
        lambda port: manager.LlamaServerTopology(router_proc, [router_proc], False, ""),
    )
    monkeypatch.setattr(
        manager, "find_all_llama_server_processes", lambda: [router_proc]
    )
    monkeypatch.setattr(manager, "_is_descended_from", lambda pid, ancestors: False)
    monkeypatch.setattr(manager, "_list_gpu_compute_processes", lambda: [gpu_proc])

    state = manager.check_chat_gpu_preemption("8001")

    assert state["should_defer"] is True
    assert state["reason"] == "higher_priority_gpu_process_present"
    assert state["competing_processes"] == [gpu_proc]
