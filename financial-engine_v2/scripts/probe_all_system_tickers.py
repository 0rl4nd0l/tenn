#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import SessionLocal  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.services.pipeline import backfill_ticker_sync  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe all known system tickers over a history window (default 5y), "
            "download announcements, and optionally process documents."
        )
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="History window in years (default: 5).",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=0,
        help="Optional cap for number of tickers (0 = all).",
    )
    parser.add_argument(
        "--ticker",
        action="append",
        help="Optional ticker filter. Repeat or pass comma-separated values.",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Run extraction/processing after successful download.",
    )
    parser.add_argument(
        "--max-backfill-retries",
        type=int,
        default=3,
        help="Retries per ticker for transient connection errors.",
    )
    parser.add_argument(
        "--no-resume-pending",
        action="store_true",
        help="Disable pending-download resume phase after probes.",
    )
    parser.add_argument(
        "--resume-max-retries",
        type=int,
        default=5,
        help="Retries per pending document in resume phase.",
    )
    parser.add_argument(
        "--resume-retry-delay-seconds",
        type=float,
        default=2.0,
        help="Base delay for pending retry backoff.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "all_system_tickers_probe_report.json"),
        help="Output report path.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for child scripts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    return parser.parse_args()


def parse_ticker_args(values: list[str] | None) -> list[str]:
    if not values:
        return []
    tickers: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for token in raw.split(","):
            ticker = token.strip().upper()
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            tickers.append(ticker)
    return tickers


def load_system_tickers(explicit: list[str], max_tickers: int) -> list[str]:
    db = SessionLocal()
    try:
        rows = db.query(Document.ticker).distinct().order_by(Document.ticker.asc()).all()
        discovered = [str(r[0]).strip().upper() for r in rows if r and r[0]]
    finally:
        db.close()

    if explicit:
        allowed = set(explicit)
        discovered = [t for t in discovered if t in allowed]
        missing = [t for t in explicit if t not in set(discovered)]
        discovered.extend(missing)

    deduped: list[str] = []
    seen: set[str] = set()
    for t in discovered:
        if not t or t in seen:
            continue
        seen.add(t)
        deduped.append(t)

    if max_tickers > 0:
        deduped = deduped[:max_tickers]
    return deduped


def main() -> None:
    args = parse_args()
    if args.years <= 0:
        raise SystemExit("--years must be > 0")
    if args.max_backfill_retries <= 0:
        raise SystemExit("--max-backfill-retries must be > 0")
    if args.max_tickers < 0:
        raise SystemExit("--max-tickers must be >= 0")

    explicit_tickers = parse_ticker_args(args.ticker)
    tickers = load_system_tickers(explicit_tickers, args.max_tickers)
    if not tickers:
        raise SystemExit("No tickers found in system. Populate documents first or pass --ticker.")

    if args.dry_run:
        resume_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "resume_pending_downloads.py"),
            "--ticker",
            ",".join(tickers),
            "--max-retries",
            str(args.resume_max_retries),
            "--retry-delay-seconds",
            str(args.resume_retry_delay_seconds),
            "--report",
            str(Path(args.report).with_name(f"{Path(args.report).stem}_resume.json")),
        ]
        if args.process_documents:
            resume_cmd.append("--process-documents")

        plan = {
            "dry_run": True,
            "script": "probe_all_system_tickers",
            "settings": {
                "tickers_total": len(tickers),
                "tickers_sample": tickers[:25],
                "years": args.years,
                "process_documents": bool(args.process_documents),
                "max_backfill_retries": args.max_backfill_retries,
                "resume_pending": not args.no_resume_pending,
                "resume_max_retries": args.resume_max_retries,
                "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
                "explicit_tickers": explicit_tickers,
                "max_tickers": args.max_tickers,
                "report": str(args.report),
            },
            "resume_command": None if args.no_resume_pending else resume_cmd,
            "notes": [
                "Dry-run skips backfill/resume execution and does not write reports.",
            ],
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "started_at": utc_now(),
        "settings": {
            "tickers_total": len(tickers),
            "years": args.years,
            "process_documents": bool(args.process_documents),
            "max_backfill_retries": args.max_backfill_retries,
            "resume_pending": not args.no_resume_pending,
            "resume_max_retries": args.resume_max_retries,
            "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
            "explicit_tickers": explicit_tickers,
            "max_tickers": args.max_tickers,
        },
        "tickers": tickers,
        "backfill": {
            "results": [],
            "totals": {
                "found": 0,
                "inserted": 0,
                "processed": 0,
                "skipped_download": 0,
                "errors": 0,
            },
        },
        "resume": None,
        "status": "success",
    }

    any_failures = False
    for ticker in tickers:
        completed = False
        for attempt in range(1, args.max_backfill_retries + 1):
            try:
                print(f"[probe] {ticker} attempt {attempt}", flush=True)
                result = backfill_ticker_sync(
                    ticker=ticker,
                    years=args.years,
                    process_documents=bool(args.process_documents),
                )
                result["attempt"] = attempt
                summary["backfill"]["results"].append(result)
                summary["backfill"]["totals"]["found"] += int(result.get("found", 0))
                summary["backfill"]["totals"]["inserted"] += int(result.get("inserted", 0))
                summary["backfill"]["totals"]["processed"] += int(result.get("processed", 0))
                summary["backfill"]["totals"]["skipped_download"] += int(result.get("skipped_download", 0))
                summary["backfill"]["totals"]["errors"] += int(result.get("error_count", 0))
                print(
                    f"[probe] {ticker} done found={result.get('found')} inserted={result.get('inserted')} "
                    f"processed={result.get('processed')} skipped={result.get('skipped_download')} "
                    f"errors={result.get('error_count')}",
                    flush=True,
                )
                completed = True
                break
            except httpx.ConnectError as exc:
                print(f"[probe] {ticker} transient connect error: {exc}", flush=True)
                if attempt < args.max_backfill_retries:
                    time.sleep(attempt * 3)
                    continue
                summary["backfill"]["results"].append(
                    {"ticker": ticker, "attempt": attempt, "failed": True, "error": str(exc)}
                )
                any_failures = True
            except Exception as exc:
                print(f"[probe] {ticker} failed: {exc}", flush=True)
                summary["backfill"]["results"].append(
                    {"ticker": ticker, "attempt": attempt, "failed": True, "error": str(exc)}
                )
                any_failures = True
                break
        if not completed and any_failures:
            continue

    resume_rc = 0
    if not args.no_resume_pending:
        resume_report = report_path.with_name(f"{report_path.stem}_resume.json")
        resume_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "resume_pending_downloads.py"),
            "--ticker",
            ",".join(tickers),
            "--max-retries",
            str(args.resume_max_retries),
            "--retry-delay-seconds",
            str(args.resume_retry_delay_seconds),
            "--report",
            str(resume_report),
        ]
        if args.process_documents:
            resume_cmd.append("--process-documents")

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"backend{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "backend"
        env.setdefault("DATABASE_URL", "sqlite:///./data/fe_local.db")

        print(f"[resume] running: {' '.join(resume_cmd)}", flush=True)
        completed = subprocess.run(resume_cmd, cwd=str(REPO_ROOT), env=env, check=False)
        resume_rc = completed.returncode
        resume_payload: dict[str, object] = {"returncode": resume_rc, "report_path": str(resume_report)}
        if resume_report.exists():
            try:
                resume_payload["report"] = json.loads(resume_report.read_text(encoding="utf-8"))
            except Exception as exc:
                resume_payload["report_load_error"] = str(exc)
        summary["resume"] = resume_payload

    summary["ended_at"] = utc_now()
    summary["status"] = "success" if not any_failures and resume_rc == 0 else "failed"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        f"[summary] status={summary['status']} tickers={len(tickers)} "
        f"inserted={summary['backfill']['totals']['inserted']} "
        f"processed={summary['backfill']['totals']['processed']} "
        f"errors={summary['backfill']['totals']['errors']} report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
