"""Tests for read-only LLM task formatting (pre-boot / capabilities)."""

from __future__ import annotations

from pathlib import Path

from cockpit.core.config import (
    compute_effective_cockpit_config,
    format_llm_backend_tasks_from_cfg,
    llm_task_summary_lines_from_cfg,
)


def _write_minimal_cockpit_yaml(config_dir: Path) -> None:
    (config_dir / "cockpit.yaml").write_text(
        "llm:\n  provider: llamacpp\n  model: placeholder\n  llamacpp_url: http://127.0.0.1:8001\n",
        encoding="utf-8",
    )


def test_format_llm_backend_tasks_from_cfg_shows_tasks(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "config").mkdir()
    _write_minimal_cockpit_yaml(tmp_path / "config")
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "allow_env_override: false\n"
        "hybrid_router_policy: local_preferred\n"
        "llm_profile_label: ops\n"
        "tool_debug: failures\n"
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: chat-model-x\n"
        "  llamacpp_url: http://127.0.0.1:8001\n"
        "  ollama_url: http://127.0.0.1:11434\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EXTRACT_MODEL", "extract-model-y")

    cfg = compute_effective_cockpit_config(
        tmp_path,
        str(tmp_path / "config" / "cockpit.yaml"),
        profile="full",
        read_only=False,
        no_web=False,
    )
    text = format_llm_backend_tasks_from_cfg(
        cfg,
        tmp_path,
        cockpit_config_path=str(tmp_path / "config" / "cockpit.yaml"),
    )

    assert "chat-model-x" in text
    assert "EXTRACT_MODEL=extract-model-y" in text
    assert "11434" in text


def test_llm_task_summary_lines_from_cfg_matches_env_extract(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "config").mkdir()
    _write_minimal_cockpit_yaml(tmp_path / "config")
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "hybrid_router_policy: local_preferred\n"
        "tool_debug: failures\n"
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: m1\n"
        "  llamacpp_url: http://127.0.0.1:8001\n"
        "  ollama_url: http://ollama\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EXTRACT_MODEL", "extract-verify-xyz")

    cfg = compute_effective_cockpit_config(
        tmp_path,
        str(tmp_path / "config" / "cockpit.yaml"),
        profile="full",
        read_only=False,
        no_web=False,
    )
    lines = llm_task_summary_lines_from_cfg(cfg)
    joined = "\n".join(lines)

    assert "m1" in joined
    assert "EXTRACT_MODEL=extract-verify-xyz" in joined


def test_verify_chat_model_matches_accepts_stem_equivalence() -> None:
    from cockpit.core.config import verify_chat_model_matches_llamacpp_runtime

    cfg = {
        "llm": {"provider": "llamacpp", "model": "qwen2.5-coder-14b"},
        "cockpit_llm": {},
    }
    assert (
        verify_chat_model_matches_llamacpp_runtime(
            cfg, "/models/qwen2.5-coder-14b.gguf"
        )
        is None
    )


def test_verify_effective_config_rejects_bad_policy(tmp_path: Path) -> None:
    from cockpit.core.config import (
        compute_effective_cockpit_config,
        verify_effective_config_for_preboot,
    )

    (tmp_path / "config").mkdir()
    _write_minimal_cockpit_yaml(tmp_path / "config")
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "hybrid_router_policy: not_a_real_policy\n"
        "tool_debug: failures\n"
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: m1\n"
        "  llamacpp_url: http://127.0.0.1:8001\n",
        encoding="utf-8",
    )
    cfg = compute_effective_cockpit_config(
        tmp_path,
        str(tmp_path / "config" / "cockpit.yaml"),
        profile="full",
        read_only=False,
        no_web=False,
    )
    errs = verify_effective_config_for_preboot(cfg)
    assert any("Invalid hybrid_router_policy" in e for e in errs)


def test_stack_defaults_set_anthropic_api_key_when_unset(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "config").mkdir()
    _write_minimal_cockpit_yaml(tmp_path / "config")
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "hybrid_router_policy: local_preferred\n"
        "tool_debug: failures\n"
        "defaults:\n"
        "  anthropic_model: claude-sonnet-4-6\n"
        '  anthropic_api_key: "test-key-from-defaults"\n'
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: m1\n"
        "  llamacpp_url: http://127.0.0.1:8001\n"
        "  ollama_url: http://127.0.0.1:11434\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    cfg = compute_effective_cockpit_config(
        tmp_path,
        str(tmp_path / "config" / "cockpit.yaml"),
        profile="full",
        read_only=False,
        no_web=False,
    )
    text = format_llm_backend_tasks_from_cfg(
        cfg,
        tmp_path,
        cockpit_config_path=str(tmp_path / "config" / "cockpit.yaml"),
    )

    assert "ANTHROPIC_API_KEY" in text
    assert "ANTHROPIC_API_KEY=set" in text
    assert "ANTHROPIC_MODEL=claude-sonnet-4-6" in text
    assert (
        cfg["cockpit_llm"]["defaults"]["anthropic_api_key"] == "test-key-from-defaults"
    )
