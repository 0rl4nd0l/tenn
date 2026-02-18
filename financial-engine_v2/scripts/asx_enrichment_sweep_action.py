#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
        "--no-historical-fallback",
        action="store_true",
        help="Disable historical per-ticker fallback when daily-all discovery is empty.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Discover/insert only, no PDF download.",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Run extraction/financial parsing after successful download.",
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


def _build_ticker_universe(db, limit: int) -> list[str]:
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

    # Priority: recent broad feed universe, then known DB universe, then ASX20 seed.
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
) -> tuple[list, int]:
    start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
    end = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
    discovered = []
    attempted = 0
    seen_urls: set[str] = set()
    for ticker in tickers:
        attempted += 1
        try:
            rows = provider.discover(ticker=ticker, start=start, end=end)
        except Exception:
            continue
        for row in rows:
            if row.source_url in seen_urls:
                continue
            seen_urls.add(row.source_url)
            discovered.append(row)
    return discovered, attempted


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
            "historical_fallback_enabled": not args.no_historical_fallback,
            "skip_download": args.skip_download,
            "process_documents": args.process_documents,
        },
        "totals": {
            "days_attempted": 0,
            "days_completed": 0,
            "discovered": 0,
            "inserted": 0,
            "processed": 0,
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
        for day_offset in range(args.days_back):
            target_day = (end_day - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
            summary["totals"]["days_attempted"] = int(summary["totals"]["days_attempted"]) + 1

            day_report: dict[str, object] = {
                "date": target_day.strftime("%Y-%m-%d"),
                "discovery_mode": "",
                "found": 0,
                "inserted": 0,
                "processed": 0,
                "skipped_download": 0,
                "fallback_used": False,
                "fallback_tickers_attempted": 0,
                "errors": [],
                "classification": None,
            }
            is_today = target_day.date() >= datetime.now(timezone.utc).date()
            discovered = []

            # Historical mode: use robust per-ticker ASX discovery path, not daily-all endpoint.
            if not is_today and not args.no_historical_fallback and args.fallback_max_tickers > 0:
                tickers = _build_ticker_universe(db, args.fallback_max_tickers)
                discovered, attempted = _discover_historical_by_ticker(
                    provider,
                    tickers=tickers,
                    target_day=target_day,
                )
                day_report["discovery_mode"] = "historical_ticker"
                day_report["fallback_used"] = True
                day_report["fallback_tickers_attempted"] = attempted
            else:
                discovered = provider.discover_daily_all(day=target_day)
                day_report["discovery_mode"] = "daily_all"
                if not discovered and is_today and not args.no_historical_fallback and args.fallback_max_tickers > 0:
                    tickers = _build_ticker_universe(db, args.fallback_max_tickers)
                    discovered, attempted = _discover_historical_by_ticker(
                        provider,
                        tickers=tickers,
                        target_day=target_day,
                    )
                    day_report["discovery_mode"] = "daily_all_then_historical_ticker"
                    day_report["fallback_used"] = True
                    day_report["fallback_tickers_attempted"] = attempted
            day_report["found"] = len(discovered)
            summary["totals"]["discovered"] = int(summary["totals"]["discovered"]) + len(discovered)

            inserted = insert_discovered_documents(db, discovered)
            new_document_ids = inserted["new_document_ids"]
            day_report["inserted"] = int(inserted["inserted"])
            summary["totals"]["inserted"] = int(summary["totals"]["inserted"]) + int(inserted["inserted"])

            if int(inserted["inserted"]) == 0:
                consecutive_empty_days += 1
            else:
                consecutive_empty_days = 0

            if not args.skip_download:
                for document_id in new_document_ids:
                    try:
                        download_pdf_for_document(db, document_id)
                        if args.process_documents:
                            process_document(document_id)
                        day_report["processed"] = int(day_report["processed"]) + 1
                        summary["totals"]["processed"] = int(summary["totals"]["processed"]) + 1
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
                f"processed={day_report['processed']} errors={len(day_report['errors'])}",
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
        f"processed={summary['totals']['processed']} "
        f"classified={summary['totals']['classified']} "
        f"errors={summary['totals']['errors']} "
        f"report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
