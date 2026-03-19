#!/usr/bin/env python3
"""
Root single-command launcher for the current system.

Usage:
  python3 run.py

This delegates to financial-engine_v2/run.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = ROOT / "financial-engine_v2"


def main() -> int:
    target = ENGINE_ROOT / "run.py"
    if not target.exists():
        print(f"Missing runner: {target}")
        return 1
    cmd = [sys.executable, str(target)]
    completed = subprocess.run(cmd, cwd=str(ENGINE_ROOT), check=False)
    return completed.returncode


if __name__ == "__main__":
    print(
        "WARNING: This is not the canonical execution path.\n"
        "Use financial-engine_v2/scripts/run_local_backend.sh instead.",
        flush=True,
    )
    raise SystemExit(main())
