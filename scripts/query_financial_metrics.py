#!/usr/bin/env python3
"""
Query extracted financial metrics for a ticker with deterministic, variant-safe selection.

Usage:
  python scripts/query_financial_metrics.py --ticker BHP
  python scripts/query_financial_metrics.py --ticker BHP --format csv
  python scripts/query_financial_metrics.py --ticker BHP --metric revenue
  python scripts/query_financial_metrics.py --ticker BHP --include-variants
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
BROAD_OUT = ROOT / "reports" / "broad_ticker_test"
SINGLE_OUT = ROOT / "reports"

SOURCE_MODE_PREFERENCE = {
    "table_bbox": 4,
    "docling_table": 3,
    "line": 2,
    "parse_error": 1,
}
PRIMARY_VARIANT_BASE_ORDER = (
    "",
    "statutory",
    "reported",
    "ifrs",
    "gaap",
    "adjusted",
    "before_significant_items",
    "ex_significant_items",
    "underlying",
)
FLOW_METRICS = {
    "revenue",
    "segment_revenue",
    "gross_profit",
    "gross_margin_pct",
    "ebit",
    "ebitda",
    "operating_margin_pct",
    "net_income",
    "npat",
    "eps",
    "free_cash_flow",
    "operating_cash_flow",
    "capex",
    "guidance",
    "growth_pct",
}


def load_canonical(ticker: str) -> list:
    """Load canonical rows from broad_ticker_test or reports/financial_metrics_<ticker>.json."""
    json_path = BROAD_OUT / ticker / "canonical.json"
    if not json_path.exists():
        json_path = SINGLE_OUT / f"financial_metrics_{ticker.lower()}.json"
    if not json_path.exists():
        return []
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def _row_value_num(row: Dict[str, object]) -> float:
    try:
        return float(row.get("value", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _variant_rank(variant: str) -> int:
    v = str(variant or "").strip().lower()
    if not v:
        return 0
    for idx, token in enumerate(PRIMARY_VARIANT_BASE_ORDER):
        if token and token in v:
            return idx + 1
    return len(PRIMARY_VARIANT_BASE_ORDER) + 1


def _row_rank(row: Dict[str, object]) -> Tuple[int, int, int, int, int, int]:
    source_mode = str(row.get("source_mode", "")).strip().lower()
    return (
        1 if bool(row.get("primary_metric_value")) else 0,
        1 if str(row.get("canonical_tier", "strict")).strip().lower() == "strict" else 0,
        -_variant_rank(str(row.get("metric_variant", ""))),
        int(row.get("canonical_confidence_score", 0) or 0),
        int(SOURCE_MODE_PREFERENCE.get(source_mode, 0)),
        -int(row.get("line_no", 0) or 0),  # stable tiebreak
    )


def _flow_duration_dedupe_key(row: Dict[str, object]) -> str:
    metric = str(row.get("metric", "")).strip().lower()
    period_scope = str(row.get("period_scope", "")).strip().lower()
    period_type = str(row.get("period_type", "")).strip().lower()
    is_flow = period_scope == "flow" or period_type in {"annual", "half_yearly", "quarterly"} or metric in FLOW_METRICS
    if not is_flow:
        return ""
    try:
        months = int(row.get("reporting_period_months", 0) or 0)
    except (TypeError, ValueError):
        months = 0
    if months > 0:
        return f"{months}m"
    cadence = str(row.get("reporting_cadence", "")).strip().lower()
    if cadence in {"annual", "half_yearly", "quarterly"}:
        return cadence
    return "flow_unknown"


def _dedupe_metric_period(rows: List[Dict[str, object]], include_variants: bool) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str, str, str], List[Dict[str, object]]] = defaultdict(list)
    for r in rows:
        metric = str(r.get("metric", "")).strip().lower()
        period = str(r.get("statement_period_end", "")).strip()
        variant = str(r.get("metric_variant", "")).strip().lower() if include_variants else ""
        duration_key = _flow_duration_dedupe_key(r)
        grouped[(metric, variant, period, duration_key)].append(r)

    selected: List[Dict[str, object]] = []
    dropped: List[Dict[str, object]] = []
    for _, group_rows in grouped.items():
        ranked = sorted(group_rows, key=_row_rank, reverse=True)
        winner = ranked[0]
        selected.append(winner)
        dropped.extend(ranked[1:])
    return selected, dropped


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Query canonical financial metrics for a ticker.")
    ap.add_argument("--ticker", required=True, help="Ticker symbol (e.g. BHP, 10X, A2M)")
    ap.add_argument(
        "--json-path",
        default="",
        help="Optional explicit canonical JSON path. Overrides default ticker lookup paths.",
    )
    ap.add_argument("--metric", default=None, help="Filter by metric name (e.g. revenue, npat)")
    ap.add_argument(
        "--period-type",
        choices=["quarterly", "half_yearly", "annual", "point_in_time", "other", "unknown"],
        default=None,
        help="Optional filter by normalized period type.",
    )
    ap.add_argument(
        "--reporting-cadence",
        choices=["quarterly", "half_yearly", "annual", "other", "unknown"],
        default=None,
        help="Optional filter by inferred reporting cadence (for both stock and flow metrics).",
    )
    ap.add_argument(
        "--canonical-tier",
        choices=["strict", "table_promoted"],
        default=None,
        help="Optional filter by canonical tier provenance.",
    )
    ap.add_argument("--format", choices=["table", "csv", "json"], default="table", help="Output format")
    ap.add_argument(
        "--include-variants",
        action="store_true",
        help="Keep metric_variant dimension separate. Default collapses to one primary row per metric-period.",
    )
    ap.add_argument(
        "--include-non-primary",
        action="store_true",
        help="Include rows with primary_metric_value=false when present. Default only keeps primary rows if available.",
    )
    ap.add_argument(
        "--suppress-conflict-summary",
        action="store_true",
        help="Do not print dropped duplicate/conflict summary to stderr.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    if args.json_path:
        json_path = Path(args.json_path).expanduser().resolve()
        if not json_path.exists():
            print(f"JSON path not found: {json_path}", file=sys.stderr)
            return 2
        obj = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(obj, list):
            print(f"Expected JSON array at {json_path}", file=sys.stderr)
            return 2
        rows = [r for r in obj if isinstance(r, dict)]
    else:
        rows = load_canonical(args.ticker.upper())
    if not rows:
        print(f"No canonical data for {args.ticker}. Run extraction first:", file=sys.stderr)
        print(
            f"  python scripts/extract_financial_metrics.py --pdf-dir financial-engine_v2/data/asx/docs/{args.ticker} --out-json reports/financial_metrics_{args.ticker.lower()}.json",
            file=sys.stderr,
        )
        print(
            "  or: python scripts/run_extract_broad_tickers.py --max-tickers 1",
            file=sys.stderr,
        )
        return 2

    if args.metric:
        metric_filter = args.metric.strip().lower()
        rows = [r for r in rows if str(r.get("metric", "")).strip().lower() == metric_filter]
    if args.period_type:
        wanted_period_type = args.period_type.strip().lower()
        rows = [r for r in rows if str(r.get("period_type", "unknown")).strip().lower() == wanted_period_type]
    if args.reporting_cadence:
        wanted_reporting_cadence = args.reporting_cadence.strip().lower()
        rows = [r for r in rows if str(r.get("reporting_cadence", "unknown")).strip().lower() == wanted_reporting_cadence]
    if args.canonical_tier:
        wanted_tier = args.canonical_tier.strip().lower()
        rows = [r for r in rows if str(r.get("canonical_tier", "strict")).strip().lower() == wanted_tier]

    has_primary_flag = any("primary_metric_value" in r for r in rows)
    if has_primary_flag and not args.include_non_primary:
        primary_rows = [r for r in rows if bool(r.get("primary_metric_value"))]
        if primary_rows:
            rows = primary_rows

    # Keep numeric metric rows only for this CLI.
    rows = [r for r in rows if str(r.get("value_type", "")).strip().lower() in {"amount", "percent"}]

    selected_rows, dropped_rows = _dedupe_metric_period(rows, include_variants=args.include_variants)
    for r in selected_rows:
        if "primary_metric_value" not in r:
            r["primary_metric_value"] = True

    selected_rows.sort(
        key=lambda r: (
            str(r.get("metric", "")).strip().lower(),
            str(r.get("metric_variant", "")).strip().lower(),
            str(r.get("statement_period_end", "")).strip(),
        )
    )

    if not args.suppress_conflict_summary and dropped_rows:
        print(
            f"[query_financial_metrics] dropped {len(dropped_rows)} lower-ranked duplicate/conflict rows "
            f"(include_variants={args.include_variants})",
            file=sys.stderr,
        )

    if args.format == "json":
        print(json.dumps(selected_rows, indent=2))
        return 0

    if args.format == "csv":
        import csv

        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "metric",
                "metric_variant",
                "period_type",
                "period_scope",
                "period_length_months",
                "reporting_cadence",
                "reporting_period_months",
                "reporting_cadence_inference_source",
                "canonical_tier",
                "canonical_promotion_reason",
                "statement_period_end",
                "value",
                "currency",
                "primary_metric_value",
                "canonical_confidence_score",
                "row_label",
                "statement_period",
                "source_file",
            ]
        )
        for r in selected_rows:
            source_file = Path(str(r.get("file", ""))).name if r.get("file") else ""
            writer.writerow(
                [
                    r.get("metric", ""),
                    r.get("metric_variant", ""),
                    r.get("period_type", "unknown"),
                    r.get("period_scope", ""),
                    r.get("period_length_months", 0),
                    r.get("reporting_cadence", "unknown"),
                    r.get("reporting_period_months", 0),
                    r.get("reporting_cadence_inference_source", ""),
                    r.get("canonical_tier", "strict"),
                    r.get("canonical_promotion_reason", ""),
                    r.get("statement_period_end", ""),
                    r.get("value", ""),
                    r.get("currency", ""),
                    bool(r.get("primary_metric_value")),
                    int(r.get("canonical_confidence_score", 0) or 0),
                    (r.get("row_label", "") or "")[:80],
                    (r.get("statement_period", "") or r.get("period", ""))[:80],
                    source_file,
                ]
            )
        return 0

    # table
    print(f"\n{args.ticker.upper()} — {len(selected_rows)} selected rows\n")
    print(
        f"{'metric':<30} {'variant':<18} {'ptype':<13} {'cadence':<11} {'tier':<13} {'scope':<6} {'period_end':<12} {'value':>15} {'curr':<4} {'prim':<5} row_label"
    )
    print("-" * 171)
    for r in selected_rows:
        metric = str(r.get("metric", ""))[:29]
        variant = str(r.get("metric_variant", ""))[:17]
        period_type = str(r.get("period_type", "unknown"))[:13]
        reporting_cadence = str(r.get("reporting_cadence", "unknown"))[:11]
        canonical_tier = str(r.get("canonical_tier", "strict"))[:13]
        period_scope = str(r.get("period_scope", ""))[:5]
        period = str(r.get("statement_period_end", ""))
        val_raw = r.get("value", "")
        if isinstance(val_raw, (int, float)):
            val = f"{val_raw:,.0f}" if float(val_raw).is_integer() else f"{val_raw:,.4g}"
        else:
            val = str(val_raw)
        curr = str(r.get("currency", ""))[:3]
        prim = "yes" if bool(r.get("primary_metric_value")) else "no"
        label = str(r.get("row_label", "") or "")[:45]
        print(
            f"{metric:<30} {variant:<18} {period_type:<13} {reporting_cadence:<11} {canonical_tier:<13} {period_scope:<6} "
            f"{period:<12} {val:>15} {curr:<4} {prim:<5} {label}"
        )
    print()

    if dropped_rows and not args.suppress_conflict_summary:
        # Small summary to make variant/conflict behavior explicit.
        conflict_keys = defaultdict(int)
        for r in dropped_rows:
            k = (
                str(r.get("metric", "")),
                str(r.get("statement_period_end", "")),
                _flow_duration_dedupe_key(r),
            )
            conflict_keys[k] += 1
        print("Dropped conflicts summary (metric, period, duration -> dropped_rows):")
        for (metric, period, duration), count in sorted(conflict_keys.items()):
            duration_text = duration or "-"
            print(f"  {metric:<24} {period} {duration_text:<12} -> {count}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
