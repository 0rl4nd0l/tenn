#!/usr/bin/env python3
"""Run operator-gated Codex CLI investigations for Cockpit flagged reports."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_reports_root(repo_root: Path) -> Path:
    workspace = os.getenv("COCKPIT_WORKSPACE_ROOT", "").strip()
    base = Path(workspace) if workspace else repo_root
    return (base / "reports" / "cockpit" / "flagged_sessions").resolve()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _find_report_dir(root: Path, report_id: str) -> Path:
    normalized = str(report_id or "").strip()
    if not normalized:
        raise ValueError("report_id is required")
    for candidate in root.glob(f"*/{normalized}"):
        if candidate.is_dir():
            return candidate.resolve()
    raise FileNotFoundError(f"Report not found under {root}: {normalized}")


def _iter_queued_reports(root: Path) -> list[Path]:
    if not root.exists():
        return []
    rows: list[tuple[float, Path]] = []
    for investigation_path in root.glob("*/*/investigation.json"):
        try:
            payload = _read_json(investigation_path)
        except Exception:
            continue
        if str(payload.get("status") or "") == "queued":
            rows.append((investigation_path.stat().st_mtime, investigation_path.parent))
    rows.sort(key=lambda item: item[0])
    return [item[1] for item in rows]


def _resolve_prompt_path(
    *,
    repo_root: Path,
    report_dir: Path,
    investigation: dict[str, Any],
) -> Path:
    raw = str(investigation.get("codex_prompt_path") or "").strip()
    if raw:
        candidate = Path(raw)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        repo_candidate = (repo_root / candidate).resolve()
        if repo_candidate.exists():
            return repo_candidate
    fallback = report_dir / "codex_prompt.md"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Missing codex_prompt.md for {report_dir.name}")


def _update_investigation(path: Path, **updates: Any) -> dict[str, Any]:
    payload = _read_json(path)
    payload.update(updates)
    payload["updated_at"] = _now_iso()
    _write_json(path, payload)
    return payload


def _build_codex_command(
    *,
    args: argparse.Namespace,
    repo_root: Path,
    output_path: Path,
) -> list[str]:
    sandbox = "workspace-write" if args.apply else args.sandbox
    return [
        args.codex_bin,
        "exec",
        "--json",
        "-c",
        'approval_policy="never"',
        "-C",
        str(repo_root),
        "--sandbox",
        sandbox,
        "--output-last-message",
        str(output_path),
        "-",
    ]


def _run_report(args: argparse.Namespace, repo_root: Path, report_dir: Path) -> int:
    investigation_path = report_dir / "investigation.json"
    if not investigation_path.exists():
        raise FileNotFoundError(f"Missing investigation.json for {report_dir}")

    investigation = _read_json(investigation_path)
    if str(investigation.get("status") or "") != "queued" and not args.force:
        print(
            f"Skipping {report_dir.name}: status={investigation.get('status')!r}",
            file=sys.stderr,
        )
        return 0

    prompt_path = _resolve_prompt_path(
        repo_root=repo_root,
        report_dir=report_dir,
        investigation=investigation,
    )
    prompt = prompt_path.read_text(encoding="utf-8")
    output_path = report_dir / "codex-last-message.md"
    events_path = report_dir / "codex-events.jsonl"
    stderr_path = report_dir / "codex-stderr.log"
    command = _build_codex_command(args=args, repo_root=repo_root, output_path=output_path)

    if args.dry_run:
        print(" ".join(command))
        print(f"prompt={prompt_path}")
        return 0

    if shutil.which(args.codex_bin) is None and not Path(args.codex_bin).exists():
        raise FileNotFoundError(f"Codex CLI not found: {args.codex_bin}")

    lock_path = report_dir / "investigation.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"Skipping {report_dir.name}: lock exists at {lock_path}", file=sys.stderr)
        return 0

    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(f"pid={os.getpid()}\nstarted_at={_now_iso()}\n")

        _update_investigation(
            investigation_path,
            status="running",
            started_at=_now_iso(),
            codex_command=command,
            codex_events_path=str(events_path),
            codex_stderr_path=str(stderr_path),
            codex_output_path=str(output_path),
        )
        with events_path.open("w", encoding="utf-8") as events_file, stderr_path.open(
            "w",
            encoding="utf-8",
        ) as stderr_file:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                cwd=repo_root,
                stdout=events_file,
                stderr=stderr_file,
                check=False,
            )

        final_status = "completed" if completed.returncode == 0 else "failed"
        _update_investigation(
            investigation_path,
            status=final_status,
            completed_at=_now_iso(),
            returncode=completed.returncode,
        )
        print(f"{report_dir.name}: {final_status} returncode={completed.returncode}")
        return completed.returncode
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    repo_root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Run Codex CLI against queued Cockpit flagged-report investigations.",
    )
    parser.add_argument("--report-id", help="Run one flagged report by report_id.")
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_reports_root(repo_root),
        help="Flagged report root. Defaults to COCKPIT_WORKSPACE_ROOT/reports/... or repo reports/...",
    )
    parser.add_argument("--once", action="store_true", help="Run one queued report and exit.")
    parser.add_argument("--watch", action="store_true", help="Poll for queued reports.")
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument("--dry-run", action="store_true", help="Print the Codex command only.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Use workspace-write sandbox so Codex can implement a minimal fix.",
    )
    parser.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write", "danger-full-access"),
        default="read-only",
        help="Codex sandbox when --apply is not set.",
    )
    parser.add_argument("--force", action="store_true", help="Run even if status is not queued.")
    parser.add_argument("--codex-bin", default=shutil.which("codex") or "codex")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.report_id:
        return _run_report(args, repo_root, _find_report_dir(root, args.report_id))

    if not args.watch:
        args.once = True

    while True:
        queued = _iter_queued_reports(root)
        if queued:
            returncode = _run_report(args, repo_root, queued[0])
            if args.once:
                return returncode
        elif args.once:
            print(f"No queued investigations under {root}")
            return 0
        time.sleep(max(1.0, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
