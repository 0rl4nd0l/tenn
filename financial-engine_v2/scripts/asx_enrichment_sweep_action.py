#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.providers.asx_provider import ASXProvider  # noqa: E402
from app.providers.universe import ASX20  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.services.announcement_importance import classify_documents_and_materialize  # noqa: E402
from app.services.pipeline import download_pdf_for_document, insert_discovered_documents, process_document  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise SystemExit(f"Invalid --end-date '{raw}', expected YYYY-MM-DD") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk ASX enrichment sweep: ingest many days of all-announcements, download PDFs, and classify/sort."
    )
    parser.add_argument(
        "--end-date",
        default="",
        help="Sweep ending day in YYYY-MM-DD (default: today UTC).",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="How many days back to sweep including end-date.",
    )
    parser.add_argument(
        "--max-new-docs",
        type=int,
        default=0,
        help="Stop after this many new inserted docs (0 = no cap).",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=100,
        help="Stop if processing errors exceed this count.",
    )
    parser.add_argument(
        "--stop-after-empty-days",
        type=int,
        default=10,
        help="Early stop after this many consecutive days with 0 inserts (0 = disabled).",
    )
    parser.add_argument(
        "--fallback-max-tickers",
        type=int,
        default=1000,
        help="When daily-all discovery is empty, try up to this many tickers for historical per-ticker discovery.",
    )
    parser.add_argument(
        "--ticker-universe-file",
        default=str(REPO_ROOT / "data" / "raw" / "asx_ticker_universe.txt"),
        help="Optional newline/comma-separated ticker universe file to widen historical discovery coverage.",
    )
    parser.add_argument(
        "--no-historical-fallback",
        action="store_true",
        help="Disable historical per-ticker fallback when daily-all discovery is empty.",
    )
    parser.add_argument(
        "--request-delay-ms",
        type=int,
        default=300,
        help="Base delay between historical per-ticker requests (ms).",
    )
    parser.add_argument(
        "--request-jitter-ms",
        type=int,
        default=350,
        help="Random additional delay per request (0..N ms).",
    )
    parser.add_argument(
        "--failure-backoff-ms",
        type=int,
        default=1200,
        help="Base backoff delay after ticker fetch failure (ms, exponential by streak).",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=50,
        help="Stop historical ticker sweep for the day after this many consecutive failures (0 = disabled).",
    )
    parser.add_argument(
        "--no-skip-complete-ticker-days",
        action="store_true",
        help="Do not skip ticker/day probes already fully ingested for that day.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Discover/insert only, no PDF download.",
    )
    parser.add_argument(
        "--download-existing-missing",
        action="store_true",
        help="Also download/process discovered records already in DB if local PDF is missing.",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Run extraction/financial parsing after successful download.",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Keep embeddings enabled during --process-documents (default sweep behavior disables embeddings).",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "asx" / "asx_enrichment_sweep_report.json"),
        help="Output summary report path.",
    )
    return parser.parse_args()


def _load_marketindex_tickers() -> list[str]:
    path = REPO_ROOT / "data" / "raw" / "marketindex_announcements.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("announcements", []) if isinstance(payload, dict) else []
    tickers: list[str] = []
    seen: set[str] = set()
    for row in rows:
        ticker = str((row or {}).get("ticker", "")).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tickers


def _load_tickers_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    tickers: list[str] = []
    seen: set[str] = set()
    for raw in text.replace(",", "\n").splitlines():
        token = raw.strip().upper()
        if not token or token in seen:
            continue
        if not token.isalnum() or len(token) < 2 or len(token) > 6:
            continue
        seen.add(token)
        tickers.append(token)
    return tickers


def _build_ticker_universe(db, limit: int, universe_file: Path | None = None) -> list[str]:
    universe: list[str] = []
    seen: set[str] = set()

    def _add_many(items: list[str]) -> None:
        for raw in items:
            ticker = str(raw or "").strip().upper()
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            universe.append(ticker)
            if limit > 0 and len(universe) >= limit:
                return

    # Priority: explicit universe file, recent broad feed universe, known DB universe, then ASX20 seed.
    if universe_file is not None:
        _add_many(_load_tickers_from_file(universe_file))
    _add_many(_load_marketindex_tickers())
    if limit <= 0 or len(universe) < limit:
        rows = db.query(Document.ticker).distinct().all()
        _add_many([r[0] for r in rows if r and r[0]])
    if limit <= 0 or len(universe) < limit:
        _add_many(ASX20)

    return universe[:limit] if limit > 0 else universe


def _discover_historical_by_ticker(
    provider: ASXProvider,
    *,
    tickers: list[str],
    target_day: datetime,
    request_delay_ms: int = 0,
    request_jitter_ms: int = 0,
    failure_backoff_ms: int = 0,
    max_consecutive_failures: int = 0,
    skip_tickers: set[str] | None = None,
) -> tuple[list, int, int, int]:
    start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
    end = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
    discovered = []
    attempted = 0
    failed = 0
    skipped = 0
    consecutive_failures = 0
    seen_urls: set[str] = set()
    for ticker in tickers:
        if skip_tickers and ticker in skip_tickers:
            skipped += 1
            continue
        attempted += 1
        try:
            rows = provider.discover(ticker=ticker, start=start, end=end)
            consecutive_failures = 0
        except Exception:
            failed += 1
            consecutive_failures += 1
            if failure_backoff_ms > 0:
                backoff = failure_backoff_ms * max(1, min(consecutive_failures, 6))
                time.sleep(backoff / 1000.0)
            if max_consecutive_failures > 0 and consecutive_failures >= max_consecutive_failures:
                break
            if request_delay_ms > 0 or request_jitter_ms > 0:
                base = max(0, request_delay_ms) / 1000.0
                jitter = random.uniform(0, max(0, request_jitter_ms) / 1000.0)
                time.sleep(base + jitter)
            continue
        for row in rows:
            if row.source_url in seen_urls:
                continue
            seen_urls.add(row.source_url)
            discovered.append(row)
        if request_delay_ms > 0 or request_jitter_ms > 0:
            base = max(0, request_delay_ms) / 1000.0
            jitter = random.uniform(0, max(0, request_jitter_ms) / 1000.0)
            time.sleep(base + jitter)
    return discovered, attempted, failed, skipped


def _complete_tickers_for_day(db, target_day: datetime) -> set[str]:
    day_start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    rows = (
        db.query(Document.ticker, Document.pdf_path, Document.pdf_sha256)
        .filter(Document.published_at >= day_start, Document.published_at < day_end)
        .all()
    )
    by_ticker: dict[str, dict[str, int]] = {}
    for ticker, pdf_path, pdf_sha256 in rows:
        t = str(ticker or "").strip().upper()
        if not t:
            continue
        slot = by_ticker.setdefault(t, {"total": 0, "missing": 0})
        slot["total"] += 1
        marker = (pdf_sha256 or "").strip().lower()
        has_file = bool(pdf_path and Path(pdf_path).exists())
        if not marker or marker.startswith("blocked_") or not has_file:
            slot["missing"] += 1
    return {t for t, counts in by_ticker.items() if counts["total"] > 0 and counts["missing"] == 0}


def main() -> None:
    args = parse_args()
    if args.days_back <= 0:
        raise SystemExit("--days-back must be > 0")
    if args.max_new_docs < 0:
        raise SystemExit("--max-new-docs must be >= 0")
    if args.max_errors < 0:
        raise SystemExit("--max-errors must be >= 0")
    if args.stop_after_empty_days < 0:
        raise SystemExit("--stop-after-empty-days must be >= 0")
    if args.fallback_max_tickers < 0:
        raise SystemExit("--fallback-max-tickers must be >= 0")
    if args.request_delay_ms < 0:
        raise SystemExit("--request-delay-ms must be >= 0")
    if args.request_jitter_ms < 0:
        raise SystemExit("--request-jitter-ms must be >= 0")
    if args.failure_backoff_ms < 0:
        raise SystemExit("--failure-backoff-ms must be >= 0")
    if args.max_consecutive_failures < 0:
        raise SystemExit("--max-consecutive-failures must be >= 0")

    end_day = _parse_date(args.end_date)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "settings": {
            "end_date": end_day.strftime("%Y-%m-%d"),
            "days_back": args.days_back,
            "max_new_docs": args.max_new_docs,
            "max_errors": args.max_errors,
            "stop_after_empty_days": args.stop_after_empty_days,
            "fallback_max_tickers": args.fallback_max_tickers,
            "ticker_universe_file": args.ticker_universe_file,
            "historical_fallback_enabled": not args.no_historical_fallback,
            "request_delay_ms": args.request_delay_ms,
            "request_jitter_ms": args.request_jitter_ms,
            "failure_backoff_ms": args.failure_backoff_ms,
            "max_consecutive_failures": args.max_consecutive_failures,
            "skip_complete_ticker_days": not args.no_skip_complete_ticker_days,
            "skip_download": args.skip_download,
            "download_existing_missing": args.download_existing_missing,
            "process_documents": args.process_documents,
            "with_embeddings": args.with_embeddings,
        },
        "totals": {
            "days_attempted": 0,
            "days_completed": 0,
            "discovered": 0,
            "inserted": 0,
            "existing_missing_recovered": 0,
            "downloaded": 0,
            "processed": 0,
            "process_errors": 0,
            "skipped_download": 0,
            "errors": 0,
            "classified": 0,
        },
        "days": [],
        "status": "success",
    }

    provider = ASXProvider()
    db = SessionLocal()
    consecutive_empty_days = 0
    stop_reason = ""

    try:
        if args.process_documents and not args.with_embeddings:
            settings.enable_embeddings = False
            settings.enable_qdrant = False
        for day_offset in range(args.days_back):
            target_day = (end_day - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
            summary["totals"]["days_attempted"] = int(summary["totals"]["days_attempted"]) + 1

            day_report: dict[str, object] = {
                "date": target_day.strftime("%Y-%m-%d"),
                "discovery_mode": "",
                "found": 0,
                "inserted": 0,
                "existing_missing_recovered": 0,
                "downloaded": 0,
                "processed": 0,
                "process_errors": 0,
                "skipped_download": 0,
                "fallback_used": False,
                "fallback_tickers_attempted": 0,
                "fallback_ticker_failures": 0,
                "fallback_ticker_skipped_complete": 0,
                "errors": [],
                "classification": None,
            }
            is_today = target_day.date() >= datetime.now(timezone.utc).date()
            discovered = []

            # Historical mode: use robust per-ticker ASX discovery path, not daily-all endpoint.
            if not is_today and not args.no_historical_fallback and args.fallback_max_tickers > 0:
                tickers = _build_ticker_universe(
                    db,
                    args.fallback_max_tickers,
                    universe_file=Path(args.ticker_universe_file) if args.ticker_universe_file else None,
                )
                completed = _complete_tickers_for_day(db, target_day) if not args.no_skip_complete_ticker_days else set()
                discovered, attempted, failed, skipped = _discover_historical_by_ticker(
                    provider,
                    tickers=tickers,
                    target_day=target_day,
                    request_delay_ms=args.request_delay_ms,
                    request_jitter_ms=args.request_jitter_ms,
                    failure_backoff_ms=args.failure_backoff_ms,
                    max_consecutive_failures=args.max_consecutive_failures,
                    skip_tickers=completed,
                )
                day_report["discovery_mode"] = "historical_ticker"
                day_report["fallback_used"] = True
                day_report["fallback_tickers_attempted"] = attempted
                day_report["fallback_ticker_failures"] = failed
                day_report["fallback_ticker_skipped_complete"] = skipped
            else:
                discovered = provider.discover_daily_all(day=target_day)
                day_report["discovery_mode"] = "daily_all"
                if not discovered and is_today and not args.no_historical_fallback and args.fallback_max_tickers > 0:
                    tickers = _build_ticker_universe(
                        db,
                        args.fallback_max_tickers,
                        universe_file=Path(args.ticker_universe_file) if args.ticker_universe_file else None,
                    )
                    completed = _complete_tickers_for_day(db, target_day) if not args.no_skip_complete_ticker_days else set()
                    discovered, attempted, failed, skipped = _discover_historical_by_ticker(
                        provider,
                        tickers=tickers,
                        target_day=target_day,
                        request_delay_ms=args.request_delay_ms,
                        request_jitter_ms=args.request_jitter_ms,
                        failure_backoff_ms=args.failure_backoff_ms,
                        max_consecutive_failures=args.max_consecutive_failures,
                        skip_tickers=completed,
                    )
                    day_report["discovery_mode"] = "daily_all_then_historical_ticker"
                    day_report["fallback_used"] = True
                    day_report["fallback_tickers_attempted"] = attempted
                    day_report["fallback_ticker_failures"] = failed
                    day_report["fallback_ticker_skipped_complete"] = skipped
            day_report["found"] = len(discovered)
            summary["totals"]["discovered"] = int(summary["totals"]["discovered"]) + len(discovered)

            inserted = insert_discovered_documents(db, discovered)
            new_document_ids = inserted["new_document_ids"]
            day_report["inserted"] = int(inserted["inserted"])
            summary["totals"]["inserted"] = int(summary["totals"]["inserted"]) + int(inserted["inserted"])

            process_document_ids = list(new_document_ids)
            if args.download_existing_missing and discovered:
                discovered_urls = list({d.source_url for d in discovered if d.source_url})
                if discovered_urls:
                    rows = (
                        db.query(Document.document_id, Document.pdf_path, Document.pdf_sha256)
                        .filter(Document.source_url.in_(discovered_urls))
                        .all()
                    )
                    new_id_set = {str(x) for x in new_document_ids}
                    for doc_id, pdf_path, pdf_sha256 in rows:
                        doc_id_s = str(doc_id)
                        if doc_id_s in new_id_set:
                            continue
                        marker = (pdf_sha256 or "").strip()
                        has_file = bool(pdf_path and Path(pdf_path).exists())
                        if marker and has_file and not marker.lower().startswith("blocked_"):
                            continue
                        process_document_ids.append(doc_id_s)
                        day_report["existing_missing_recovered"] = int(day_report["existing_missing_recovered"]) + 1
                summary["totals"]["existing_missing_recovered"] = (
                    int(summary["totals"]["existing_missing_recovered"])
                    + int(day_report["existing_missing_recovered"])
                )

            if int(inserted["inserted"]) == 0:
                consecutive_empty_days += 1
            else:
                consecutive_empty_days = 0

            if not args.skip_download:
                for document_id in process_document_ids:
                    try:
                        download_pdf_for_document(db, document_id)
                        day_report["downloaded"] = int(day_report["downloaded"]) + 1
                        summary["totals"]["downloaded"] = int(summary["totals"]["downloaded"]) + 1
                        day_report["processed"] = int(day_report["processed"]) + 1
                        summary["totals"]["processed"] = int(summary["totals"]["processed"]) + 1
                        if args.process_documents:
                            try:
                                result = process_document(document_id)
                                if str(result.get("extraction_status", "")).lower() == "failed":
                                    day_report["process_errors"] = int(day_report["process_errors"]) + 1
                                    summary["totals"]["process_errors"] = int(summary["totals"]["process_errors"]) + 1
                                    day_report["errors"].append(
                                        {"document_id": document_id, "error": "process_document_extraction_failed"}
                                    )
                                    summary["totals"]["errors"] = int(summary["totals"]["errors"]) + 1
                            except Exception as proc_exc:
                                day_report["process_errors"] = int(day_report["process_errors"]) + 1
                                summary["totals"]["process_errors"] = int(summary["totals"]["process_errors"]) + 1
                                day_report["errors"].append({"document_id": document_id, "error": f"process_document_error: {proc_exc}"})
                                summary["totals"]["errors"] = int(summary["totals"]["errors"]) + 1
                    except RuntimeError as exc:
                        if "marketindex_headed_required" in str(exc):
                            day_report["skipped_download"] = int(day_report["skipped_download"]) + 1
                            summary["totals"]["skipped_download"] = int(summary["totals"]["skipped_download"]) + 1
                            continue
                        db.rollback()
                        day_report["errors"].append({"document_id": document_id, "error": str(exc)})
                        summary["totals"]["errors"] = int(summary["totals"]["errors"]) + 1
                    except httpx.HTTPStatusError as exc:
                        db.rollback()
                        day_report["errors"].append({"document_id": document_id, "error": str(exc)})
                        summary["totals"]["errors"] = int(summary["totals"]["errors"]) + 1
                    except Exception as exc:
                        db.rollback()
                        day_report["errors"].append({"document_id": document_id, "error": str(exc)})
                        summary["totals"]["errors"] = int(summary["totals"]["errors"]) + 1

            if settings.enable_importance_classification and new_document_ids:
                try:
                    result = classify_documents_and_materialize(
                        db,
                        document_ids=new_document_ids,
                        output_root=settings.importance_output_root,
                        materialize_output=settings.importance_materialize_output,
                        include_pdf_text=settings.importance_include_pdf_text,
                        link_mode=settings.importance_link_mode,
                        sort_source_docs=settings.importance_sort_source_docs,
                    )
                    day_report["classification"] = result
                    summary["totals"]["classified"] = int(summary["totals"]["classified"]) + int(result.get("classified_count", 0))
                except Exception as exc:
                    day_report["classification"] = {"error": str(exc)}

            summary["days"].append(day_report)
            summary["totals"]["days_completed"] = int(summary["totals"]["days_completed"]) + 1

            print(
                "[asx_sweep] "
                f"date={day_report['date']} mode={day_report['discovery_mode']} "
                f"found={day_report['found']} inserted={day_report['inserted']} "
                f"recovered={day_report['existing_missing_recovered']} "
                f"downloaded={day_report['downloaded']} processed={day_report['processed']} "
                f"process_errors={day_report['process_errors']} errors={len(day_report['errors'])}",
                flush=True,
            )

            if args.max_new_docs > 0 and int(summary["totals"]["inserted"]) >= args.max_new_docs:
                stop_reason = f"max_new_docs_reached:{args.max_new_docs}"
                break
            if args.max_errors > 0 and int(summary["totals"]["errors"]) >= args.max_errors:
                stop_reason = f"max_errors_reached:{args.max_errors}"
                summary["status"] = "partial_failure"
                break
            if args.stop_after_empty_days > 0 and consecutive_empty_days >= args.stop_after_empty_days:
                stop_reason = f"consecutive_empty_days:{consecutive_empty_days}"
                break
    finally:
        db.close()

    summary["ended_at"] = _utc_now()
    summary["stop_reason"] = stop_reason or "completed_requested_window"
    if int(summary["totals"]["errors"]) > 0 and summary["status"] == "success":
        summary["status"] = "partial_failure"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        "[asx_sweep] "
        f"days_completed={summary['totals']['days_completed']} "
        f"inserted={summary['totals']['inserted']} "
        f"downloaded={summary['totals']['downloaded']} "
        f"processed={summary['totals']['processed']} "
        f"process_errors={summary['totals']['process_errors']} "
        f"classified={summary['totals']['classified']} "
        f"errors={summary['totals']['errors']} "
        f"report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
