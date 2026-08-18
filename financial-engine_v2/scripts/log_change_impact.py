#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "reports" / "change_impact_log.md"


def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return (completed.stdout or "").strip()


def _changed_files() -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    buckets = [
        _run_git("diff", "--name-only"),
        _run_git("diff", "--cached", "--name-only"),
        _run_git("ls-files", "--others", "--exclude-standard"),
    ]
    for bucket in buckets:
        for raw in bucket.splitlines():
            path = raw.strip()
            if not path or path in seen:
                continue
            seen.add(path)
            files.append(path)
    return sorted(files)


def _default_change_id() -> str:
    date_token = datetime.now(timezone.utc).strftime("%Y%m%d")
    short = _run_git("rev-parse", "--short", "HEAD") or "local"
    return f"{date_token}-{short}-impact"


def _default_author() -> str:
    return _run_git("config", "user.name") or "unknown"


def _validate_required(args: argparse.Namespace) -> tuple[bool, list[str]]:
    """Return (ok, missing_fields) where missing_fields are still at their TBD default."""
    required = ["scope", "why", "expected_impact", "validation", "rollback"]
    missing = [f for f in required if getattr(args, f.replace("-", "_"), "TBD") == "TBD"]
    return (len(missing) == 0, missing)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a structured entry to reports/change_impact_log.md.")
    parser.add_argument("--change-id", default=_default_change_id())
    parser.add_argument("--scope", default="TBD")
    parser.add_argument("--why", default="TBD")
    parser.add_argument("--expected-impact", default="TBD")
    parser.add_argument("--risk-level", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--validation", default="TBD")
    parser.add_argument("--rollback", default="TBD")
    parser.add_argument("--author", default=_default_author())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ok, missing = _validate_required(args)
    if not ok:
        print(f"Missing required change-impact fields: {', '.join(missing)}")
        print("Provide explicit values instead of defaults (TBD).")
        return 2

    files = _changed_files()
    date_text = datetime.now(timezone.utc).date().isoformat()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("# Change Impact Log\n\n", encoding="utf-8")

    lines: list[str] = [
        "",
        f"### Change ID: {args.change_id}",
        f"- Date: {date_text}",
        f"- Author: {args.author}",
        f"- Scope: {args.scope}",
        "- Files:",
    ]
    if files:
        lines.extend([f"  - `{path}`" for path in files])
    else:
        lines.append("  - `TBD`")
    lines.extend(
        [
            f"- Why: {args.why}",
            f"- Expected impact: {args.expected_impact}",
            f"- Risk level: {args.risk_level}",
            f"- Validation commands: {args.validation}",
            f"- Rollback plan: {args.rollback}",
            "- Observed issues after deploy:",
            "  - none recorded yet.",
            "",
        ]
    )

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Appended impact entry to {LOG_PATH}")
    print(f"Detected files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
