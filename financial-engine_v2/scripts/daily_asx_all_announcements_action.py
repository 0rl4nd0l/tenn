#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from _run_metadata import build_run_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.providers.asx_provider import ASXProvider  # noqa: E402
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
        raise SystemExit(f"Invalid --date '{raw}', expected YYYY-MM-DD") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest all ASX announcements for a given day (separate from ticker backfill)."
    )
    parser.add_argument(
        "--date",
        default="",
        help="Target day in YYYY-MM-DD (default: today UTC).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Discover/insert only, without downloading PDFs.",
    )
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Run extraction/chunking/financial parsing after successful download.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "asx" / "daily_asx_all_announcements_report.json"),
        help="Output summary report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_day = _parse_date(args.date)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "settings": {
            "date": target_day.strftime("%Y-%m-%d"),
            "skip_download": args.skip_download,
            "process_documents": args.process_documents,
        },
        "discovery": {},
        "insert": {},
        "processing": {
            "processed": 0,
            "skipped_download": 0,
            "errors": [],
        },
        "classification": None,
    }

    provider = ASXProvider()
    discovered = provider.discover_daily_all(day=target_day)
    summary["discovery"] = {
        "found": len(discovered),
        "tickers": sorted({d.ticker for d in discovered if d.ticker})[:1000],
    }

    db = SessionLocal()
    try:
        inserted = insert_discovered_documents(db, discovered)
        summary["insert"] = {
            "found": inserted["found"],
            "inserted": inserted["inserted"],
            "found_by_ticker": inserted["found_by_ticker"],
            "inserted_by_ticker": inserted["inserted_by_ticker"],
        }

        new_document_ids = inserted["new_document_ids"]
        if not args.skip_download:
            for document_id in new_document_ids:
                try:
                    download_pdf_for_document(db, document_id)
                    if args.process_documents:
                        process_document(document_id)
                    summary["processing"]["processed"] = int(summary["processing"]["processed"]) + 1
                except RuntimeError as exc:
                    msg = str(exc)
                    if "marketindex_headed_required" in msg:
                        summary["processing"]["skipped_download"] = int(summary["processing"]["skipped_download"]) + 1
                        continue
                    db.rollback()
                    summary["processing"]["errors"].append({"document_id": document_id, "error": msg})
                except httpx.HTTPStatusError as exc:
                    db.rollback()
                    summary["processing"]["errors"].append({"document_id": document_id, "error": str(exc)})
                except Exception as exc:
                    db.rollback()
                    summary["processing"]["errors"].append({"document_id": document_id, "error": str(exc)})

        if settings.enable_importance_classification and new_document_ids:
            try:
                summary["classification"] = classify_documents_and_materialize(
                    db,
                    document_ids=new_document_ids,
                    output_root=settings.importance_output_root,
                    materialize_output=settings.importance_materialize_output,
                    include_pdf_text=settings.importance_include_pdf_text,
                    link_mode=settings.importance_link_mode,
                    sort_source_docs=settings.importance_sort_source_docs,
                )
            except Exception as exc:
                summary["classification"] = {"error": str(exc)}
    finally:
        db.close()

    summary["ended_at"] = _utc_now()
    summary["status"] = "success" if not summary["processing"]["errors"] else "partial_failure"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        "[daily_asx_all] "
        f"date={target_day.strftime('%Y-%m-%d')} "
        f"found={summary['discovery'].get('found')} "
        f"inserted={summary['insert'].get('inserted')} "
        f"processed={summary['processing'].get('processed')} "
        f"errors={len(summary['processing'].get('errors', []))} "
        f"report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
