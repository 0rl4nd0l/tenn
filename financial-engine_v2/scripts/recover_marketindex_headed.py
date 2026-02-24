#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.announcement_importance import classify_documents_and_materialize  # noqa: E402
from app.services.marketindex_headed_recovery import recover_marketindex_documents_headed  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(description="Recover MarketIndex documents using headed browser session.")
    parser.add_argument(
        "--ticker",
        action="append",
        help="Optional ticker filter. Repeat or pass comma-separated values.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max documents to attempt (0 = no limit).")
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "marketindex_headed_recovery_report.json"),
        help="Path to recovery JSON report.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Resolve candidates only; do not write DB/files.")
    parser.add_argument("--headless", action="store_true", help="Accepted for compatibility but unsupported.")
    parser.add_argument(
        "--min-recovered-count",
        type=int,
        default=0,
        help="Fail with exit code 3 if recovered count is below this value.",
    )
    return parser


async def main():
    args = build_parser().parse_args()

    if args.headless:
        print("Headless mode is unsupported for MarketIndex recovery. Re-run without --headless.")
        raise SystemExit(2)
    if args.limit < 0:
        raise ValueError("--limit must be >= 0")
    if args.min_recovered_count < 0:
        raise ValueError("--min-recovered-count must be >= 0")

    report_path = Path(args.report)
    if not args.dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = utc_now()
    started_ts = time.time()
    db = SessionLocal()

    try:
        recovery = await recover_marketindex_documents_headed(
            db=db,
            ticker_filters=args.ticker,
            limit=args.limit,
            dry_run=args.dry_run,
            logger=print,
        )
        if not args.dry_run:
            recovered_ids = [
                item.get("document_id")
                for item in recovery.get("results", [])
                if item.get("outcome") == "downloaded" and item.get("document_id")
            ]
            if recovered_ids:
                try:
                    recovery["importance_classification"] = classify_documents_and_materialize(
                        db,
                        document_ids=recovered_ids,
                        output_root=settings.importance_output_root,
                        materialize_output=settings.importance_materialize_output,
                        include_pdf_text=settings.importance_include_pdf_text,
                        link_mode=settings.importance_link_mode,
                        sort_source_docs=settings.importance_sort_source_docs,
                    )
                except Exception as exc:
                    recovery["importance_classification"] = {"error": str(exc)}
    finally:
        db.close()

    ended_at = utc_now()
    duration_seconds = round(time.time() - started_ts, 3)
    report = {
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        **recovery,
    }
    if not args.dry_run:
        report_path.write_text(json.dumps(report, indent=2))
        print(
            f"Headed recovery complete: selected={report['selected_total']} "
            f"attempted={report['attempted']} recovered={report['recovered']} "
            f"skipped={report['skipped']} failed={report['failed']} "
            f"classified={((report.get('importance_classification') or {}).get('classified_count', 0))} "
            f"report={report_path}"
        )

        if report["recovered"] < args.min_recovered_count:
            print(
                f"Recovered count {report['recovered']} is below --min-recovered-count {args.min_recovered_count}."
            )
            raise SystemExit(3)
    else:
        print(json.dumps(report, indent=2))
        print(
            f"Headed recovery dry-run complete: selected={report['selected_total']} "
            f"attempted={report['attempted']} recovered={report['recovered']} "
            f"skipped={report['skipped']} failed={report['failed']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
