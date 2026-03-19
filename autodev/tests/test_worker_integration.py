from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from autodev.runtime import native_manager
import pytest


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr}")


def _init_repo(repo: Path) -> None:
    _run(["git", "init"], repo)
    _run(["git", "config", "user.name", "autodev-test"], repo)
    _run(["git", "config", "user.email", "autodev-test@example.com"], repo)


def _commit_all(repo: Path, message: str) -> None:
    _run(["git", "add", "-A"], repo)
    _run(["git", "commit", "-m", message], repo)


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


def _worker(role: str, mode: str, text: str = "ok") -> native_manager.WorkerExecution:
    return native_manager.WorkerExecution(
        role=role,
        mode=mode,
        command=["fake-worker", role, mode],
        returncode=0,
        stdout=text,
        stderr="",
    )


@pytest.fixture(autouse=True)
def _mock_ready_backends(monkeypatch):
    monkeypatch.setattr(
        native_manager,
        "_collect_backend_readiness",
        lambda config: {
            "planner_mode": "openai",
            "planner_backend_state": "ready",
            "planner_detail": "ok",
            "worker_backend": "ollama",
            "worker_backend_state": "ready",
            "worker_detail": "ok",
            "gateway_state": "ready",
            "gateway_detail": "ok",
        },
    )


def test_execute_analyze_creates_native_manifest(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    monkeypatch.setattr(
        native_manager,
        "run_worker_process",
        lambda config, role, mode, workspace, prompt: _worker(role, mode, "analysis complete"),
    )

    result = native_manager.execute_request(cfg, mode="analyze", request_text="analyze the openclaw bridge")

    assert result["status"] == "completed"
    run_dir = cfg.runs_root / result["run_id"]
    assert (run_dir / "request.json").exists()
    assert (run_dir / "manager.json").exists()
    assert (run_dir / "workers.json").exists()
    assert (run_dir / "commands.json").exists()
    assert (run_dir / "report.md").exists()
    assert not (cfg.temp_root / result["run_id"]).exists()
    assert (repo / "README.md").read_text(encoding="utf-8") == "hello\n"


def test_analyze_discards_workspace_edits(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    target = repo / "README.md"
    target.write_text("before\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    def fake_worker(config, role: str, mode: str, workspace: Path, prompt: str) -> native_manager.WorkerExecution:
        if role == "review-local":
            (workspace / "README.md").write_text("mutated in analyze workspace\n", encoding="utf-8")
        return _worker(role, mode, f"{role} complete")

    monkeypatch.setattr(native_manager, "run_worker_process", fake_worker)

    result = native_manager.execute_request(cfg, mode="analyze", request_text="analyze the bridge")

    assert result["status"] == "analysis_modified_files"
    assert result["patch_applied"] is False
    assert target.read_text(encoding="utf-8") == "before\n"
    assert not (cfg.temp_root / result["run_id"]).exists()


def test_fix_applies_patch_back_to_main_repo(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    target = repo / "app.txt"
    target.write_text("before\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    def fake_worker(config, role: str, mode: str, workspace: Path, prompt: str) -> native_manager.WorkerExecution:
        if role == "coder-local":
            (workspace / "app.txt").write_text("after\n", encoding="utf-8")
        return _worker(role, mode, f"{role} complete")

    monkeypatch.setattr(native_manager, "run_worker_process", fake_worker)

    result = native_manager.execute_request(cfg, mode="fix", request_text="fix the app output")

    assert result["status"] == "applied"
    assert result["patch_applied"] is True
    assert target.read_text(encoding="utf-8") == "after\n"
    run_dir = cfg.runs_root / result["run_id"]
    assert (run_dir / "patch.diff").exists()
    commands_payload = json.loads((run_dir / "commands.json").read_text(encoding="utf-8"))
    command_names = [item["name"] for item in commands_payload["commands"]]
    assert "git_worktree_add" in command_names
    assert "git_apply_patch" in command_names
    assert "git_worktree_remove" in command_names


def test_fix_blocks_when_main_worktree_is_dirty(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    target = repo / "app.txt"
    target.write_text("before\n", encoding="utf-8")
    _commit_all(repo, "init")
    target.write_text("dirty main worktree\n", encoding="utf-8")
    cfg = _config(repo, tmp_path)

    def fake_worker(config, role: str, mode: str, workspace: Path, prompt: str) -> native_manager.WorkerExecution:
        if role == "coder-local":
            (workspace / "app.txt").write_text("worker change\n", encoding="utf-8")
        return _worker(role, mode, f"{role} complete")

    monkeypatch.setattr(native_manager, "run_worker_process", fake_worker)

    result = native_manager.execute_request(cfg, mode="fix", request_text="fix the app output")

    assert result["status"] == "main_worktree_conflict"
    assert result["patch_applied"] is False
    assert target.read_text(encoding="utf-8") == "dirty main worktree\n"


def test_fix_blocks_protected_paths_without_explicit_scope(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    protected = repo / "financial-engine_v2" / "engine.py"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text("before\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    def fake_worker(config, role: str, mode: str, workspace: Path, prompt: str) -> native_manager.WorkerExecution:
        if role == "coder-local":
            target = workspace / "financial-engine_v2" / "engine.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("after\n", encoding="utf-8")
        return _worker(role, mode, f"{role} complete")

    monkeypatch.setattr(native_manager, "run_worker_process", fake_worker)

    result = native_manager.execute_request(cfg, mode="fix", request_text="fix the openclaw manager")

    assert result["status"] == "protected_path_blocked"
    assert result["patch_applied"] is False
    assert result["protected_path_hits"] == ["financial-engine_v2/engine.py"]
    assert protected.read_text(encoding="utf-8") == "before\n"


def test_execute_request_blocks_when_planner_not_ready(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    monkeypatch.setattr(
        native_manager,
        "_collect_backend_readiness",
        lambda config: {
            "planner_mode": "openai",
            "planner_backend_state": "missing_api_key",
            "planner_detail": "OPENAI_API_KEY is missing.",
            "worker_backend": "ollama",
            "worker_backend_state": "ready",
            "worker_detail": "ok",
            "gateway_state": "ready",
            "gateway_detail": "ok",
        },
    )

    result = native_manager.execute_request(cfg, mode="analyze", request_text="analyze the bridge")

    assert result["status"] == "planner_not_ready"
    assert result["error"] == "OPENAI_API_KEY is missing."
    run_dir = cfg.runs_root / result["run_id"]
    workers_payload = json.loads((run_dir / "workers.json").read_text(encoding="utf-8"))
    assert workers_payload["workers"] == []


def test_execute_request_blocks_when_worker_backend_not_ready(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    monkeypatch.setattr(
        native_manager,
        "_collect_backend_readiness",
        lambda config: {
            "planner_mode": "openai",
            "planner_backend_state": "ready",
            "planner_detail": "ok",
            "worker_backend": "ollama",
            "worker_backend_state": "unreachable",
            "worker_detail": "Could not reach ollama",
            "gateway_state": "ready",
            "gateway_detail": "ok",
        },
    )

    result = native_manager.execute_request(cfg, mode="fix", request_text="fix the bridge")

    assert result["status"] == "worker_backend_not_ready"
    assert result["error"] == "Could not reach ollama"
    run_dir = cfg.runs_root / result["run_id"]
    workers_payload = json.loads((run_dir / "workers.json").read_text(encoding="utf-8"))
    assert workers_payload["workers"] == []


def test_create_worktree_clone_fallback_cleans_partial_target(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)
    commands: list[dict[str, object]] = []
    run_id = "20260309T030000Z"
    expected_worktree = cfg.temp_root / run_id / "repo"
    clone_checked = {"value": False}

    def fake_git(config, args: list[str], cwd=None):
        if args[:4] == ["worktree", "add", "--detach", "--no-checkout"]:
            expected_worktree.mkdir(parents=True, exist_ok=True)
            (expected_worktree / "leftover.txt").write_text("partial\n", encoding="utf-8")
            return 1, "", "simulated worktree failure"
        return 0, "", ""

    def fake_run_command(cmd: list[str], cwd=None):
        if cmd[:3] == ["git", "clone", "--local"]:
            assert cmd[-1] == "."
            assert cwd == expected_worktree
            assert not (expected_worktree / "leftover.txt").exists()
            clone_checked["value"] = True
            (expected_worktree / ".git").mkdir(parents=True, exist_ok=True)
            return 0, "", ""
        if cmd[:4] == ["git", "sparse-checkout", "set", "--no-cone"]:
            assert cwd == expected_worktree
            return 0, "", ""
        if cmd == ["git", "checkout", "--detach", "HEAD"]:
            return 0, "", ""
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(native_manager, "_git", fake_git)
    monkeypatch.setattr(native_manager, "_run_command", fake_run_command)

    worktree = native_manager._create_worktree(cfg, run_id, commands)

    assert worktree == expected_worktree
    assert clone_checked["value"] is True
    assert worktree.exists()
    command_names = [entry["name"] for entry in commands]
    assert command_names == ["git_worktree_add", "git_clone_fallback", "git_sparse_checkout_set", "git_checkout_detached"]


def test_execute_request_cleans_partial_temp_dir_when_worktree_creation_fails(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    def fake_create_worktree(config, run_id: str, commands):
        target = config.temp_root / run_id / "repo"
        target.mkdir(parents=True, exist_ok=True)
        (target / "leftover.txt").write_text("partial\n", encoding="utf-8")
        raise RuntimeError("worktree setup failed")

    monkeypatch.setattr(native_manager, "_create_worktree", fake_create_worktree)

    result = native_manager.execute_request(cfg, mode="analyze", request_text="analyze bridge")

    assert result["status"] == "failed"
    assert result["error"] == "worktree setup failed"
    assert not (cfg.temp_root / result["run_id"]).exists()


def test_prune_stale_temp_runs_removes_old_entries(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)

    old_run = cfg.temp_root / "20260309T000000Z"
    keep_run = cfg.temp_root / "20260309T000100Z"
    old_run.mkdir(parents=True, exist_ok=True)
    keep_run.mkdir(parents=True, exist_ok=True)
    old_timestamp = time.time() - 3600
    os.utime(old_run, (old_timestamp, old_timestamp))
    monkeypatch.setenv("OPENCLAW_TENN_TMP_TTL_SECONDS", "300")

    native_manager._prune_stale_temp_runs(cfg, keep_run_id="20260309T000100Z")

    assert not old_run.exists()
    assert keep_run.exists()


def test_run_worker_process_scales_request_timeout(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(native_manager.subprocess, "run", fake_run)

    result = native_manager.run_worker_process(
        cfg,
        role="review-local",
        mode="analyze",
        workspace=repo,
        prompt="health check",
    )

    assert result.returncode == 0
    command = captured["command"]
    assert isinstance(command, list)
    assert command[command.index("--num-ctx") + 1] == "32768"
    timeout_value = command[command.index("--request-timeout-seconds") + 1]
    assert timeout_value == "30"


def test_run_worker_process_honors_request_timeout_override(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setenv("OPENCLAW_TENN_WORKER_REQUEST_TIMEOUT_SECONDS", "37")
    monkeypatch.setattr(native_manager.subprocess, "run", fake_run)

    result = native_manager.run_worker_process(
        cfg,
        role="review-local",
        mode="analyze",
        workspace=repo,
        prompt="health check",
    )

    assert result.returncode == 0
    command = captured["command"]
    assert isinstance(command, list)
    assert command[command.index("--num-ctx") + 1] == "32768"
    timeout_value = command[command.index("--request-timeout-seconds") + 1]
    assert timeout_value == "37"


def test_run_worker_process_uses_openai_endpoint_for_llamacpp_worker(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "init")
    cfg = _config(repo, tmp_path)
    cfg = replace(
        cfg,
        worker_provider="llamacpp",
        worker_model="qwen2.5-coder-14b",
        worker_openai_base_url="http://127.0.0.1:8000/v1",
        worker_openai_api_key="local-openai-key",
    )
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(native_manager.subprocess, "run", fake_run)

    result = native_manager.run_worker_process(
        cfg,
        role="review-local",
        mode="analyze",
        workspace=repo,
        prompt="health check",
    )

    assert result.returncode == 0
    command = captured["command"]
    assert isinstance(command, list)
    assert command[command.index("--provider") + 1] == "openai"
    assert command[command.index("--base-url") + 1] == "http://127.0.0.1:8000/v1"
    assert command[command.index("--api-key") + 1] == "local-openai-key"


def test_build_worker_prompt_strips_previous_worker_output() -> None:
    previous_report = """# OpenClaw Tenn Run Report
- run id: `20260309T000000Z`

## Request
old request

## Worker Results
### review-local
- return code: `0`

```text
run_shell(command="bridge health check", timeout_seconds=60)
```
"""
    prompt = native_manager._build_worker_prompt(
        mode="analyze",
        role="review-local",
        request_text="new request",
        previous_report=previous_report,
        protected_paths=("docs/",),
    )

    assert "Previous run context follows" in prompt
    assert "old request" in prompt
    assert "run_shell(command=" not in prompt
