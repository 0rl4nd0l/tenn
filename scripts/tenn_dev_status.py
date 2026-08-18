#!/usr/bin/env python3
"""Print a compact Tenn development status report.

This command is intentionally read-only. It shells out to git and, when present,
the Tenn git guard preflight runner.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


STATE_CLEAN = "CLEAN"
STATE_DIRTY = "DIRTY"
STATE_REPORT_ONLY_OK = "REPORT_ONLY_OK"
STATE_STALE_PATH = "STALE_PATH"
STATE_BLOCKED = "BLOCKED"


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def git_output(repo_root: Path, *args: str) -> str:
    return run(["git", *args], cwd=repo_root, check=True).stdout.rstrip("\n")


def find_repo_root() -> Path:
    completed = run(["git", "rev-parse", "--show-toplevel"], check=True)
    return Path(completed.stdout.strip()).resolve()


def parse_status_lines(status_text: str) -> list[str]:
    return [line for line in status_text.splitlines() if line.strip()]


def status_code(line: str) -> str:
    if line.startswith("?? "):
        return "??"
    if len(line) >= 2:
        return line[:2].strip() or line[:2]
    return "?"


def status_path(line: str) -> str:
    if line.startswith("?? "):
        return line[3:]
    return line[3:] if len(line) > 3 else line


def summarize_status(lines: list[str]) -> str:
    if not lines:
        return "clean"
    counts = Counter(status_code(line) for line in lines)
    summary = ", ".join(f"{code}:{counts[code]}" for code in sorted(counts))
    shown = ", ".join(status_path(line) for line in lines[:5])
    suffix = "" if len(lines) <= 5 else f", ... +{len(lines) - 5} more"
    return f"{summary} [{shown}{suffix}]"


def ignored_report_bundles(repo_root: Path) -> list[str]:
    reports_root = repo_root / "reports" / "agent_jobs"
    if not reports_root.exists():
        return []
    completed = run(
        ["git", "status", "--ignored", "--short", "reports/agent_jobs"],
        cwd=repo_root,
        check=True,
    )
    bundles: set[str] = set()
    for raw_line in completed.stdout.splitlines():
        if not raw_line.startswith("!! "):
            continue
        rel = raw_line[3:].strip().rstrip("/")
        parts = Path(rel).parts
        if len(parts) >= 3 and parts[0] == "reports" and parts[1] == "agent_jobs":
            bundles.add("/".join(parts[:3]))
    return sorted(bundles)


def find_guard(repo_root: Path) -> Path | None:
    candidates = [
        Path("/home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py"),
        repo_root / ".agents" / "skills" / "tenn-git-guard" / "scripts" / "tenn_git_guard.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_guard(repo_root: Path, guard_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    python = shutil.which("python3") or sys.executable
    completed = run(
        [
            python,
            str(guard_path),
            "preflight",
            "--repo-root",
            str(repo_root),
            "--topic",
            "tenn_dev_status",
            "--json",
        ],
        cwd=repo_root,
        timeout=60,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        return None, message
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return None, f"invalid guard json: {exc}"
    return parsed, None


def compact_guard_summary(guard: dict[str, Any] | None, error: str | None) -> dict[str, str]:
    if guard is None:
        return {
            "guard_available": "yes",
            "guard_result": "ERROR",
            "guard_error": error or "unknown",
        }
    path_ownership = guard.get("path_ownership") if isinstance(guard.get("path_ownership"), dict) else {}
    return {
        "guard_available": "yes",
        "guard_result": str(guard.get("final_decision", "DATA_MISSING")),
        "guard_path_classification": str(path_ownership.get("classification", "DATA_MISSING")),
        "guard_stop_reimplementation": str(guard.get("stop_reimplementation", "DATA_MISSING")).lower(),
        "guard_duplicate_work": str(guard.get("duplicate_work_classification", "DATA_MISSING")),
        "guard_registry": str(guard.get("registry_status", "DATA_MISSING")),
        "guard_ledger": str(guard.get("ledger_status", "DATA_MISSING")),
    }


def only_report_status(lines: list[str]) -> bool:
    return bool(lines) and all(status_path(line).startswith("reports/agent_jobs/") for line in lines)


def classify_state(
    status_lines: list[str],
    guard: dict[str, Any] | None,
    guard_error: str | None,
) -> str:
    path_class = ""
    final_decision = ""
    stop_reimplementation = False
    if guard:
        path_ownership = guard.get("path_ownership") if isinstance(guard.get("path_ownership"), dict) else {}
        path_class = str(path_ownership.get("classification", "")).upper()
        final_decision = str(guard.get("final_decision", "")).lower()
        stop_reimplementation = bool(guard.get("stop_reimplementation"))

    if guard_error or final_decision in {"block", "data_missing"}:
        return STATE_STALE_PATH if path_class == "STALE_PATH" else STATE_BLOCKED
    if path_class == "STALE_PATH" or stop_reimplementation:
        return STATE_STALE_PATH
    if not status_lines:
        return STATE_CLEAN
    if only_report_status(status_lines):
        return STATE_REPORT_ONLY_OK
    return STATE_DIRTY


def next_safe_action(state: str) -> str:
    if state == STATE_CLEAN:
        return "Create/validate a task card, then run the focused command or edit from this checkout."
    if state == STATE_REPORT_ONLY_OK:
        return "Report-only artifacts are present; preserve, ignore, or clean them only with owner approval."
    if state == STATE_STALE_PATH:
        return "Do not implement here; create a fresh canonical task worktree or write a task card/patch recommendation."
    if state == STATE_BLOCKED:
        return "Stop and resolve guard/data-missing/owner-boundary evidence before mutation."
    return "Inspect dirty files, classify ownership, and avoid unrelated edits."


def print_row(key: str, value: str) -> None:
    print(f"{key}: {value}")


def main() -> int:
    try:
        repo_root = find_repo_root()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write((exc.stderr or "not inside a git repository").strip() + "\n")
        return 2

    branch = git_output(repo_root, "branch", "--show-current") or "DETACHED"
    head = git_output(repo_root, "rev-parse", "HEAD")
    status_text = git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    status_lines = parse_status_lines(status_text)
    untracked = any(line.startswith("?? ") for line in status_lines)
    ignored_bundles = ignored_report_bundles(repo_root)

    guard_path = find_guard(repo_root)
    guard: dict[str, Any] | None = None
    guard_error: str | None = None
    if guard_path is not None:
        guard, guard_error = run_guard(repo_root, guard_path)

    state = classify_state(status_lines, guard, guard_error)

    print_row("REPO_ROOT", str(repo_root))
    print_row("BRANCH", branch)
    print_row("HEAD", head)
    print_row("GIT_STATUS", summarize_status(status_lines))
    print_row("UNTRACKED_FILES", "yes" if untracked else "no")
    print_row("IGNORED_REPORT_BUNDLES", f"yes ({len(ignored_bundles)})" if ignored_bundles else "no")
    if ignored_bundles:
        print_row("IGNORED_REPORT_SAMPLE", ", ".join(ignored_bundles[:5]))
    if guard_path is None:
        print_row("GUARD_AVAILABLE", "no")
    else:
        summary = compact_guard_summary(guard, guard_error)
        print_row("GUARD_PATH", str(guard_path))
        for key, value in summary.items():
            print_row(key.upper(), value)
    print_row("STATE", state)
    print_row("NEXT_SAFE_ACTION", next_safe_action(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
