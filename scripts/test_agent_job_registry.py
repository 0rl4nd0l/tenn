from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import agent_job_registry as registry


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = REPO_ROOT / "scripts" / "agent_job_registry.py"


@pytest.fixture(autouse=True)
def isolated_registry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENN_AGENT_REGISTRY_ROOT", raising=False)
    monkeypatch.delenv("TENN_AGENT_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
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
    job_id: str,
    lane: str = "Evaluation",
    allowed_files: list[str] | None = None,
    output_dir: str | None = None,
    production_data_access: bool = False,
    stale_after_seconds: int | None = None,
) -> Path:
    allowed_files = allowed_files or [f"src/{job_id}.py"]
    output_dir = output_dir or f"reports/agent_jobs/{job_id}"
    card = repo / "docs" / "agent_tasks" / f"{job_id}.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"job_id: {job_id}",
        f"lane: {lane}",
        "owner: Codex",
        "allowed_files:",
    ]
    lines.extend(f"  - {path}" for path in allowed_files)
    lines.extend(
        [
            "approval_required: true",
            "timeout_seconds: 300",
            f"output_dir: {output_dir}",
            "mutation_mode: safe_extension",
            f"production_data_access: {'true' if production_data_access else 'false'}",
        ]
    )
    if stale_after_seconds is not None:
        lines.append(f"stale_after_seconds: {stale_after_seconds}")
    lines.extend(["---", "", "Test task card.", ""])
    card.write_text("\n".join(lines), encoding="utf-8")
    return card


def git_repo(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "user.email", "agent-job-registry@example.invalid")
    run_git(tmp_path, "config", "user.name", "Agent Job Registry Tests")
    (tmp_path / ".gitignore").write_text(".tenn/\nreports/agent_jobs/\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("a = 1\n", encoding="utf-8")
    (src / "b.py").write_text("b = 1\n", encoding="utf-8")
    first = task_card(tmp_path, job_id="job-a", lane="Evaluation", allowed_files=["src/a.py"])
    second = task_card(tmp_path, job_id="job-b", lane="Reporting", allowed_files=["src/b.py"])
    run_git(tmp_path, "add", ".gitignore", "src/a.py", "src/b.py", str(first), str(second))
    run_git(tmp_path, "commit", "-m", "init")
    return tmp_path


def run_registry(repo: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(REGISTRY_SCRIPT), *args, "--repo-root", str(repo)],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed, json.loads(completed.stdout)


def active_record_path(repo: Path, job_id: str) -> Path:
    return registry.resolve_registry_location(repo).root / "active" / f"{job_id}.json"


def test_env_registry_root_overrides_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = git_repo(tmp_path / "repo")
    env_root = tmp_path / "env-registry"
    config_root = tmp_path / "config-registry"
    run_git(repo, "config", "tenn.agentRegistryRoot", str(config_root))
    monkeypatch.setenv("TENN_AGENT_REGISTRY_ROOT", str(env_root))

    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert Path(str(payload["registry_root"])) == env_root.resolve()
    assert payload["registry_scope"] == "shared"
    assert (env_root / "active" / "job-a.json").exists()
    assert not (config_root / "active" / "job-a.json").exists()


def test_git_config_registry_root_is_used_when_env_absent(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    config_root = tmp_path / "config-registry"
    run_git(repo, "config", "tenn.agentRegistryRoot", str(config_root))

    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert Path(str(payload["registry_root"])) == config_root.resolve()
    assert payload["registry_scope"] == "shared"
    assert (config_root / "active" / "job-a.json").exists()


def test_git_common_dir_fallback_is_shared_for_linked_worktrees(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")

    repo_location = registry.resolve_registry_location(repo)
    linked_location = registry.resolve_registry_location(linked)

    assert repo_location.registry_scope == "shared"
    assert linked_location.registry_scope == "shared"
    assert repo_location.git_common_dir is not None
    assert repo_location.root == repo_location.git_common_dir / "tenn-agent-registry"
    assert linked_location.root == repo_location.root


def test_repo_local_fallback_emits_warning(tmp_path: Path) -> None:
    non_git = tmp_path / "not-a-git-repo"
    non_git.mkdir()

    payload = registry.list_active_jobs(repo_root=non_git)

    assert payload["ok"] is True
    assert payload["registry_scope"] == "repo_local_fallback"
    assert Path(str(payload["registry_root"])) == (non_git / ".tenn" / "agent_jobs").resolve()
    assert "repo-local .tenn/agent_jobs fallback" in str(payload["warnings"])


def test_list_active_includes_registry_metadata(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)

    completed, payload = run_registry(repo, "list-active")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["registry_root"]
    assert payload["registry_scope"] == "shared"
    assert payload["repo_root"] == str(repo.resolve())
    assert payload["git_common_dir"]


def test_linked_worktrees_see_same_active_job(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")

    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    active = registry.list_active_jobs(repo_root=linked)

    assert active["registry_root"] == claim["registry_root"]
    assert [job["job_id"] for job in active["active_jobs"]] == ["job-a"]
    assert active["active_jobs"][0]["worktree"] == str(repo.resolve())


def test_overlapping_allowed_files_across_linked_worktrees_blocks(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    overlapping = task_card(
        linked,
        job_id="job-overlap",
        lane="Reporting",
        allowed_files=["src/a.py"],
    )

    result = registry.check_overlap_for_task_card(overlapping, repo_root=linked)

    assert result["ok"] is False
    assert "allowed_files src/a.py" in str(result["issues"])


def test_non_overlapping_files_across_different_lanes_passes_in_linked_worktree(tmp_path: Path) -> None:
    repo = git_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    run_git(repo, "worktree", "add", "--detach", str(linked), "HEAD")
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    result = registry.check_overlap_for_task_card(linked / "docs" / "agent_tasks" / "job-b.md", repo_root=linked)

    assert result["ok"] is True
    assert result["issues"] == []


def test_claim_valid_task_card_creates_active_and_status_records(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert active_record_path(repo, "job-a").exists()
    assert (repo / "reports" / "agent_jobs" / "job-a" / "status.json").exists()
    record = json.loads(active_record_path(repo, "job-a").read_text(encoding="utf-8"))
    assert record["allowed_files"] == ["src/a.py"]
    assert record["worktree"] == str(repo.resolve())
    assert record["started_at"] == record["last_seen_at"]
    assert record["status"] == "active"


def test_claim_invalid_task_card_fails_without_active_record(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    invalid = task_card(
        repo,
        job_id="job-invalid",
        lane="Evaluation",
        allowed_files=["src/a.py"],
        production_data_access=True,
    )

    completed, payload = run_registry(repo, "claim", invalid.relative_to(repo).as_posix())

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "production_data_access" in str(payload["issues"])
    assert not active_record_path(repo, "job-invalid").exists()


def test_second_task_with_overlapping_allowed_files_fails(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True
    overlapping = task_card(
        repo,
        job_id="job-overlap",
        lane="Reporting",
        allowed_files=["src/a.py"],
    )

    result = registry.check_overlap_for_task_card(overlapping, repo_root=repo)

    assert result["ok"] is False
    assert "allowed_files" in str(result["issues"])


def test_different_lane_and_files_passes(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    result = registry.check_overlap_for_task_card(repo / "docs" / "agent_tasks" / "job-b.md", repo_root=repo)

    assert result["ok"] is True
    assert result["issues"] == []


def test_stale_lock_produces_warning_without_blocking(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    started = datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc)
    claim = registry.claim_task_card(
        repo / "docs" / "agent_tasks" / "job-a.md",
        repo_root=repo,
        now=started,
        stale_after_seconds=60,
    )
    assert claim["ok"] is True

    active_path = active_record_path(repo, "job-a")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    stale_at = (started - timedelta(seconds=120)).isoformat().replace("+00:00", "Z")
    active["heartbeat_at"] = stale_at
    active["last_seen_at"] = stale_at
    active_path.write_text(json.dumps(active), encoding="utf-8")

    overlapping = task_card(
        repo,
        job_id="job-overlap",
        lane="Evaluation",
        allowed_files=["src/a.py"],
        stale_after_seconds=60,
    )
    result = registry.check_overlap_for_task_card(
        overlapping,
        repo_root=repo,
        now=started,
        stale_after_seconds=60,
    )

    assert result["ok"] is True
    assert "stale lock warning-only" in str(result["warnings"])


def test_release_removes_active_record_and_updates_status(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    claim = registry.claim_task_card(repo / "docs" / "agent_tasks" / "job-a.md", repo_root=repo)
    assert claim["ok"] is True

    release = registry.release_job("job-a", repo_root=repo)

    assert release["ok"] is True
    assert not active_record_path(repo, "job-a").exists()
    status = json.loads((repo / "reports" / "agent_jobs" / "job-a" / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "released"
