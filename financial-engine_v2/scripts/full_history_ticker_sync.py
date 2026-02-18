#!/usr/bin/env python3
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

from app.providers.universe import ASX20  # noqa: E402
from app.services.pipeline import backfill_ticker_sync  # noqa: E402


def _parse_tickers(values):
    if not values:
        return []
    tickers = []
    for raw in values:
        for token in raw.split(","):
            token = token.strip().upper()
            if token:
                tickers.append(token)
    seen = set()
    ordered = []
    for ticker in tickers:
        if ticker in seen:
            continue
        seen.add(ticker)
        ordered.append(ticker)
    return ordered


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run full-history ticker announcement gathering (ASX discovery + PDF download + pending resume)."
    )
    parser.add_argument(
        "--ticker",
        action="append",
        help="Ticker filter. Repeat or pass comma-separated values.",
    )
    parser.add_argument(
        "--asx10",
        action="store_true",
        help="Use ASX10 universe (first 10 from ASX20) when --ticker is not provided.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="History window in years for discovery.",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Also run extraction/embedding processing after each successful download.",
    )
    parser.add_argument(
        "--max-backfill-retries",
        type=int,
        default=3,
        help="Retries per ticker for transient discovery connect errors.",
    )
    parser.add_argument(
        "--no-resume-pending",
        action="store_true",
        help="Disable pending-download resume phase after backfill.",
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
        help="Base delay for resume retry backoff.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "ticker_full_history_report.json"),
        help="Output path for run report JSON.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for child scripts.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    tickers = _parse_tickers(args.ticker)
    if not tickers and args.asx10:
        tickers = ASX20[:10]
    if not tickers:
        raise SystemExit("No tickers provided. Use --ticker <TICKER> or --asx10.")
    if args.years <= 0:
        raise SystemExit("--years must be > 0")
    if args.max_backfill_retries <= 0:
        raise SystemExit("--max-backfill-retries must be > 0")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "started_at": _utc_now(),
        "settings": {
            "tickers": tickers,
            "years": args.years,
            "process_documents": args.process_documents,
            "max_backfill_retries": args.max_backfill_retries,
            "resume_pending": not args.no_resume_pending,
            "resume_max_retries": args.resume_max_retries,
            "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
        },
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
    }

    backfill_failed = False
    for ticker in tickers:
        ticker_done = False
        for attempt in range(1, args.max_backfill_retries + 1):
            try:
                print(f"[backfill] {ticker} attempt {attempt}", flush=True)
                result = backfill_ticker_sync(
                    ticker=ticker,
                    years=args.years,
                    process_documents=args.process_documents,
                )
                result["attempt"] = attempt
                summary["backfill"]["results"].append(result)
                summary["backfill"]["totals"]["found"] += result.get("found", 0)
                summary["backfill"]["totals"]["inserted"] += result.get("inserted", 0)
                summary["backfill"]["totals"]["processed"] += result.get("processed", 0)
                summary["backfill"]["totals"]["skipped_download"] += result.get("skipped_download", 0)
                summary["backfill"]["totals"]["errors"] += result.get("error_count", 0)
                print(
                    f"[backfill] {ticker} done found={result.get('found')} inserted={result.get('inserted')} "
                    f"processed={result.get('processed')} skipped={result.get('skipped_download')} "
                    f"errors={result.get('error_count')}",
                    flush=True,
                )
                ticker_done = True
                break
            except httpx.ConnectError as exc:
                print(f"[backfill] {ticker} transient connect error: {exc}", flush=True)
                if attempt < args.max_backfill_retries:
                    time.sleep(attempt * 3)
                    continue
                summary["backfill"]["results"].append(
                    {
                        "ticker": ticker,
                        "attempt": attempt,
                        "failed": True,
                        "error": str(exc),
                    }
                )
                backfill_failed = True
            except Exception as exc:
                summary["backfill"]["results"].append(
                    {
                        "ticker": ticker,
                        "attempt": attempt,
                        "failed": True,
                        "error": str(exc),
                    }
                )
                print(f"[backfill] {ticker} failed: {exc}", flush=True)
                backfill_failed = True
                break
        if not ticker_done and backfill_failed:
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

        resume_payload = {"returncode": resume_rc, "report_path": str(resume_report)}
        if resume_report.exists():
            try:
                resume_payload["report"] = json.loads(resume_report.read_text(encoding="utf-8"))
            except Exception as exc:
                resume_payload["report_load_error"] = str(exc)
        summary["resume"] = resume_payload

    summary["ended_at"] = _utc_now()
    summary["status"] = "success" if not backfill_failed and resume_rc == 0 else "failed"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[summary] status={summary['status']} report={report_path}")

    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
