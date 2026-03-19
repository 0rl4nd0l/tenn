"""Git repository operations with safety checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess


PROTECTED_BRANCHES = {"main", "master"}


@dataclass(frozen=True)
class RepoResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


def run_git(repo_path: Path, args: list[str]) -> RepoResult:
    cmd = ["git", *args]
    proc = subprocess.run(
        cmd,
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    return RepoResult(
        command=cmd,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def current_branch(repo_path: Path) -> str:
    result = run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    if result.exit_code != 0:
        raise RuntimeError(f"Failed to get current branch: {result.stderr.strip()}")
    return result.stdout.strip()


def assert_not_protected_branch(branch_name: str) -> None:
    if branch_name in PROTECTED_BRANCHES:
        raise RuntimeError(
            f"Refusing operation on protected branch '{branch_name}'. Use an agent branch."
        )


def build_agent_branch(task_slug: str, now: datetime | None = None) -> str:
    today = (now or datetime.utcnow()).strftime("%Y-%m-%d")
    safe_slug = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in task_slug).strip("-")
    safe_slug = safe_slug or "task"
    return f"agent/{today}/{safe_slug}"


def create_or_checkout_branch(repo_path: Path, branch_name: str) -> list[RepoResult]:
    results: list[RepoResult] = []
    if branch_name in PROTECTED_BRANCHES:
        raise RuntimeError("Branch name collides with protected branch.")
    existing = run_git(repo_path, ["branch", "--list", branch_name])
    results.append(existing)
    if existing.exit_code != 0:
        raise RuntimeError(f"Unable to query branches: {existing.stderr.strip()}")
    if existing.stdout.strip():
        checkout = run_git(repo_path, ["checkout", branch_name])
        results.append(checkout)
        if checkout.exit_code != 0:
            raise RuntimeError(f"Unable to checkout existing branch: {checkout.stderr.strip()}")
        return results
    create = run_git(repo_path, ["checkout", "-b", branch_name])
    results.append(create)
    if create.exit_code != 0:
        raise RuntimeError(f"Unable to create branch '{branch_name}': {create.stderr.strip()}")
    return results


def diff_numstat(repo_path: Path) -> dict[str, tuple[int, int]]:
    result = run_git(repo_path, ["diff", "--numstat"])
    if result.exit_code != 0:
        return {}
    stats: dict[str, tuple[int, int]] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add_raw, del_raw, path = parts[0], parts[1], parts[2]
        try:
            added = int(add_raw) if add_raw.isdigit() else 0
            deleted = int(del_raw) if del_raw.isdigit() else 0
        except ValueError:
            added, deleted = 0, 0
        stats[path] = (added, deleted)
    return stats


def changed_files(repo_path: Path) -> list[str]:
    result = run_git(repo_path, ["diff", "--name-only"])
    if result.exit_code != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def has_diff(repo_path: Path) -> bool:
    result = run_git(repo_path, ["diff", "--quiet"])
    # git diff --quiet exits with 1 when there are changes.
    return result.exit_code == 1


def commit_all_changes(repo_path: Path, message: str) -> list[RepoResult]:
    results: list[RepoResult] = []
    add_result = run_git(repo_path, ["add", "-A"])
    results.append(add_result)
    if add_result.exit_code != 0:
        return results
    commit_result = run_git(repo_path, ["commit", "-m", message])
    results.append(commit_result)
    return results


def _is_tracked_path(repo_path: Path, rel_path: str) -> bool:
    result = run_git(repo_path, ["ls-files", "--error-unmatch", rel_path])
    return result.exit_code == 0


def revert_paths(repo_path: Path, paths: list[str]) -> list[RepoResult]:
    results: list[RepoResult] = []
    if not paths:
        return results
    tracked: list[str] = []
    untracked: list[str] = []
    for rel_path in paths:
        if _is_tracked_path(repo_path, rel_path):
            tracked.append(rel_path)
        else:
            untracked.append(rel_path)
    if tracked:
        restore = run_git(repo_path, ["restore", "--staged", "--worktree", "--", *tracked])
        results.append(restore)
    for rel_path in untracked:
        abs_path = repo_path / rel_path
        if abs_path.is_file():
            os.remove(abs_path)
        elif abs_path.is_dir():
            for root, dirs, files in os.walk(abs_path, topdown=False):
                for file_name in files:
                    os.remove(Path(root) / file_name)
                for dir_name in dirs:
                    os.rmdir(Path(root) / dir_name)
            os.rmdir(abs_path)
    return results

