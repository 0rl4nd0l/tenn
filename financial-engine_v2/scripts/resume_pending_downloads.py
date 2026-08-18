#!/usr/bin/env python3
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import or_

from _run_metadata import build_run_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.providers.universe import ASX20  # noqa: E402
from app.services.announcement_importance import classify_documents_and_materialize  # noqa: E402
from app.services.pipeline import download_pdf_for_document, process_document  # noqa: E402
from marketindex_recovery_reporting import (  # noqa: E402
    MARKETINDEX_HEADED_RECOVERY_MARKERS,
    add_marketindex_recovery_blocker,
    build_marketindex_recovery_summary,
)


def _parse_tickers(values):
    if not values:
        return []
    tickers = []
    for raw in values:
        for token in raw.split(","):
            token = token.strip().upper()
            if token:
                tickers.append(token)
    deduped = []
    seen = set()
    for ticker in tickers:
        if ticker in seen:
            continue
        seen.add(ticker)
        deduped.append(ticker)
    return deduped


def _summarize_marketindex_headed_recovery_rows(rows, tickers) -> dict:
    summary = build_marketindex_recovery_summary(tickers)
    for row in rows or []:
        add_marketindex_recovery_blocker(
            summary,
            ticker=getattr(row, "ticker", ""),
            marker=getattr(row, "pdf_sha256", ""),
            document_id=getattr(row, "document_id", ""),
            source_url=getattr(row, "source_url", ""),
            stage="existing_blocker",
        )
    return summary


def _load_existing_marketindex_recovery_summary(db, tickers) -> dict:
    summary = build_marketindex_recovery_summary(tickers)
    try:
        query = (
            db.query(Document)
            .filter(Document.ticker.in_(_parse_tickers(tickers)))
            .filter(Document.pdf_sha256.in_(list(MARKETINDEX_HEADED_RECOVERY_MARKERS)))
            .filter(Document.source_url.ilike("%marketindex.com.au%"))
            .order_by(Document.published_at.desc().nullslast())
        )
        return _summarize_marketindex_headed_recovery_rows(query.all(), tickers)
    except Exception as exc:
        summary["query_error"] = str(exc)
        return summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resume downloads for existing documents with empty pdf_sha256."
    )
    parser.add_argument(
        "--ticker",
        action="append",
        help="Optional ticker filter. Repeat or pass comma-separated values. Defaults to ASX10.",
    )
    parser.add_argument(
        "--limit-per-ticker",
        type=int,
        default=0,
        help="Max pending rows per ticker to process (0 = no limit).",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Also run extraction/chunking processing after successful download.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "resume_pending_downloads_report.json"),
        help="Report JSON output path.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Max attempts per document for retryable network failures.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=2.0,
        help="Base delay between retries for retryable network failures.",
    )
    parser.add_argument(
        "--skip-importance-classification",
        action="store_true",
        help="Disable post-ingestion importance folder classification step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = _parse_tickers(args.ticker) or ASX20[:10]
    if getattr(args, "dry_run", False):
        pending_by_ticker: dict[str, int] = {}
        marketindex_summary = build_marketindex_recovery_summary(tickers)
        db = SessionLocal()
        try:
            for ticker in tickers:
                query = (
                    db.query(Document)
                    .filter(Document.ticker == ticker)
                    .filter(or_(Document.pdf_sha256 == "", Document.pdf_sha256.is_(None)))
                    .order_by(Document.published_at.desc().nullslast())
                )
                if args.limit_per_ticker and args.limit_per_ticker > 0:
                    query = query.limit(args.limit_per_ticker)
                pending_by_ticker[ticker] = int(query.count())
            marketindex_summary = _load_existing_marketindex_recovery_summary(db, tickers)
        finally:
            db.close()

        plan = {
            "dry_run": True,
            "script": "resume_pending_downloads",
            "settings": {
                "tickers_total": len(tickers),
                "tickers": tickers,
                "limit_per_ticker": args.limit_per_ticker,
                "process_documents": bool(args.process_documents),
                "max_retries": args.max_retries,
                "retry_delay_seconds": args.retry_delay_seconds,
                "skip_importance_classification": bool(args.skip_importance_classification),
                "report": str(args.report),
            },
            "estimates": {
                "pending_by_ticker": pending_by_ticker,
                "pending_total": sum(pending_by_ticker.values()),
            },
            "notes": [
                "Dry-run does not download PDFs, run extraction, classify docs, or write reports.",
            ],
            "marketindex_headed_recovery": marketindex_summary,
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    started = datetime.now(timezone.utc)
    report = {
        "started_at": started.isoformat(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "tickers": tickers,
        "process_documents": args.process_documents,
        "limit_per_ticker": args.limit_per_ticker,
        "results": [],
        "totals": {
            "pending_selected": 0,
            "processed": 0,
            "skipped_download": 0,
            "requires_headed_recovery_count": 0,
            "extraction_failed_count": 0,
            "errors": 0,
        },
        "marketindex_headed_recovery": build_marketindex_recovery_summary(tickers),
    }

    db = SessionLocal()
    try:
        report["marketindex_headed_recovery"] = _load_existing_marketindex_recovery_summary(db, tickers)
        for ticker in tickers:
            existing_marketindex_summary = _load_existing_marketindex_recovery_summary(db, [ticker])
            query = (
                db.query(Document)
                .filter(Document.ticker == ticker)
                .filter(or_(Document.pdf_sha256 == "", Document.pdf_sha256.is_(None)))
                .order_by(Document.published_at.desc().nullslast())
            )
            if args.limit_per_ticker and args.limit_per_ticker > 0:
                query = query.limit(args.limit_per_ticker)
            rows = query.all()
            dedup_rows = []
            seen_source_urls: set[str] = set()
            duplicate_source_rows = 0
            for row in rows:
                source_key = str(getattr(row, "source_url", "") or "").strip().lower()
                if source_key and source_key in seen_source_urls:
                    duplicate_source_rows += 1
                    continue
                if source_key:
                    seen_source_urls.add(source_key)
                dedup_rows.append(row)

            ticker_result = {
                "ticker": ticker,
                "pending_selected": len(dedup_rows),
                "pending_duplicate_source_rows_skipped": duplicate_source_rows,
                "processed": 0,
                "skipped_download": 0,
                "requires_headed_recovery_count": int(
                    existing_marketindex_summary.get("requires_headed_recovery_count") or 0
                ),
                "extraction_failed_count": 0,
                "errors": [],
                "importance_classification": None,
                "marketindex_headed_recovery": existing_marketindex_summary,
            }
            processed_document_ids: list[str] = []

            for row in dedup_rows:
                attempts = max(1, int(args.max_retries))
                last_error = None
                attempts_used = 0
                for attempt in range(1, attempts + 1):
                    attempts_used = attempt
                    try:
                        download_pdf_for_document(db, row.document_id)
                        if args.process_documents:
                            proc_result = process_document(row.document_id) or {}
                            if (proc_result.get("extraction_status") or "").strip().lower() == "failed":
                                ticker_result["extraction_failed_count"] += 1
                                ticker_result["errors"].append({
                                    "document_id": str(row.document_id),
                                    "stage": "process_document",
                                    "error": "extraction_failed",
                                    "extraction_status": proc_result.get("extraction_status"),
                                })
                        ticker_result["processed"] += 1
                        processed_document_ids.append(str(row.document_id))
                        last_error = None
                        break
                    except RuntimeError as exc:
                        if "marketindex_headed_required" in str(exc):
                            row.pdf_sha256 = "blocked_marketindex_headed_required"
                            db.commit()
                            ticker_result["skipped_download"] += 1
                            ticker_result["requires_headed_recovery_count"] += 1
                            add_marketindex_recovery_blocker(
                                ticker_result["marketindex_headed_recovery"],
                                ticker=ticker,
                                marker="blocked_marketindex_headed_required",
                                document_id=getattr(row, "document_id", ""),
                                source_url=getattr(row, "source_url", ""),
                                stage="download",
                            )
                            add_marketindex_recovery_blocker(
                                report["marketindex_headed_recovery"],
                                ticker=ticker,
                                marker="blocked_marketindex_headed_required",
                                document_id=getattr(row, "document_id", ""),
                                source_url=getattr(row, "source_url", ""),
                                stage="download",
                            )
                            last_error = None
                            break
                        db.rollback()
                        last_error = exc
                        break
                    except httpx.HTTPStatusError as exc:
                        request_url = str(exc.request.url)
                        if exc.response.status_code == 403 and "marketindex.com.au" in request_url:
                            row.pdf_sha256 = "blocked_marketindex_403"
                            db.commit()
                            ticker_result["skipped_download"] += 1
                            ticker_result["requires_headed_recovery_count"] += 1
                            add_marketindex_recovery_blocker(
                                ticker_result["marketindex_headed_recovery"],
                                ticker=ticker,
                                marker="blocked_marketindex_403",
                                document_id=getattr(row, "document_id", ""),
                                source_url=getattr(row, "source_url", "") or request_url,
                                stage="download",
                            )
                            add_marketindex_recovery_blocker(
                                report["marketindex_headed_recovery"],
                                ticker=ticker,
                                marker="blocked_marketindex_403",
                                document_id=getattr(row, "document_id", ""),
                                source_url=getattr(row, "source_url", "") or request_url,
                                stage="download",
                            )
                            last_error = None
                            break
                        db.rollback()
                        last_error = exc
                        break
                    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                        db.rollback()
                        last_error = exc
                        if attempt < attempts:
                            time.sleep(float(args.retry_delay_seconds) * attempt)
                            continue
                        break
                    except Exception as exc:
                        db.rollback()
                        last_error = exc
                        break

                if last_error is not None:
                    ticker_result["errors"].append(
                        {
                            "document_id": str(row.document_id),
                            "error": str(last_error),
                            "attempts": attempts_used,
                        }
                    )

            ticker_result["error_count"] = len(ticker_result["errors"])

            if not args.skip_importance_classification and processed_document_ids:
                try:
                    ticker_result["importance_classification"] = classify_documents_and_materialize(
                        db,
                        ticker=ticker,
                        document_ids=processed_document_ids,
                        output_root=settings.importance_output_root,
                        materialize_output=settings.importance_materialize_output,
                        include_pdf_text=settings.importance_include_pdf_text,
                        link_mode=settings.importance_link_mode,
                        sort_source_docs=settings.importance_sort_source_docs,
                    )
                except Exception as exc:
                    ticker_result["importance_classification"] = {"error": str(exc)}

            report["results"].append(ticker_result)
            report["totals"]["pending_selected"] += ticker_result["pending_selected"]
            report["totals"]["processed"] += ticker_result["processed"]
            report["totals"]["skipped_download"] += ticker_result["skipped_download"]
            report["totals"]["requires_headed_recovery_count"] += ticker_result["requires_headed_recovery_count"]
            report["totals"]["extraction_failed_count"] += ticker_result["extraction_failed_count"]
            report["totals"]["errors"] += ticker_result["error_count"]

            print(
                f"[resume] {ticker}: pending={ticker_result['pending_selected']} "
                f"dup_source_skipped={ticker_result['pending_duplicate_source_rows_skipped']} "
                f"processed={ticker_result['processed']} skipped={ticker_result['skipped_download']} "
                f"requires_headed_recovery={ticker_result['requires_headed_recovery_count']} "
                f"errors={ticker_result['error_count']} "
                f"importance_classified={((ticker_result.get('importance_classification') or {}).get('classified_count', 0))}",
                flush=True,
            )
            if ticker_result["requires_headed_recovery_count"]:
                print(
                    "[resume] MarketIndex headed recovery required: "
                    f"{ticker_result['marketindex_headed_recovery']['recommended_command']}",
                    flush=True,
                )
    finally:
        db.close()

    ended = datetime.now(timezone.utc)
    report["ended_at"] = ended.isoformat()
    report["duration_seconds"] = (ended - started).total_seconds()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[resume] report={report_path}")

    if report["totals"]["errors"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
