from __future__ import annotations

from cockpit.core.config import RuntimeFlags, apply_runtime_flags


def test_apply_runtime_flags_respects_router_mode_opt_in_env(monkeypatch):
    monkeypatch.setenv("COCKPIT_ROUTER_MODE", "1")

    cfg = apply_runtime_flags(
        {"llm": {"provider": "llamacpp", "router_mode_opt_in": False}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
        ),
    )

    assert cfg["llm"]["router_mode_opt_in"] is True
