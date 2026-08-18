#!/usr/bin/env python3
"""Focused self-check for the host-global Codex stop_check hook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HOOK = Path("/home/l4nd0/.codex/hooks/stop_check.py")


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def run_hook(repo: Path, cache_dir: Path, *, terminal: bool, thread_id: str) -> dict[str, object]:
    env = os.environ.copy()
    env["CODEX_STOP_CHECK_REPO"] = str(repo)
    env["CODEX_STOP_CHECK_CACHE_DIR"] = str(cache_dir)
    env["CODEX_THREAD_ID"] = thread_id
    if terminal:
        env["CODEX_STOP_CHECK_TERMINAL_HANDOFF"] = "1"
    else:
        env.pop("CODEX_STOP_CHECK_TERMINAL_HANDOFF", None)

    completed = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"hook_event_name": "Stop"}),
        cwd=repo,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(f"hook exited {completed.returncode}: {completed.stderr}")
    return json.loads(completed.stdout or "{}")


def main() -> int:
    with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as cache_tmp:
        repo = Path(repo_tmp)
        cache = Path(cache_tmp)
        run_git(repo, "init")
        run_git(repo, "config", "user.email", "stop-check@example.invalid")
        run_git(repo, "config", "user.name", "Stop Check")
        (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        run_git(repo, "add", "tracked.txt")
        run_git(repo, "commit", "-m", "init")
        (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

        first_terminal = run_hook(repo, cache, terminal=True, thread_id="terminal-thread")
        second_terminal = run_hook(repo, cache, terminal=True, thread_id="terminal-thread")
        first_non_terminal = run_hook(repo, cache, terminal=False, thread_id="active-thread")
        second_non_terminal = run_hook(repo, cache, terminal=False, thread_id="active-thread")

    assert "MILESTONE NOT COMMITTED" in str(first_terminal), first_terminal
    assert second_terminal == {}, second_terminal
    assert "MILESTONE NOT COMMITTED" in str(first_non_terminal), first_non_terminal
    assert "MILESTONE NOT COMMITTED" in str(second_non_terminal), second_non_terminal

    print("PASS: first terminal dirty warning emitted")
    print("PASS: repeated terminal dirty warning suppressed")
    print("PASS: non-terminal dirty warnings still emit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
