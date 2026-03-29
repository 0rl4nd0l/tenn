from __future__ import annotations

from pathlib import Path

from cockpit.core.config import RuntimeFlags, apply_runtime_flags


def test_apply_runtime_flags_respects_router_mode_opt_in_env(monkeypatch, tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "allow_env_override: true\n"
        "hybrid_router_policy: local_preferred\n"
        "llm_profile_label: ops\n"
        "tool_debug: failures\n"
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: qwen2.5-coder-14b\n"
        "  router_mode_opt_in: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COCKPIT_ROUTER_MODE", "1")

    cfg = apply_runtime_flags(
        {"llm": {"provider": "llamacpp", "router_mode_opt_in": False}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["llm"]["router_mode_opt_in"] is True
