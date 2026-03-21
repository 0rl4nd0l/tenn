#!/usr/bin/env python3
"""Forensic diagnostics for section-level metric coverage gaps.

This script is validation-only. It does not modify parser outputs or extraction
logic. It analyzes canonical metric presence by period and classifies whether
missing data is likely row-level or section-level.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd


PERIOD_CANDIDATES = ["period_end", "statement_period_end", "period_end_date"]
METRIC_CANDIDATES = ["metric_base", "metric", "metric_name"]
CONFIDENCE_CANDIDATES = ["canonical_confidence_score", "confidence_score"]

INCOME_CORE = {"revenue", "ebit", "net_income"}
BALANCE_SHEET_CORE = {
    "total_assets",
    "total_liabilities",
    "total_equity",
    "cash_and_equivalents",
    "total_debt",
}
CASHFLOW_CORE = {"operating_cash_flow", "capital_expenditure"}

FULL_STATEMENTS_PRESENT = "FULL_STATEMENTS_PRESENT"
INCOME_ONLY = "INCOME_ONLY"
BALANCE_SHEET_PARTIAL = "BALANCE_SHEET_PARTIAL"
CASHFLOW_PARTIAL = "CASHFLOW_PARTIAL"
MULTI_SECTION_MISSING = "MULTI_SECTION_MISSING"


def _find_col(df: pd.DataFrame, candidates: Sequence[str], required: bool = False) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        got = lower.get(c.lower())
        if got:
            return got
    if required:
        raise ValueError(f"Missing required column. Expected one of: {', '.join(candidates)}")
    return None


def _normalize_period(series: pd.Series) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip()
    dt = pd.to_datetime(raw, errors="coerce")
    out = raw.copy()
    out.loc[dt.notna()] = dt.loc[dt.notna()].dt.strftime("%Y-%m-%d")
    return out


def _period_sort_key(period: str) -> int:
    try:
        return int(str(period).replace("-", ""))
    except ValueError:
        return 0


def _norm_metric(metric: str) -> str:
    m = (metric or "").strip().lower()
    alias = {
        "npat": "net_income",
        "profit_after_tax": "net_income",
        "cash": "cash_and_equivalents",
        "cash_and_equivalents_opening": "cash_and_equivalents",
        "cash_and_equivalents_closing": "cash_and_equivalents",
        "total_borrowings": "total_debt",
        "capex": "capital_expenditure",
        "net_cash_from_operating_activities": "operating_cash_flow",
    }
    return alias.get(m, m)


def _prepare_canonical(canonical_df: pd.DataFrame, min_confidence: int = 0) -> pd.DataFrame:
    if canonical_df.empty:
        raise ValueError("canonical input is empty")

    period_col = _find_col(canonical_df, PERIOD_CANDIDATES, required=True)
    metric_col = _find_col(canonical_df, METRIC_CANDIDATES, required=True)
    conf_col = _find_col(canonical_df, CONFIDENCE_CANDIDATES, required=False)

    out = canonical_df.copy()
    out["period_end"] = _normalize_period(out[period_col])
    out["metric_norm"] = out[metric_col].fillna("").astype(str).map(_norm_metric)
    out["canonical_confidence_score_num"] = (
        pd.to_numeric(out[conf_col], errors="coerce").fillna(0.0) if conf_col else 0.0
    )
    out = out[(out["period_end"] != "") & (out["metric_norm"] != "")].copy()
    out = out[out["canonical_confidence_score_num"] >= float(min_confidence)].copy()
    return out


def _classify_period(metrics_present: Set[str]) -> Dict[str, object]:
    has_income_core = INCOME_CORE.issubset(metrics_present)
    has_balance_sheet_core = BALANCE_SHEET_CORE.issubset(metrics_present)

    has_ocf = "operating_cash_flow" in metrics_present
    has_capex = "capital_expenditure" in metrics_present
    has_fcf = "free_cash_flow" in metrics_present
    has_cashflow_core = (has_ocf and has_capex) or has_fcf

    bs_count = len(metrics_present.intersection(BALANCE_SHEET_CORE))
    balance_sheet_partial = bs_count > 0 and not has_balance_sheet_core

    ocf_capex_xor = has_ocf ^ has_capex
    cashflow_partial = ocf_capex_xor or (has_fcf and not (has_ocf and has_capex))

    debt_missing_with_other_bs = (
        "total_debt" not in metrics_present
        and len(metrics_present.intersection({"total_assets", "total_liabilities", "total_equity", "cash_and_equivalents"})) >= 2
    )
    cash_missing_with_other_bs = (
        "cash_and_equivalents" not in metrics_present
        and len(metrics_present.intersection({"total_assets", "total_liabilities", "total_equity", "total_debt"})) >= 2
    )
    ocf_missing_with_capex = (not has_ocf) and has_capex
    capex_missing_with_ocf = has_ocf and (not has_capex)

    missing_bs = sorted(m for m in BALANCE_SHEET_CORE if m not in metrics_present)
    missing_cf = sorted(m for m in CASHFLOW_CORE if m not in metrics_present)

    if has_income_core and has_balance_sheet_core and has_cashflow_core:
        cls = FULL_STATEMENTS_PRESENT
    elif has_income_core and (len(metrics_present.intersection(BALANCE_SHEET_CORE)) == 0) and (not has_cashflow_core) and (not cashflow_partial):
        cls = INCOME_ONLY
    elif balance_sheet_partial and not cashflow_partial:
        cls = BALANCE_SHEET_PARTIAL
    elif cashflow_partial and not balance_sheet_partial:
        cls = CASHFLOW_PARTIAL
    else:
        cls = MULTI_SECTION_MISSING

    return {
        "has_income_core": int(has_income_core),
        "has_balance_sheet_core": int(has_balance_sheet_core),
        "has_cashflow_core": int(has_cashflow_core),
        "balance_sheet_partial": int(balance_sheet_partial),
        "cashflow_partial": int(cashflow_partial),
        "debt_missing_with_other_bs": int(debt_missing_with_other_bs),
        "cash_missing_with_other_bs": int(cash_missing_with_other_bs),
        "ocf_present": int(has_ocf),
        "capex_present": int(has_capex),
        "fcf_present": int(has_fcf),
        "ocf_missing_with_capex": int(ocf_missing_with_capex),
        "capex_missing_with_ocf": int(capex_missing_with_ocf),
        "missing_balance_sheet_metrics": ",".join(missing_bs),
        "missing_cashflow_metrics": ",".join(missing_cf),
        "classification": cls,
    }


def run_forensic(canonical_df: pd.DataFrame, out_dir: Path, min_confidence: int = 0) -> Dict[str, object]:
    prepared = _prepare_canonical(canonical_df, min_confidence=min_confidence)
    grouped = (
        prepared.groupby("period_end", as_index=False)["metric_norm"]
        .agg(lambda x: sorted(set(x.tolist())))
        .rename(columns={"metric_norm": "metrics_present"})
    )

    rows: List[Dict[str, object]] = []
    for rec in grouped.to_dict(orient="records"):
        period_end = str(rec["period_end"])
        metrics_present = set(rec["metrics_present"])
        cls = _classify_period(metrics_present)
        rows.append(
            {
                "period_end": period_end,
                "period_sort_key": _period_sort_key(period_end),
                "total_metrics_present": len(metrics_present),
                "present_metrics": ",".join(sorted(metrics_present)),
                **cls,
            }
        )

    forensic_df = pd.DataFrame(rows).sort_values(by=["period_sort_key", "period_end"])

    periods_income_only = forensic_df.loc[forensic_df["classification"] == INCOME_ONLY, "period_end"].astype(str).tolist()
    periods_bs_partial = forensic_df.loc[
        (forensic_df["classification"] == BALANCE_SHEET_PARTIAL) | (forensic_df["debt_missing_with_other_bs"] == 1) | (forensic_df["cash_missing_with_other_bs"] == 1),
        "period_end",
    ].astype(str).tolist()
    periods_cf_partial = forensic_df.loc[
        (forensic_df["classification"] == CASHFLOW_PARTIAL) | (forensic_df["cashflow_partial"] == 1),
        "period_end",
    ].astype(str).tolist()
    periods_full = forensic_df.loc[forensic_df["classification"] == FULL_STATEMENTS_PRESENT, "period_end"].astype(str).tolist()

    period_count = max(len(forensic_df), 1)
    repeated_bs_gap = len(set(periods_bs_partial)) >= 2 and (len(set(periods_bs_partial)) / period_count) >= 0.3
    repeated_cf_gap = len(set(periods_cf_partial)) >= 2 and (len(set(periods_cf_partial)) / period_count) >= 0.3
    repeated_income_only = len(set(periods_income_only)) >= 2
    multi_missing_count = int((forensic_df["classification"] == MULTI_SECTION_MISSING).sum())
    structural_pattern_detected = bool(repeated_bs_gap or repeated_cf_gap or repeated_income_only or multi_missing_count >= 2)

    summary = {
        "periods_income_only": sorted(set(periods_income_only)),
        "periods_balance_sheet_partial": sorted(set(periods_bs_partial)),
        "periods_cashflow_partial": sorted(set(periods_cf_partial)),
        "periods_full_statements": sorted(set(periods_full)),
        "structural_pattern_detected": structural_pattern_detected,
        "counts": {
            "total_periods": int(len(forensic_df)),
            "income_only": int((forensic_df["classification"] == INCOME_ONLY).sum()),
            "balance_sheet_partial": int((forensic_df["classification"] == BALANCE_SHEET_PARTIAL).sum()),
            "cashflow_partial": int((forensic_df["classification"] == CASHFLOW_PARTIAL).sum()),
            "multi_section_missing": int((forensic_df["classification"] == MULTI_SECTION_MISSING).sum()),
            "full_statements_present": int((forensic_df["classification"] == FULL_STATEMENTS_PRESENT).sum()),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "balance_sheet_forensic_summary.csv"
    json_path = out_dir / "balance_sheet_forensic_summary.json"
    forensic_df.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        **summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose section-level balance sheet/cashflow coverage gaps.")
    ap.add_argument("--canonical", required=True, help="Path to canonical.csv")
    ap.add_argument("--out-dir", default="", help="Output directory (default: canonical parent)")
    ap.add_argument("--min-confidence", type=int, default=0, help="Optional confidence floor for diagnostics")
    args = ap.parse_args()

    canonical_path = Path(args.canonical).expanduser().resolve()
    if not canonical_path.exists():
        raise SystemExit(f"Canonical file not found: {canonical_path}")

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else canonical_path.parent
    canonical_df = pd.read_csv(canonical_path)
    result = run_forensic(canonical_df, out_dir, min_confidence=max(0, int(args.min_confidence)))

    print(f"Periods analyzed: {result['counts']['total_periods']}")
    print(f"Structural pattern detected: {result['structural_pattern_detected']}")
    print(f"Output: {result['csv_path']}")
    print(f"Output: {result['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
