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


def test_collect_flags_minimal_env_only():
    screen = _make_screen()
    widgets = {
        "#opt-readonly": SimpleNamespace(value=False),
        "#opt-web": SimpleNamespace(value=True),
        "#opt-rag": SimpleNamespace(value=True),
        "#opt-verbose": SimpleNamespace(value=False),
        "#opt-profile": SimpleNamespace(value="full"),
    }

    def _query_one(self, selector, cls=None):
        return widgets[selector]

    screen.query_one = MethodType(_query_one, screen)

    flags = screen._collect_flags()

    assert flags["read_only"] is False
    assert flags["no_web"] is False
    assert "COCKPIT_ROUTER_MODE" not in flags.get("env", {})
