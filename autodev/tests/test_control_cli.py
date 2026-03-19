from __future__ import annotations

import json
from pathlib import Path
import sys

from autodev.runtime import native_manager
import pytest


def _config(repo: Path, tmp_root: Path) -> native_manager.TennManagerConfig:
    worker_script = repo / "scripts" / "local_codex_agent.py"
    worker_script.parent.mkdir(parents=True, exist_ok=True)
    worker_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return native_manager.TennManagerConfig(
        repo_root=repo,
        reports_root=repo / "autodev" / "reports",
        runs_root=repo / "autodev" / "reports" / "runs",
        sessions_root=repo / "autodev" / "reports" / "sessions",
        temp_root=tmp_root / "tmp-openclaw",
        default_branch="main",
        protected_paths=("financial-engine_v2/", ".git/"),
        worker_script=worker_script,
        worker_model="qwen2.5-coder:14b",
        worker_ollama_url="http://127.0.0.1:11434",
        worker_max_tool_steps=8,
        worker_timeout_seconds=60,
        planner_model="openai/gpt-4.1-mini",
        python_bin=sys.executable,
    )


@pytest.fixture(autouse=True)
def _isolate_openclaw_auth_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TENN_OPENCLAW_AUTH_FILE", str(tmp_path / "auth-profiles.json"))


def test_status_ignores_legacy_run_dirs(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    cfg = _config(repo, tmp_path)
    legacy = cfg.runs_root / "20260308T231540Z"
    legacy.mkdir(parents=True, exist_ok=True)
    native = cfg.runs_root / "20260309T010101Z"
    native.mkdir(parents=True, exist_ok=True)
    (native / "request.json").write_text(json.dumps({"request": "analyze router"}) + "\n", encoding="utf-8")
    (native / "manager.json").write_text(
        json.dumps({"mode": "analyze", "status": "completed", "patch_applied": False, "changed_files": []}) + "\n",
        encoding="utf-8",
    )

    rc = native_manager.cmd_status(cfg)

    assert rc == 0
    out = capsys.readouterr().out
    assert "last_run_id=20260309T010101Z" in out
    assert "last_mode=analyze" in out
    assert "last_status=completed" in out


def test_task_run_alias_maps_to_fix(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_cfg = native_manager.TennManagerConfig(
        repo_root=Path("/tmp/repo"),
        reports_root=Path("/tmp/repo/autodev/reports"),
        runs_root=Path("/tmp/repo/autodev/reports/runs"),
        sessions_root=Path("/tmp/repo/autodev/reports/sessions"),
        temp_root=Path("/tmp/tenn-openclaw-tests"),
        default_branch="main",
        protected_paths=("financial-engine_v2/",),
        worker_script=Path("/tmp/repo/scripts/local_codex_agent.py"),
        worker_model="qwen2.5-coder:14b",
        worker_ollama_url="http://127.0.0.1:11434",
        worker_max_tool_steps=8,
        worker_timeout_seconds=60,
        planner_model="openai/gpt-4.1-mini",
        python_bin=sys.executable,
    )

    def fake_load_config() -> native_manager.TennManagerConfig:
        return fake_cfg

    def fake_handle(config, mode: str, text_parts: list[str]) -> int:
        captured["config"] = config
        captured["mode"] = mode
        captured["text_parts"] = text_parts
        return 0

    monkeypatch.setattr(native_manager, "load_config", fake_load_config)
    monkeypatch.setattr(native_manager, "_handle_request_command", fake_handle)

    rc = native_manager.main(["task-run", "fix", "the", "openclaw", "bridge"])

    assert rc == 0
    assert captured["config"] == fake_cfg
    assert captured["mode"] == "fix"
    assert captured["text_parts"] == ["fix the openclaw bridge"]


def test_deprecated_start_command_fails() -> None:
    rc = native_manager.main(["start"])
    assert rc == 2


def test_load_config_openai_first_without_key(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)

    cfg = native_manager.load_config(repo)

    assert cfg.planner_model == "ollama/qwen2.5-coder:7b"


def test_load_config_local_planner_override(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "ollama/qwen2.5-coder:7b")

    cfg = native_manager.load_config(repo)

    assert cfg.planner_model == "ollama/qwen2.5-coder:7b"


def test_load_config_force_openai_without_key(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", "1")

    cfg = native_manager.load_config(repo)

    assert cfg.planner_model == "openai/gpt-4.1-mini"


def test_load_config_uses_openclaw_auth_profile_for_openai(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    auth_file = tmp_path / "auth-profiles.json"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    auth_file.write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "openai:manual": {"provider": "openai", "token": "sk-test", "type": "token"},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)

    cfg = native_manager.load_config(repo)

    assert cfg.planner_model == "openai/gpt-4.1-mini"


def test_load_config_local_planner_override_beats_openclaw_auth_profile(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    auth_file = tmp_path / "auth-profiles.json"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    auth_file.write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "openai:manual": {"provider": "openai", "token": "sk-test", "type": "token"},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_FORCE_OPENAI_PLANNER", raising=False)
    monkeypatch.setenv("OPENCLAW_TENN_LOCAL_PLANNER_MODEL", "llamacpp/qwen2.5-coder-14b")

    cfg = native_manager.load_config(repo)

    assert cfg.planner_model == "llamacpp/qwen2.5-coder-14b"


def test_load_config_uses_llamacpp_worker_from_yaml_provider(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text(
        "\n".join(
            (
                "llm_provider_balanced: llamacpp",
                "llama_cpp_model_balanced: qwen2.5-coder-14b",
                "llama_cpp_base_url: http://127.0.0.1:8000/v1",
                "llama_cpp_api_key: local-openai-key",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENCLAW_TENN_WORKER_PROVIDER", raising=False)
    monkeypatch.delenv("OPENCLAW_TENN_WORKER_MODEL", raising=False)

    cfg = native_manager.load_config(repo)

    assert cfg.worker_provider == "llamacpp"
    assert cfg.worker_model == "qwen2.5-coder-14b"
    assert cfg.worker_openai_base_url == "http://127.0.0.1:8000/v1"
    assert cfg.worker_openai_api_key == "local-openai-key"


def test_load_config_honors_worker_num_ctx_override(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "autodev").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "autodev.yaml").write_text("ollama_model_balanced: qwen2.5-coder:7b\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_TENN_WORKER_NUM_CTX", "65536")

    cfg = native_manager.load_config(repo)

    assert cfg.worker_num_ctx == 65536


def test_status_marks_incomplete_when_manager_missing(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    cfg = _config(repo, tmp_path)
    run_dir = cfg.runs_root / "20260309T010102Z"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "request.json").write_text(json.dumps({"mode": "analyze", "request": "health check"}) + "\n", encoding="utf-8")

    rc = native_manager.cmd_status(cfg)

    assert rc == 0
    out = capsys.readouterr().out
    assert "last_run_id=20260309T010102Z" in out
    assert "last_status=incomplete" in out
