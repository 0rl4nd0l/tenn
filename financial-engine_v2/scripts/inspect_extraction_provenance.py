#!/usr/bin/env python3
"""
inspect_extraction_provenance.py — Show metric provenance for an extraction run.

Provenance records which table (type + page number + row label) each metric
was extracted from, enabling manual verification against the source PDF.

Usage:
    # By ticker + period_end (looks up via asx_periodic_financials → source_document_id):
    python scripts/inspect_extraction_provenance.py --ticker BHP --period-end 2021-06-30

    # By document UUID directly:
    python scripts/inspect_extraction_provenance.py --document-id <uuid>

    # JSON output:
    python scripts/inspect_extraction_provenance.py --ticker RMS --period-end 2025-12-31 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.models.asx_financials import ASXPeriodicFinancial  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.models.extractions import ExtractionRun  # noqa: E402


METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show metric provenance for an extraction run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip(),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--document-id",
        help="Document UUID (from documents.document_id).",
    )
    group.add_argument(
        "--ticker",
        help="ASX ticker (requires --period-end).",
    )
    parser.add_argument(
        "--period-end",
        help="Period end date YYYY-MM-DD (used with --ticker).",
    )
    parser.add_argument(
        "--period-type",
        choices=["A", "H", "Q"],
        default=None,
        help="Period type filter when multiple rows exist for same ticker + period_end.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Output raw JSON instead of human-readable format.",
    )
    return parser.parse_args()


def _resolve_document_id(db, args: argparse.Namespace) -> str | None:
    """Return document_id string from either --document-id or --ticker+--period-end."""
    if args.document_id:
        return args.document_id

    if not args.period_end:
        print("ERROR: --period-end is required when using --ticker.", file=sys.stderr)
        sys.exit(1)

    query = db.query(ASXPeriodicFinancial).filter(
        ASXPeriodicFinancial.ticker == args.ticker.upper(),
        ASXPeriodicFinancial.period_end == args.period_end,
    )
    if args.period_type:
        query = query.filter(ASXPeriodicFinancial.period_type == args.period_type)

    rows = query.all()
    if not rows:
        print(
            f"ERROR: No asx_periodic_financials row found for "
            f"ticker={args.ticker!r}, period_end={args.period_end!r}",
            file=sys.stderr,
        )
        return None
    if len(rows) > 1:
        types = [r.period_type for r in rows]
        print(
            f"WARNING: Multiple rows found for {args.ticker}/{args.period_end} "
            f"(period_types={types}). Using first. Specify --period-type to narrow.",
            file=sys.stderr,
        )
    return str(rows[0].source_document_id)


def _fetch_run(db, document_id: str) -> ExtractionRun | None:
    """Return the most recent successful ExtractionRun for a document."""
    run = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_id == document_id)
        .filter(ExtractionRun.status.in_(["ok", "ok_low_confidence"]))
        .order_by(ExtractionRun.created_at.desc())
        .first()
    )
    if run is None:
        # Fall back to any run (might be failed — still useful for debugging)
        run = (
            db.query(ExtractionRun)
            .filter(ExtractionRun.document_id == document_id)
            .order_by(ExtractionRun.created_at.desc())
            .first()
        )
    return run


def _print_human(document_id: str, run: ExtractionRun, provenance: dict) -> None:
    doc_str = document_id[:8] + "…"
    print(f"\nExtraction Provenance Report")
    print(f"{'=' * 60}")
    print(f"  Document ID  : {document_id}")
    print(f"  Run ID       : {run.run_id}")
    print(f"  Status       : {run.status}")
    print(f"  Prompt hash  : {run.prompt_hash or '—'}")
    print(f"  Created at   : {run.created_at}")
    print(f"  Extractor    : {run.extractor_version or '—'}")
    print(f"{'=' * 60}")

    sj = run.structured_json or {}
    currency = sj.get("currency", "?")
    scale = sj.get("scale", "?")
    period_type = sj.get("period_type", "?")
    period_end = sj.get("period_end", "?")
    print(f"  Period       : {period_type}  ending {period_end}")
    print(f"  Currency     : {currency}   Scale: {scale}")
    print()

    if not provenance:
        print("  No provenance recorded (structured_json missing or empty).")
        return

    extracted_metrics = [m for m in METRIC_FIELDS if m in provenance]
    missing_metrics = [m for m in METRIC_FIELDS if m not in provenance]

    if extracted_metrics:
        print("  Metrics with provenance:")
        for m in extracted_metrics:
            prov_str = provenance[m]
            val = sj.get("metrics", {}).get(m)
            val_str = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
            print(f"    {m:<22}  {val_str:<18}  ← {prov_str}")

    print()
    if missing_metrics:
        print("  Metrics NOT extracted (no provenance):")
        for m in missing_metrics:
            print(f"    {m}")
    else:
        print("  All 10 standard metrics have provenance.")
    print()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        document_id = _resolve_document_id(db, args)
        if document_id is None:
            sys.exit(1)

        # Confirm document exists
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if doc is None:
            print(f"WARNING: No document row found for document_id={document_id}", file=sys.stderr)

        run = _fetch_run(db, document_id)
        if run is None:
            print(f"ERROR: No ExtractionRun found for document_id={document_id}", file=sys.stderr)
            sys.exit(1)

        sj = run.structured_json or {}
        provenance: dict = sj.get("provenance", {})

        if args.as_json:
            out = {
                "document_id": document_id,
                "run_id": str(run.run_id),
                "status": run.status,
                "prompt_hash": run.prompt_hash,
                "created_at": str(run.created_at),
                "period_type": sj.get("period_type"),
                "period_end": sj.get("period_end"),
                "currency": sj.get("currency"),
                "scale": sj.get("scale"),
                "provenance": provenance,
                "extracted_metrics": [m for m in METRIC_FIELDS if m in provenance],
                "missing_metrics": [m for m in METRIC_FIELDS if m not in provenance],
            }
            print(json.dumps(out, indent=2))
        else:
            _print_human(document_id, run, provenance)

    finally:
        db.close()


if __name__ == "__main__":
    main()
