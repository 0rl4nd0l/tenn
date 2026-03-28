from __future__ import annotations

from types import MethodType, SimpleNamespace

from cockpit.ui.preboot import PreBootScreen


def _make_screen() -> PreBootScreen:
    screen = PreBootScreen()
    screen._llama_proc = None
    screen._llama_fs_models = []
    return screen


def test_find_router_loaded_model_prefers_matching_filesystem_path(monkeypatch):
    screen = _make_screen()
    screen._llama_proc = {
        "router_mode": True,
        "raw_args": ["--host", "127.0.0.1", "--port", "8001", "--api-key", "secret"],
    }
    screen._llama_fs_models = [
        {
            "path": "/models/qwen2.5-coder-14b.gguf",
            "name": "qwen2.5-coder-14b.gguf",
            "stem": "qwen2.5-coder-14b",
        }
    ]
    monkeypatch.setattr(
        "cockpit.ui.preboot.list_models_api",
        lambda host, port, api_key="": [{"name": "qwen2.5-coder-14b", "state": "loaded"}],
    )

    loaded = screen._find_router_loaded_model()

    assert loaded == "/models/qwen2.5-coder-14b.gguf"


def test_find_router_loaded_model_returns_router_name_when_not_on_filesystem(monkeypatch):
    screen = _make_screen()
    screen._llama_proc = {
        "router_mode": True,
        "raw_args": ["--host", "127.0.0.1", "--port", "8001"],
    }
    monkeypatch.setattr(
        "cockpit.ui.preboot.list_models_api",
        lambda host, port, api_key="": [{"name": "hf/qwen-special", "state": "loaded"}],
    )

    loaded = screen._find_router_loaded_model()

    assert loaded == "hf/qwen-special"


def test_needs_model_switch_uses_router_loaded_names(monkeypatch):
    screen = _make_screen()
    screen._llama_proc = {
        "router_mode": True,
        "raw_args": ["--host", "127.0.0.1", "--port", "8001", "--api-key", "secret"],
    }
    monkeypatch.setattr(
        "cockpit.ui.preboot.list_models_api",
        lambda host, port, api_key="": [{"name": "qwen2.5-coder-14b", "state": "loaded"}],
    )

    assert screen._needs_model_switch({"llm_provider": "llamacpp", "llm_model": "qwen2.5-coder-14b"}) is False
    assert screen._needs_model_switch({"llm_provider": "llamacpp", "llm_model": "deepseek-r1"}) is True


def test_needs_model_switch_uses_path_and_mmap_for_single_model(monkeypatch):
    screen = _make_screen()
    screen._llama_proc = {
        "router_mode": False,
        "model_path": "/models/current.gguf",
        "raw_args": ["-m", "/models/current.gguf"],
    }

    checkbox = SimpleNamespace(value=False)

    def _query_one(self, selector, cls=None):
        assert selector == "#opt-mmap-off"
        return checkbox

    screen.query_one = MethodType(_query_one, screen)
    monkeypatch.setattr("cockpit.ui.preboot.has_no_mmap", lambda raw_args: False)

    assert (
        screen._needs_model_switch(
            {
                "llm_provider": "llamacpp",
                "llm_model_path": "/models/current.gguf",
            }
        )
        is False
    )
    assert (
        screen._needs_model_switch(
            {
                "llm_provider": "llamacpp",
                "llm_model_path": "/models/next.gguf",
            }
        )
        is True
    )

    checkbox.value = True
    assert (
        screen._needs_model_switch(
            {
                "llm_provider": "llamacpp",
                "llm_model_path": "/models/current.gguf",
            }
        )
        is True
    )


def test_needs_model_switch_returns_false_without_llama_process():
    screen = _make_screen()

    assert screen._needs_model_switch({"llm_provider": "llamacpp", "llm_model": "anything"}) is False


def test_needs_model_switch_returns_false_for_non_llamacpp_provider():
    screen = _make_screen()
    screen._llama_proc = {
        "router_mode": True,
        "raw_args": ["--host", "127.0.0.1", "--port", "8001"],
    }

    assert screen._needs_model_switch({"llm_provider": "ollama", "llm_model": "llama3:latest"}) is False


def test_router_mode_tag_uses_capability_state():
    screen = _make_screen()
    screen._router_capability = {"active_mode": "router_mode_available_not_active"}
    assert screen._router_mode_tag() == "  (router available)"

    screen._router_capability = {"active_mode": "router_mode_degraded"}
    assert screen._router_mode_tag() == "  (router degraded)"

    screen._router_capability = {"active_mode": "router_mode_active"}
    assert screen._router_mode_tag() == "  (router active)"


def test_router_mode_tag_blocks_on_ambiguous_topology():
    screen = _make_screen()
    screen._llama_topology = {
        "ambiguous": True,
        "reason": "multiple_chat_runtime_candidates",
    }

    assert screen._router_mode_tag() == "  (topology blocked: multiple chat runtime candidates)"


def test_topology_blocks_router_mode_returns_true_for_ambiguous_state():
    screen = _make_screen()
    screen._llama_topology = {
        "ambiguous": True,
        "reason": "multiple_chat_runtime_candidates",
    }

    assert screen._topology_blocks_router_mode() is True


def test_collect_flags_carries_router_mode_opt_in():
    screen = _make_screen()
    screen._llama_proc = {"router_mode": False}
    screen._llama_fs_models = [
        {"path": "/models/qwen2.5-coder-14b.gguf", "stem": "qwen2.5-coder-14b"},
        {"path": "/models/qwen2.5-14b-instruct.gguf", "stem": "qwen2.5-14b-instruct"},
    ]

    widgets = {
        "#opt-readonly": SimpleNamespace(value=False),
        "#opt-web": SimpleNamespace(value=True),
        "#opt-rag": SimpleNamespace(value=True),
        "#opt-verbose": SimpleNamespace(value=False),
        "#opt-router-mode": SimpleNamespace(value=True),
        "#opt-profile": SimpleNamespace(value="full"),
        "#opt-provider": SimpleNamespace(value="llamacpp"),
        "#opt-model": SimpleNamespace(value="/models/qwen2.5-coder-14b.gguf"),
        "#opt-extraction-model": SimpleNamespace(value="/models/qwen2.5-14b-instruct.gguf"),
        "#opt-orchestrator-model": SimpleNamespace(value=""),
        "#opt-subagent-model": SimpleNamespace(value=""),
        "#opt-router-policy": SimpleNamespace(value="local_only"),
    }

    def _query_one(self, selector, cls=None):
        return widgets[selector]

    screen.query_one = MethodType(_query_one, screen)

    flags = screen._collect_flags()

    assert flags["router_mode_opt_in"] is True
    assert flags["env"]["COCKPIT_ROUTER_MODE"] == "1"
    assert flags["env"]["LLAMA_SERVER_ROUTER_MODE"] == "1"
