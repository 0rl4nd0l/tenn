#!/usr/bin/env python3
"""Section-aware capture reinforcement layer.

This layer does not change extraction logic. It:
1) Builds a page-level statement section index per PDF.
2) Detects missing statement sections from canonical outputs.
3) Runs a targeted second extraction pass on indexed section pages only.
4) Re-runs validation + forensic diagnostics and reports before/after deltas.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd


PERIOD_CANDIDATES = ["statement_period_end", "period_end", "period_end_date"]
METRIC_CANDIDATES = ["metric_base", "metric", "metric_name"]
FILE_CANDIDATES = ["file", "source_file", "file_id"]
CURRENCY_CANDIDATES = ["currency", "reporting_currency"]

INCOME_CORE = {"revenue", "ebit", "net_income"}
BALANCE_SHEET_CORE = {"cash_and_equivalents", "total_assets", "total_liabilities", "total_equity", "total_debt"}
BALANCE_SHEET_METRICS = {
    "cash_and_equivalents",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "total_debt",
    "net_debt",
    "current_assets",
    "current_liabilities",
}
CASHFLOW_CORE = {"operating_cash_flow", "capital_expenditure", "free_cash_flow"}
CASHFLOW_METRICS = {
    "operating_cash_flow",
    "capital_expenditure",
    "capex",
    "free_cash_flow",
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "cash_and_equivalents",
}

SECTION_TYPES = ("income_statement", "balance_sheet", "cash_flow")

HEADING_PATTERNS = {
    "income_statement": [
        re.compile(r"\bstatement\s+of\s+profit\s+or\s+loss\b", re.IGNORECASE),
        re.compile(r"\bincome\s+statement\b", re.IGNORECASE),
        re.compile(r"\bstatement\s+of\s+comprehensive\s+income\b", re.IGNORECASE),
    ],
    "balance_sheet": [
        re.compile(r"\bstatement\s+of\s+financial\s+position\b", re.IGNORECASE),
        re.compile(r"\bbalance\s+sheet\b", re.IGNORECASE),
    ],
    "cash_flow": [
        re.compile(r"\bstatement\s+of\s+cash\s+flows?\b", re.IGNORECASE),
        re.compile(r"\bcash\s+flow\s+statement\b", re.IGNORECASE),
    ],
}

SUPPORT_PATTERNS = {
    "income_statement": [
        re.compile(r"\brevenue\b", re.IGNORECASE),
        re.compile(r"\bebit\b", re.IGNORECASE),
        re.compile(r"\bprofit\s*/?\s*\(?loss\)?\b", re.IGNORECASE),
    ],
    "balance_sheet": [
        re.compile(r"\btotal\s+assets?\b", re.IGNORECASE),
        re.compile(r"\btotal\s+liabilities?\b", re.IGNORECASE),
        re.compile(r"\btotal\s+equity\b", re.IGNORECASE),
        re.compile(r"\bnet\s+assets?\b", re.IGNORECASE),
    ],
    "cash_flow": [
        re.compile(r"\boperating\s+activities\b", re.IGNORECASE),
        re.compile(r"\binvesting\s+activities\b", re.IGNORECASE),
        re.compile(r"\bfinancing\s+activities\b", re.IGNORECASE),
    ],
}

EXCLUSION_PAGE_PATTERNS = [
    re.compile(r"\bnotes?\s+to\s+the\s+financial\s+statements?\b", re.IGNORECASE),
    re.compile(r"\breconciliation\b", re.IGNORECASE),
    re.compile(r"\bnon[-\s]?ifrs\b", re.IGNORECASE),
    re.compile(r"\bunderlying\b", re.IGNORECASE),
    re.compile(r"\badjusted\b", re.IGNORECASE),
]

CASHFLOW_CONTINUATION_MAX_PAGES = 2

CASHFLOW_CONTINUATION_PATTERNS = [
    re.compile(r"\boperating\s+activities\b", re.IGNORECASE),
    re.compile(r"\binvesting\s+activities\b", re.IGNORECASE),
    re.compile(r"\bfinancing\s+activities\b", re.IGNORECASE),
    re.compile(r"\bcash\s+generated\s+from\s+operations\b", re.IGNORECASE),
    re.compile(r"\bnet\s+operating\s+cash\s+flow\b", re.IGNORECASE),
    re.compile(r"\bnet\s+cash\b", re.IGNORECASE),
    re.compile(r"\bcash\s+and\s+cash\s+equivalents\b", re.IGNORECASE),
]

NOTES_HEADING_PATTERNS = [
    re.compile(r"\bnotes?\s+to\s+the\s+financial\s+statements?\b", re.IGNORECASE),
    re.compile(r"^\s*notes?\b", re.IGNORECASE),
]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SELF_DIR = Path(__file__).resolve().parent
# Support invocation from either repo root or scripts/ subdirectory
ROOT = _SELF_DIR.parent if _SELF_DIR.name == "scripts" else _SELF_DIR
EXTRACT = _load_module(ROOT / "scripts" / "extract_financial_metrics.py", "extract_financial_metrics")
VALIDATION = _load_module(ROOT / "scripts" / "validation_quality_cycle.py", "validation_quality_cycle")
FORENSIC = _load_module(ROOT / "balance_sheet_forensic_analysis.py", "balance_sheet_forensic_analysis")
CASHFLOW_ADAPTER = _load_module(ROOT / "scripts" / "cashflow_layout_adapter.py", "cashflow_layout_adapter")
ORCHESTRATOR = _load_module(ROOT / "scripts" / "extract_pass_orchestrator.py", "extract_pass_orchestrator")
PROVENANCE = _load_module(ROOT / "scripts" / "provenance_contract.py", "provenance_contract")
OCR_LAST_RESORT = _load_module(ROOT / "scripts" / "ocr_last_resort.py", "ocr_last_resort")
VALIDATION_GATES = _load_module(ROOT / "scripts" / "validation_gates.py", "validation_gates")


def _find_col(df: pd.DataFrame, candidates: Sequence[str], required: bool = False) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        got = lower.get(c.lower())
        if got:
            return got
    if required:
        raise ValueError(f"Missing required column; expected one of: {', '.join(candidates)}")
    return None


def _normalize_period(series: pd.Series) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip()
    dt = pd.to_datetime(raw, errors="coerce")
    out = raw.copy()
    out.loc[dt.notna()] = dt.loc[dt.notna()].dt.strftime("%Y-%m-%d")
    return out


def _norm_metric(metric: str) -> str:
    m = (metric or "").strip().lower()
    alias = {
        "npat": "net_income",
        "cash": "cash_and_equivalents",
        "cash_and_equivalents_opening": "cash_and_equivalents",
        "cash_and_equivalents_closing": "cash_and_equivalents",
        "capex": "capital_expenditure",
        "net_cash_from_operating_activities": "operating_cash_flow",
        "total_borrowings": "total_debt",
    }
    return alias.get(m, m)


def _period_sort_key(period: str) -> int:
    try:
        return int(str(period).replace("-", ""))
    except ValueError:
        return 0


def _safe_int(v: object, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _should_exclude_page(page_text: str, heading_text: str) -> bool:
    txt = f"{heading_text}\n{page_text}".strip()
    return any(p.search(txt) for p in EXCLUSION_PAGE_PATTERNS)


def _numeric_table_like(page_lines: List[Dict[str, object]]) -> bool:
    numeric_line_count = 0
    for ln in page_lines:
        nums = ln.get("numeric_words", [])
        count = len([t for t in nums if not bool(t.get("minor_for_table", False))])
        if count >= 2:
            numeric_line_count += 1
    return numeric_line_count >= 3


def _page_text(lines: List[Dict[str, object]]) -> Tuple[str, str]:
    all_text = "\n".join(str(ln.get("text", "")) for ln in lines if str(ln.get("text", "")).strip())
    heading_text = "\n".join(
        str(ln.get("text", ""))
        for ln in lines[:30]
        if str(ln.get("text", "")).strip()
    )
    return all_text, heading_text


def _has_statement_heading(text: str, section_types: Sequence[str]) -> bool:
    for section in section_types:
        for pat in HEADING_PATTERNS.get(section, []):
            if pat.search(text):
                return True
    return False


def _has_cashflow_continuation_cue(text: str) -> bool:
    return any(p.search(text) for p in CASHFLOW_CONTINUATION_PATTERNS)


def _is_notes_heading(text: str) -> bool:
    return any(p.search(text) for p in NOTES_HEADING_PATTERNS)


def build_section_index_for_pdf(pdf: Path, prepared_pages: Dict[int, List[Dict[str, object]]]) -> Dict[str, object]:
    sections: Dict[str, Dict[str, object]] = {
        s: {"pages": [], "signals": []} for s in SECTION_TYPES
    }
    debug = {
        "cashflow_heading_pages": [],
        "cashflow_continuation_pages_added": [],
        "cashflow_stop_reasons": [],
    }
    if not prepared_pages:
        return {"file_id": pdf.stem, "sections": sections, "debug": debug}

    heading_pages: Dict[str, Set[int]] = {s: set() for s in SECTION_TYPES}
    page_cache: Dict[int, Tuple[str, str]] = {}

    for page in sorted(prepared_pages.keys()):
        all_text, heading_text = _page_text(prepared_pages[page])
        page_cache[page] = (all_text, heading_text)
        if _should_exclude_page(all_text, heading_text):
            continue
        text_for_heading = f"{heading_text}\n{all_text}"
        for section in SECTION_TYPES:
            matched = [pat.pattern for pat in HEADING_PATTERNS[section] if pat.search(text_for_heading)]
            if matched:
                heading_pages[section].add(page)
                sections[section]["signals"].extend(sorted(set(matched)))

    # Add heading pages first.
    for section in SECTION_TYPES:
        pages = sorted(heading_pages[section])
        sections[section]["pages"] = pages

    # Conservative continuation: include immediate numeric-table pages after a
    # heading page if no exclusion cues are present.
    all_heading_pages = set().union(*heading_pages.values()) if heading_pages else set()
    for section in SECTION_TYPES:
        if section == "cash_flow":
            continue
        page_set = set(sections[section]["pages"])
        changed = True
        while changed:
            changed = False
            for page in sorted(prepared_pages.keys()):
                if page in page_set:
                    continue
                prev = page - 1
                if prev not in page_set:
                    continue
                all_text, heading_text = page_cache.get(page, ("", ""))
                if _should_exclude_page(all_text, heading_text):
                    continue
                if page in all_heading_pages and page not in heading_pages[section]:
                    continue
                if _numeric_table_like(prepared_pages[page]):
                    page_set.add(page)
                    sections[section]["signals"].append("continuation_numeric_table")
                    changed = True
        sections[section]["pages"] = sorted(page_set)
        sections[section]["signals"] = sorted(set(sections[section]["signals"]))

    # Cash-flow continuation indexing: include continuation pages after a
    # cash-flow heading page while continuation cues persist.
    cashflow_page_set = set(sections["cash_flow"]["pages"])
    continuation_added: Set[int] = set()
    stop_reasons: Set[str] = set()
    sorted_pages = sorted(prepared_pages.keys())
    page_index = {p: idx for idx, p in enumerate(sorted_pages)}

    for heading_page in sorted(heading_pages["cash_flow"]):
        start_idx = page_index.get(heading_page)
        if start_idx is None:
            continue
        heading_stop_reason = ""
        for step in range(1, CASHFLOW_CONTINUATION_MAX_PAGES + 1):
            target_idx = start_idx + step
            if target_idx >= len(sorted_pages):
                heading_stop_reason = "max_pages"
                break
            page = sorted_pages[target_idx]
            all_text, heading_text = page_cache.get(page, ("", ""))
            text_for_heading = f"{heading_text}\n{all_text}".strip()

            if _has_statement_heading(text_for_heading, ("income_statement", "balance_sheet")):
                heading_stop_reason = "next_statement_heading"
                break
            if _is_notes_heading(text_for_heading):
                heading_stop_reason = "notes"
                break
            if _should_exclude_page(all_text, heading_text):
                heading_stop_reason = "excluded_page"
                break
            if not _has_cashflow_continuation_cue(text_for_heading):
                heading_stop_reason = "no_continuation_cue"
                break

            if page not in cashflow_page_set:
                continuation_added.add(page)
            cashflow_page_set.add(page)
            sections["cash_flow"]["signals"].append("continuation_cashflow_cue")
        else:
            heading_stop_reason = "max_pages"

        if heading_stop_reason:
            stop_reasons.add(heading_stop_reason)

    sections["cash_flow"]["pages"] = sorted(cashflow_page_set)
    sections["cash_flow"]["signals"] = sorted(set(sections["cash_flow"]["signals"]))
    debug["cashflow_heading_pages"] = sorted(heading_pages["cash_flow"])
    debug["cashflow_continuation_pages_added"] = sorted(continuation_added)
    debug["cashflow_stop_reasons"] = sorted(stop_reasons)
    return {"file_id": pdf.stem, "sections": sections, "debug": debug}


def _candidate_pdf_paths(canonical_df: pd.DataFrame, pdf_dir: Path) -> List[Path]:
    file_col = _find_col(canonical_df, FILE_CANDIDATES, required=False)
    paths: List[Path] = []
    if file_col:
        for v in canonical_df[file_col].dropna().astype(str).tolist():
            if not v.strip():
                continue
            p = Path(v).expanduser()
            if p.exists() and p.suffix.lower() == ".pdf":
                paths.append(p.resolve())
    if paths:
        return sorted(set(paths))
    if pdf_dir.exists():
        return sorted(p.resolve() for p in pdf_dir.rglob("*.pdf") if p.is_file())
    return []


def _prepare_canonical_df(canonical_df: pd.DataFrame) -> pd.DataFrame:
    period_col = _find_col(canonical_df, PERIOD_CANDIDATES, required=True)
    metric_col = _find_col(canonical_df, METRIC_CANDIDATES, required=True)
    file_col = _find_col(canonical_df, FILE_CANDIDATES, required=True)
    out = canonical_df.copy()
    out["period_end"] = _normalize_period(out[period_col])
    out["metric_norm"] = out[metric_col].fillna("").astype(str).map(_norm_metric)
    file_series = out[file_col].fillna("").astype(str).str.strip()

    def _normalize_file_path(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""
        p = Path(raw).expanduser()
        if p.exists():
            return str(p.resolve())
        return raw

    out["file_norm"] = file_series.map(_normalize_file_path)
    out = out[(out["period_end"] != "") & (out["metric_norm"] != "") & (out["file_norm"] != "")].copy()
    return out


def _build_currency_hints(canonical_df: pd.DataFrame) -> Tuple[Dict[Tuple[str, str], str], Dict[str, str]]:
    file_col = _find_col(canonical_df, FILE_CANDIDATES, required=False)
    period_col = _find_col(canonical_df, PERIOD_CANDIDATES, required=False)
    currency_col = _find_col(canonical_df, CURRENCY_CANDIDATES, required=False)
    if not file_col or not currency_col:
        return {}, {}

    tmp = canonical_df.copy()
    tmp["_file"] = tmp[file_col].fillna("").astype(str).str.strip()
    if period_col:
        tmp["_period_end"] = _normalize_period(tmp[period_col])
    else:
        tmp["_period_end"] = ""
    tmp["_currency"] = tmp[currency_col].fillna("").astype(str).str.strip()
    tmp = tmp[(tmp["_file"] != "") & (tmp["_currency"] != "")]
    if tmp.empty:
        return {}, {}

    by_file_period: Dict[Tuple[str, str], str] = {}
    by_file: Dict[str, str] = {}
    for (file_path, period_end), grp in tmp.groupby(["_file", "_period_end"], dropna=False):
        currencies = sorted(set(c for c in grp["_currency"].tolist() if str(c).strip() and str(c).upper() != "UNKNOWN"))
        if len(currencies) == 1:
            by_file_period[(str(file_path), str(period_end))] = str(currencies[0])
    for file_path, grp in tmp.groupby("_file", dropna=False):
        currencies = sorted(set(c for c in grp["_currency"].tolist() if str(c).strip() and str(c).upper() != "UNKNOWN"))
        if len(currencies) == 1:
            by_file[str(file_path)] = str(currencies[0])
    return by_file_period, by_file


def _apply_currency_hints(
    rows: Sequence[Dict[str, object]],
    *,
    by_file_period: Dict[Tuple[str, str], str],
    by_file: Dict[str, str],
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        rr = dict(row)
        currency = str(rr.get("currency", "")).strip()
        if currency and currency.upper() != "UNKNOWN":
            out.append(rr)
            continue
        file_path = str(rr.get("file", "")).strip()
        period_end = str(rr.get("statement_period_end", "")).strip()
        hint = by_file_period.get((file_path, period_end), "")
        if not hint:
            hint = by_file.get(file_path, "")
        if hint:
            rr["currency"] = hint
            rr["currency_inferred_from_doc_context"] = 1
        out.append(rr)
    return out


def _ticker_from_file_path(file_path: str) -> str:
    parts = Path(str(file_path or "")).parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return str(parts[idx + 1]).upper()
    return ""


def _normalize_currency_token(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    up = raw.upper()
    mapping = {
        "USD": "US$",
        "US$": "US$",
        "US DOLLAR": "US$",
        "AUD": "A$",
        "A$": "A$",
        "NZD": "NZ$",
        "NZ$": "NZ$",
    }
    return mapping.get(up, raw)


def _is_missing_currency(value: object) -> bool:
    text = str(value or "").strip()
    return (not text) or text.upper() == "UNKNOWN"


def _is_generic_currency(value: object) -> bool:
    text = str(value or "").strip()
    return _is_missing_currency(text) or text == "$"


def _backfill_missing_currency(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    file_col = _find_col(merged_df, FILE_CANDIDATES, required=False)
    currency_col = _find_col(merged_df, CURRENCY_CANDIDATES, required=False)
    if not file_col or not currency_col or merged_df.empty:
        return merged_df, {
            "rows_input": int(len(merged_df)),
            "rows_missing_before": 0,
            "rows_filled_from_file_hint": 0,
            "rows_filled_from_ticker_hint": 0,
            "rows_missing_after": 0,
        }

    out = merged_df.copy()
    out["_file_norm"] = out[file_col].fillna("").astype(str).str.strip()
    out["_currency_norm"] = out[currency_col].fillna("").map(_normalize_currency_token)

    rows_missing_before = int(out["_currency_norm"].map(_is_missing_currency).sum())
    if rows_missing_before == 0:
        out = out.drop(columns=["_file_norm", "_currency_norm"], errors="ignore")
        return out, {
            "rows_input": int(len(merged_df)),
            "rows_missing_before": int(rows_missing_before),
            "rows_filled_from_file_hint": 0,
            "rows_filled_from_ticker_hint": 0,
            "rows_missing_after": 0,
        }

    file_hints: Dict[str, str] = {}
    for file_path, grp in out.groupby("_file_norm", dropna=False):
        if not str(file_path).strip():
            continue
        candidates = sorted(
            {
                str(c).strip()
                for c in grp["_currency_norm"].tolist()
                if not _is_generic_currency(c)
            }
        )
        if len(candidates) == 1:
            file_hints[str(file_path)] = candidates[0]

    ticker_counts: Dict[str, Counter] = {}
    for rec in out[["_file_norm", "_currency_norm"]].to_dict(orient="records"):
        file_path = str(rec["_file_norm"])
        currency = str(rec["_currency_norm"])
        if not file_path or _is_generic_currency(currency):
            continue
        ticker = _ticker_from_file_path(file_path)
        if not ticker:
            continue
        ticker_counts.setdefault(ticker, Counter())[currency] += 1

    ticker_hints: Dict[str, str] = {}
    for ticker, counts in ticker_counts.items():
        if not counts:
            continue
        top_currency, top_count = counts.most_common(1)[0]
        total = int(sum(counts.values()))
        if total <= 0:
            continue
        share = float(top_count / total)
        # Conservative fallback: only use ticker-level inference with strong dominance.
        if top_count >= 5 and share >= 0.9:
            ticker_hints[ticker] = str(top_currency)

    rows_filled_file = 0
    rows_filled_ticker = 0
    for idx, rec in out[["_file_norm", "_currency_norm"]].to_dict(orient="index").items():
        if not _is_missing_currency(rec["_currency_norm"]):
            continue
        file_path = str(rec["_file_norm"]).strip()
        if not file_path:
            continue
        hint = file_hints.get(file_path, "")
        if hint:
            out.at[idx, currency_col] = hint
            out.at[idx, "_currency_norm"] = hint
            out.at[idx, "currency_inferred_from_file_context"] = 1
            rows_filled_file += 1
            continue
        ticker = _ticker_from_file_path(file_path)
        hint = ticker_hints.get(ticker, "")
        if hint:
            out.at[idx, currency_col] = hint
            out.at[idx, "_currency_norm"] = hint
            out.at[idx, "currency_inferred_from_ticker_context"] = 1
            rows_filled_ticker += 1

    rows_missing_after = int(out["_currency_norm"].map(_is_missing_currency).sum())
    out = out.drop(columns=["_file_norm", "_currency_norm"], errors="ignore")
    stats = {
        "rows_input": int(len(merged_df)),
        "rows_missing_before": int(rows_missing_before),
        "rows_filled_from_file_hint": int(rows_filled_file),
        "rows_filled_from_ticker_hint": int(rows_filled_ticker),
        "rows_missing_after": int(rows_missing_after),
    }
    return out, stats


def _build_file_period_presence(canonical_df: pd.DataFrame) -> Dict[Tuple[str, str], Set[str]]:
    prepared = _prepare_canonical_df(canonical_df)
    out: Dict[Tuple[str, str], Set[str]] = {}
    for rec in prepared[["file_norm", "period_end", "metric_norm"]].to_dict(orient="records"):
        key = (str(rec["file_norm"]), str(rec["period_end"]))
        out.setdefault(key, set()).add(str(rec["metric_norm"]))
    return out


def _missing_sections_for_period(metrics: Set[str]) -> Set[str]:
    missing: Set[str] = set()
    has_income_core = INCOME_CORE.issubset(metrics)
    has_balance_sheet_core = BALANCE_SHEET_CORE.issubset(metrics)
    has_cashflow_core = (
        ("operating_cash_flow" in metrics and "capital_expenditure" in metrics)
        or ("free_cash_flow" in metrics)
    )
    if has_income_core and not has_balance_sheet_core:
        missing.add("balance_sheet")
    if has_income_core and not has_cashflow_core:
        missing.add("cash_flow")
    return missing


def _build_pdf_missing_sections(file_period_presence: Dict[Tuple[str, str], Set[str]]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for (file_path, _period), metrics in file_period_presence.items():
        missing = _missing_sections_for_period(metrics)
        if not missing:
            continue
        out.setdefault(file_path, set()).update(missing)
    return out


def _build_pdf_missing_periods_by_section(
    file_period_presence: Dict[Tuple[str, str], Set[str]]
) -> Dict[str, Dict[str, Set[str]]]:
    out: Dict[str, Dict[str, Set[str]]] = {}
    for (file_path, period_end), metrics in file_period_presence.items():
        missing = _missing_sections_for_period(metrics)
        if not missing:
            continue
        by_section = out.setdefault(file_path, {})
        for section in missing:
            by_section.setdefault(section, set()).add(period_end)
    return out


def _context_has_exclusion(text: str) -> bool:
    t = str(text or "")
    return any(p.search(t) for p in EXCLUSION_PAGE_PATTERNS)


def _normalize_candidate_row(rr: Dict[str, object], canonical_columns: Sequence[str]) -> Dict[str, object]:
    out = {c: "" for c in canonical_columns}
    for c in canonical_columns:
        if c in rr:
            out[c] = rr[c]
    # Ensure minimum expected fields.
    out["file"] = out.get("file", rr.get("file", ""))
    out["metric"] = out.get("metric", rr.get("metric", ""))
    out["metric_base"] = out.get("metric_base", rr.get("metric_base", out.get("metric", "")))
    out["statement_period_end"] = out.get("statement_period_end", rr.get("statement_period_end", ""))
    out["period"] = out.get("period", rr.get("period", ""))
    out["canonical_confidence_score"] = _safe_int(out.get("canonical_confidence_score", rr.get("canonical_confidence_score", 0)), 0)
    out["inside_table"] = bool(out.get("inside_table", rr.get("inside_table", True)))
    return out


def _normalize_numeric_value(value: object) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace(",", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _drop_ambiguous_cashflow_context_rows(
    canonical_df: pd.DataFrame,
    cand_df: pd.DataFrame,
) -> pd.DataFrame:
    if canonical_df.empty or cand_df.empty:
        return cand_df
    required_cols = {"file", "statement_period_end"}
    if not required_cols.issubset(canonical_df.columns) or not required_cols.issubset(cand_df.columns):
        return cand_df
    if "metric" not in canonical_df.columns and "metric_base" not in canonical_df.columns:
        return cand_df
    if "metric" not in cand_df.columns and "metric_base" not in cand_df.columns:
        return cand_df
    if "source_mode" not in cand_df.columns:
        return cand_df

    def _metric_series(df: pd.DataFrame) -> pd.Series:
        if "metric_base" in df.columns:
            return df["metric_base"].fillna(df.get("metric", "")).astype(str).map(_norm_metric)
        return df["metric"].fillna("").astype(str).map(_norm_metric)

    def _value_series(df: pd.DataFrame) -> pd.Series:
        val_col = df["value"].map(_normalize_numeric_value) if "value" in df.columns else pd.Series([None] * len(df), index=df.index)
        if "raw_value" in df.columns:
            raw_col = df["raw_value"].map(_normalize_numeric_value)
            return val_col.where(val_col.notna(), raw_col)
        return val_col

    base = canonical_df.copy()
    base["_metric_norm"] = _metric_series(base)
    base["_value_norm"] = _value_series(base)
    base["_period"] = base["statement_period_end"].fillna("").astype(str).str.strip()
    base["_file"] = base["file"].fillna("").astype(str).str.strip()
    base = base.loc[
        (base["_metric_norm"] == "operating_cash_flow")
        & (base["_file"] != "")
        & (base["_period"] != "")
        & (base["_value_norm"].notna())
    ].copy()
    if base.empty:
        return cand_df

    base["_value_key"] = base["_value_norm"].map(lambda v: round(float(v), 6))
    base_key_to_periods: Dict[Tuple[str, float], Set[str]] = {}
    for rec in base[["_file", "_value_key", "_period"]].to_dict(orient="records"):
        key = (str(rec["_file"]), float(rec["_value_key"]))
        base_key_to_periods.setdefault(key, set()).add(str(rec["_period"]))

    cand = cand_df.copy()
    cand["_metric_norm"] = _metric_series(cand)
    cand["_value_norm"] = _value_series(cand)
    cand["_period"] = cand["statement_period_end"].fillna("").astype(str).str.strip()
    cand["_file"] = cand["file"].fillna("").astype(str).str.strip()
    cand["_source_mode"] = cand["source_mode"].fillna("").astype(str).str.strip().str.lower()
    cand["_value_key"] = cand["_value_norm"].map(lambda v: round(float(v), 6) if pd.notna(v) else None)

    drop_idx: Set[int] = set()
    for idx, rec in cand[
        ["_metric_norm", "_file", "_period", "_source_mode", "_value_key"]
    ].to_dict(orient="index").items():
        if str(rec["_metric_norm"]) != "operating_cash_flow":
            continue
        if str(rec["_source_mode"]) != "cashflow_context_line":
            continue
        file_key = str(rec["_file"]).strip()
        period = str(rec["_period"]).strip()
        value_key = rec["_value_key"]
        if not file_key or not period or value_key is None:
            continue
        existing_periods = base_key_to_periods.get((file_key, float(value_key)), set())
        if existing_periods and period not in existing_periods:
            drop_idx.add(idx)

    if not drop_idx:
        return cand_df
    kept = cand.drop(index=list(drop_idx), errors="ignore")
    kept = kept.drop(
        columns=["_metric_norm", "_value_norm", "_period", "_file", "_source_mode", "_value_key"],
        errors="ignore",
    )
    return kept


def _merge_canonical_rows(
    canonical_df: pd.DataFrame,
    candidate_rows: List[Dict[str, object]],
) -> pd.DataFrame:
    if not candidate_rows:
        return canonical_df.copy()

    columns = list(canonical_df.columns)
    normalized_candidates = [_normalize_candidate_row(r, columns) for r in candidate_rows]
    if not normalized_candidates:
        return canonical_df.copy()
    cand_df = pd.DataFrame(normalized_candidates, columns=columns)
    if cand_df.empty:
        return canonical_df.copy()

    if "metric_base" in cand_df.columns:
        metric_series = cand_df["metric_base"].fillna(cand_df.get("metric", "")).astype(str).str.strip().str.lower()
        cand_df = cand_df.loc[metric_series != "cashflow_unmapped"].copy()

    if "statement_period_end" in cand_df.columns:
        period_series = cand_df["statement_period_end"].fillna("").astype(str).str.strip()
        cand_df = cand_df.loc[period_series != ""].copy()

    if "canonical_confidence_score" in cand_df.columns:
        conf_floor = int(getattr(EXTRACT, "CANONICAL_CONFIDENCE_THRESHOLD", 2) or 2)
        conf_series = pd.to_numeric(cand_df["canonical_confidence_score"], errors="coerce").fillna(0).astype(int)
        cand_df = cand_df.loc[conf_series >= conf_floor].copy()

    if cand_df.empty:
        return canonical_df.copy()
    cand_df = _drop_ambiguous_cashflow_context_rows(canonical_df, cand_df)
    if cand_df.empty:
        return canonical_df.copy()

    base_df = canonical_df.copy()
    base_df["_is_new_candidate"] = 0
    cand_df["_is_new_candidate"] = 1

    combined = pd.concat([base_df, cand_df], ignore_index=True, sort=False)

    for col in ["canonical_confidence_score", "line_no", "page_number"]:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce").fillna(0)
    for col in ["statement_period_end", "metric", "metric_variant", "balance_position", "file"]:
        if col in combined.columns:
            combined[col] = combined[col].fillna("").astype(str)

    sort_cols = []
    asc = []
    if "canonical_confidence_score" in combined.columns:
        sort_cols.append("canonical_confidence_score")
        asc.append(False)
    if "_is_new_candidate" in combined.columns:
        sort_cols.append("_is_new_candidate")
        asc.append(True)  # prefer existing rows on ties
    if "line_no" in combined.columns:
        sort_cols.append("line_no")
        asc.append(True)
    if sort_cols:
        combined = combined.sort_values(by=sort_cols, ascending=asc)

    key_cols = [c for c in ["file", "metric", "metric_variant", "statement_period_end", "balance_position", "raw_value"] if c in combined.columns]
    if key_cols:
        combined = combined.drop_duplicates(subset=key_cols, keep="first")

    rows = combined.drop(columns=["_is_new_candidate"], errors="ignore").to_dict(orient="records")
    # Reuse existing conflict and identity guards from extraction pipeline.
    kept_rows, _demoted = EXTRACT.resolve_canonical_conflicts(rows)
    kept_rows, _bs_demoted = EXTRACT.apply_balance_sheet_identity_guard(kept_rows)
    kept_rows = EXTRACT.dedupe(kept_rows)

    out = pd.DataFrame(kept_rows)
    # Keep column order deterministic and include any new columns at tail.
    ordered_cols = list(canonical_df.columns) + [c for c in out.columns if c not in canonical_df.columns]
    out = out.reindex(columns=ordered_cols)
    return out


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _join_unique(values: Iterable[object], limit: int = 3) -> str:
    out: List[str] = []
    seen = set()
    for v in values:
        s = str(v).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return " | ".join(out)


def _safe_ratio_loss(before_count: int, after_count: int) -> float:
    if before_count <= 0:
        return 0.0
    loss = (before_count - after_count) / float(before_count)
    if loss < 0:
        loss = 0.0
    return float(round(loss, 6))


def _run_validation_and_forensic(
    canonical_df: pd.DataFrame,
    derived_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    out_dir: Path,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    VALIDATION.run_validation(canonical_df, derived_df, risk_df, out_dir)
    validation_summary_path = out_dir / "validation_summary.json"
    validation_summary = json.loads(validation_summary_path.read_text(encoding="utf-8"))
    forensic_summary = FORENSIC.run_forensic(canonical_df, out_dir, min_confidence=0)
    return validation_summary, forensic_summary


def run_section_capture_layer(
    pdf_dir: Path,
    canonical_path: Path,
    out_dir: Path,
    *,
    force_section_pass: bool = False,
    audit_cashflow_pre_scope: bool = False,
    audit_max_pages_per_pdf: int = 2,
) -> Dict[str, object]:
    canonical_df = pd.read_csv(canonical_path)
    canonical_parent = canonical_path.parent
    derived_df = _read_optional_csv(canonical_parent / "derived_metrics.csv")
    risk_df = _read_optional_csv(canonical_parent / "risk_signals.csv")

    before_dir = out_dir / "section_capture_before"
    after_dir = out_dir / "section_capture_after"
    before_validation, before_forensic = _run_validation_and_forensic(canonical_df, derived_df, risk_df, before_dir)

    structural_detected = bool(before_forensic.get("structural_pattern_detected", False))
    full_statements_before = int(before_forensic.get("counts", {}).get("full_statements_present", 0))
    auto_enable = structural_detected and full_statements_before == 0
    section_pass_enabled = bool(force_section_pass or auto_enable)

    audit_enabled = bool(audit_cashflow_pre_scope)
    run_id = out_dir.name
    audit_target_periods_all: Set[str] = set()
    forensic_before_df = _read_optional_csv(before_dir / "balance_sheet_forensic_summary.csv")
    if not forensic_before_df.empty and {"period_end", "has_cashflow_core"}.issubset(forensic_before_df.columns):
        audit_target_periods_all = set(
            forensic_before_df.loc[
                pd.to_numeric(forensic_before_df["has_cashflow_core"], errors="coerce").fillna(0).astype(int) == 0,
                "period_end",
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .tolist()
        )
        audit_target_periods_all.discard("")

    file_period_presence = _build_file_period_presence(canonical_df)
    missing_sections_by_pdf = _build_pdf_missing_sections(file_period_presence)
    missing_periods_by_pdf_section = _build_pdf_missing_periods_by_section(file_period_presence)

    pdf_paths = _candidate_pdf_paths(canonical_df, pdf_dir)
    section_index_dir = out_dir / "section_index"
    section_index_dir.mkdir(parents=True, exist_ok=True)

    candidate_rows: List[Dict[str, object]] = []
    raw_candidate_rows_count = 0
    section_index_paths: List[str] = []
    section_index_debug_rows: List[Dict[str, object]] = []
    processed_pdf_count = 0
    rows_added_from_cashflow_adapter = 0
    adapter_rows_pre_scope_total = 0
    adapter_rows_emitted_unmapped_total = 0
    adapter_rows_mapped_capex_total = 0
    adapter_rows_mapped_capex_v2_total = 0
    adapter_capex_rows_stitched_total = 0
    adapter_capex_rows_reconstructed_total = 0
    adapter_capex_rows_consumed_total = 0
    adapter_capex_rows_xy_paired_total = 0
    adapter_capex_xy_pair_candidates_total = 0
    adapter_capex_xy_pair_attempt_count = 0
    adapter_capex_rows_recovered_via_table_fallback_total = 0
    adapter_camelot_pages_scanned_total = 0
    adapter_camelot_tables_found_total = 0
    adapter_capex_rows_phrase_match_total = 0
    adapter_capex_rows_numeric_failed_total = 0
    adapter_capex_rows_fallback_eligible_total = 0
    adapter_camelot_pages_with_eligible_rows_total = 0
    adapter_camelot_fallback_invocation_attempted_total = 0
    adapter_camelot_fallback_blocked_by_gate_total = 0
    adapter_fallback_block_reason_phrase_not_matched_total = 0
    adapter_fallback_block_reason_statutory_mismatch_total = 0
    adapter_fallback_block_reason_not_cashflow_page_total = 0
    adapter_fallback_block_reason_numeric_not_failed_total = 0
    adapter_fallback_block_reason_no_eligible_pages_total = 0
    adapter_rows_mapped_ocf_total = 0
    ocr_pages_considered_total = 0
    ocr_pages_triggered_total = 0
    ocr_dependency_missing_total = 0
    ocr_pages_attempted_total = 0
    ocr_pages_succeeded_total = 0
    ocr_rows_emitted_total = 0
    ocr_disabled = str(os.environ.get("SECTION_CAPTURE_DISABLE_OCR", "0")).strip().lower() in {"1", "true", "yes", "on"}
    capex_periods_v2_after_set: Set[str] = set()
    pdfs_with_cashflow_heading = 0
    continuation_pages_added_total = 0
    cashflow_pages_before_total = 0
    cashflow_pages_after_total = 0
    audit_pre_scope_rows: List[Dict[str, object]] = []
    audit_post_scope_rows: List[Dict[str, object]] = []
    audit_canonical_written_rows: List[Dict[str, object]] = []
    audit_target_periods_hit: Set[str] = set()
    audit_target_pdfs_hit: Set[str] = set()
    audit_target_pages_total = 0

    for pdf in pdf_paths:
        pdf_candidate_rows_before = int(len(candidate_rows))
        prepared_pages = EXTRACT._prepare_bbox_pages(pdf)
        section_index = build_section_index_for_pdf(pdf, prepared_pages)
        section_debug = section_index.get("debug", {}) if isinstance(section_index, dict) else {}
        heading_pages = sorted(
            int(p) for p in section_debug.get("cashflow_heading_pages", []) if str(p).strip()
        )
        continuation_pages = sorted(
            int(p) for p in section_debug.get("cashflow_continuation_pages_added", []) if str(p).strip()
        )
        final_cashflow_pages = sorted(
            int(p) for p in section_index.get("sections", {}).get("cash_flow", {}).get("pages", []) if str(p).strip()
        )
        stop_reasons = sorted(str(s) for s in section_debug.get("cashflow_stop_reasons", []) if str(s).strip())
        if heading_pages:
            pdfs_with_cashflow_heading += 1
        continuation_pages_added_total += len(continuation_pages)
        cashflow_pages_before_total += len(heading_pages)
        cashflow_pages_after_total += len(final_cashflow_pages)
        section_index_debug_rows.append(
            {
                "file_stem": pdf.stem,
                "cashflow_heading_pages": ",".join(str(p) for p in heading_pages),
                "cashflow_continuation_pages_added": ",".join(str(p) for p in continuation_pages),
                "final_cashflow_pages": ",".join(str(p) for p in final_cashflow_pages),
                "stop_reason": ",".join(stop_reasons),
            }
        )
        index_path = section_index_dir / f"{pdf.stem}.section_index.json"
        index_path.write_text(json.dumps(section_index, indent=2), encoding="utf-8")
        section_index_paths.append(str(index_path))

        missing_sections = missing_sections_by_pdf.get(str(pdf), set())
        missing_periods_for_pdf = missing_periods_by_pdf_section.get(str(pdf), {})
        cashflow_missing_periods = set(missing_periods_for_pdf.get("cash_flow", set()))
        audit_target_periods_for_pdf = set(cashflow_missing_periods)
        if audit_target_periods_all:
            audit_target_periods_for_pdf &= audit_target_periods_all
        audit_target_pages_for_pdf = sorted(final_cashflow_pages)
        if audit_max_pages_per_pdf > 0:
            audit_target_pages_for_pdf = audit_target_pages_for_pdf[: int(audit_max_pages_per_pdf)]
        if audit_enabled and audit_target_periods_for_pdf and audit_target_pages_for_pdf:
            audit_target_periods_hit.update(audit_target_periods_for_pdf)
            audit_target_pdfs_hit.add(str(pdf))
            audit_target_pages_total += len(audit_target_pages_for_pdf)

        if not section_pass_enabled:
            continue
        if not missing_sections:
            continue
        source_kind = EXTRACT.classify_pdf_source_kind(pdf)

        # Cashflow layout adapter activation (section-scoped).
        run_cashflow_layout_adapter = bool("cash_flow" in missing_sections and cashflow_missing_periods)

        selected_balance_pages: Set[int] = set()
        if "balance_sheet" in missing_sections:
            selected_balance_pages.update(
                int(p) for p in section_index.get("sections", {}).get("balance_sheet", {}).get("pages", [])
            )
        selected_cashflow_pages: Set[int] = set()
        if "cash_flow" in missing_sections:
            selected_cashflow_pages.update(
                int(p) for p in section_index.get("sections", {}).get("cash_flow", {}).get("pages", [])
            )

        if run_cashflow_layout_adapter and selected_cashflow_pages:
            audit_collector = None
            if audit_enabled and audit_target_periods_for_pdf and audit_target_pages_for_pdf:
                audit_collector = {
                    "run_id": run_id,
                    "file_stem": pdf.stem,
                    "pdf_path": str(pdf),
                    "target_periods": sorted(audit_target_periods_for_pdf),
                    "target_pages": sorted(audit_target_pages_for_pdf),
                }
            adapter_rows, adapter_stats = CASHFLOW_ADAPTER.extract_cashflow_candidates(
                extract_mod=EXTRACT,
                pdf=pdf,
                source_kind=source_kind,
                prepared_pages=prepared_pages,
                selected_cashflow_pages=selected_cashflow_pages,
                missing_periods=cashflow_missing_periods,
                exclusion_fn=_context_has_exclusion,
                audit_collector=audit_collector,
            )
            rows_added_from_cashflow_adapter += len(adapter_rows)
            adapter_rows_pre_scope_total += int(adapter_stats.get("rows_scoped", 0) or 0)
            adapter_rows_emitted_unmapped_total += int(adapter_stats.get("rows_emitted_unmapped_numeric", 0) or 0)
            adapter_rows_mapped_capex_total += int(adapter_stats.get("rows_mapped_to_capex", 0) or 0)
            adapter_rows_mapped_capex_v2_total += int(adapter_stats.get("rows_mapped_to_capex_v2", 0) or 0)
            adapter_capex_rows_stitched_total += int(adapter_stats.get("capex_rows_stitched", 0) or 0)
            adapter_capex_rows_reconstructed_total += int(adapter_stats.get("capex_rows_reconstructed", 0) or 0)
            adapter_capex_rows_consumed_total += int(adapter_stats.get("capex_rows_consumed_following_lines", 0) or 0)
            adapter_capex_rows_xy_paired_total += int(adapter_stats.get("capex_rows_xy_paired", 0) or 0)
            adapter_capex_xy_pair_candidates_total += int(
                adapter_stats.get("capex_xy_pair_candidates_considered_total", 0) or 0
            )
            adapter_capex_xy_pair_attempt_count += int(adapter_stats.get("capex_xy_pair_attempt_count", 0) or 0)
            adapter_capex_rows_recovered_via_table_fallback_total += int(
                adapter_stats.get("capex_rows_recovered_via_table_fallback", 0) or 0
            )
            adapter_camelot_pages_scanned_total += int(adapter_stats.get("camelot_pages_scanned", 0) or 0)
            adapter_camelot_tables_found_total += int(adapter_stats.get("camelot_tables_found", 0) or 0)
            adapter_capex_rows_phrase_match_total += int(adapter_stats.get("capex_rows_phrase_match", 0) or 0)
            adapter_capex_rows_numeric_failed_total += int(adapter_stats.get("capex_rows_numeric_failed", 0) or 0)
            adapter_capex_rows_fallback_eligible_total += int(
                adapter_stats.get("capex_rows_fallback_eligible", 0) or 0
            )
            adapter_camelot_pages_with_eligible_rows_total += int(
                adapter_stats.get("camelot_pages_with_eligible_rows", 0) or 0
            )
            adapter_camelot_fallback_invocation_attempted_total += int(
                adapter_stats.get("camelot_fallback_invocation_attempted", 0) or 0
            )
            adapter_camelot_fallback_blocked_by_gate_total += int(
                adapter_stats.get("camelot_fallback_blocked_by_gate", 0) or 0
            )
            adapter_fallback_block_reason_phrase_not_matched_total += int(
                adapter_stats.get("fallback_block_reason_phrase_not_matched", 0) or 0
            )
            adapter_fallback_block_reason_statutory_mismatch_total += int(
                adapter_stats.get("fallback_block_reason_statutory_mismatch", 0) or 0
            )
            adapter_fallback_block_reason_not_cashflow_page_total += int(
                adapter_stats.get("fallback_block_reason_not_cashflow_page", 0) or 0
            )
            adapter_fallback_block_reason_numeric_not_failed_total += int(
                adapter_stats.get("fallback_block_reason_numeric_not_failed", 0) or 0
            )
            adapter_fallback_block_reason_no_eligible_pages_total += int(
                adapter_stats.get("fallback_block_reason_no_eligible_pages", 0) or 0
            )
            adapter_rows_mapped_ocf_total += int(adapter_stats.get("rows_mapped_to_ocf", 0) or 0)
            for rr in adapter_rows:
                mapped_src = str(rr.get("mapping_source", "")).strip()
                metric_base = _norm_metric(str(rr.get("metric_base", rr.get("metric", ""))))
                period_end = str(rr.get("statement_period_end", "")).strip()
                if mapped_src == "cashflow_phrase_map_v2" and metric_base == "capital_expenditure" and period_end:
                    capex_periods_v2_after_set.add(period_end)
            raw_candidate_rows_count += int(len(adapter_rows))
            candidate_rows.extend(adapter_rows)
            if audit_collector is not None:
                audit_pre_scope_rows.extend(audit_collector.get("pre_scope_rows", []))
                audit_post_scope_rows.extend(audit_collector.get("post_scope_rows", []))
                audit_canonical_written_rows.extend(audit_collector.get("canonical_written_rows", []))

        if selected_balance_pages:
            filtered_pages = {p: prepared_pages[p] for p in sorted(selected_balance_pages) if p in prepared_pages}
            if filtered_pages:
                blocks = EXTRACT.segment_statement_blocks(pdf, source_kind=source_kind, prepared_pages=filtered_pages)
                # Guardrail: drop blocks with explicit note/reconciliation/non-IFRS style context.
                filtered_blocks = []
                for b in blocks:
                    ctx = f"{b.get('title', '')}\n{b.get('context_text', '')}"
                    if _context_has_exclusion(ctx):
                        continue
                    filtered_blocks.append(b)
                if filtered_blocks:
                    rows = EXTRACT.extract_metrics_from_blocks(
                        pdf,
                        filtered_blocks,
                        strict_metric_rows_only=False,
                        prepared_pages=filtered_pages,
                    )
                    split = EXTRACT.split_rows_by_scope(rows)
                    rows_canonical = split.get("canonical_rows", [])
                    for rr in rows_canonical:
                        if int(rr.get("page_number", 0) or 0) not in selected_balance_pages:
                            continue
                        metric = _norm_metric(str(rr.get("metric_base", rr.get("metric", ""))))
                        if metric not in BALANCE_SHEET_METRICS:
                            continue
                        if _context_has_exclusion(
                            f"{rr.get('statement_title', '')} {rr.get('table_header_text', '')} {rr.get('row_label', '')}"
                        ):
                            continue
                        raw_candidate_rows_count += 1
                        candidate_rows.append(rr)

        selected_pages_for_ocr = sorted(set(selected_balance_pages) | set(selected_cashflow_pages))
        pdf_candidate_rows_added = int(len(candidate_rows) - pdf_candidate_rows_before)
        if selected_pages_for_ocr and pdf_candidate_rows_added == 0 and not ocr_disabled:
            missing_balance_periods = set(missing_periods_for_pdf.get("balance_sheet", set()))
            period_hint_candidates = sorted(set(cashflow_missing_periods) | set(missing_balance_periods))
            period_end_hint = period_hint_candidates[0] if period_hint_candidates else ""
            statement_type_hint = "cash_flow" if selected_cashflow_pages else "balance_sheet"
            ocr_rows, ocr_stats = OCR_LAST_RESORT.collect_ocr_candidates_for_pdf(
                pdf,
                pages=selected_pages_for_ocr,
                prepared_pages=prepared_pages,
                source_kind=source_kind,
                table_failed_pages=selected_pages_for_ocr,
                period_end_hint=period_end_hint,
                period_type_hint="",
                scope_hint="consolidated_statement",
                statement_type_hint=statement_type_hint,
            )
            ocr_pages_considered_total += int(ocr_stats.get("pages_considered", 0) or 0)
            ocr_pages_triggered_total += int(ocr_stats.get("pages_triggered", 0) or 0)
            ocr_dependency_missing_total += int(ocr_stats.get("dependency_missing", 0) or 0)
            ocr_pages_attempted_total += int(ocr_stats.get("pages_ocr_attempted", 0) or 0)
            ocr_pages_succeeded_total += int(ocr_stats.get("pages_ocr_succeeded", 0) or 0)
            ocr_rows_emitted_total += int(ocr_stats.get("rows_emitted", 0) or 0)
            raw_candidate_rows_count += int(len(ocr_rows))
            candidate_rows.extend(ocr_rows)

        if selected_balance_pages or selected_cashflow_pages:
            processed_pdf_count += 1

    section_index_debug_df = pd.DataFrame(
        section_index_debug_rows,
        columns=[
            "file_stem",
            "cashflow_heading_pages",
            "cashflow_continuation_pages_added",
            "final_cashflow_pages",
            "stop_reason",
        ],
    )
    if not section_index_debug_df.empty:
        section_index_debug_df = section_index_debug_df.sort_values(by=["file_stem"])
    section_index_debug_path = out_dir / "section_index_debug.csv"
    section_index_debug_df.to_csv(section_index_debug_path, index=False)

    pdfs_indexed = len(pdf_paths)
    continuation_summary = {
        "pdfs_indexed": int(pdfs_indexed),
        "pdfs_with_cashflow_heading": int(pdfs_with_cashflow_heading),
        "continuation_pages_added_total": int(continuation_pages_added_total),
        "avg_cashflow_pages_per_pdf_before": float(
            round(cashflow_pages_before_total / pdfs_indexed, 6) if pdfs_indexed else 0.0
        ),
        "avg_cashflow_pages_per_pdf_after": float(
            round(cashflow_pages_after_total / pdfs_indexed, 6) if pdfs_indexed else 0.0
        ),
    }
    continuation_summary_path = out_dir / "cashflow_continuation_summary.json"
    continuation_summary_path.write_text(json.dumps(continuation_summary, indent=2), encoding="utf-8")

    currency_by_file_period, currency_by_file = _build_currency_hints(canonical_df)
    candidate_rows = _apply_currency_hints(
        candidate_rows,
        by_file_period=currency_by_file_period,
        by_file=currency_by_file,
    )

    orchestrated = ORCHESTRATOR.select_canonical_candidates(candidate_rows)
    candidate_rows_for_merge = list(orchestrated.get("canonical_rows", []))
    orchestrator_context_rows = list(orchestrated.get("context_rows", []))
    orchestrator_quarantined_rows = list(orchestrated.get("quarantined_rows", []))
    orchestrator_stats = dict(orchestrated.get("stats", {}))
    orchestrator_summary_path = out_dir / "orchestrator_summary.json"
    orchestrator_summary_path.write_text(
        json.dumps(
            {
                "stats": orchestrator_stats,
                "rows_context": int(len(orchestrator_context_rows)),
                "rows_quarantined": int(len(orchestrator_quarantined_rows)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "orchestrator_context_rows.json").write_text(
        json.dumps(orchestrator_context_rows, indent=2),
        encoding="utf-8",
    )
    (out_dir / "orchestrator_quarantined_rows.json").write_text(
        json.dumps(orchestrator_quarantined_rows, indent=2),
        encoding="utf-8",
    )

    merged_df = _merge_canonical_rows(canonical_df, candidate_rows_for_merge)
    merged_df, currency_backfill_stats = _backfill_missing_currency(merged_df)
    quarantine_dir = out_dir / "quarantine"
    merged_df, quarantine_summary, gate_quarantined_rows = VALIDATION_GATES.apply_statement_level_quarantine_df(
        merged_df,
        out_dir=quarantine_dir,
    )
    quarantine_summary_path = quarantine_dir / "quarantine_summary.json"

    canonical_after_csv = out_dir / "canonical_section_capture.csv"
    canonical_after_json = out_dir / "canonical_section_capture.json"
    merged_df.to_csv(canonical_after_csv, index=False)
    canonical_after_json.write_text(json.dumps(merged_df.to_dict(orient="records"), indent=2), encoding="utf-8")

    cashflow_unmapped_summary_path = out_dir / "cashflow_unmapped_emission_summary.json"
    capex_periods_present_after = 0
    capex_periods_present_after_v2 = int(len(capex_periods_v2_after_set))
    ocf_periods_present_after = 0
    try:
        metric_col_after = _find_col(merged_df, METRIC_CANDIDATES, required=True)
        period_col_after = _find_col(merged_df, PERIOD_CANDIDATES, required=True)
        metric_series_after = merged_df[metric_col_after].fillna("").astype(str).map(_norm_metric)
        period_series_after = _normalize_period(merged_df[period_col_after])
        mapping_source_series = (
            merged_df["mapping_source"].fillna("").astype(str).str.strip()
            if "mapping_source" in merged_df.columns
            else None
        )
        capex_periods_present_after = int(
            period_series_after[metric_series_after == "capital_expenditure"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        )
        if mapping_source_series is not None:
            capex_periods_present_after_v2 = int(
                period_series_after[
                    (metric_series_after == "capital_expenditure")
                    & (mapping_source_series == "cashflow_phrase_map_v2")
                ]
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )
        ocf_periods_present_after = int(
            period_series_after[metric_series_after == "operating_cash_flow"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        )
    except Exception:
        capex_periods_present_after = 0
        capex_periods_present_after_v2 = int(len(capex_periods_v2_after_set))
        ocf_periods_present_after = 0

    cashflow_unmapped_summary = {
        "rows_pre_scope": int(adapter_rows_pre_scope_total),
        "rows_emitted_unmapped_numeric": int(adapter_rows_emitted_unmapped_total),
        "rows_mapped_to_capex": int(adapter_rows_mapped_capex_total),
        "rows_mapped_to_capex_v2": int(adapter_rows_mapped_capex_v2_total),
        "capex_rows_stitched": int(adapter_capex_rows_stitched_total),
        "capex_rows_reconstructed": int(adapter_capex_rows_reconstructed_total),
        "capex_rows_consumed_following_lines": int(adapter_capex_rows_consumed_total),
        "capex_rows_xy_paired": int(adapter_capex_rows_xy_paired_total),
        "capex_xy_pair_candidates_considered_avg": float(
            round(
                adapter_capex_xy_pair_candidates_total / adapter_capex_xy_pair_attempt_count,
                6,
            )
            if adapter_capex_xy_pair_attempt_count
            else 0.0
        ),
        "capex_rows_recovered_via_table_fallback": int(adapter_capex_rows_recovered_via_table_fallback_total),
        "camelot_pages_scanned": int(adapter_camelot_pages_scanned_total),
        "camelot_tables_found": int(adapter_camelot_tables_found_total),
        "capex_rows_phrase_match": int(adapter_capex_rows_phrase_match_total),
        "capex_rows_numeric_failed": int(adapter_capex_rows_numeric_failed_total),
        "capex_rows_fallback_eligible": int(adapter_capex_rows_fallback_eligible_total),
        "camelot_pages_with_eligible_rows": int(adapter_camelot_pages_with_eligible_rows_total),
        "camelot_fallback_invocation_attempted": int(adapter_camelot_fallback_invocation_attempted_total),
        "camelot_fallback_blocked_by_gate": int(adapter_camelot_fallback_blocked_by_gate_total),
        "fallback_block_reason_phrase_not_matched": int(adapter_fallback_block_reason_phrase_not_matched_total),
        "fallback_block_reason_statutory_mismatch": int(adapter_fallback_block_reason_statutory_mismatch_total),
        "fallback_block_reason_not_cashflow_page": int(adapter_fallback_block_reason_not_cashflow_page_total),
        "fallback_block_reason_numeric_not_failed": int(adapter_fallback_block_reason_numeric_not_failed_total),
        "fallback_block_reason_no_eligible_pages": int(adapter_fallback_block_reason_no_eligible_pages_total),
        "rows_mapped_to_ocf": int(adapter_rows_mapped_ocf_total),
        "capex_periods_present_after": int(capex_periods_present_after),
        "capex_periods_present_after_v2": int(capex_periods_present_after_v2),
        "ocf_periods_present_after": int(ocf_periods_present_after),
    }
    cashflow_unmapped_summary_path.write_text(
        json.dumps(cashflow_unmapped_summary, indent=2),
        encoding="utf-8",
    )

    audit_pre_scope_path = out_dir / "cashflow_pre_scope_rows.csv"
    audit_post_scope_path = out_dir / "cashflow_post_scope_rows.csv"
    audit_canonical_written_path = out_dir / "cashflow_canonical_written_rows.csv"
    audit_summary_path = out_dir / "cashflow_audit_summary.json"
    if audit_enabled:
        pre_cols = [
            "run_id",
            "file_stem",
            "pdf_path",
            "period_end",
            "page_number",
            "block_id",
            "row_idx",
            "raw_text",
            "raw_numeric_tokens",
            "numeric_token_count",
            "extracted_numeric_values",
            "chosen_numeric_value",
            "chosen_value",
            "numeric_parse_ok",
            "numeric_parse_reason",
            "consumed_by_reconstruction",
            "reconstruction_source_row_idx",
            "xy_pair_attempted",
            "xy_pair_success",
            "xy_pair_selected_source",
            "metric",
            "metric_base",
            "scope_stage",
        ]
        post_cols = pre_cols + ["scope", "context_reason"]
        written_cols = [
            "file_stem",
            "period_end",
            "page_number",
            "raw_text",
            "metric",
            "metric_base",
            "value",
            "canonical_confidence_score",
            "reason_if_dropped",
            "pdf_path",
            "scope_stage",
        ]

        pre_df = pd.DataFrame(audit_pre_scope_rows)
        post_df = pd.DataFrame(audit_post_scope_rows)
        written_df = pd.DataFrame(audit_canonical_written_rows)
        for c in pre_cols:
            if c not in pre_df.columns:
                pre_df[c] = ""
        for c in post_cols:
            if c not in post_df.columns:
                post_df[c] = ""
        for c in written_cols:
            if c not in written_df.columns:
                written_df[c] = ""
        pre_df = pre_df.reindex(columns=pre_cols)
        post_df = post_df.reindex(columns=post_cols)

        # Keep only rows that survive canonical merge, based on stable canonical key.
        merged_keys_full = set()
        merged_keys_basic = set()
        has_raw_value_col = "raw_value" in merged_df.columns
        key_cols = [c for c in ["file", "metric", "statement_period_end"] if c in merged_df.columns]
        if key_cols:
            cols = key_cols + (["raw_value"] if has_raw_value_col else [])
            for rec in merged_df[cols].to_dict(orient="records"):
                basic = (
                    str(rec.get("file", "")),
                    str(rec.get("metric", "")),
                    str(rec.get("statement_period_end", "")),
                )
                merged_keys_basic.add(basic)
                if has_raw_value_col:
                    merged_keys_full.add(basic + (str(rec.get("raw_value", "")),))

        kept_written_rows: List[Dict[str, object]] = []
        for rec in written_df.to_dict(orient="records"):
            key_basic = (
                str(rec.get("pdf_path", "")),
                str(rec.get("metric", "")),
                str(rec.get("period_end", "")),
            )
            key_full = key_basic + (str(rec.get("chosen_value", "")),)
            keep = False
            if not merged_keys_basic:
                keep = True
            elif has_raw_value_col:
                keep = key_full in merged_keys_full or key_basic in merged_keys_basic
            else:
                keep = key_basic in merged_keys_basic
            if keep:
                out = dict(rec)
                out["reason_if_dropped"] = ""
                kept_written_rows.append(out)
        written_df = pd.DataFrame(kept_written_rows)
        for c in written_cols:
            if c not in written_df.columns:
                written_df[c] = ""
        written_df = written_df.reindex(columns=written_cols)

        pre_df.to_csv(audit_pre_scope_path, index=False)
        post_df.to_csv(audit_post_scope_path, index=False)
        written_df.to_csv(audit_canonical_written_path, index=False)

        rows_pre_scope = int(len(pre_df))
        rows_post_scope_primary = int(
            len(post_df[post_df["scope"].astype(str).str.lower() == "primary"])
        )
        rows_post_scope_context = int(
            len(post_df[post_df["scope"].astype(str).str.lower() == "context"])
        )
        rows_written_canonical = int(len(written_df))
        rows_post_scope_total = rows_post_scope_primary + rows_post_scope_context

        pre_metric_base = (
            pre_df["metric_base"].fillna("").astype(str).str.strip().str.lower().tolist()
            if "metric_base" in pre_df.columns
            else []
        )
        unmapped_counter = Counter(
            m for m in pre_metric_base if m in {"", "unknown", "other"}
        )
        top_unmapped = [[k, int(v)] for k, v in unmapped_counter.most_common(20)]

        raw_text_lower = (
            pre_df["raw_text"].fillna("").astype(str).str.lower()
            if "raw_text" in pre_df.columns
            else pd.Series(dtype=str)
        )
        keyword_queries = {
            "investing": "investing",
            "property": "property",
            "plant": "plant",
            "equipment": "equipment",
            "additions": "additions",
            "purchase": "purchase",
            "payments": "payments",
            "capex": "capex",
            "financing": "financing",
            "capital": "capital",
        }
        keyword_counts = {
            key: int(raw_text_lower.str.contains(val, na=False).sum())
            for key, val in keyword_queries.items()
        }

        capex_like_mask = (
            raw_text_lower.str.contains("purchase", na=False)
            & (
                raw_text_lower.str.contains("property, plant and equipment", na=False)
                | raw_text_lower.str.contains("property plant and equipment", na=False)
            )
        )
        capex_like_df = pre_df[capex_like_mask].copy()
        capex_like_rows_pre_scope = int(len(capex_like_df))
        capex_like_rows_with_numeric_tokens = int(
            pd.to_numeric(capex_like_df.get("numeric_token_count", 0), errors="coerce")
            .fillna(0)
            .astype(int)
            .gt(0)
            .sum()
        )
        capex_like_rows_numeric_parse_ok = int(
            pd.to_numeric(capex_like_df.get("numeric_parse_ok", 0), errors="coerce")
            .fillna(0)
            .astype(int)
            .eq(1)
            .sum()
        )
        capex_like_rows_numeric_parse_failed = int(
            max(0, capex_like_rows_pre_scope - capex_like_rows_numeric_parse_ok)
        )
        fail_reason_counter = Counter(
            capex_like_df.loc[
                pd.to_numeric(capex_like_df.get("numeric_parse_ok", 0), errors="coerce")
                .fillna(0)
                .astype(int)
                .eq(0),
                "numeric_parse_reason",
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", "ambiguous")
            .tolist()
        )
        top_numeric_parse_fail_reasons = [
            [k, int(v)] for k, v in fail_reason_counter.most_common(10)
        ]

        audit_summary = {
            "target_periods": int(len(audit_target_periods_hit)),
            "target_pdfs": int(len(audit_target_pdfs_hit)),
            "target_pages": int(audit_target_pages_total),
            "counts": {
                "rows_pre_scope": rows_pre_scope,
                "rows_post_scope_primary": rows_post_scope_primary,
                "rows_post_scope_context": rows_post_scope_context,
                "rows_written_canonical": rows_written_canonical,
            },
            "drop_off": {
                "pre_to_post_scope_loss_pct": _safe_ratio_loss(rows_pre_scope, rows_post_scope_total),
                "post_scope_to_canonical_loss_pct": _safe_ratio_loss(rows_post_scope_total, rows_written_canonical),
            },
            "top_unmapped_metric_base_pre_scope": top_unmapped,
            "top_raw_text_contains_keywords": keyword_counts,
            "capex_numeric_audit": {
                "capex_like_rows_pre_scope": capex_like_rows_pre_scope,
                "capex_like_rows_with_numeric_tokens": capex_like_rows_with_numeric_tokens,
                "capex_like_rows_numeric_parse_ok": capex_like_rows_numeric_parse_ok,
                "capex_like_rows_numeric_parse_failed": capex_like_rows_numeric_parse_failed,
                "capex_rows_stitched": int(adapter_capex_rows_stitched_total),
                "capex_rows_reconstructed": int(adapter_capex_rows_reconstructed_total),
                "capex_rows_consumed_following_lines": int(adapter_capex_rows_consumed_total),
                "capex_rows_xy_paired": int(adapter_capex_rows_xy_paired_total),
                "capex_xy_pair_candidates_considered_avg": float(
                    round(
                        adapter_capex_xy_pair_candidates_total / adapter_capex_xy_pair_attempt_count,
                        6,
                    )
                    if adapter_capex_xy_pair_attempt_count
                    else 0.0
                ),
                "capex_rows_recovered_via_table_fallback": int(adapter_capex_rows_recovered_via_table_fallback_total),
                "camelot_pages_scanned": int(adapter_camelot_pages_scanned_total),
                "camelot_tables_found": int(adapter_camelot_tables_found_total),
                "capex_rows_phrase_match": int(adapter_capex_rows_phrase_match_total),
                "capex_rows_numeric_failed": int(adapter_capex_rows_numeric_failed_total),
                "capex_rows_fallback_eligible": int(adapter_capex_rows_fallback_eligible_total),
                "camelot_pages_with_eligible_rows": int(adapter_camelot_pages_with_eligible_rows_total),
                "camelot_fallback_invocation_attempted": int(adapter_camelot_fallback_invocation_attempted_total),
                "camelot_fallback_blocked_by_gate": int(adapter_camelot_fallback_blocked_by_gate_total),
                "fallback_block_reason_phrase_not_matched": int(
                    adapter_fallback_block_reason_phrase_not_matched_total
                ),
                "fallback_block_reason_statutory_mismatch": int(
                    adapter_fallback_block_reason_statutory_mismatch_total
                ),
                "fallback_block_reason_not_cashflow_page": int(
                    adapter_fallback_block_reason_not_cashflow_page_total
                ),
                "fallback_block_reason_numeric_not_failed": int(
                    adapter_fallback_block_reason_numeric_not_failed_total
                ),
                "fallback_block_reason_no_eligible_pages": int(
                    adapter_fallback_block_reason_no_eligible_pages_total
                ),
                "top_numeric_parse_fail_reasons": top_numeric_parse_fail_reasons,
            },
        }
        audit_summary_path.write_text(json.dumps(audit_summary, indent=2), encoding="utf-8")

    after_validation, after_forensic = _run_validation_and_forensic(merged_df, derived_df, risk_df, after_dir)
    full_statements_after = int(after_forensic.get("counts", {}).get("full_statements_present", 0))

    improvement = {
        "before": {
            "balance_sheet_completeness_mean": float(before_validation.get("balance_sheet_completeness_mean", 0.0)),
            "fcf_completeness_mean": float(before_validation.get("fcf_completeness_mean", 0.0)),
            "periods_full_statements_count": int(full_statements_before),
        },
        "after": {
            "balance_sheet_completeness_mean": float(after_validation.get("balance_sheet_completeness_mean", 0.0)),
            "fcf_completeness_mean": float(after_validation.get("fcf_completeness_mean", 0.0)),
            "periods_full_statements_count": int(full_statements_after),
        },
        "delta": {
            "balance_sheet_completeness_mean": float(
                float(after_validation.get("balance_sheet_completeness_mean", 0.0))
                - float(before_validation.get("balance_sheet_completeness_mean", 0.0))
            ),
            "fcf_completeness_mean": float(
                float(after_validation.get("fcf_completeness_mean", 0.0))
                - float(before_validation.get("fcf_completeness_mean", 0.0))
            ),
            "full_statements_added": int(full_statements_after - full_statements_before),
        },
        "section_pass_enabled": bool(section_pass_enabled),
        "section_pass_auto_triggered": bool(auto_enable),
        "candidate_rows_added": int(raw_candidate_rows_count),
        "candidate_rows_added_after_orchestrator": int(len(candidate_rows_for_merge)),
        "pdfs_indexed": int(pdfs_indexed),
        "pdfs_processed_in_section_pass": int(processed_pdf_count),
        "orchestrator_summary_json": str(orchestrator_summary_path),
        "orchestrator_context_rows_json": str(out_dir / "orchestrator_context_rows.json"),
        "orchestrator_quarantined_rows_json": str(out_dir / "orchestrator_quarantined_rows.json"),
        "quarantine_summary_json": str(quarantine_summary_path),
        "quarantine_rows_count": int(len(gate_quarantined_rows)),
        "section_index_files": section_index_paths,
        "section_index_debug_csv": str(section_index_debug_path),
        "cashflow_continuation_summary_json": str(continuation_summary_path),
        "cashflow_unmapped_emission_summary_json": str(cashflow_unmapped_summary_path),
        "ocr_stats": {
            "disabled": bool(ocr_disabled),
            "pages_considered": int(ocr_pages_considered_total),
            "pages_triggered": int(ocr_pages_triggered_total),
            "dependency_missing": int(ocr_dependency_missing_total),
            "pages_ocr_attempted": int(ocr_pages_attempted_total),
            "pages_ocr_succeeded": int(ocr_pages_succeeded_total),
            "rows_emitted": int(ocr_rows_emitted_total),
        },
        "validation_gate_stats": quarantine_summary,
        "currency_backfill_stats": currency_backfill_stats,
        "audit_cashflow_pre_scope_enabled": bool(audit_enabled),
        "cashflow_pre_scope_rows_csv": str(audit_pre_scope_path),
        "cashflow_post_scope_rows_csv": str(audit_post_scope_path),
        "cashflow_canonical_written_rows_csv": str(audit_canonical_written_path),
        "cashflow_audit_summary_json": str(audit_summary_path),
        "canonical_after_csv": str(canonical_after_csv),
        "canonical_after_json": str(canonical_after_json),
        "before_dir": str(before_dir),
        "after_dir": str(after_dir),
    }

    summary_path = out_dir / "section_capture_improvement_summary.json"
    summary_path.write_text(json.dumps(improvement, indent=2), encoding="utf-8")

    cashflow_partial_before = int(before_forensic.get("counts", {}).get("cashflow_partial", 0))
    cashflow_partial_after = int(after_forensic.get("counts", {}).get("cashflow_partial", 0))
    cashflow_adapter_summary = {
        "before": {
            "fcf_completeness_mean": float(before_validation.get("fcf_completeness_mean", 0.0)),
            "cashflow_partial_count": cashflow_partial_before,
            "periods_full_statements_count": int(full_statements_before),
        },
        "after": {
            "fcf_completeness_mean": float(after_validation.get("fcf_completeness_mean", 0.0)),
            "cashflow_partial_count": cashflow_partial_after,
            "periods_full_statements_count": int(full_statements_after),
        },
        "delta": {
            "fcf_completeness_mean": float(
                float(after_validation.get("fcf_completeness_mean", 0.0))
                - float(before_validation.get("fcf_completeness_mean", 0.0))
            ),
            "full_statements_added": int(full_statements_after - full_statements_before),
            "cashflow_periods_recovered": int(max(0, cashflow_partial_before - cashflow_partial_after)),
        },
        "rows_added_from_cashflow_adapter": int(rows_added_from_cashflow_adapter),
    }
    cashflow_summary_path = out_dir / "cashflow_adapter_improvement_summary.json"
    cashflow_summary_path.write_text(json.dumps(cashflow_adapter_summary, indent=2), encoding="utf-8")
    return {
        "summary_path": str(summary_path),
        "cashflow_adapter_summary_path": str(cashflow_summary_path),
        **improvement,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Section-aware multi-pass capture layer.")
    ap.add_argument("--pdf-dir", required=True, help="Directory containing PDFs (or run dir)")
    ap.add_argument("--canonical", required=True, help="Path to existing canonical.csv")
    ap.add_argument("--out-dir", required=True, help="Output run directory")
    ap.add_argument("--force-section-pass", action="store_true", help="Force section-aware second pass regardless of trigger.")
    ap.add_argument(
        "--audit-cashflow-pre-scope",
        type=int,
        default=0,
        help="Enable pre-scope/post-scope/canonical cashflow audit artifacts (1=on, 0=off).",
    )
    ap.add_argument(
        "--audit-max-pages-per-pdf",
        type=int,
        default=2,
        help="Maximum number of cashflow indexed pages per PDF to include in audit artifacts.",
    )
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    canonical_path = Path(args.canonical).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    if not canonical_path.exists():
        raise SystemExit(f"Canonical file not found: {canonical_path}")
    if not pdf_dir.exists():
        raise SystemExit(f"PDF directory not found: {pdf_dir}")

    result = run_section_capture_layer(
        pdf_dir=pdf_dir,
        canonical_path=canonical_path,
        out_dir=out_dir,
        force_section_pass=bool(args.force_section_pass),
        audit_cashflow_pre_scope=bool(int(args.audit_cashflow_pre_scope)),
        audit_max_pages_per_pdf=int(args.audit_max_pages_per_pdf),
    )

    print(f"Section pass enabled: {result['section_pass_enabled']}")
    print(f"Candidate rows added: {result['candidate_rows_added']}")
    print(f"PDFs indexed: {result['pdfs_indexed']}")
    print(f"PDFs processed in section pass: {result['pdfs_processed_in_section_pass']}")
    print(f"Output: {result['section_index_debug_csv']}")
    print(f"Output: {result['cashflow_continuation_summary_json']}")
    print(f"Output: {result['cashflow_unmapped_emission_summary_json']}")
    print(f"Output: {result['orchestrator_summary_json']}")
    print(f"Output: {result['quarantine_summary_json']}")
    if bool(result.get("audit_cashflow_pre_scope_enabled", False)):
        print(f"Output: {result['cashflow_pre_scope_rows_csv']}")
        print(f"Output: {result['cashflow_post_scope_rows_csv']}")
        print(f"Output: {result['cashflow_canonical_written_rows_csv']}")
        print(f"Output: {result['cashflow_audit_summary_json']}")
    print(f"Output: {result['summary_path']}")
    print(f"Output: {result['cashflow_adapter_summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
