#!/usr/bin/env python3
import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from _run_metadata import build_run_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))
ROOT_SCRIPTS = REPO_ROOT.parent / "scripts"
if str(ROOT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ROOT_SCRIPTS))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models import Document  # noqa: E402
from app.providers.universe import ASX20  # noqa: E402
from app.services.pipeline import backfill_ticker_sync  # noqa: E402
from health_guard import assert_healthy, load_health_snapshot  # noqa: E402
from ticker_quarantine import add_to_quarantine, load_quarantine  # noqa: E402

# Set by signal handler when user stops the script (Ctrl+C / SIGTERM). Checked in main loop.
_interrupt_requested = False


def _handle_interrupt(_signum, _frame):
    global _interrupt_requested
    _interrupt_requested = True


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


def _load_tickers_from_file(path: Path):
    if not path.exists():
        raise SystemExit(f"Ticker universe file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    tokens = []
    for line in raw.splitlines():
        part = line.split("#", 1)[0]
        tokens.extend(part.split(","))
    cleaned = []
    seen = set()
    for token in tokens:
        ticker = token.strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        cleaned.append(ticker)
    return cleaned


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _build_child_backend_env() -> dict[str, str]:
    """Keep child scripts on the same backend runtime config as the parent process."""
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"backend{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "backend"
    )
    env.setdefault("DATABASE_URL", str(settings.database_url))
    env.setdefault("DATA_ROOT", str(settings.data_root))
    env.setdefault("DOCS_ROOT", str(settings.docs_root))
    return env


def _document_count_for_ticker(ticker: str) -> int:
    """Return number of documents in DB for this ticker (for skip-complete logic)."""
    db = SessionLocal()
    try:
        return db.query(Document).filter(Document.ticker == ticker.upper()).count()
    finally:
        db.close()


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
        "--asx20",
        action="store_true",
        help="Use ASX20 universe when --ticker is not provided.",
    )
    parser.add_argument(
        "--ticker-universe-file",
        default="",
        help="Optional newline/comma-separated ticker universe file.",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=0,
        help="Optional cap for loaded tickers (0 = all).",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=5.0,
        help="History window in years for discovery (use for bulk long-term backfill).",
    )
    parser.add_argument(
        "--months",
        type=float,
        default=None,
        help="If set, use this many months for discovery instead of --years (e.g. 3 for recent updater).",
    )
    parser.add_argument(
        "--skip-complete",
        action="store_true",
        help="(Bulk mode) Skip tickers that already have at least --min-docs-to-skip documents in DB.",
    )
    parser.add_argument(
        "--min-docs-to-skip",
        type=int,
        default=50,
        help="When --skip-complete: tickers with this many or more documents are skipped (default 50).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Max parallel documents per ticker for download+process (1=sequential; 2–4 recommended).",
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
        "--ticker-delay-seconds",
        type=float,
        default=1.5,
        help="Base delay between tickers to reduce request burstiness.",
    )
    parser.add_argument(
        "--ticker-delay-jitter-seconds",
        type=float,
        default=1.0,
        help="Random extra delay [0..jitter] between tickers.",
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
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for child scripts.",
    )
    parser.add_argument(
        "--audit-extraction-backlog",
        action="store_true",
        help="After sync/resume, run extraction backlog audit + failure taxonomy reports.",
    )
    parser.add_argument(
        "--health-json",
        default=str(REPO_ROOT.parent / "reports" / "research_engine_health.json"),
        help="Health snapshot JSON path used for pre-run gating.",
    )
    parser.add_argument(
        "--allow-warning",
        action="store_true",
        help="Allow execution when health snapshot overall_status=warning.",
    )
    parser.add_argument(
        "--no-quarantine",
        action="store_true",
        help="Disable ticker quarantine: do not exclude quarantined tickers, and do not add new ones (no_announcements_no_existing_docs).",
    )
    return parser


def main():
    args = build_parser().parse_args()

    tickers = _parse_tickers(args.ticker)
    used_universe_file = False
    if args.ticker_universe_file:
        tickers = _load_tickers_from_file(Path(args.ticker_universe_file))
        used_universe_file = True
        if not args.no_quarantine:
            quarantine = load_quarantine(REPO_ROOT)
        else:
            quarantine = set()
        if quarantine:
            excluded_list = [t for t in tickers if t.upper() in quarantine]
            tickers = [t for t in tickers if t.upper() not in quarantine]
            if excluded_list:
                sample = sorted(excluded_list)[:15]
                print(f"[quarantine] excluding {len(excluded_list)} ticker(s) (no announcements, no existing docs): {sample}{'...' if len(excluded_list) > 15 else ''}", flush=True)
    if not tickers and args.asx10:
        tickers = ASX20[:10]
    if not tickers and args.asx20:
        tickers = list(ASX20)
    if not tickers:
        raise SystemExit("No tickers provided. Use --ticker, --ticker-universe-file, --asx10, or --asx20.")
    if args.max_tickers < 0:
        raise SystemExit("--max-tickers must be >= 0")
    if args.max_tickers > 0:
        tickers = tickers[: args.max_tickers]
    years_effective = (args.months / 12.0) if args.months is not None else float(args.years)
    if years_effective <= 0:
        raise SystemExit("--years or --months must be > 0")
    if args.max_backfill_retries <= 0:
        raise SystemExit("--max-backfill-retries must be > 0")
    if args.ticker_delay_seconds < 0:
        raise SystemExit("--ticker-delay-seconds must be >= 0")
    if args.ticker_delay_jitter_seconds < 0:
        raise SystemExit("--ticker-delay-jitter-seconds must be >= 0")

    if args.dry_run:
        resume_cmd = None
        if not args.no_resume_pending:
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
            "script": "full_history_ticker_sync",
            "settings": {
                "tickers_total": len(tickers),
                "tickers_sample": tickers[:25],
                "years_effective": years_effective,
                "skip_complete": args.skip_complete,
                "min_docs_to_skip": args.min_docs_to_skip,
                "process_documents": bool(args.process_documents),
                "max_backfill_retries": args.max_backfill_retries,
                "ticker_delay_seconds": args.ticker_delay_seconds,
                "ticker_delay_jitter_seconds": args.ticker_delay_jitter_seconds,
                "resume_pending": not args.no_resume_pending,
                "resume_max_retries": args.resume_max_retries,
                "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
                "audit_extraction_backlog": bool(args.audit_extraction_backlog),
                "report": str(args.report),
            },
            "resume_command": resume_cmd,
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    snapshot = load_health_snapshot(str(args.health_json))
    assert_healthy(snapshot, allow_warning=bool(args.allow_warning))

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "started_at": _utc_now(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "settings": {
            "tickers": tickers,
            "years_effective": years_effective,
            "skip_complete": args.skip_complete,
            "min_docs_to_skip": args.min_docs_to_skip,
            "concurrency": max(1, int(args.concurrency)),
            "process_documents": args.process_documents,
            "max_backfill_retries": args.max_backfill_retries,
            "ticker_delay_seconds": args.ticker_delay_seconds,
            "ticker_delay_jitter_seconds": args.ticker_delay_jitter_seconds,
            "resume_pending": not args.no_resume_pending,
            "resume_max_retries": args.resume_max_retries,
            "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
            "audit_extraction_backlog": bool(args.audit_extraction_backlog),
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
        "post_reports": {},
    }

    backfill_failed = False
    interrupted_by_signal = False
    total_tickers = len(tickers)
    signal.signal(signal.SIGINT, _handle_interrupt)
    signal.signal(signal.SIGTERM, _handle_interrupt)
    for index, ticker in enumerate(tickers, start=1):
        if _interrupt_requested:
            interrupted_by_signal = True
            print("[interrupt] stopping after current run; will write report and run quarantine.", flush=True)
            break
        print(f"[progress] ticker_index={index}/{total_tickers} ticker={ticker}", flush=True)
        if args.skip_complete:
            doc_count = _document_count_for_ticker(ticker)
            if doc_count >= args.min_docs_to_skip:
                summary["backfill"]["results"].append({
                    "ticker": ticker,
                    "skipped_complete": True,
                    "existing_doc_count": doc_count,
                    "found": 0,
                    "inserted": 0,
                    "processed": 0,
                    "skipped_download": 0,
                })
                print(f"[backfill] {ticker} skipped (already complete: {doc_count} docs >= {args.min_docs_to_skip})", flush=True)
                delay = args.ticker_delay_seconds + (random.random() * args.ticker_delay_jitter_seconds)
                if delay > 0:
                    time.sleep(delay)
                continue
        ticker_done = False
        for attempt in range(1, args.max_backfill_retries + 1):
            try:
                print(f"[backfill] {ticker} attempt {attempt}", flush=True)
                result = backfill_ticker_sync(
                    ticker=ticker,
                    years=years_effective,
                    process_documents=args.process_documents,
                    max_workers=max(1, int(args.concurrency)),
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
                    f"errors={result.get('error_count')} "
                    f"importance_classified={((result.get('importance_classification') or {}).get('classified_count', 0))}",
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
        delay = args.ticker_delay_seconds + (random.random() * args.ticker_delay_jitter_seconds)
        if delay > 0:
            time.sleep(delay)

    resume_rc = 0
    if not interrupted_by_signal and not args.no_resume_pending:
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

        env = _build_child_backend_env()

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

    if not interrupted_by_signal and args.audit_extraction_backlog:
        backlog_audit_path = report_path.with_name(f"{report_path.stem}_extraction_backlog_audit.json")
        taxonomy_path = report_path.with_name(f"{report_path.stem}_extraction_failure_taxonomy.json")
        audit_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "audit_extraction_backlog.py"),
            "--out-json",
            str(backlog_audit_path),
        ]
        classify_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "classify_extraction_failures.py"),
            "--out-json",
            str(taxonomy_path),
        ]
        env = _build_child_backend_env()

        print(f"[post] running: {' '.join(audit_cmd)}", flush=True)
        audit_run = subprocess.run(audit_cmd, cwd=str(REPO_ROOT), env=env, check=False)
        print(f"[post] running: {' '.join(classify_cmd)}", flush=True)
        classify_run = subprocess.run(classify_cmd, cwd=str(REPO_ROOT), env=env, check=False)
        summary["post_reports"] = {
            "extraction_backlog_audit": {
                "returncode": int(audit_run.returncode),
                "report_path": str(backlog_audit_path),
            },
            "extraction_failure_taxonomy": {
                "returncode": int(classify_run.returncode),
                "report_path": str(taxonomy_path),
            },
        }
        if int(audit_run.returncode) != 0 or int(classify_run.returncode) != 0:
            backfill_failed = True

    summary["ended_at"] = _utc_now()
    if interrupted_by_signal:
        summary["status"] = "interrupted"
    else:
        summary["status"] = "success" if not backfill_failed and resume_rc == 0 else "failed"

    # Quarantine: when run used universe file and (succeeded or interrupted), and at least one ticker had data
    if used_universe_file and summary["status"] in ("success", "interrupted") and not args.no_quarantine:
        results = summary.get("backfill", {}).get("results") or []
        any_had_found = any(
            r.get("found", 0) > 0 and not r.get("failed")
            for r in results
        )
        if any_had_found:
            candidates = [
                r.get("ticker")
                for r in results
                if not r.get("failed")
                and r.get("found", -1) == 0
                and r.get("existing_doc_count", -1) == 0
                and r.get("ticker")
            ]
            if candidates:
                newly = add_to_quarantine(REPO_ROOT, candidates)
                if newly:
                    print(f"[quarantine] added {len(newly)} ticker(s) (no announcements, no existing docs): {sorted(newly)}", flush=True)
                    summary["quarantine_added"] = newly

    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[summary] status={summary['status']} report={report_path}")

    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
