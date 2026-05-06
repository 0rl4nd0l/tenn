from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT = REPO_ROOT / "scripts" / "agent_job_hook.py"
CONTRACT_SCRIPT = REPO_ROOT / "scripts" / "agent_job_contract.py"
REGISTRY_SCRIPT = REPO_ROOT / "scripts" / "agent_job_registry.py"


@pytest.fixture(autouse=True)
def isolated_registry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENN_AGENT_REGISTRY_ROOT", raising=False)
    monkeypatch.delenv("TENN_AGENT_TASK_CARD", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def task_card(
    repo: Path,
    *,
    allowed_files: list[str],
    production_data_access: bool = False,
    job_id: str = "hook-test-job",
    lane: str = "Evaluation",
    filename: str = "test-task.md",
) -> Path:
    card = repo / "docs" / "agent_tasks" / filename
    card.parent.mkdir(parents=True, exist_ok=True)
    production_access = "true" if production_data_access else "false"
    allowed = "\n".join(f"  - {path}" for path in allowed_files)
    card.write_text(
        "\n".join(
            [
                "---",
                f"job_id: {job_id}",
                f"lane: {lane}",
                "owner: Codex",
                "allowed_files:",
                allowed,
                "approval_required: true",
                "timeout_seconds: 300",
                f"output_dir: reports/agent_jobs/{job_id}",
                "mutation_mode: safe_extension",
                f"production_data_access: {production_access}",
                "---",
                "",
                "Test task card.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return card


def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    repo.mkdir(parents=True, exist_ok=True)
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "agent-job-hook@example.invalid")
    run_git(repo, "config", "user.name", "Agent Job Hook Tests")

    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "agent_job_contract.py").write_text(CONTRACT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (scripts / "agent_job_registry.py").write_text(REGISTRY_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / ".gitignore").write_text(".tenn/\nreports/agent_jobs/\n__pycache__/\n", encoding="utf-8")

    src = repo / "src"
    src.mkdir()
    (src / "allowed.py").write_text("allowed = 1\n", encoding="utf-8")
    (src / "outside.py").write_text("outside = 1\n", encoding="utf-8")
    task_card(repo, allowed_files=["src/allowed.py"])

    run_git(
        repo,
        "add",
        ".gitignore",
        "scripts/agent_job_contract.py",
        "scripts/agent_job_registry.py",
        "src/allowed.py",
        "src/outside.py",
        "docs/agent_tasks/test-task.md",
    )
    run_git(repo, "commit", "-m", "init")
    return repo


def run_hook(
    repo: Path,
    *,
    env: dict[str, str] | None = None,
    platform: str = "codex",
    event: str = "Stop",
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    completed = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT), "--platform", platform, "--event", event, "--repo-root", str(repo)],
        input=json.dumps({"hook_event_name": event}),
        cwd=repo,
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return completed, payload


def run_repo_registry(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    completed = subprocess.run(
        [sys.executable, str(repo / "scripts" / "agent_job_registry.py"), *args, "--repo-root", str(repo)],
        cwd=repo,
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def test_no_active_task_card_exits_success_with_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload == {}
    assert completed.stderr == ""


def test_no_active_task_card_stays_silent_with_shared_registry_jobs(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    shared_root = tmp_path / "shared-registry"
    claim_completed, claim_payload = run_repo_registry(
        repo,
        "claim",
        "docs/agent_tasks/test-task.md",
        env={"TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )
    assert claim_completed.returncode == 0
    assert claim_payload["ok"] is True

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "", "TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )

    assert completed.returncode == 0
    assert payload == {}


def test_active_valid_task_card_with_allowed_diff_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload == {"systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"}


def test_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "src/outside.py" in str(payload["reason"])


def test_invalid_task_card_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    task_card(repo, allowed_files=["src/allowed.py"], production_data_access=True)
    run_git(repo, "add", "docs/agent_tasks/test-task.md")
    run_git(repo, "commit", "-m", "invalid task card")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"})

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "production_data_access" in str(payload["reason"])


def test_codex_stop_output_is_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="codex",
        event="Stop",
    )

    assert completed.returncode == 0
    assert isinstance(payload, dict)


def test_claude_stop_and_session_end_outputs_are_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    for event in ("Stop", "SessionEnd"):
        completed, payload = run_hook(
            repo,
            env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
            platform="claude",
            event=event,
        )

        assert completed.returncode == 0
        assert isinstance(payload, dict)


def test_gemini_before_tool_no_active_task_card_allows_with_valid_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": ""},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {"decision": "allow"}


def test_gemini_before_tool_active_task_card_allows_without_report_artifact(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "allowed.py").write_text("allowed = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload == {
        "decision": "allow",
        "additionalContext": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md",
    }
    assert not (repo / "reports" / "agent_jobs" / "hook-test-job" / "diff-check.json").exists()


def test_gemini_before_tool_outside_diff_returns_blocking_json(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    (repo / "src" / "outside.py").write_text("outside = 2\n", encoding="utf-8")

    completed, payload = run_hook(
        repo,
        env={"TENN_AGENT_TASK_CARD": "docs/agent_tasks/test-task.md"},
        platform="gemini",
        event="BeforeTool",
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "src/outside.py" in str(payload["reason"])
    assert "src/outside.py" in str(payload["additionalContext"])


def test_active_task_marker_is_supported(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    marker = repo / ".tenn" / "active_agent_task"
    marker.parent.mkdir()
    marker.write_text("docs/agent_tasks/test-task.md\n", encoding="utf-8")

    completed, payload = run_hook(repo, env={"TENN_AGENT_TASK_CARD": ""})

    assert completed.returncode == 0
    assert payload == {"systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"}


def test_active_task_card_blocks_overlap_using_shared_registry_root(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    shared_root = tmp_path / "shared-registry"
    active = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        job_id="active-lock",
        lane="Evaluation",
        filename="active-lock.md",
    )
    overlap = task_card(
        repo,
        allowed_files=["src/allowed.py"],
        job_id="hook-overlap",
        lane="Reporting",
        filename="overlap.md",
    )
    run_git(repo, "add", str(active.relative_to(repo)), str(overlap.relative_to(repo)))
    run_git(repo, "commit", "-m", "add shared registry hook cards")
    claim_completed, claim_payload = run_repo_registry(
        repo,
        "claim",
        active.relative_to(repo).as_posix(),
        env={"TENN_AGENT_REGISTRY_ROOT": str(shared_root)},
    )
    assert claim_completed.returncode == 0
    assert claim_payload["registry_root"] == str(shared_root.resolve())

    completed, payload = run_hook(
        repo,
        env={
            "TENN_AGENT_REGISTRY_ROOT": str(shared_root),
            "TENN_AGENT_TASK_CARD": overlap.relative_to(repo).as_posix(),
        },
    )

    assert completed.returncode == 0
    assert payload["decision"] == "block"
    assert "active-lock" in str(payload["reason"])
    assert "allowed_files src/allowed.py" in str(payload["reason"])


def test_claude_stop_hook_no_longer_contains_plain_diff_output() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop_commands = [
        hook["command"]
        for group in settings["hooks"]["Stop"]
        for hook in group["hooks"]
        if hook.get("type") == "command"
    ]

    assert any("scripts/agent_job_hook.py --platform claude --event Stop" in command for command in stop_commands)
    assert not any(command.strip() == "git diff --stat HEAD 2>/dev/null || true" for command in stop_commands)


def test_gemini_before_tool_runs_task_card_hook() -> None:
    settings = json.loads((REPO_ROOT / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    before_tool_commands = [
        hook["command"]
        for group in settings["hooks"]["BeforeTool"]
        for hook in group["hooks"]
        if hook.get("type") == "command"
    ]

    assert any(
        "scripts/agent_job_hook.py --platform gemini --event BeforeTool" in command
        for command in before_tool_commands
    )
