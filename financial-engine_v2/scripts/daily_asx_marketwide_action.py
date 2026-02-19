#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dateutil import parser as dtparser

from _run_metadata import build_run_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.providers.asx_provider import ASXProvider  # noqa: E402
from app.services.announcement_importance import classify_documents_and_materialize  # noqa: E402
from app.services.pipeline import (  # noqa: E402
    download_pdf_for_document,
    insert_discovered_documents,
    process_document,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ASX market-wide daily announcement ingestion (all tickers found on ASX daily feed)."
    )
    parser.add_argument("--days", type=int, default=1, help="Lookback window in days (1 = today).")
    parser.add_argument(
        "--process-documents",
        action="store_true",
        help="Run extraction/chunking/financial parsing after each successful PDF download.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Only discover/insert announcements; do not download PDFs.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "asx" / "daily_asx_marketwide_action_report.json"),
        help="Output summary report path.",
    )
    parser.add_argument(
        "--fallback-max-tickers",
        type=int,
        default=250,
        help="If market-wide discovery returns empty, sweep these many recent tickers from MarketIndex feed.",
    )
    parser.add_argument(
        "--disable-marketwide-fallback",
        action="store_true",
        help="Disable fallback ticker sweep when market-wide ASX page returns empty.",
    )
    return parser.parse_args()


def _load_recent_marketindex_tickers(days: int) -> list[str]:
    candidates = [
        (REPO_ROOT / "data" / "raw" / "marketindex_announcements.json"),
        (BACKEND_ROOT / settings.marketindex_announcements_file).resolve(),
        (REPO_ROOT / settings.marketindex_announcements_file).resolve(),
    ]
    path = None
    for p in candidates:
        if p.exists():
            path = p
            break
    if not path:
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows = payload.get("announcements") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    tickers: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or len(ticker) < 2 or len(ticker) > 5:
            continue
        date_text = str(row.get("date") or "").strip()
        if date_text:
            try:
                dt = dtparser.parse(date_text, dayfirst=True)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    continue
            except Exception:
                pass
        tickers.add(ticker)
    return sorted(tickers)


def main() -> None:
    args = parse_args()
    if args.days <= 0:
        raise SystemExit("--days must be > 0")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "settings": {
            "days": args.days,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "process_documents": args.process_documents,
            "skip_download": args.skip_download,
            "fallback_max_tickers": args.fallback_max_tickers,
            "disable_marketwide_fallback": args.disable_marketwide_fallback,
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
    discovered = provider.discover_marketwide(start=start, end=end)
    discovery_mode = "marketwide"
    fallback_tickers: list[str] = []
    if not discovered and not args.disable_marketwide_fallback:
        fallback_tickers = _load_recent_marketindex_tickers(days=max(1, args.days))
        if args.fallback_max_tickers > 0:
            fallback_tickers = fallback_tickers[: args.fallback_max_tickers]
        for ticker in fallback_tickers:
            try:
                discovered.extend(provider.discover(ticker, start=start, end=end))
            except Exception:
                continue
        if fallback_tickers:
            discovery_mode = "ticker_sweep_fallback"

    if discovered:
        dedup = {}
        for doc in discovered:
            dedup[doc.source_url] = doc
        discovered = list(dedup.values())

    summary["discovery"] = {
        "mode": discovery_mode,
        "found": len(discovered),
        "tickers": sorted({d.ticker for d in discovered if d.ticker})[:500],
        "fallback_tickers_used": fallback_tickers[:500],
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
        "[daily_asx_marketwide] "
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
