#!/usr/bin/env python3
"""Batch analysis script — populate tickers with financial data.

Two modes:
  1. --backfill: Run full pipeline (discover → download → extract) for tickers.
     Requires llama-server running for LLM extraction.
  2. --analyse-only: Run deterministic (D1, no LLM) analysis on tickers that
     already have extracted financial rows in asx_periodic_financials.

Usage examples:
    # Check what data exists (dry run)
    python scripts/batch_analyse.py --status

    # Backfill + extract for specific tickers (needs llama-server)
    python scripts/batch_analyse.py --backfill --tickers CBA,NAB,ANZ,WBC

    # Backfill ASX20 (needs llama-server)
    python scripts/batch_analyse.py --backfill --asx20

    # D1 analysis only on whatever has data (no LLM needed)
    python scripts/batch_analyse.py --analyse-only

    # Backfill without extraction (download PDFs only, no llama-server needed)
    python scripts/batch_analyse.py --backfill --no-extract --tickers CBA,NAB
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TENN_ROOT = REPO_ROOT.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models.asx_financials import ASXPeriodicFinancial  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.providers.universe import ASX20  # noqa: E402
from app.services.analysis.financial_metrics import build_metrics_summary  # noqa: E402
from app.services.analysis.periodic_snapshot_export import (  # noqa: E402
    build_financial_snapshot_v0,
    default_analysis_dir,
    write_financial_snapshot_v0,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_tickers(raw: str) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()
    for token in raw.replace(",", " ").split():
        t = token.strip().upper()
        if t and t not in seen:
            seen.add(t)
            tickers.append(t)
    return tickers


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def status_report() -> dict[str, Any]:
    """Report current state of documents and financials in DB."""
    db = SessionLocal()
    try:
        doc_count = db.query(Document).count()
        tickers_with_docs = (
            db.query(Document.ticker, db.query(Document).filter(Document.ticker == Document.ticker).count())
        )
        # Simpler approach
        from sqlalchemy import func, text

        ticker_doc_counts = (
            db.query(Document.ticker, func.count(Document.document_id))
            .group_by(Document.ticker)
            .order_by(func.count(Document.document_id).desc())
            .all()
        )

        fin_count = db.query(ASXPeriodicFinancial).count()
        ticker_fin_counts = (
            db.query(ASXPeriodicFinancial.ticker, func.count(ASXPeriodicFinancial.ticker))
            .group_by(ASXPeriodicFinancial.ticker)
            .order_by(func.count(ASXPeriodicFinancial.ticker).desc())
            .all()
        )

        return {
            "total_documents": doc_count,
            "tickers_with_documents": {t: c for t, c in ticker_doc_counts},
            "total_financial_rows": fin_count,
            "tickers_with_financials": {t: c for t, c in ticker_fin_counts},
            "asx20": list(ASX20),
            "asx20_with_data": [t for t in ASX20 if any(ft == t for ft, _ in ticker_fin_counts)],
            "asx20_missing_data": [t for t in ASX20 if not any(ft == t for ft, _ in ticker_fin_counts)],
        }
    finally:
        db.close()


def backfill_tickers(
    tickers: list[str],
    *,
    years: float = 5.0,
    process_documents: bool = True,
) -> dict[str, Any]:
    """Run backfill_ticker_sync for each ticker."""
    from app.services.pipeline import backfill_ticker_sync

    results: list[dict[str, Any]] = []
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Backfilling {ticker}...", flush=True)
        try:
            result = backfill_ticker_sync(
                ticker=ticker,
                years=years,
                process_documents=process_documents,
            )
            print(
                f"  found={result.get('found')} inserted={result.get('inserted')} "
                f"processed={result.get('processed')} errors={result.get('error_count')}",
                flush=True,
            )
            results.append({"ticker": ticker, "status": "ok", **result})
        except Exception as exc:
            print(f"  ERROR: {exc}", flush=True)
            results.append({"ticker": ticker, "status": "error", "error": str(exc)})

    return {
        "tickers_attempted": len(tickers),
        "tickers_ok": sum(1 for r in results if r["status"] == "ok"),
        "tickers_error": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }


def analyse_tickers(tickers: list[str] | None = None) -> dict[str, Any]:
    """Run D1 deterministic analysis on tickers with existing financial data.

    If tickers is None, analyses all tickers that have data.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import func

        if tickers:
            available = (
                db.query(ASXPeriodicFinancial.ticker, func.count(ASXPeriodicFinancial.ticker))
                .filter(ASXPeriodicFinancial.ticker.in_([t.upper() for t in tickers]))
                .group_by(ASXPeriodicFinancial.ticker)
                .all()
            )
        else:
            available = (
                db.query(ASXPeriodicFinancial.ticker, func.count(ASXPeriodicFinancial.ticker))
                .group_by(ASXPeriodicFinancial.ticker)
                .all()
            )

        if not available:
            return {"error": "No tickers with financial data found", "results": []}

        analysis_dir = default_analysis_dir(TENN_ROOT)
        results: list[dict[str, Any]] = []

        for ticker, row_count in available:
            print(f"\nAnalysing {ticker} ({row_count} financial rows)...", flush=True)

            # Fetch all rows for this ticker
            fin_rows = (
                db.query(ASXPeriodicFinancial)
                .filter(ASXPeriodicFinancial.ticker == ticker)
                .order_by(ASXPeriodicFinancial.period_end.desc())
                .all()
            )
            raw_rows = [_row_to_dict(r) for r in fin_rows]

            # Build snapshots for each period type present
            period_types_present = set(str(r.get("period_type", "")).upper() for r in raw_rows)
            snapshots: dict[str, dict[str, Any]] = {}

            for ptype in sorted(period_types_present):
                if not ptype:
                    continue
                snapshot = build_financial_snapshot_v0(
                    ticker, db, period_type=ptype, max_periods=10
                )
                snapshots[ptype] = snapshot

                # Write snapshot to disk
                ptype_label = {"A": "annual", "H": "half_year", "Q": "quarterly"}.get(ptype, ptype.lower())
                out_path = analysis_dir / ticker / f"financial_snapshot_{ptype_label}.json"
                write_financial_snapshot_v0(out_path, snapshot)
                print(f"  {ptype_label}: {snapshot['metrics_summary']['period_count']} periods, "
                      f"health_score={snapshot['metrics_summary']['financial_health_score']}", flush=True)

            # Build combined metrics summary (prefer annual, fall back to half-year)
            primary_ptype = "A" if "A" in period_types_present else ("H" if "H" in period_types_present else "Q")
            primary = snapshots.get(primary_ptype, {})
            metrics = primary.get("metrics_summary", {})

            result_entry = {
                "ticker": ticker,
                "total_rows": row_count,
                "period_types": sorted(period_types_present),
                "primary_period_type": primary_ptype,
                "period_count": metrics.get("period_count", 0),
                "financial_health_score": metrics.get("financial_health_score"),
                "trends": metrics.get("trends", {}),
                "snapshots_written": [str(analysis_dir / ticker / f"financial_snapshot_{pt}.json") for pt in period_types_present],
            }

            # Add latest period summary
            if metrics.get("periods"):
                latest = metrics["periods"][-1]
                result_entry["latest_period"] = {
                    "period_end": latest.get("period_end"),
                    "revenue": latest.get("revenue"),
                    "ebit": latest.get("ebit"),
                    "ebit_margin": latest.get("ebit_margin"),
                    "fcf": latest.get("fcf"),
                    "net_debt": latest.get("net_debt"),
                }

            results.append(result_entry)

        # Summary report
        summary = {
            "timestamp": _utc_now(),
            "tickers_analysed": len(results),
            "analysis_dir": str(analysis_dir),
            "results": results,
        }

        # Write combined report
        report_path = analysis_dir / "batch_analysis_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"\nReport written to {report_path}", flush=True)

        return summary
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch financial data population and analysis."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true", help="Show current data status.")
    mode.add_argument("--backfill", action="store_true", help="Run discovery + download + extraction pipeline.")
    mode.add_argument("--analyse-only", action="store_true", help="Run D1 analysis on existing data (no LLM).")

    parser.add_argument("--tickers", default="", help="Comma-separated ticker list.")
    parser.add_argument("--asx20", action="store_true", help="Use ASX20 universe.")
    parser.add_argument("--asx10", action="store_true", help="Use first 10 of ASX20.")
    parser.add_argument("--years", type=float, default=5.0, help="History window for backfill.")
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Backfill without extraction (download PDFs only, no llama-server needed).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.status:
        report = status_report()
        print(json.dumps(report, indent=2, default=str))
        return

    # Resolve ticker list
    tickers: list[str] = []
    if args.tickers:
        tickers = _parse_tickers(args.tickers)
    elif args.asx20:
        tickers = list(ASX20)
    elif args.asx10:
        tickers = list(ASX20[:10])

    if args.backfill:
        if not tickers:
            print("ERROR: --backfill requires --tickers, --asx20, or --asx10", file=sys.stderr)
            raise SystemExit(1)
        process = not args.no_extract
        if process:
            # Check llama-server is reachable
            extraction_url = (
                os.getenv("EXTRACTION_LLAMACPP_URL", "").strip().rstrip("/")
                or os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").strip().rstrip("/")
            )
            if extraction_url.endswith("/v1"):
                extraction_url = extraction_url[:-3]
            import urllib.error
            import urllib.request
            try:
                urllib.request.urlopen(f"{extraction_url}/v1/models", timeout=5)
            except (urllib.error.URLError, OSError) as exc:
                print(
                    f"WARNING: llama-server not reachable at {extraction_url}: {exc}\n"
                    "Extraction will fail. Use --no-extract to skip extraction.",
                    file=sys.stderr,
                )
                raise SystemExit(1)

        result = backfill_tickers(tickers, years=args.years, process_documents=process)
        print(f"\n{'='*60}")
        print(f"Backfill complete: {result['tickers_ok']}/{result['tickers_attempted']} succeeded")
        if result["tickers_error"]:
            print(f"Errors: {result['tickers_error']}")
        print(json.dumps(result, indent=2, default=str))

    elif args.analyse_only:
        result = analyse_tickers(tickers if tickers else None)
        print(f"\n{'='*60}")
        print(f"Analysis complete: {result.get('tickers_analysed', 0)} tickers")
        for r in result.get("results", []):
            score = r.get("financial_health_score", "N/A")
            latest = r.get("latest_period", {})
            rev = latest.get("revenue")
            rev_str = f"${rev/1e9:.1f}B" if rev and rev > 1e9 else (f"${rev/1e6:.0f}M" if rev and rev > 1e6 else str(rev))
            print(f"  {r['ticker']:6s} score={score:>5}  rev={rev_str:>10}  periods={r.get('period_count', 0)}")


if __name__ == "__main__":
    main()
