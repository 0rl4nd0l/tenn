from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip() or None


def build_run_metadata(repo_root: Path, script_file: str) -> dict[str, Any]:
    script_path = Path(script_file).resolve()
    commit = _git(repo_root, "rev-parse", "HEAD")
    short_commit = _git(repo_root, "rev-parse", "--short", "HEAD")
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(repo_root, "status", "--porcelain")

    payload: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "script": str(script_path.relative_to(repo_root)) if repo_root in script_path.parents else str(script_path),
        "python": sys.version.split()[0],
        "git": {
            "branch": branch,
            "commit": commit,
            "commit_short": short_commit,
            "dirty": bool(status),
        },
    }
    if commit is None:
        payload["git"]["available"] = False
    else:
        payload["git"]["available"] = True
    return payload
