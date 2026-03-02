#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.models.extractions import ExtractionRun  # noqa: E402
from app.services.pipeline import process_document  # noqa: E402


FINANCIAL_TITLE_HINTS = {
    "appendix 4c",
    "appendix 4d",
    "appendix 4e",
    "quarterly activities report",
    "half year",
    "half-year",
    "half yearly report",
    "results announcement",
    "results presentation",
    "annual report",
    "financial report",
    "cash flow",
    "cashflow",
}

NON_FINANCIAL_TITLE_HINTS = {
    "annual general meeting",
    "agm",
    "notice of annual general meeting",
    "proxy form",
    "change of director",
    "substantial holding",
    "notification of cessation",
    "notification regarding unquoted securities",
    "dividend/distribution",
    "group action",
    "prices us bond",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_financial_candidate(doc: Document) -> bool:
    subtype = (doc.doc_subtype or "").strip().lower()
    title = (doc.title or "").strip().lower()
    if any(h in title for h in NON_FINANCIAL_TITLE_HINTS):
        return False
    if subtype in {"4c", "4d", "4e", "activities"}:
        return True
    if subtype == "report":
        return any(h in title for h in {"annual report", "financial report", "half year", "half-year", "results announcement"})
    return any(h in title for h in FINANCIAL_TITLE_HINTS)


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild one ticker's financial rows by re-processing already downloaded local documents."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. BHP.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max documents to process (0 = all candidates).",
    )
    parser.add_argument(
        "--since",
        default="",
        help="Only consider docs with published_at >= this ISO date (e.g. 2024-01-01).",
    )
    parser.add_argument(
        "--include-non-financial-candidates",
        action="store_true",
        help="Process all docs for the ticker, not only financial-like candidates.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess docs even if a prior successful extraction run exists.",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Enable embedding/vector writes while rebuilding (disabled by default).",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "rebuild_ticker_financials_from_docs_report.json"),
        help="Output report path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ticker = args.ticker.strip().upper()
    if not ticker:
        raise SystemExit("--ticker is required")
    if args.limit < 0:
        raise SystemExit("--limit must be >= 0")

    since_dt = _parse_dt(args.since)
    if args.dry_run:
        total_docs = None
        if since_dt:
            db = SessionLocal()
            try:
                total_docs = (
                    db.query(Document)
                    .filter(Document.ticker == ticker, Document.published_at.isnot(None), Document.published_at >= since_dt)
                    .count()
                )
            finally:
                db.close()

        plan = {
            "dry_run": True,
            "script": "rebuild_ticker_financials_from_docs",
            "settings": {
                "ticker": ticker,
                "limit": args.limit,
                "since": args.since or None,
                "include_non_financial_candidates": bool(args.include_non_financial_candidates),
                "force": bool(args.force),
                "with_embeddings": bool(args.with_embeddings),
                "report": str(args.report),
            },
            "estimates": {
                "docs_since_count": total_docs,
                "note": "docs_since_count is only computed when --since is provided; candidate filters apply at runtime.",
            },
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Rebuild focuses on extraction->financial rows; embeddings are optional and expensive.
    if not args.with_embeddings:
        settings.enable_embeddings = False
        settings.enable_qdrant = False

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "settings": {
            "ticker": ticker,
            "limit": args.limit,
            "since": args.since or None,
            "include_non_financial_candidates": args.include_non_financial_candidates,
            "force": args.force,
            "with_embeddings": args.with_embeddings,
        },
        "selected_count": 0,
        "processed_count": 0,
        "extraction_failed_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "items": [],
    }

    db = SessionLocal()
    try:
        q = db.query(Document).filter(Document.ticker == ticker).order_by(Document.published_at.desc().nullslast())
        rows = q.all()
        if since_dt:
            rows = [r for r in rows if r.published_at and r.published_at >= since_dt]
        if not args.include_non_financial_candidates:
            rows = [r for r in rows if _is_financial_candidate(r)]
        if args.limit > 0:
            rows = rows[: args.limit]
        summary["selected_count"] = len(rows)

        for row in rows:
            item = {
                "document_id": str(row.document_id),
                "published_at": str(row.published_at) if row.published_at else None,
                "title": row.title,
                "result": None,
            }
            try:
                if not args.force:
                    prior_ok = (
                        db.query(ExtractionRun)
                        .filter(ExtractionRun.document_id == row.document_id, ExtractionRun.status == "ok")
                        .first()
                    )
                    if prior_ok:
                        item["result"] = "skipped_already_extracted"
                        summary["skipped_count"] = int(summary["skipped_count"]) + 1
                        summary["items"].append(item)
                        continue

                result = process_document(str(row.document_id))
                extraction_status = result.get("extraction_status", "unknown")
                item["result"] = extraction_status
                item["details"] = result
                summary["processed_count"] = int(summary["processed_count"]) + 1
                if extraction_status == "failed":
                    item["error"] = "extraction_failed"
                    summary["extraction_failed_count"] = int(summary["extraction_failed_count"]) + 1
                    summary["error_count"] = int(summary["error_count"]) + 1
            except Exception as exc:
                item["result"] = "error"
                item["error"] = str(exc)
                summary["error_count"] = int(summary["error_count"]) + 1
            summary["items"].append(item)
    finally:
        db.close()

    summary["ended_at"] = _utc_now()
    summary["status"] = "success" if int(summary["error_count"]) == 0 else "partial_failure"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        f"[rebuild_financials] ticker={ticker} selected={summary['selected_count']} "
        f"processed={summary['processed_count']} skipped={summary['skipped_count']} "
        f"errors={summary['error_count']} report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
