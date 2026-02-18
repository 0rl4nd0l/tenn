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
from app.models.asx_financials import ASXPeriodicFinancial  # noqa: E402
from app.models.documents import Document  # noqa: E402


EXPECTED_GAP_DAYS = {
    "Q": (92, 45),
    "H": (183, 70),
    "A": (365, 120),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit one ticker's asx_periodic_financials quality (gaps, confidence, source linkage)."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. BHP.")
    parser.add_argument(
        "--low-confidence-threshold",
        type=float,
        default=0.40,
        help="Confidence threshold for flagging rows.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "audit_ticker_financials_report.json"),
        help="Output report path.",
    )
    return parser.parse_args()


def _check_period_gaps(rows: list[ASXPeriodicFinancial]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    by_type: dict[str, list[ASXPeriodicFinancial]] = {}
    for row in rows:
        by_type.setdefault((row.period_type or "").strip().upper(), []).append(row)

    for ptype, group in by_type.items():
        if ptype not in EXPECTED_GAP_DAYS:
            continue
        target, tolerance = EXPECTED_GAP_DAYS[ptype]
        ordered = sorted(group, key=lambda r: r.period_end)
        for prev, curr in zip(ordered[:-1], ordered[1:]):
            gap = (curr.period_end - prev.period_end).days
            if gap > (target + tolerance):
                issues.append(
                    {
                        "period_type": ptype,
                        "previous_period_end": str(prev.period_end),
                        "current_period_end": str(curr.period_end),
                        "gap_days": gap,
                        "expected_days": target,
                        "tolerance_days": tolerance,
                    }
                )
    return issues


def main() -> None:
    args = parse_args()
    ticker = args.ticker.strip().upper()
    if not ticker:
        raise SystemExit("--ticker is required")
    if not 0 <= args.low_confidence_threshold <= 1:
        raise SystemExit("--low-confidence-threshold must be between 0 and 1")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "settings": {
            "ticker": ticker,
            "low_confidence_threshold": args.low_confidence_threshold,
        },
        "counts": {},
        "issues": {},
        "status": "ok",
    }

    db = SessionLocal()
    try:
        rows = (
            db.query(ASXPeriodicFinancial)
            .filter(ASXPeriodicFinancial.ticker == ticker)
            .order_by(ASXPeriodicFinancial.period_end.desc())
            .all()
        )
        doc_ids = [r.source_document_id for r in rows if r.source_document_id]
        docs = db.query(Document).filter(Document.document_id.in_(doc_ids)).all() if doc_ids else []
        docs_by_id = {d.document_id: d for d in docs}

        low_conf = [
            r
            for r in rows
            if r.confidence_metrics is not None and float(r.confidence_metrics) < args.low_confidence_threshold
        ]
        missing_source_doc = [r for r in rows if r.source_document_id not in docs_by_id]
        missing_pdf_file = []
        for r in rows:
            d = docs_by_id.get(r.source_document_id)
            if not d:
                continue
            p = Path(d.pdf_path or "")
            if not p.is_absolute():
                p = (REPO_ROOT / p).resolve()
            if not p.exists():
                missing_pdf_file.append(
                    {
                        "period_end": str(r.period_end),
                        "period_type": r.period_type,
                        "document_id": str(r.source_document_id),
                        "pdf_path": str(p),
                    }
                )

        by_type: dict[str, int] = {}
        for row in rows:
            p = (row.period_type or "").strip().upper() or "?"
            by_type[p] = by_type.get(p, 0) + 1

        gap_issues = _check_period_gaps(rows)

        summary["counts"] = {
            "rows_total": len(rows),
            "rows_by_period_type": by_type,
            "low_confidence_rows": len(low_conf),
            "missing_source_document_rows": len(missing_source_doc),
            "missing_pdf_files": len(missing_pdf_file),
            "gap_issues": len(gap_issues),
        }
        summary["issues"] = {
            "low_confidence_rows": [
                {
                    "period_end": str(r.period_end),
                    "period_type": r.period_type,
                    "confidence_metrics": r.confidence_metrics,
                    "source_document_id": str(r.source_document_id),
                }
                for r in low_conf[:50]
            ],
            "missing_source_document_rows": [
                {
                    "period_end": str(r.period_end),
                    "period_type": r.period_type,
                    "source_document_id": str(r.source_document_id),
                }
                for r in missing_source_doc[:50]
            ],
            "missing_pdf_files": missing_pdf_file[:50],
            "period_gap_issues": gap_issues[:100],
        }
        summary["status"] = (
            "warn"
            if (len(low_conf) + len(missing_source_doc) + len(missing_pdf_file) + len(gap_issues)) > 0
            else "ok"
        )
    finally:
        db.close()

    summary["ended_at"] = _utc_now()
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        f"[audit_financials] ticker={ticker} status={summary['status']} "
        f"rows={summary['counts'].get('rows_total', 0)} "
        f"low_conf={summary['counts'].get('low_confidence_rows', 0)} "
        f"gaps={summary['counts'].get('gap_issues', 0)} report={report_path}",
        flush=True,
    )
    if summary["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
