#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".githooks"
PRE_PUSH = HOOKS_DIR / "pre-push"


PRE_PUSH_CONTENT = """#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/financial-engine_v2"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[hooks] python3 not found; skipping context check"
  exit 0
fi

if python3 scripts/refresh_codex_context.py --mode workspace --check-significant >/tmp/tenn_context_check.out 2>&1; then
  echo "[hooks] context check: no significant changes detected"
  exit 0
fi

rc=$?
cat /tmp/tenn_context_check.out || true
if [ "$rc" -eq 3 ]; then
  echo "[hooks] Significant changes detected."
  echo "[hooks] Run: make -C financial-engine_v2 context-refresh"
  exit 0
fi

echo "[hooks] context check failed unexpectedly; allowing push"
exit 0
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install git hooks for TENN context-change notifications.")
    parser.add_argument(
        "--set-hooks-path",
        action="store_true",
        help="Also set local git config core.hooksPath=.githooks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    PRE_PUSH.write_text(PRE_PUSH_CONTENT, encoding="utf-8")
    os.chmod(PRE_PUSH, os.stat(PRE_PUSH).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed hook: {PRE_PUSH}")

    if args.set_hooks_path:
        completed = subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            print(f"Failed to set hooksPath: {completed.stderr.strip()}")
            return completed.returncode
        print("Configured core.hooksPath=.githooks")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
