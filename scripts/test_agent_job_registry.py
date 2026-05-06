from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import agent_job_registry as registry


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = REPO_ROOT / "scripts" / "agent_job_registry.py"


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


def test_claim_valid_task_card_creates_active_and_status_records(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    completed, payload = run_registry(repo, "claim", "docs/agent_tasks/job-a.md")

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert (repo / ".tenn" / "agent_jobs" / "active" / "job-a.json").exists()
    assert (repo / "reports" / "agent_jobs" / "job-a" / "status.json").exists()


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
    assert not (repo / ".tenn" / "agent_jobs" / "active" / "job-invalid.json").exists()


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

    active_path = repo / ".tenn" / "agent_jobs" / "active" / "job-a.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    active["heartbeat_at"] = (started - timedelta(seconds=120)).isoformat().replace("+00:00", "Z")
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
    assert not (repo / ".tenn" / "agent_jobs" / "active" / "job-a.json").exists()
    status = json.loads((repo / "reports" / "agent_jobs" / "job-a" / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "released"
