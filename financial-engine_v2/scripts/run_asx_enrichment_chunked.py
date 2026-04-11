#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SWEEP_SCRIPT = REPO_ROOT / "scripts" / "asx_enrichment_sweep_action.py"
NARRATIVE_POLICY_VALUES = ("full", "selective", "metrics_only")


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    dt = datetime.strptime(raw, "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ASX enrichment in consistent 14-day (or custom) chunks over a long horizon."
    )
    parser.add_argument("--end-date", default="", help="Final day (YYYY-MM-DD), default today UTC.")
    parser.add_argument("--total-days-back", type=int, default=1825, help="Total history depth (default 5 years).")
    parser.add_argument("--chunk-days", type=int, default=14, help="Days per chunk (default 14).")
    parser.add_argument("--fallback-max-tickers", type=int, default=1200)
    parser.add_argument(
        "--ticker-universe-file",
        default=str(REPO_ROOT / "data" / "raw" / "asx_ticker_universe.txt"),
    )
    parser.add_argument(
        "--download-existing-missing",
        dest="download_existing_missing",
        action="store_true",
        help="Enable recovery of existing DB rows with missing local PDFs.",
    )
    parser.add_argument(
        "--no-download-existing-missing",
        dest="download_existing_missing",
        action="store_false",
        help="Disable recovery of existing DB rows with missing local PDFs.",
    )
    parser.set_defaults(download_existing_missing=True)
    parser.add_argument("--process-documents", action="store_true")
    parser.add_argument(
        "--narrative-policy",
        choices=NARRATIVE_POLICY_VALUES,
        default="full",
        help="Narrative extraction policy when --process-documents is enabled.",
    )
    parser.add_argument("--request-delay-ms", type=int, default=700)
    parser.add_argument("--request-jitter-ms", type=int, default=900)
    parser.add_argument("--failure-backoff-ms", type=int, default=2500)
    parser.add_argument("--max-consecutive-failures", type=int, default=20)
    parser.add_argument("--max-errors", type=int, default=500)
    parser.add_argument("--stop-after-empty-days", type=int, default=10)
    parser.add_argument(
        "--reports-dir",
        default=str(REPO_ROOT / "reports" / "asx"),
        help="Directory for per-chunk reports and rollup.",
    )
    parser.add_argument(
        "--rollup-report",
        default=str(REPO_ROOT / "reports" / "asx" / "asx_enrichment_chunked_rollup.json"),
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    return parser.parse_args()


def _chunk_end_dates(final_end: datetime, total_days_back: int, chunk_days: int) -> list[datetime]:
    ends: list[datetime] = []
    covered = 0
    current_end = final_end
    while covered < total_days_back:
        ends.append(current_end)
        covered += chunk_days
        current_end = current_end - timedelta(days=chunk_days)
    return ends


def main() -> None:
    args = parse_args()
    if args.total_days_back <= 0:
        raise SystemExit("--total-days-back must be > 0")
    if args.chunk_days <= 0:
        raise SystemExit("--chunk-days must be > 0")

    end_date = _parse_date(args.end_date)
    if args.dry_run:
        chunk_ends = _chunk_end_dates(end_date, args.total_days_back, args.chunk_days)
        plan = {
            "dry_run": True,
            "script": "run_asx_enrichment_chunked",
            "settings": {
                "end_date": end_date.strftime("%Y-%m-%d"),
                "total_days_back": args.total_days_back,
                "chunk_days": args.chunk_days,
                "chunks_total": len(chunk_ends),
                "fallback_max_tickers": args.fallback_max_tickers,
                "ticker_universe_file": args.ticker_universe_file,
                "download_existing_missing": bool(args.download_existing_missing),
                "process_documents": bool(args.process_documents),
                "narrative_policy": args.narrative_policy,
                "request_delay_ms": args.request_delay_ms,
                "request_jitter_ms": args.request_jitter_ms,
                "failure_backoff_ms": args.failure_backoff_ms,
                "max_consecutive_failures": args.max_consecutive_failures,
                "max_errors": args.max_errors,
                "stop_after_empty_days": args.stop_after_empty_days,
                "reports_dir": str(args.reports_dir),
                "rollup_report": str(args.rollup_report),
            },
            "samples": {
                "first_chunk_end": chunk_ends[0].strftime("%Y-%m-%d") if chunk_ends else None,
                "last_chunk_end": chunk_ends[-1].strftime("%Y-%m-%d") if chunk_ends else None,
            },
            "notes": [
                "Dry-run does not execute per-chunk sweep commands or write rollup/report files.",
            ],
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = Path(args.rollup_report)
    rollup_path.parent.mkdir(parents=True, exist_ok=True)

    chunk_ends = _chunk_end_dates(end_date, args.total_days_back, args.chunk_days)
    rollup: dict[str, object] = {
        "started_at": _utc_now(),
        "settings": {
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_days_back": args.total_days_back,
            "chunk_days": args.chunk_days,
            "fallback_max_tickers": args.fallback_max_tickers,
            "ticker_universe_file": args.ticker_universe_file,
            "download_existing_missing": bool(args.download_existing_missing),
            "process_documents": bool(args.process_documents),
            "narrative_policy": args.narrative_policy,
            "request_delay_ms": args.request_delay_ms,
            "request_jitter_ms": args.request_jitter_ms,
            "failure_backoff_ms": args.failure_backoff_ms,
            "max_consecutive_failures": args.max_consecutive_failures,
            "max_errors": args.max_errors,
            "stop_after_empty_days": args.stop_after_empty_days,
        },
        "chunks": [],
        "totals": {
            "discovered": 0,
            "inserted": 0,
            "existing_missing_recovered": 0,
            "downloaded": 0,
            "processed": 0,
            "process_errors": 0,
            "errors": 0,
            "classified": 0,
        },
        "status": "success",
    }

    for index, chunk_end in enumerate(chunk_ends, start=1):
        stamp = chunk_end.strftime("%Y%m%d")
        report_path = reports_dir / f"asx_enrichment_chunk_{index:03d}_{stamp}.json"
        cmd = [
            args.python,
            str(SWEEP_SCRIPT),
            "--end-date",
            chunk_end.strftime("%Y-%m-%d"),
            "--days-back",
            str(args.chunk_days),
            "--fallback-max-tickers",
            str(args.fallback_max_tickers),
            "--ticker-universe-file",
            args.ticker_universe_file,
            "--request-delay-ms",
            str(args.request_delay_ms),
            "--request-jitter-ms",
            str(args.request_jitter_ms),
            "--failure-backoff-ms",
            str(args.failure_backoff_ms),
            "--max-consecutive-failures",
            str(args.max_consecutive_failures),
            "--max-errors",
            str(args.max_errors),
            "--stop-after-empty-days",
            str(args.stop_after_empty_days),
            "--report",
            str(report_path),
        ]
        if args.download_existing_missing:
            cmd.append("--download-existing-missing")
        if args.process_documents:
            cmd.append("--process-documents")
            cmd.extend(["--narrative-policy", args.narrative_policy])

        print(f"[chunked] chunk={index}/{len(chunk_ends)} end={chunk_end.strftime('%Y-%m-%d')}", flush=True)
        completed = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
        chunk_payload: dict[str, object] = {
            "index": index,
            "end_date": chunk_end.strftime("%Y-%m-%d"),
            "report": str(report_path),
            "returncode": int(completed.returncode),
        }
        if report_path.exists():
            try:
                parsed = json.loads(report_path.read_text(encoding="utf-8"))
                chunk_payload["status"] = parsed.get("status")
                chunk_payload["totals"] = parsed.get("totals", {})
                totals = parsed.get("totals", {})
                for key in rollup["totals"]:
                    rollup["totals"][key] = int(rollup["totals"][key]) + int(totals.get(key, 0))
            except Exception as exc:
                chunk_payload["report_load_error"] = str(exc)
        else:
            chunk_payload["report_missing"] = True

        rollup["chunks"].append(chunk_payload)
        if completed.returncode != 0:
            rollup["status"] = "partial_failure"

        rollup_path.write_text(json.dumps(rollup, indent=2), encoding="utf-8")

    rollup["ended_at"] = _utc_now()
    rollup_path.write_text(json.dumps(rollup, indent=2), encoding="utf-8")
    print(f"[chunked] status={rollup['status']} rollup={rollup_path}", flush=True)
    if rollup["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
