#!/usr/bin/env python3
"""Validation-only quality diagnostics for canonical/derived/risk outputs.

This script does not modify extraction logic or source data. It reads existing
CSV outputs and emits deterministic validation artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(
        "pandas is required for validation_quality_cycle.py. "
        "Install with: pip install pandas"
    ) from exc


# Threshold/constants (deterministic; do not tune dynamically)
SCS_IS_WEIGHT = 0.45
SCS_BS_WEIGHT = 0.45
SCS_CF_WEIGHT = 0.10

BS_SPARSE_THRESHOLD = 0.25
LEVERAGE_JUMP_THRESHOLD = 3.0
MARGIN_JUMP_THRESHOLD_PCT_POINTS = 15.0
RISK_FLICKER_THRESHOLD = 0.5
LOW_COVERAGE_THRESHOLD = 0.60

IS_CORE = ["revenue", "ebit", "net_income"]
BS_CORE = ["cash_and_equivalents", "total_assets", "total_liabilities", "total_equity"]
CF_CORE = ["free_cash_flow"]
CORE_METRICS = IS_CORE + BS_CORE + CF_CORE

CANONICAL_PERIOD_CANDIDATES = ["period_end", "statement_period_end", "period_end_date"]
CANONICAL_METRIC_CANDIDATES = ["metric", "metric_name"]
CANONICAL_VALUE_CANDIDATES = ["value", "value_num"]
CANONICAL_CONF_CANDIDATES = ["canonical_confidence_score", "confidence_score"]
CANONICAL_INT_CANDIDATES = ["integrity_score"]

DERIVED_PERIOD_CANDIDATES = ["period_end", "statement_period_end", "period_end_date"]
DERIVED_METRIC_CANDIDATES = ["metric", "metric_name"]
DERIVED_VALUE_CANDIDATES = ["value", "value_num"]

RISK_PERIOD_CANDIDATES = ["period_end", "statement_period_end", "period_end_date"]

RISK_ID_COLUMNS = {
    "file",
    "file_id",
    "company",
    "period_sort_key",
    "created_utc",
    "updated_utc",
    "signal_type",
    "signal_name",
    "signal_value",
    "risk_level",
    "explanation",
    "period_end",
    "statement_period_end",
    "period_end_date",
}


def _find_first_column(df: pd.DataFrame, candidates: Sequence[str], required: bool = False) -> Optional[str]:
    lower_to_orig = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        key = candidate.lower()
        if key in lower_to_orig:
            return lower_to_orig[key]
    if required:
        raise ValueError(f"Missing required column. Expected one of: {', '.join(candidates)}")
    return None


def _normalize_period_series(series: pd.Series) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    normalized = raw.copy()
    normalized.loc[parsed.notna()] = parsed.loc[parsed.notna()].dt.strftime("%Y-%m-%d")
    return normalized


def _normalize_metric_name(metric: str) -> str:
    m = (metric or "").strip().lower()
    if not m:
        return m
    aliases = {
        "npat": "net_income",
        "cash": "cash_and_equivalents",
        "cash_and_equivalents_opening": "cash_and_equivalents",
        "cash_and_equivalents_closing": "cash_and_equivalents",
        "ebit_margin_pct": "ebit_margin",
        "fcf_conversion_pct": "fcf_conversion",
        "cash_runway_periods": "cash_runway",
        "roic_pct": "roic",
    }
    return aliases.get(m, m)


def _state_from_risk_value(value: object) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0
    text = str(value).strip().lower()
    if not text:
        return 0
    mapping = {
        "low": 1,
        "medium": 2,
        "med": 2,
        "high": 3,
        "critical": 4,
        "true": 1,
        "false": 0,
        "yes": 1,
        "no": 0,
        "y": 1,
        "n": 0,
        "on": 1,
        "off": 0,
    }
    if text in mapping:
        return mapping[text]
    try:
        return int(float(text))
    except ValueError:
        return 0


def _max_consecutive_gap(values: List[int]) -> int:
    max_gap = 0
    cur = 0
    for v in values:
        if v == 0:
            cur += 1
            if cur > max_gap:
                max_gap = cur
        else:
            cur = 0
    return max_gap


def _blink_count(values: List[int]) -> int:
    if len(values) < 3:
        return 0
    count = 0
    for i in range(1, len(values) - 1):
        if values[i - 1] == 1 and values[i] == 0 and values[i + 1] == 1:
            count += 1
    return count


def _longest_stable_run(states: List[int]) -> int:
    if not states:
        return 0
    best = 1
    run = 1
    for i in range(1, len(states)):
        if states[i] == states[i - 1]:
            run += 1
            if run > best:
                best = run
        else:
            run = 1
    return best


def _isolated_high(states: List[int], high_threshold: int = 3) -> bool:
    if not states:
        return False
    if len(states) == 1:
        return states[0] >= high_threshold
    for i, state in enumerate(states):
        if state < high_threshold:
            continue
        prev_low = i == 0 or states[i - 1] < high_threshold
        next_low = i == len(states) - 1 or states[i + 1] < high_threshold
        if prev_low and next_low:
            return True
    return False


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _load_csv_or_empty(path: Optional[str]) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def _prepare_canonical(canonical_df: pd.DataFrame) -> pd.DataFrame:
    if canonical_df.empty:
        raise ValueError("canonical input is empty")

    period_col = _find_first_column(canonical_df, CANONICAL_PERIOD_CANDIDATES, required=True)
    metric_col = _find_first_column(canonical_df, CANONICAL_METRIC_CANDIDATES, required=True)
    value_col = _find_first_column(canonical_df, CANONICAL_VALUE_CANDIDATES, required=True)
    metric_base_col = _find_first_column(canonical_df, ["metric_base"], required=False)
    conf_col = _find_first_column(canonical_df, CANONICAL_CONF_CANDIDATES, required=False)
    int_col = _find_first_column(canonical_df, CANONICAL_INT_CANDIDATES, required=False)

    out = canonical_df.copy()
    out["period_end"] = _normalize_period_series(out[period_col])
    out["metric_raw"] = out[metric_col].fillna("").astype(str).str.strip()
    if metric_base_col:
        base_series = out[metric_base_col].fillna("").astype(str).str.strip()
        metric_source = base_series.where(base_series != "", out["metric_raw"])
    else:
        metric_source = out["metric_raw"]
    out["metric_norm"] = metric_source.map(_normalize_metric_name)
    out["value_num"] = pd.to_numeric(out[value_col], errors="coerce")
    out["canonical_confidence_score_num"] = (
        pd.to_numeric(out[conf_col], errors="coerce").fillna(0.0) if conf_col else 0.0
    )
    out["integrity_score_num"] = (
        pd.to_numeric(out[int_col], errors="coerce").fillna(0.0) if int_col else 0.0
    )
    out = out[out["period_end"].astype(str) != ""].copy()
    return out


def _build_presence_matrix(canonical: pd.DataFrame) -> pd.DataFrame:
    present = (
        canonical.assign(is_present=1)
        .groupby(["period_end", "metric_norm"], as_index=False)["is_present"]
        .max()
        .pivot(index="period_end", columns="metric_norm", values="is_present")
        .fillna(0)
        .astype(int)
    )
    present = present.sort_index()
    present.index.name = "period_end"
    return present


def _build_period_metric_values(canonical: pd.DataFrame) -> pd.DataFrame:
    ranked = canonical.copy()
    ranked["value_abs"] = ranked["value_num"].abs()
    ranked = ranked.sort_values(
        by=[
            "period_end",
            "metric_norm",
            "canonical_confidence_score_num",
            "integrity_score_num",
            "value_abs",
            "value_num",
        ],
        ascending=[True, True, False, False, False, False],
    )
    best = ranked.drop_duplicates(subset=["period_end", "metric_norm"], keep="first")
    values = best.pivot(index="period_end", columns="metric_norm", values="value_num").sort_index()
    values.index.name = "period_end"
    return values


def _get_metric_series_from_derived(derived_df: pd.DataFrame, metric_name: str) -> pd.Series:
    if derived_df.empty:
        return pd.Series(dtype="float64")
    period_col = _find_first_column(derived_df, DERIVED_PERIOD_CANDIDATES, required=False)
    if period_col is None:
        return pd.Series(dtype="float64")
    metric_col = _find_first_column(derived_df, DERIVED_METRIC_CANDIDATES, required=False)
    value_col = _find_first_column(derived_df, DERIVED_VALUE_CANDIDATES, required=False)

    if metric_col and value_col:
        temp = derived_df.copy()
        temp["period_end"] = _normalize_period_series(temp[period_col])
        temp["metric_norm"] = temp[metric_col].fillna("").astype(str).map(_normalize_metric_name)
        temp["value_num"] = pd.to_numeric(temp[value_col], errors="coerce")
        series = (
            temp[temp["metric_norm"] == metric_name]
            .groupby("period_end", as_index=True)["value_num"]
            .mean()
            .sort_index()
        )
        return series

    # Wide fallback
    if metric_name in derived_df.columns:
        temp = derived_df.copy()
        temp["period_end"] = _normalize_period_series(temp[period_col])
        temp["value_num"] = pd.to_numeric(temp[metric_name], errors="coerce")
        return temp.groupby("period_end", as_index=True)["value_num"].mean().sort_index()

    return pd.Series(dtype="float64")


def _build_risk_state_table(risk_df: pd.DataFrame, periods: List[str]) -> pd.DataFrame:
    if risk_df.empty:
        return pd.DataFrame(index=periods)

    period_col = _find_first_column(risk_df, RISK_PERIOD_CANDIDATES, required=False)
    if period_col is None:
        return pd.DataFrame(index=periods)

    temp = risk_df.copy()
    temp["period_end"] = _normalize_period_series(temp[period_col])
    signal_name_col = _find_first_column(temp, ["signal_name"], required=False)
    risk_level_col = _find_first_column(temp, ["risk_level"], required=False)
    signal_value_col = _find_first_column(temp, ["signal_value"], required=False)

    if signal_name_col:
        # Long format: one row per signal_name/period.
        level_source_col = risk_level_col if risk_level_col else signal_value_col
        if level_source_col is None:
            return pd.DataFrame(index=periods)
        temp["state"] = temp[level_source_col].map(_state_from_risk_value)
        grouped = (
            temp.groupby(["period_end", signal_name_col], as_index=False)["state"]
            .max()
            .pivot(index="period_end", columns=signal_name_col, values="state")
            .fillna(0)
            .astype(int)
        )
    else:
        # Wide format: treat non-id columns as risk flags.
        flag_cols = [c for c in temp.columns if c.lower() not in RISK_ID_COLUMNS]
        if not flag_cols:
            return pd.DataFrame(index=periods)
        grouped = temp[["period_end"] + flag_cols].copy()
        for col in flag_cols:
            grouped[col] = grouped[col].map(_state_from_risk_value)
        grouped = grouped.groupby("period_end", as_index=False)[flag_cols].max().set_index("period_end")

    grouped = grouped.reindex(periods).fillna(0).astype(int)
    grouped.index.name = "period_end"
    return grouped


def run_validation(
    canonical_df: pd.DataFrame,
    derived_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    out_dir: Path,
) -> None:
    canonical = _prepare_canonical(canonical_df)
    presence = _build_presence_matrix(canonical)
    values = _build_period_metric_values(canonical)

    periods = sorted(presence.index.tolist())

    # 1) Structural completeness scoring
    completeness_rows: List[Dict[str, object]] = []
    for period_end in periods:
        row_present = presence.loc[period_end]

        has_revenue = int(row_present.get("revenue", 0))
        has_ebit = int(row_present.get("ebit", 0))
        has_net_income = int(row_present.get("net_income", 0))
        has_cash = int(row_present.get("cash_and_equivalents", 0))
        has_total_assets = int(row_present.get("total_assets", 0))
        has_total_liabilities = int(row_present.get("total_liabilities", 0))
        has_total_equity = int(row_present.get("total_equity", 0))
        has_fcf = int(row_present.get("free_cash_flow", 0))

        is_score = (has_revenue + has_ebit + has_net_income) / 3.0
        bs_score = (has_cash + has_total_assets + has_total_liabilities + has_total_equity) / 4.0
        cf_score = float(has_fcf)
        scs = (SCS_IS_WEIGHT * is_score) + (SCS_BS_WEIGHT * bs_score) + (SCS_CF_WEIGHT * cf_score)

        missing_core = []
        if not has_revenue:
            missing_core.append("revenue")
        if not has_ebit:
            missing_core.append("ebit")
        if not has_net_income:
            missing_core.append("net_income_or_npat")
        if not has_cash:
            missing_core.append("cash")
        if not has_total_assets:
            missing_core.append("total_assets")
        if not has_total_liabilities:
            missing_core.append("total_liabilities")
        if not has_total_equity:
            missing_core.append("total_equity")
        if not has_fcf:
            missing_core.append("free_cash_flow")

        completeness_rows.append(
            {
                "period_end": period_end,
                "IS_score": round(is_score, 6),
                "BS_score": round(bs_score, 6),
                "CF_score": round(cf_score, 6),
                "SCS": round(scs, 6),
                "total_metrics_present": int(row_present.sum()),
                "missing_core_metrics": ",".join(missing_core),
            }
        )

    completeness_df = pd.DataFrame(completeness_rows).sort_values("period_end")
    _write_csv(completeness_df, out_dir / "validation_period_completeness.csv")

    # 2A) Metric presence matrix
    presence_matrix_df = presence.reset_index().rename(columns={"period_end": "period_end"})
    _write_csv(presence_matrix_df, out_dir / "validation_metric_presence_matrix.csv")

    # 2B) Metric coverage diagnosis
    coverage_rows: List[Dict[str, object]] = []
    total_periods = len(periods)
    for metric in sorted(presence.columns.tolist()):
        seq = presence[metric].astype(int).tolist()
        periods_present = int(sum(seq))
        coverage_rows.append(
            {
                "metric": metric,
                "periods_present": periods_present,
                "total_periods": total_periods,
                "coverage_rate": round(periods_present / total_periods if total_periods else 0.0, 6),
                "max_consecutive_gap": _max_consecutive_gap(seq),
                "blink_count": _blink_count(seq),
            }
        )
    coverage_df = pd.DataFrame(coverage_rows).sort_values("metric")
    _write_csv(coverage_df, out_dir / "validation_metric_coverage.csv")

    # 2C) Coverage flags
    coverage_flags_df = pd.DataFrame(
        {
            "period_end": periods,
            "ebit_present_revenue_missing": [
                int(presence.loc[p, "ebit"] == 1 and presence.loc[p, "revenue"] == 0)
                if "ebit" in presence.columns and "revenue" in presence.columns
                else 0
                for p in periods
            ],
            "revenue_present_ebit_missing": [
                int(presence.loc[p, "revenue"] == 1 and presence.loc[p, "ebit"] == 0)
                if "ebit" in presence.columns and "revenue" in presence.columns
                else 0
                for p in periods
            ],
            "ebit_present_npat_missing": [
                int(presence.loc[p, "ebit"] == 1 and presence.loc[p, "net_income"] == 0)
                if "ebit" in presence.columns and "net_income" in presence.columns
                else 0
                for p in periods
            ],
            "balance_sheet_sparse": [
                int(
                    completeness_df.loc[completeness_df["period_end"] == p, "BS_score"].iloc[0]
                    <= BS_SPARSE_THRESHOLD
                )
                for p in periods
            ],
        }
    )
    _write_csv(coverage_flags_df.sort_values("period_end"), out_dir / "validation_coverage_flags.csv")

    # 3) Economic plausibility checks
    ebit_series = values["ebit"] if "ebit" in values.columns else pd.Series(index=periods, dtype="float64")
    npat_series = values["net_income"] if "net_income" in values.columns else pd.Series(index=periods, dtype="float64")
    ebit_series = ebit_series.reindex(periods)
    npat_series = npat_series.reindex(periods)

    both_present = ebit_series.notna() & npat_series.notna()
    sign_mismatch = (ebit_series * npat_series < 0) & both_present
    npat_gt_ebit = (npat_series > ebit_series) & both_present

    delta_ebit = ebit_series.diff()
    delta_npat = npat_series.diff()
    prev_both_present = both_present & both_present.shift(1, fill_value=False)
    delta_direction_mismatch = (delta_ebit * delta_npat < 0) & prev_both_present

    leverage_series = _get_metric_series_from_derived(derived_df, "net_debt_to_ebitda").reindex(periods)
    leverage_prev = leverage_series.shift(1)
    leverage_jump = (
        (leverage_series.notna())
        & (leverage_prev.notna())
        & ((leverage_series - leverage_prev).abs() > LEVERAGE_JUMP_THRESHOLD)
    )
    leverage_isolated = pd.Series(False, index=periods)
    if len(periods) > 0:
        for idx, p in enumerate(periods):
            cur = pd.notna(leverage_series.loc[p])
            if not cur:
                continue
            prev_missing = True if idx == 0 else pd.isna(leverage_series.iloc[idx - 1])
            next_missing = True if idx == len(periods) - 1 else pd.isna(leverage_series.iloc[idx + 1])
            if prev_missing and next_missing:
                leverage_isolated.loc[p] = True
    leverage_jump_flag = leverage_jump | leverage_isolated

    margin_series = _get_metric_series_from_derived(derived_df, "ebit_margin").reindex(periods)
    margin_prev = margin_series.shift(1)
    margin_jump = (
        (margin_series.notna())
        & (margin_prev.notna())
        & ((margin_series - margin_prev).abs() > MARGIN_JUMP_THRESHOLD_PCT_POINTS)
    )

    economic_df = pd.DataFrame(
        {
            "period_end": periods,
            "ebit_npat_sign_mismatch": sign_mismatch.reindex(periods).fillna(False).astype(int).values,
            "npat_gt_ebit": npat_gt_ebit.reindex(periods).fillna(False).astype(int).values,
            "leverage_jump_flag": leverage_jump_flag.reindex(periods).fillna(False).astype(int).values,
            "margin_jump_flag": margin_jump.reindex(periods).fillna(False).astype(int).values,
            "ebit_npat_delta_direction_mismatch": delta_direction_mismatch.reindex(periods)
            .fillna(False)
            .astype(int)
            .values,
        }
    ).sort_values("period_end")
    _write_csv(economic_df, out_dir / "validation_economic_flags.csv")

    # 4) Risk signal stability audit
    risk_state = _build_risk_state_table(risk_df, periods)
    risk_rows: List[Dict[str, object]] = []
    if not risk_state.empty:
        for signal in sorted(risk_state.columns.tolist()):
            states = risk_state[signal].astype(int).tolist()
            transitions = sum(1 for i in range(1, len(states)) if states[i] != states[i - 1])
            transition_rate = transitions / (len(states) - 1) if len(states) > 1 else 0.0
            risk_rows.append(
                {
                    "risk_signal": signal,
                    "total_state_changes": transitions,
                    "transition_rate": round(transition_rate, 6),
                    "longest_stable_run": _longest_stable_run(states),
                    "high_flicker": int(transition_rate > RISK_FLICKER_THRESHOLD),
                    "isolated_high": int(_isolated_high(states)),
                    "periods_observed": len(states),
                }
            )
    risk_stability_df = pd.DataFrame(
        risk_rows,
        columns=[
            "risk_signal",
            "total_state_changes",
            "transition_rate",
            "longest_stable_run",
            "high_flicker",
            "isolated_high",
            "periods_observed",
        ],
    )
    _write_csv(risk_stability_df, out_dir / "validation_risk_stability.csv")

    # 5) Summary JSON
    low_coverage_metrics = (
        coverage_df.loc[coverage_df["coverage_rate"] < LOW_COVERAGE_THRESHOLD, "metric"].astype(str).tolist()
        if not coverage_df.empty
        else []
    )
    sparse_bs_periods = (
        coverage_flags_df.loc[coverage_flags_df["balance_sheet_sparse"] == 1, "period_end"].astype(str).tolist()
        if not coverage_flags_df.empty
        else []
    )
    risk_flicker_detected = (
        bool((risk_stability_df["high_flicker"] == 1).any()) if not risk_stability_df.empty else False
    )

    summary = {
        "total_periods": int(len(periods)),
        "average_SCS": float(round(completeness_df["SCS"].mean(), 6)) if not completeness_df.empty else 0.0,
        "income_completeness_mean": float(round(completeness_df["IS_score"].mean(), 6))
        if not completeness_df.empty
        else 0.0,
        "balance_sheet_completeness_mean": float(round(completeness_df["BS_score"].mean(), 6))
        if not completeness_df.empty
        else 0.0,
        "fcf_completeness_mean": float(round(completeness_df["CF_score"].mean(), 6))
        if not completeness_df.empty
        else 0.0,
        "metrics_with_low_coverage": sorted(low_coverage_metrics),
        "periods_with_sparse_balance_sheet": sorted(sparse_bs_periods),
        "economic_flag_counts": {
            "ebit_npat_mismatch": int(economic_df["ebit_npat_sign_mismatch"].sum()) if not economic_df.empty else 0,
            "leverage_jump": int(economic_df["leverage_jump_flag"].sum()) if not economic_df.empty else 0,
            "margin_jump": int(economic_df["margin_jump_flag"].sum()) if not economic_df.empty else 0,
        },
        "risk_flicker_detected": bool(risk_flicker_detected),
    }
    summary_path = out_dir / "validation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Validation periods: {len(periods)}")
    print(f"Output: {out_dir / 'validation_period_completeness.csv'}")
    print(f"Output: {out_dir / 'validation_metric_coverage.csv'}")
    print(f"Output: {out_dir / 'validation_coverage_flags.csv'}")
    print(f"Output: {out_dir / 'validation_economic_flags.csv'}")
    print(f"Output: {out_dir / 'validation_risk_stability.csv'}")
    print(f"Output: {summary_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validation quality diagnostics on canonical/derived/risk outputs.")
    ap.add_argument("--input", required=True, help="Path to canonical.csv")
    ap.add_argument("--derived", default="", help="Optional path to derived.csv")
    ap.add_argument("--risk", default="", help="Optional path to risk_signals.csv")
    ap.add_argument("--out-dir", default=".", help="Directory for validation outputs")
    args = ap.parse_args()

    canonical_path = Path(args.input).expanduser().resolve()
    if not canonical_path.exists():
        raise SystemExit(f"Input canonical file not found: {canonical_path}")

    canonical_df = pd.read_csv(canonical_path)
    derived_df = _load_csv_or_empty(args.derived)
    risk_df = _load_csv_or_empty(args.risk)
    out_dir = Path(args.out_dir).expanduser().resolve()

    run_validation(canonical_df, derived_df, risk_df, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
