#!/usr/bin/env python3
"""Write ``reports/analysis/{TICKER}/financial_snapshot_v0.json`` from Postgres/SQLite.

Deterministic export from ``asx_periodic_financials`` only — no LLM.
See ``app.services.analysis.periodic_snapshot_export``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap() -> None:
    root = Path(__file__).resolve().parents[1]
    backend = root / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def main() -> int:
    _bootstrap()

    from app.core.db import SessionLocal
    from app.services.analysis.periodic_snapshot_export import (
        build_financial_snapshot_v0,
        default_analysis_dir,
        write_financial_snapshot_v0,
    )

    p = argparse.ArgumentParser(description="Export financial_snapshot_v0 JSON for a ticker.")
    p.add_argument("ticker", help="ASX ticker, e.g. BHP")
    p.add_argument(
        "--period-type",
        default="A",
        help="Filter periodic rows: A, H, or Q (default A)",
    )
    p.add_argument(
        "--max-periods",
        type=int,
        default=5,
        help="Max periods in the snapshot (default 5)",
    )
    p.add_argument(
        "--output",
        default="",
        help="Output file path (default: reports/analysis/{TICKER}/financial_snapshot_v0.json)",
    )
    p.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of writing a file",
    )
    args = p.parse_args()

    db = SessionLocal()
    try:
        payload = build_financial_snapshot_v0(
            args.ticker,
            db,
            period_type=args.period_type,
            max_periods=args.max_periods,
        )
    finally:
        db.close()

    if args.stdout:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        return 0

    out = Path(args.output) if args.output else (
        default_analysis_dir() / args.ticker.strip().upper() / "financial_snapshot_v0.json"
    )
    write_financial_snapshot_v0(out, payload)
    print(str(out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
