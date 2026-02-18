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

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.services.announcement_importance import classify_documents_and_materialize  # noqa: E402


def _parse_tickers(values: list[str] | None) -> list[str]:
    if not values:
        return []
    tickers: list[str] = []
    for raw in values:
        for token in raw.split(","):
            token = token.strip().upper()
            if token:
                tickers.append(token)
    deduped: list[str] = []
    seen = set()
    for ticker in tickers:
        if ticker in seen:
            continue
        seen.add(ticker)
        deduped.append(ticker)
    return deduped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify ingested announcements into announcement-type folders based on title/PDF content."
    )
    parser.add_argument("--ticker", action="append", help="Ticker filter. Repeat or pass comma-separated values.")
    parser.add_argument("--limit", type=int, default=0, help="Max documents per run (0 = no limit).")
    parser.add_argument(
        "--output-root",
        default=settings.importance_output_root,
        help="Destination root for announcement-type folders.",
    )
    parser.add_argument(
        "--link-mode",
        choices=["symlink", "copy"],
        default=settings.importance_link_mode,
        help="How to materialize files in announcement-type folders.",
    )
    parser.add_argument(
        "--no-pdf-text",
        action="store_true",
        help="Skip PDF text scan and classify using metadata/title only.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "importance" / "announcement_importance_report.json"),
        help="Report JSON output path.",
    )
    parser.add_argument(
        "--no-sort-source-docs",
        action="store_true",
        help="Do not move source files under docs/<ticker>/<label>.",
    )
    parser.add_argument(
        "--only-unsorted",
        action="store_true",
        help="Only classify docs not already under docs/<ticker>/<announcement_type>/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = _parse_tickers(args.ticker)
    started_at = datetime.now(timezone.utc)

    report: dict[str, object] = {
        "started_at": started_at.isoformat(),
        "settings": {
            "tickers": tickers,
            "limit": args.limit,
            "output_root": args.output_root,
            "link_mode": args.link_mode,
            "include_pdf_text": not args.no_pdf_text,
            "only_unsorted": args.only_unsorted,
        },
        "results": [],
    }

    db = SessionLocal()
    try:
        run_tickers = tickers or [None]
        for ticker in run_tickers:
            result = classify_documents_and_materialize(
                db,
                ticker=ticker,
                limit=args.limit,
                output_root=args.output_root,
                include_pdf_text=not args.no_pdf_text,
                link_mode=args.link_mode,
                sort_source_docs=not args.no_sort_source_docs,
                only_unsorted=args.only_unsorted,
            )
            result["ticker"] = ticker
            report["results"].append(result)
            print(
                f"[importance] ticker={ticker or 'ALL'} classified={result['classified_count']} "
                f"skipped={result['skipped_count']} by_type={result.get('by_type', result.get('by_label', {}))}",
                flush=True,
            )
    finally:
        db.close()

    ended_at = datetime.now(timezone.utc)
    report["ended_at"] = ended_at.isoformat()
    report["duration_seconds"] = (ended_at - started_at).total_seconds()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[importance] report={report_path}", flush=True)


if __name__ == "__main__":
    main()
