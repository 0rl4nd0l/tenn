#!/usr/bin/env python3
"""Structural capital continuity enhancement layer (validation-safe).

This script does not modify parser outputs or canonical extraction rules.
It derives structural fields from existing canonical/derived/risk outputs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


MIN_CANONICAL_CONFIDENCE = 3
LEVERAGE_JUMP_THRESHOLD = 3.0
LEVERAGE_LOW_MAX = 2.0
LEVERAGE_MEDIUM_MAX = 3.5
RISK_FLICKER_THRESHOLD = 0.5
LOW_SUPPORT_THRESHOLD = 0.5

PERIOD_CANDIDATES = ["period_end", "statement_period_end", "period_end_date"]
METRIC_CANDIDATES = ["metric", "metric_name"]
VALUE_CANDIDATES = ["value", "value_num"]
CONFIDENCE_CANDIDATES = ["canonical_confidence_score", "confidence_score"]
INTEGRITY_CANDIDATES = ["integrity_score"]
FILE_CANDIDATES = ["file", "file_id", "source_file"]
COMPANY_CANDIDATES = ["company"]

RISK_LEVEL_TO_STATE = {
    "": 0,
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "med": 2,
    "high": 3,
    "critical": 4,
}


def _find_column(df: pd.DataFrame, candidates: Sequence[str], required: bool = False) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        got = lower.get(cand.lower())
        if got:
            return got
    if required:
        raise ValueError(f"Missing required column; expected one of: {', '.join(candidates)}")
    return None


def _normalize_period(series: pd.Series) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    out = raw.copy()
    out.loc[parsed.notna()] = parsed.loc[parsed.notna()].dt.strftime("%Y-%m-%d")
    return out


def _period_sort_key(period_end: str) -> int:
    try:
        return int(str(period_end).replace("-", ""))
    except ValueError:
        return 0


def _infer_company(file_path: str) -> str:
    p = Path(file_path)
    parts = p.parts
    if "docs" in parts:
        i = parts.index("docs")
        if i + 1 < len(parts):
            return parts[i + 1]
    if len(parts) >= 2:
        return parts[-2]
    return ""


def _norm_metric(metric: str) -> str:
    m = str(metric or "").strip().lower()
    m = re.sub(r"[^a-z0-9_]+", "_", m)
    m = re.sub(r"_+", "_", m).strip("_")
    alias = {
        "npat": "net_income",
        "cash": "cash_and_equivalents",
        "capex": "capital_expenditure",
        "total_borrowings": "total_debt",
    }
    return alias.get(m, m)


def _to_float(v: object) -> Optional[float]:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v: object, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _risk_state(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(float(value))
    t = str(value).strip().lower()
    if t in RISK_LEVEL_TO_STATE:
        return RISK_LEVEL_TO_STATE[t]
    try:
        return int(float(t))
    except ValueError:
        return 0


def _risk_level_from_ratio(ratio: Optional[float], ebitda: Optional[float], support: str) -> str:
    if support == "insufficient_inputs":
        return "UNKNOWN"
    if ebitda is None or ebitda <= 0:
        return "CRITICAL"
    if ratio is None:
        return "UNKNOWN"
    if ratio < LEVERAGE_LOW_MAX:
        return "LOW"
    if ratio <= LEVERAGE_MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def _read_csv_or_empty(path: Optional[str]) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def _canonical_best_rows(canonical_df: pd.DataFrame) -> pd.DataFrame:
    period_col = _find_column(canonical_df, PERIOD_CANDIDATES, required=True)
    metric_col = _find_column(canonical_df, METRIC_CANDIDATES, required=True)
    metric_base_col = _find_column(canonical_df, ["metric_base"], required=False)
    value_col = _find_column(canonical_df, VALUE_CANDIDATES, required=True)
    conf_col = _find_column(canonical_df, CONFIDENCE_CANDIDATES, required=False)
    integrity_col = _find_column(canonical_df, INTEGRITY_CANDIDATES, required=False)
    file_col = _find_column(canonical_df, FILE_CANDIDATES, required=False)
    company_col = _find_column(canonical_df, COMPANY_CANDIDATES, required=False)

    out = canonical_df.copy()
    out["period_end"] = _normalize_period(out[period_col])
    out["file_norm"] = out[file_col].fillna("").astype(str).str.strip() if file_col else ""
    if company_col:
        out["company_norm"] = out[company_col].fillna("").astype(str).str.strip()
    else:
        out["company_norm"] = ""
    out.loc[out["company_norm"] == "", "company_norm"] = out.loc[out["company_norm"] == "", "file_norm"].map(_infer_company)

    metric_raw = out[metric_col].fillna("").astype(str).str.strip()
    if metric_base_col:
        metric_base = out[metric_base_col].fillna("").astype(str).str.strip()
        metric_source = metric_base.where(metric_base != "", metric_raw)
    else:
        metric_source = metric_raw
    out["metric_norm"] = metric_source.map(_norm_metric)
    out["value_num"] = pd.to_numeric(out[value_col], errors="coerce")
    out["canonical_confidence_score_num"] = (
        pd.to_numeric(out[conf_col], errors="coerce").fillna(0.0) if conf_col else 0.0
    )
    out["integrity_score_num"] = (
        pd.to_numeric(out[integrity_col], errors="coerce").fillna(0.0) if integrity_col else 0.0
    )
    out["period_sort_key"] = out["period_end"].map(_period_sort_key)
    out["abs_value"] = out["value_num"].abs()

    out = out[(out["period_end"] != "") & (out["metric_norm"] != "")].copy()
    out = out.sort_values(
        by=[
            "file_norm",
            "company_norm",
            "period_end",
            "metric_norm",
            "canonical_confidence_score_num",
            "integrity_score_num",
            "abs_value",
            "value_num",
        ],
        ascending=[True, True, True, True, False, False, False, False],
    )
    out = out.drop_duplicates(subset=["file_norm", "company_norm", "period_end", "metric_norm"], keep="first")
    return out


def _build_metric_map(best_rows: pd.DataFrame) -> Dict[Tuple[str, str, str], Dict[str, Dict[str, float]]]:
    out: Dict[Tuple[str, str, str], Dict[str, Dict[str, float]]] = {}
    for row in best_rows.to_dict(orient="records"):
        key = (str(row["file_norm"]), str(row["company_norm"]), str(row["period_end"]))
        out.setdefault(key, {})[str(row["metric_norm"])] = {
            "value": float(row["value_num"]) if pd.notna(row["value_num"]) else float("nan"),
            "conf": float(row["canonical_confidence_score_num"]),
            "integrity": float(row["integrity_score_num"]),
            "period_sort_key": int(row["period_sort_key"]),
        }
    return out


def _select_metric(
    metric_map: Dict[str, Dict[str, float]],
    names: Iterable[str],
    *,
    min_conf: float = MIN_CANONICAL_CONFIDENCE,
) -> Tuple[Optional[float], Optional[float], str]:
    for name in names:
        rec = metric_map.get(name)
        if not rec:
            continue
        value = _to_float(rec.get("value"))
        conf = _to_float(rec.get("conf"))
        if value is None or conf is None:
            continue
        if conf < min_conf:
            continue
        return value, conf, name
    return None, None, ""


def _load_derived_index(derived_df: pd.DataFrame) -> Tuple[Dict[Tuple[str, str], Dict[str, float]], Dict[Tuple[str, str], Dict[str, float]]]:
    if derived_df.empty:
        return {}, {}
    period_col = _find_column(derived_df, PERIOD_CANDIDATES, required=False)
    if not period_col:
        return {}, {}
    metric_col = _find_column(derived_df, METRIC_CANDIDATES, required=False)
    value_col = _find_column(derived_df, VALUE_CANDIDATES, required=False)
    file_col = _find_column(derived_df, ["source_file", "file", "file_id"], required=False)
    company_col = _find_column(derived_df, COMPANY_CANDIDATES, required=False)

    exact: Dict[Tuple[str, str], Dict[str, float]] = {}
    by_company: Dict[Tuple[str, str], Dict[str, float]] = {}

    if metric_col and value_col:
        temp = derived_df.copy()
        temp["period_end"] = _normalize_period(temp[period_col])
        temp["metric_norm"] = temp[metric_col].fillna("").astype(str).map(_norm_metric)
        temp["value_num"] = pd.to_numeric(temp[value_col], errors="coerce")
        temp["file_norm"] = temp[file_col].fillna("").astype(str).str.strip() if file_col else ""
        if company_col:
            temp["company_norm"] = temp[company_col].fillna("").astype(str).str.strip()
        else:
            temp["company_norm"] = ""
        temp.loc[temp["company_norm"] == "", "company_norm"] = temp.loc[temp["company_norm"] == "", "file_norm"].map(_infer_company)
        temp = temp.dropna(subset=["value_num"])
        temp = temp[temp["period_end"] != ""]
        for row in temp.to_dict(orient="records"):
            metric = str(row["metric_norm"])
            value = float(row["value_num"])
            fkey = (str(row["file_norm"]), str(row["period_end"]))
            ckey = (str(row["company_norm"]), str(row["period_end"]))
            exact.setdefault(fkey, {})[metric] = value
            by_company.setdefault(ckey, {})[metric] = value
        return exact, by_company

    # Wide fallback
    temp = derived_df.copy()
    temp["period_end"] = _normalize_period(temp[period_col])
    temp["file_norm"] = temp[file_col].fillna("").astype(str).str.strip() if file_col else ""
    if company_col:
        temp["company_norm"] = temp[company_col].fillna("").astype(str).str.strip()
    else:
        temp["company_norm"] = ""
    temp.loc[temp["company_norm"] == "", "company_norm"] = temp.loc[temp["company_norm"] == "", "file_norm"].map(_infer_company)
    id_cols = {period_col}
    if file_col:
        id_cols.add(file_col)
    if company_col:
        id_cols.add(company_col)
    for col in temp.columns:
        if col in id_cols or col in {"period_end", "file_norm", "company_norm"}:
            continue
        metric = _norm_metric(col)
        vals = pd.to_numeric(temp[col], errors="coerce")
        for i, value in vals.items():
            if pd.isna(value):
                continue
            row = temp.iloc[i]
            fkey = (str(row["file_norm"]), str(row["period_end"]))
            ckey = (str(row["company_norm"]), str(row["period_end"]))
            exact.setdefault(fkey, {})[metric] = float(value)
            by_company.setdefault(ckey, {})[metric] = float(value)
    return exact, by_company


def _derived_value(
    exact: Dict[Tuple[str, str], Dict[str, float]],
    by_company: Dict[Tuple[str, str], Dict[str, float]],
    file_path: str,
    company: str,
    period_end: str,
    metric: str,
) -> Optional[float]:
    e = exact.get((file_path, period_end), {})
    if metric in e:
        return _to_float(e.get(metric))
    c = by_company.get((company, period_end), {})
    if metric in c:
        return _to_float(c.get(metric))
    return None


def _count_jumps(rows: List[Dict[str, object]], ratio_col: str) -> int:
    df = pd.DataFrame(rows)
    if df.empty or ratio_col not in df.columns:
        return 0
    if "group_id" not in df.columns:
        df["group_id"] = ""
    out = 0
    for _, grp in df.groupby("group_id", sort=True):
        grp = grp.sort_values(by=["period_sort_key", "period_end"])
        vals = pd.to_numeric(grp[ratio_col], errors="coerce")
        prev = vals.shift(1)
        jumps = ((vals - prev).abs() > LEVERAGE_JUMP_THRESHOLD) & vals.notna() & prev.notna()
        out += int(jumps.sum())
    return out


def _transition_stats(rows: List[Dict[str, object]], state_col: str) -> Tuple[float, bool]:
    df = pd.DataFrame(rows)
    if df.empty or state_col not in df.columns:
        return 0.0, False
    total_transitions = 0
    total_pairs = 0
    flicker = False
    for _, grp in df.groupby("group_id", sort=True):
        grp = grp.sort_values(by=["period_sort_key", "period_end"])
        states = pd.to_numeric(grp[state_col], errors="coerce").fillna(0).astype(int).tolist()
        if len(states) < 2:
            continue
        transitions = sum(1 for i in range(1, len(states)) if states[i] != states[i - 1])
        pairs = len(states) - 1
        total_transitions += transitions
        total_pairs += pairs
        rate = transitions / pairs if pairs else 0.0
        if rate > RISK_FLICKER_THRESHOLD:
            flicker = True
    return (total_transitions / total_pairs if total_pairs else 0.0), flicker


def _risk_before_states(risk_df: pd.DataFrame) -> Dict[Tuple[str, str, str], int]:
    if risk_df.empty:
        return {}
    period_col = _find_column(risk_df, PERIOD_CANDIDATES, required=False)
    if not period_col:
        return {}
    file_col = _find_column(risk_df, FILE_CANDIDATES, required=False)
    company_col = _find_column(risk_df, COMPANY_CANDIDATES, required=False)
    signal_name_col = _find_column(risk_df, ["signal_name"], required=False)
    risk_level_col = _find_column(risk_df, ["risk_level"], required=False)
    signal_value_col = _find_column(risk_df, ["signal_value"], required=False)

    out: Dict[Tuple[str, str, str], int] = {}
    temp = risk_df.copy()
    temp["period_end"] = _normalize_period(temp[period_col])
    temp["file_norm"] = temp[file_col].fillna("").astype(str).str.strip() if file_col else ""
    if company_col:
        temp["company_norm"] = temp[company_col].fillna("").astype(str).str.strip()
    else:
        temp["company_norm"] = ""
    temp.loc[temp["company_norm"] == "", "company_norm"] = temp.loc[temp["company_norm"] == "", "file_norm"].map(_infer_company)

    if signal_name_col:
        lev = temp[temp[signal_name_col].fillna("").astype(str).str.lower().str.contains("net_debt_to_ebitda|leverage")]
        if lev.empty:
            return {}
        src_col = risk_level_col if risk_level_col else signal_value_col
        if not src_col:
            return {}
        for row in lev.to_dict(orient="records"):
            key = (str(row["file_norm"]), str(row["company_norm"]), str(row["period_end"]))
            st = _risk_state(row.get(src_col))
            out[key] = max(out.get(key, 0), st)
        return out

    # Wide fallback
    wide_cols = [c for c in temp.columns if "leverage" in c.lower() or "net_debt_to_ebitda" in c.lower()]
    for row in temp.to_dict(orient="records"):
        key = (str(row["file_norm"]), str(row["company_norm"]), str(row["period_end"]))
        st = 0
        for col in wide_cols:
            st = max(st, _risk_state(row.get(col)))
        out[key] = max(out.get(key, 0), st)
    return out


def run_enhancement(
    canonical_df: pd.DataFrame,
    derived_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    out_dir: Path,
) -> Dict[str, object]:
    best = _canonical_best_rows(canonical_df)
    metric_map = _build_metric_map(best)
    derived_exact, derived_company = _load_derived_index(derived_df)
    before_risk_map = _risk_before_states(risk_df)

    keys = sorted(
        metric_map.keys(),
        key=lambda k: (
            k[1],
            _period_sort_key(k[2]),
            k[2],
            k[0],
        ),
    )

    net_debt_rows: List[Dict[str, object]] = []
    fcf_rows: List[Dict[str, object]] = []
    leverage_rows: List[Dict[str, object]] = []

    net_debt_before = 0
    net_debt_after = 0
    fcf_before = 0
    fcf_after = 0
    net_debt_structural = 0
    fcf_structural = 0

    for file_path, company, period_end in keys:
        metrics = metric_map[(file_path, company, period_end)]
        period_key = _period_sort_key(period_end)

        cash, cash_conf, cash_metric = _select_metric(metrics, ["cash_and_equivalents", "cash_and_equivalents_closing"])
        total_debt, total_debt_conf, total_debt_metric = _select_metric(metrics, ["total_debt"])
        short_debt, short_debt_conf, short_debt_metric = _select_metric(metrics, ["short_term_debt"])
        long_debt, long_debt_conf, long_debt_metric = _select_metric(metrics, ["long_term_debt"])
        equity, _, _ = _select_metric(metrics, ["total_equity"])
        liabilities, _, _ = _select_metric(metrics, ["total_liabilities"])

        debt_value = None
        debt_conf = None
        debt_source = ""
        if total_debt is not None:
            debt_value = total_debt
            debt_conf = total_debt_conf
            debt_source = total_debt_metric or "total_debt"
        elif short_debt is not None and long_debt is not None:
            debt_value = short_debt + long_debt
            debt_conf = min(float(short_debt_conf or 0.0), float(long_debt_conf or 0.0))
            debt_source = "short_plus_long_term_debt"

        support_count = int(cash is not None) + int(debt_value is not None) + int(equity is not None) + int(liabilities is not None)
        period_support = support_count / 4.0

        # Net debt
        net_debt_existing, net_debt_existing_conf, _ = _select_metric(metrics, ["net_debt"])
        net_debt_selected = None
        net_debt_source = "insufficient_inputs"
        if net_debt_existing is not None:
            net_debt_selected = net_debt_existing
            net_debt_source = "canonical_existing"
        elif cash is not None and debt_value is not None:
            net_debt_selected = debt_value - cash
            net_debt_source = "structural_derivation"
            net_debt_structural += 1

        if net_debt_existing is not None:
            net_debt_before += 1
        if net_debt_selected is not None:
            net_debt_after += 1

        net_debt_rows.append(
            {
                "file": file_path,
                "company": company,
                "period_end": period_end,
                "period_sort_key": period_key,
                "cash_and_equivalents": cash,
                "cash_metric": cash_metric,
                "debt_value": debt_value,
                "debt_source_metric": debt_source,
                "short_term_debt": short_debt,
                "long_term_debt": long_debt,
                "total_debt": total_debt,
                "net_debt_existing": net_debt_existing,
                "net_debt": net_debt_selected,
                "net_debt_source": net_debt_source,
                "canonical_confidence_floor": min(
                    [
                        v
                        for v in [
                            net_debt_existing_conf,
                            cash_conf if net_debt_source == "structural_derivation" else None,
                            debt_conf if net_debt_source == "structural_derivation" else None,
                        ]
                        if v is not None
                    ]
                    or [0.0]
                ),
                "period_capital_structure_support": round(period_support, 6),
            }
        )

        # FCF
        fcf_existing, fcf_existing_conf, _ = _select_metric(metrics, ["free_cash_flow"])
        ocf, ocf_conf, ocf_metric = _select_metric(metrics, ["operating_cash_flow", "net_cash_from_operating_activities"])
        capex, capex_conf, capex_metric = _select_metric(metrics, ["capital_expenditure", "capex"])
        fcf_selected = None
        fcf_source = "insufficient_inputs"
        if fcf_existing is not None:
            fcf_selected = fcf_existing
            fcf_source = "canonical_existing"
        elif ocf is not None and capex is not None:
            fcf_selected = ocf - capex
            fcf_source = "structural_derivation"
            fcf_structural += 1

        if fcf_existing is not None:
            fcf_before += 1
        if fcf_selected is not None:
            fcf_after += 1

        fcf_rows.append(
            {
                "file": file_path,
                "company": company,
                "period_end": period_end,
                "period_sort_key": period_key,
                "operating_cash_flow": ocf,
                "operating_cash_flow_metric": ocf_metric,
                "capital_expenditure": capex,
                "capital_expenditure_metric": capex_metric,
                "free_cash_flow_existing": fcf_existing,
                "free_cash_flow": fcf_selected,
                "fcf_source": fcf_source,
                "canonical_confidence_floor": min(
                    [
                        v
                        for v in [
                            fcf_existing_conf,
                            ocf_conf if fcf_source == "structural_derivation" else None,
                            capex_conf if fcf_source == "structural_derivation" else None,
                        ]
                        if v is not None
                    ]
                    or [0.0]
                ),
                "period_capital_structure_support": round(period_support, 6),
            }
        )

        # Leverage (after)
        ebitda, _, ebitda_metric = _select_metric(metrics, ["ebitda"])
        if ebitda is None:
            ebitda = _derived_value(derived_exact, derived_company, file_path, company, period_end, "ebitda_amount")
            if ebitda is not None:
                ebitda_metric = "ebitda_amount_derived"

        if net_debt_selected is None or ebitda is None:
            leverage_support = "insufficient_inputs"
            ratio = None
        elif abs(float(ebitda)) <= 1e-12:
            leverage_support = "sufficient_inputs"
            ratio = None
        else:
            leverage_support = "sufficient_inputs"
            ratio = float(net_debt_selected) / float(ebitda)

        risk_level = _risk_level_from_ratio(ratio, ebitda, leverage_support)
        risk_conf = "LOW_SUPPORT" if period_support < LOW_SUPPORT_THRESHOLD else "ADEQUATE_SUPPORT"

        leverage_rows.append(
            {
                "file": file_path,
                "company": company,
                "period_end": period_end,
                "period_sort_key": period_key,
                "net_debt": net_debt_selected,
                "ebitda": ebitda,
                "ebitda_source_metric": ebitda_metric,
                "net_debt_to_ebitda": ratio,
                "leverage_support": leverage_support,
                "leverage_risk_flag": risk_level,
                "risk_confidence": risk_conf,
                "period_capital_structure_support": round(period_support, 6),
                "signal_type": "leverage",
                "signal_name": "net_debt_to_ebitda_risk",
                "signal_value": ratio,
                "risk_level": risk_level,
                "explanation": (
                    "insufficient inputs for leverage ratio"
                    if leverage_support == "insufficient_inputs"
                    else (
                        "EBITDA is non-positive; leverage risk is critical"
                        if (ebitda is not None and ebitda <= 0)
                        else "leverage threshold classification from net_debt_to_ebitda"
                    )
                ),
                "created_utc": "",
            }
        )

    net_debt_df = pd.DataFrame(net_debt_rows).sort_values(by=["company", "period_sort_key", "period_end", "file"])
    fcf_df = pd.DataFrame(fcf_rows).sort_values(by=["company", "period_sort_key", "period_end", "file"])
    leverage_df = pd.DataFrame(leverage_rows).sort_values(by=["company", "period_sort_key", "period_end", "file"])

    # Risk enhanced: preserve non-leverage rows from input, replace leverage rows with recomputed output.
    risk_enhanced_rows: List[Dict[str, object]] = []
    if not risk_df.empty:
        period_col = _find_column(risk_df, PERIOD_CANDIDATES, required=False)
        signal_name_col = _find_column(risk_df, ["signal_name"], required=False)
        if period_col:
            temp = risk_df.copy()
            temp["period_end"] = _normalize_period(temp[period_col])
            temp["file"] = temp[_find_column(temp, FILE_CANDIDATES, required=False)].fillna("").astype(str).str.strip() if _find_column(temp, FILE_CANDIDATES, required=False) else ""
            temp["company"] = temp[_find_column(temp, COMPANY_CANDIDATES, required=False)].fillna("").astype(str).str.strip() if _find_column(temp, COMPANY_CANDIDATES, required=False) else ""
            temp.loc[temp["company"] == "", "company"] = temp.loc[temp["company"] == "", "file"].map(_infer_company)
            if signal_name_col:
                keep = ~temp[signal_name_col].fillna("").astype(str).str.lower().str.contains("net_debt_to_ebitda|leverage")
                temp = temp[keep].copy()
            for row in temp.to_dict(orient="records"):
                key = (str(row.get("file", "")), str(row.get("company", "")), str(row.get("period_end", "")))
                support = 0.0
                match = leverage_df[
                    (leverage_df["file"] == key[0])
                    & (leverage_df["company"] == key[1])
                    & (leverage_df["period_end"] == key[2])
                ]
                if not match.empty:
                    support = float(match.iloc[0]["period_capital_structure_support"])
                row["risk_confidence"] = "LOW_SUPPORT" if support < LOW_SUPPORT_THRESHOLD else "ADEQUATE_SUPPORT"
                row["period_capital_structure_support"] = round(support, 6)
                risk_enhanced_rows.append(row)

    for row in leverage_df.to_dict(orient="records"):
        risk_enhanced_rows.append(
            {
                "file": row["file"],
                "statement_period_end": row["period_end"],
                "company": row["company"],
                "period_sort_key": int(row["period_sort_key"]),
                "signal_type": row["signal_type"],
                "signal_name": row["signal_name"],
                "signal_value": row["signal_value"],
                "risk_level": row["risk_level"],
                "explanation": row["explanation"],
                "created_utc": "",
                "leverage_support": row["leverage_support"],
                "risk_confidence": row["risk_confidence"],
                "period_capital_structure_support": row["period_capital_structure_support"],
            }
        )

    risk_enhanced_df = pd.DataFrame(risk_enhanced_rows)
    if not risk_enhanced_df.empty:
        period_col = _find_column(risk_enhanced_df, PERIOD_CANDIDATES, required=False)
        # Prefer the more populated candidate when both period_end and
        # statement_period_end are present.
        if "statement_period_end" in risk_enhanced_df.columns:
            sp = risk_enhanced_df["statement_period_end"].fillna("").astype(str).str.strip()
            if period_col is None:
                period_col = "statement_period_end"
            else:
                cur = risk_enhanced_df[period_col].fillna("").astype(str).str.strip()
                if int((sp != "").sum()) > int((cur != "").sum()):
                    period_col = "statement_period_end"
        if period_col:
            risk_enhanced_df["period_end"] = _normalize_period(risk_enhanced_df[period_col])
            risk_enhanced_df["period_sort_key"] = risk_enhanced_df["period_end"].map(_period_sort_key)
        else:
            risk_enhanced_df["period_end"] = ""
            risk_enhanced_df["period_sort_key"] = 0
        if "company" not in risk_enhanced_df.columns:
            risk_enhanced_df["company"] = ""
        if "file" not in risk_enhanced_df.columns:
            risk_enhanced_df["file"] = ""
        risk_enhanced_df = risk_enhanced_df.sort_values(by=["company", "period_sort_key", "period_end", "signal_name"])

    # Before/after stability metrics.
    before_ratio_rows: List[Dict[str, object]] = []
    for file_path, company, period_end in keys:
        ratio = _derived_value(derived_exact, derived_company, file_path, company, period_end, "net_debt_to_ebitda")
        before_ratio_rows.append(
            {
                "group_id": file_path if file_path else company,
                "period_end": period_end,
                "period_sort_key": _period_sort_key(period_end),
                "ratio_before": ratio,
            }
        )
    after_ratio_rows = [
        {
            "group_id": (str(r.get("file", "")) or str(r.get("company", ""))),
            "period_end": str(r.get("period_end", "")),
            "period_sort_key": _safe_int(r.get("period_sort_key"), 0),
            "ratio_after": _to_float(r.get("net_debt_to_ebitda")),
        }
        for r in leverage_rows
    ]

    before_state_rows: List[Dict[str, object]] = []
    after_state_rows: List[Dict[str, object]] = []
    for file_path, company, period_end in keys:
        g = file_path if file_path else company
        before_state_rows.append(
            {
                "group_id": g,
                "period_end": period_end,
                "period_sort_key": _period_sort_key(period_end),
                "state_before": before_risk_map.get((file_path, company, period_end), 0),
            }
        )
    for row in leverage_rows:
        after_state_rows.append(
            {
                "group_id": str(row.get("file", "")) or str(row.get("company", "")),
                "period_end": str(row.get("period_end", "")),
                "period_sort_key": _safe_int(row.get("period_sort_key"), 0),
                "state_after": _risk_state(row.get("leverage_risk_flag")),
            }
        )

    leverage_jump_before = _count_jumps(before_ratio_rows, "ratio_before")
    leverage_jump_after = _count_jumps(after_ratio_rows, "ratio_after")
    transition_rate_before, risk_flicker_before = _transition_stats(before_state_rows, "state_before")
    transition_rate_after, risk_flicker_after = _transition_stats(after_state_rows, "state_after")

    total_periods = max(len(keys), 1)
    summary_required = {
        "leverage_jump_count_before": int(leverage_jump_before),
        "leverage_jump_count_after": int(leverage_jump_after),
        "risk_flicker_before": bool(risk_flicker_before),
        "risk_flicker_after": bool(risk_flicker_after),
        "net_debt_coverage_before": round(net_debt_before / total_periods, 6),
        "net_debt_coverage_after": round(net_debt_after / total_periods, 6),
        "fcf_coverage_before": round(fcf_before / total_periods, 6),
        "fcf_coverage_after": round(fcf_after / total_periods, 6),
    }
    summary = {
        **summary_required,
        "risk_transition_rate_before": round(float(transition_rate_before), 6),
        "risk_transition_rate_after": round(float(transition_rate_after), 6),
        "total_periods": int(total_periods),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    net_debt_path = out_dir / "derived_net_debt_enhanced.csv"
    fcf_path = out_dir / "derived_fcf_enhanced.csv"
    leverage_path = out_dir / "leverage_enhanced.csv"
    risk_path = out_dir / "risk_signals_enhanced.csv"
    summary_path = out_dir / "capital_structure_enhancement_summary.json"
    stability_path = out_dir / "validation_post_fix_stability.json"

    net_debt_df.to_csv(net_debt_path, index=False)
    fcf_df.to_csv(fcf_path, index=False)
    leverage_df.to_csv(leverage_path, index=False)
    risk_enhanced_df.to_csv(risk_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Backward-compatible alias for existing automation.
    stability_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "total_periods": int(total_periods),
        "net_debt_structural_derived_rows": int(net_debt_structural),
        "fcf_structural_derived_rows": int(fcf_structural),
        "net_debt_path": str(net_debt_path),
        "fcf_path": str(fcf_path),
        "leverage_path": str(leverage_path),
        "risk_path": str(risk_path),
        "summary_path": str(summary_path),
        "stability_path": str(stability_path),
        **summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Structural capital continuity enhancement layer.")
    parser.add_argument("--canonical", required=True, help="Path to canonical.csv")
    parser.add_argument("--derived", default="", help="Optional path to derived.csv")
    parser.add_argument("--risk", default="", help="Optional path to risk_signals.csv")
    parser.add_argument("--out-dir", default="", help="Output directory (default: canonical parent directory)")
    args = parser.parse_args()

    canonical_path = Path(args.canonical).expanduser().resolve()
    if not canonical_path.exists():
        raise SystemExit(f"Canonical file not found: {canonical_path}")

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else canonical_path.parent
    canonical_df = pd.read_csv(canonical_path)
    derived_df = _read_csv_or_empty(args.derived)
    risk_df = _read_csv_or_empty(args.risk)

    summary = run_enhancement(canonical_df, derived_df, risk_df, out_dir)

    print(f"Total periods: {summary['total_periods']}")
    print(f"Net debt structural rows: {summary['net_debt_structural_derived_rows']}")
    print(f"FCF structural rows: {summary['fcf_structural_derived_rows']}")
    print(f"Net debt coverage before/after: {summary['net_debt_coverage_before']} -> {summary['net_debt_coverage_after']}")
    print(f"FCF coverage before/after: {summary['fcf_coverage_before']} -> {summary['fcf_coverage_after']}")
    print(f"Leverage jumps before/after: {summary['leverage_jump_count_before']} -> {summary['leverage_jump_count_after']}")
    print(f"Risk flicker before/after: {summary['risk_flicker_before']} -> {summary['risk_flicker_after']}")
    print(f"Output: {summary['net_debt_path']}")
    print(f"Output: {summary['fcf_path']}")
    print(f"Output: {summary['leverage_path']}")
    print(f"Output: {summary['risk_path']}")
    print(f"Output: {summary['summary_path']}")
    print(f"Output: {summary['stability_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
