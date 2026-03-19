#!/usr/bin/env python3
"""Coverage gates for canonical financial metrics output."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

DEFAULT_REQUIRED_METRICS_BY_PROFILE: Dict[str, List[str]] = {
    "resources": ["revenue", "net_income", "total_assets", "total_liabilities"],
    "banks": ["revenue", "net_income", "total_assets", "total_liabilities", "total_equity"],
}
BANK_TICKERS = {"CBA", "ANZ", "NAB", "WBC", "MQG", "BEN", "BOQ", "SUN"}
FORWARD_LOOKING_PERIOD_DAYS = 370
STOCK_METRICS = {
    "total_assets",
    "total_liabilities",
    "total_equity",
    "cash_and_equivalents",
    "net_debt",
    "total_debt",
    "current_assets",
    "current_liabilities",
}


def _infer_company(row: Dict[str, object]) -> str:
    company = str(row.get("company", "")).strip()
    if company:
        return company
    file_path = str(row.get("file", "")).strip()
    if "/docs/" in file_path:
        parts = Path(file_path).parts
        if "docs" in parts:
            idx = parts.index("docs")
            if idx + 1 < len(parts):
                return str(parts[idx + 1]).strip()
    return "unknown"


def _metric(row: Dict[str, object]) -> str:
    metric_base = str(row.get("metric_base", "")).strip().lower()
    if metric_base:
        return metric_base
    return str(row.get("metric", "")).strip().lower()


def _period_end(row: Dict[str, object]) -> str:
    return str(row.get("statement_period_end", "")).strip() or str(row.get("period_end_date", "")).strip()


def _period_type(row: Dict[str, object], period_end: str) -> str:
    raw = str(row.get("period_type", "")).strip().lower()
    if raw in {"annual", "half_yearly", "quarterly"}:
        return raw
    try:
        dt = datetime.strptime(period_end, "%Y-%m-%d")
    except ValueError:
        return "unknown"
    if raw == "point_in_time":
        if dt.month == 6 and dt.day == 30:
            return "annual"
        if dt.month == 12 and dt.day == 31:
            return "half_yearly"
        return "quarterly"
    if dt.month == 6 and dt.day == 30:
        return "annual"
    if dt.month == 12 and dt.day == 31:
        return "half_yearly"
    return "unknown"


def _parse_iso_date(text: str) -> date | None:
    value = str(text or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _file_date_from_path(file_path: str) -> date | None:
    name = Path(str(file_path or "").strip()).name
    if len(name) < 10:
        return None
    return _parse_iso_date(name[:10])


def _is_forward_looking_period(row: Dict[str, object], period_end: str) -> bool:
    period_dt = _parse_iso_date(period_end)
    if period_dt is None:
        return False
    doc_dt = _parse_iso_date(str(row.get("doc_date", "")).strip())
    if doc_dt is None:
        doc_dt = _file_date_from_path(str(row.get("file", "")).strip())
    if doc_dt is None:
        return False
    return (period_dt - doc_dt).days > FORWARD_LOOKING_PERIOD_DAYS


def _parse_list_csv(text: str) -> List[str]:
    out: List[str] = []
    for tok in str(text or "").split(","):
        value = tok.strip().lower()
        if value and value not in out:
            out.append(value)
    return out


def _company_profile(company: str, coverage_profile: str) -> str:
    forced = str(coverage_profile or "auto").strip().lower()
    if forced in {"resources", "banks"}:
        return forced
    if str(company or "").strip().upper() in BANK_TICKERS:
        return "banks"
    return "resources"


def _merged_present_metrics(
    grouped: Dict[Tuple[str, str, str], Set[str]],
    *,
    company: str,
    period_type: str,
    period_end: str,
) -> Set[str]:
    present = set(grouped.get((company, period_type, period_end), set()))
    if period_type in {"annual", "half_yearly"}:
        point_in_time = grouped.get((company, "point_in_time", period_end), set())
        present.update(m for m in point_in_time if m in STOCK_METRICS)
    return present


def build_report(
    rows: Sequence[Dict[str, object]],
    *,
    required_metrics: Sequence[str],
    period_types: Sequence[str],
    recent_periods: int,
    coverage_profile: str = "auto",
) -> Dict[str, object]:
    required = [m.strip().lower() for m in required_metrics if str(m).strip()]
    ptypes = [p.strip().lower() for p in period_types if str(p).strip()]
    grouped: Dict[Tuple[str, str, str], Set[str]] = defaultdict(set)
    period_has_non_forward_row: Dict[Tuple[str, str, str], bool] = defaultdict(bool)

    for row in rows:
        period_end = _period_end(row)
        if not period_end:
            continue
        ptype = _period_type(row, period_end)
        if ptypes and ptype not in ptypes:
            continue
        company = _infer_company(row)
        metric = _metric(row)
        if metric:
            key = (company, ptype, period_end)
            grouped[key].add(metric)
            if not _is_forward_looking_period(row, period_end):
                period_has_non_forward_row[key] = True

    by_company_type: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for company, ptype, period_end in grouped:
        by_company_type[(company, ptype)].append(period_end)

    checks: List[Dict[str, object]] = []
    for (company, ptype), periods in sorted(by_company_type.items()):
        profile = _company_profile(company, coverage_profile)
        required_for_company = required or list(DEFAULT_REQUIRED_METRICS_BY_PROFILE.get(profile, []))
        unique_periods = sorted(set(periods), reverse=True)
        eligible_periods = [
            period_end
            for period_end in unique_periods
            if period_has_non_forward_row.get((company, ptype, period_end), False)
        ]
        if not eligible_periods:
            eligible_periods = unique_periods
        min_required_for_anchor = 2 if len(required_for_company) >= 2 else 1
        anchor_periods = [
            period_end
            for period_end in eligible_periods
            if sum(
                1
                for m in required_for_company
                if m in _merged_present_metrics(grouped, company=company, period_type=ptype, period_end=period_end)
            )
            >= min_required_for_anchor
        ]
        if anchor_periods:
            selected_periods = anchor_periods[: max(1, int(recent_periods))]
            selection_source = "required_metric_anchor_min_count"
        else:
            selected_periods = eligible_periods[: max(1, int(recent_periods))]
            selection_source = "all_metrics_fallback"
        for period_end in selected_periods:
            present = _merged_present_metrics(grouped, company=company, period_type=ptype, period_end=period_end)
            missing = [m for m in required_for_company if m not in present]
            checks.append(
                {
                    "company": company,
                    "profile": profile,
                    "period_type": ptype,
                    "statement_period_end": period_end,
                    "required_metrics": required_for_company,
                    "present_metrics": sorted(present),
                    "missing_metrics": missing,
                    "required_present_count": len(required_for_company) - len(missing),
                    "period_selection_source": selection_source,
                    "check_pass": len(missing) == 0,
                }
            )

    failed = [c for c in checks if not bool(c["check_pass"])]
    return {
        "gate_pass": len(failed) == 0,
        "required_metrics": required,
        "coverage_profile": coverage_profile,
        "required_metrics_by_profile": DEFAULT_REQUIRED_METRICS_BY_PROFILE,
        "period_types": ptypes,
        "period_selection_policy": "required_metric_anchor_min_count_with_stock_merge_then_all_metrics_fallback",
        "recent_periods_checked": max(1, int(recent_periods)),
        "checks_total": len(checks),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "all_checks": checks,
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Coverage gate validator for canonical financial metrics JSON.")
    ap.add_argument("input_json", help="Path to canonical financial metrics JSON.")
    ap.add_argument(
        "--required-metrics",
        default="",
        help="Optional comma-separated required metrics override.",
    )
    ap.add_argument(
        "--coverage-profile",
        default="auto",
        choices=["auto", "resources", "banks"],
        help="Coverage profile for required metric expectations.",
    )
    ap.add_argument(
        "--period-types",
        default="annual,half_yearly",
        help="Comma-separated period types to gate (annual,half_yearly,quarterly,point_in_time).",
    )
    ap.add_argument(
        "--recent-periods",
        type=int,
        default=2,
        help="How many latest periods per company+period_type to enforce.",
    )
    ap.add_argument("--out-json", default="", help="Optional output report JSON path.")
    args = ap.parse_args(argv)

    input_path = Path(args.input_json).expanduser().resolve()
    if not input_path.exists():
        print(f"[validate_financial_coverage_gates] File not found: {input_path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[validate_financial_coverage_gates] Invalid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, list):
        print("[validate_financial_coverage_gates] Expected top-level JSON array.", file=sys.stderr)
        return 2

    rows = [r for r in payload if isinstance(r, dict)]
    report = build_report(
        rows,
        required_metrics=_parse_list_csv(args.required_metrics),
        period_types=_parse_list_csv(args.period_types),
        recent_periods=max(1, int(args.recent_periods)),
        coverage_profile=str(args.coverage_profile or "auto"),
    )
    report["input_file"] = str(input_path)
    report["rows_skipped_non_object"] = len(payload) - len(rows)

    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[validate_financial_coverage_gates] Wrote report: {out_path}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["gate_pass"]:
        print(
            f"[validate_financial_coverage_gates] Gate failure: checks_failed={report['checks_failed']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
