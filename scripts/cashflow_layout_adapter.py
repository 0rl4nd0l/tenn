#!/usr/bin/env python3
"""Section-scoped cash flow layout adapter.

This module is intentionally isolated to cash-flow section pages and does not
modify global parser rules. It uses existing extractor primitives with a
cashflow-scoped tolerance mode and returns canonical candidates only after
passing through split_rows_by_scope.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import cashflow_table_fallback as CASHFLOW_TABLE_FALLBACK
except Exception:
    CASHFLOW_TABLE_FALLBACK = None


CASHFLOW_KEEP_TOKENS = (
    "net cash",
    "operating activities",
    "investing activities",
    "financing activities",
    "cash generated from operations",
    "net operating cash flow",
)

ROW_OPERATING_HINTS = (
    "net cash from operating activities",
    "cash generated from operations",
    "net operating cash flow",
)
ROW_CAPEX_HINTS = (
    "capital expenditure",
    "capex",
)

CAPEX_PHRASE_PATTERNS = (
    "purchases of property, plant and equipment",
    "purchase of property, plant and equipment",
    "purchases of property plant and equipment",
)
CAPEX_PHRASE_PATTERNS_V2 = (
    "additions to property, plant and equipment",
    "additions to property plant and equipment",
    "capital expenditure",
    "capital expenditures",
)
OPERATING_CF_PHRASE_PATTERNS = (
    "cash generated from operations",
    "net operating cash flow",
    "net operating cash flows",
)
CAPEX_EXCLUSION_TOKENS = (
    "impairment",
    "revaluation",
    "notes",
)

CASHFLOW_EMIT_UNMAPPED_NUMERIC_ROWS = True

CASHFLOW_METRIC_ALLOWLIST = {
    "operating_cash_flow",
    "capex",
    "capital_expenditure",
    "free_cash_flow",
    "cashflow_unmapped",
    "cash_and_equivalents",
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "net_debt",
    "total_debt",
}

CASHFLOW_SCOPE_BLOCKED_CONTEXT_REASONS = {
    "reconciliation_context",
    "cash_reconciliation_context",
    "acquisition_contribution_context",
    "low_canonical_confidence",
    "missing_statement_period_end",
    "narrative_row_label",
    "ambiguous_row_label",
    "metric_statement_mismatch",
    "non_canonical_scope",
    "cash_non_balance_context",
    "canonical_conflict_same_period",
    "canonical_duplicate_same_period",
}

NUMERIC_TOKEN_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?%?")
CASHFLOW_USE_RIGHTMOST_NUMERIC_IF_MULTIPLE = True
CASHFLOW_ENABLE_HORIZONTAL_RECONSTRUCTION = True
CASHFLOW_RECON_LOOKAHEAD_ROWS = 4
CASHFLOW_ENABLE_CROSS_BLOCK_PAIRING = True
CASHFLOW_XY_PAIR_Y_TOL = 8.0
CASHFLOW_NUMERIC_COL_MIN_X_MODE = "auto"
CASHFLOW_ENABLE_CAMELOT_FALLBACK = True
CASHFLOW_CAMELOT_MAX_PAGES_PER_PDF = 5
CASHFLOW_SCOPE_OVERRIDE_MIN_CANONICAL_CONFIDENCE = 2
CASHFLOW_EXCLUDE_UNMAPPED_FROM_CANONICAL = True


def _norm_text(*parts: object) -> str:
    return " ".join(str(p or "").strip() for p in parts if str(p or "").strip())


def _is_cashflow_heading(text: str) -> bool:
    t = text.lower()
    return (
        "statement of cash flow" in t
        or "statement of cash flows" in t
        or "cash flow statement" in t
        or "consolidated cash flow statement" in t
    )


def _has_keep_token(text: str) -> bool:
    t = text.lower()
    return any(tok in t for tok in CASHFLOW_KEEP_TOKENS)


def _source_scope(source_kind: str) -> str:
    sk = (source_kind or "").strip().lower()
    if sk.startswith("appendix"):
        return "appendix_statement"
    return "consolidated_statement"


def _has_numeric_value(rr: Dict[str, object]) -> bool:
    value_type = str(rr.get("value_type", "")).strip().lower()
    if value_type and value_type != "amount":
        return False
    raw_value = str(rr.get("raw_value", "")).strip()
    if raw_value:
        return True
    value = rr.get("value")
    try:
        if value is None:
            return False
        fv = float(value)
        if not math.isfinite(fv):
            return False
        return True
    except (TypeError, ValueError):
        return False


def _parse_numeric_token(token: str) -> Optional[float]:
    s = str(token or "").strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "")
    s = s.replace("%", "")
    try:
        v = float(s)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    return -v if neg else v


def _extract_numeric_values(rr: Dict[str, object]) -> List[str]:
    values: List[str] = []
    raw_value = str(rr.get("raw_value", "")).strip()
    if raw_value:
        values.append(raw_value)
    raw_values = rr.get("raw_values")
    if isinstance(raw_values, (list, tuple)):
        for v in raw_values:
            sv = str(v).strip()
            if sv:
                values.append(sv)
    line = str(rr.get("line", "")).strip()
    if line:
        for m in NUMERIC_TOKEN_RE.findall(line):
            sv = str(m).strip()
            if sv:
                values.append(sv)
    out: List[str] = []
    seen = set()
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _extract_years_from_text(text: str) -> List[str]:
    years = re.findall(r"\b(20\d{2})\b", str(text or ""))
    out: List[str] = []
    seen = set()
    for y in years:
        if y in seen:
            continue
        seen.add(y)
        out.append(y)
    return out


def _period_column_index(rr: Dict[str, object], token_count: int) -> Optional[int]:
    if token_count < 2:
        return None
    statement_period = str(rr.get("statement_period", "") or rr.get("period", "")).strip().lower()
    if "current quarter" in statement_period or "current period" in statement_period:
        return 0
    if "previous quarter" in statement_period or "previous period" in statement_period:
        return min(1, token_count - 1)

    statement_period_end = str(rr.get("statement_period_end", "")).strip()
    year = ""
    if statement_period_end:
        m = re.match(r"(\d{4})-\d{2}-\d{2}", statement_period_end)
        if m:
            year = m.group(1)
    if not year:
        return None

    header_text = _norm_text(rr.get("table_header_text", ""), rr.get("statement_title", ""))
    years = _extract_years_from_text(header_text)
    if len(years) >= 2 and token_count >= 2:
        if year == years[0]:
            return 0
        if year == years[1]:
            return min(1, token_count - 1)
    return None


def _select_numeric_token_for_cashflow_row(rr: Dict[str, object], tokens: List[str]) -> str:
    if not tokens:
        return ""
    if len(tokens) == 1:
        return str(tokens[0]).strip()
    idx = _period_column_index(rr, len(tokens))
    if idx is not None and 0 <= idx < len(tokens):
        return str(tokens[idx]).strip()
    if CASHFLOW_USE_RIGHTMOST_NUMERIC_IF_MULTIPLE:
        return str(tokens[-1]).strip()
    return str(tokens[0]).strip()


def _ensure_numeric_value_for_cashflow_row(rr: Dict[str, object]) -> None:
    if str(rr.get("numeric_parse_reason", "")).strip() in {
        "horizontal_table_reconstruction",
        "cross_block_xy_pairing",
        "camelot_lattice_recovery",
    }:
        raw_value = str(rr.get("raw_value", "")).strip()
        parsed = _parse_numeric_token(raw_value) if raw_value else None
        if parsed is not None:
            rr["value"] = parsed
        return
    tokens = _extract_numeric_values(rr)
    if len(tokens) > 1:
        selected = _select_numeric_token_for_cashflow_row(rr, tokens)
        parsed = _parse_numeric_token(selected) if selected else None
        if selected:
            rr["raw_value"] = selected
        if parsed is not None:
            rr["value"] = parsed
        return

    raw_value = str(rr.get("raw_value", "")).strip()
    parsed_raw = _parse_numeric_token(raw_value) if raw_value else None
    if parsed_raw is not None:
        rr["value"] = parsed_raw
        return

    selected = _select_numeric_token_for_cashflow_row(rr, tokens)
    parsed = _parse_numeric_token(selected) if selected else None
    if selected:
        rr["raw_value"] = selected
    if parsed is not None:
        rr["value"] = parsed


def _parse_bbox(value: object) -> Optional[Tuple[float, float, float, float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        try:
            x0 = float(value[0])
            y0 = float(value[1])
            x1 = float(value[2])
            y1 = float(value[3])
            return (x0, y0, x1, y1)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        nums = re.findall(r"-?\d+(?:\.\d+)?", value)
        if len(nums) >= 4:
            try:
                return (float(nums[0]), float(nums[1]), float(nums[2]), float(nums[3]))
            except ValueError:
                return None
    return None


def _row_bbox(rr: Dict[str, object]) -> Optional[Tuple[float, float, float, float]]:
    for key in ("row_bbox", "line_bbox", "bbox"):
        bbox = _parse_bbox(rr.get(key))
        if bbox is not None:
            return bbox
    x0 = rr.get("x0")
    y0 = rr.get("y0")
    x1 = rr.get("x1")
    y1 = rr.get("y1")
    try:
        if x0 is not None and y0 is not None and x1 is not None and y1 is not None:
            return (float(x0), float(y0), float(x1), float(y1))
    except (TypeError, ValueError):
        return None
    return None


def _row_center_y(rr: Dict[str, object]) -> Optional[float]:
    bbox = _row_bbox(rr)
    if bbox is None:
        return None
    return (bbox[1] + bbox[3]) / 2.0


def _row_x0(rr: Dict[str, object]) -> Optional[float]:
    bbox = _row_bbox(rr)
    if bbox is not None:
        return float(bbox[0])
    col_x = rr.get("col_x")
    try:
        if col_x is not None:
            return float(col_x)
    except (TypeError, ValueError):
        return None
    return None


def _quantile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    q = max(0.0, min(1.0, float(q)))
    idx = int(round((len(xs) - 1) * q))
    return xs[idx]


def _infer_cashflow_doc_type(pdf: Path, source_kind: str) -> str:
    text = f"{pdf} {source_kind}".lower()
    if any(tok in text for tok in ("presentation", "investor-day", "deck", "slides")):
        return "presentation_deck"
    if any(tok in text for tok in ("quarterly", "appendix-4c", "appendix-5b", "quarter")):
        return "quarterly_report"
    if any(tok in text for tok in ("half-year", "half-yearly", "interim")):
        return "half_year"
    if any(tok in text for tok in ("annual-report", "annual_report", "appendix-4e", "form-20-f", "preliminary-final-report")):
        return "statutory_annual"
    return "other"


def _is_capex_like_text(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False
    if any(p in t for p in CAPEX_PHRASE_PATTERNS):
        return True
    if any(p in t for p in CAPEX_PHRASE_PATTERNS_V2):
        return True
    return False


def _is_minimal_numeric_row_text(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    alpha_count = sum(1 for ch in t if ch.isalpha())
    # Allow short suffixes like "note 5" while remaining numeric-dominant.
    if alpha_count <= 6:
        return True
    return False


def _is_numeric_dominant_line(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    return bool(NUMERIC_TOKEN_RE.findall(t)) and _is_minimal_numeric_row_text(t)


def _has_operating_cashflow_phrase(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False
    return any(p in t for p in OPERATING_CF_PHRASE_PATTERNS)


def _should_forward_map_to_operating_cf(lines: List[str], idx: int) -> bool:
    if idx < 0 or idx >= len(lines):
        return False
    if not _is_numeric_dominant_line(lines[idx]):
        return False
    j = idx + 1
    if j >= len(lines):
        return False
    # Only attach the line immediately preceding the phrase label.
    if _is_numeric_dominant_line(lines[j]):
        return False
    return _has_operating_cashflow_phrase(lines[j])


def _latest_period(periods: Set[str]) -> str:
    vals = sorted(str(p).strip() for p in periods if str(p).strip())
    if not vals:
        return ""
    return vals[-1]


def _normalize_row_label_for_period_dedupe(row_label: str) -> str:
    t = str(row_label or "").strip().lower()
    if not t:
        return ""
    t = NUMERIC_TOKEN_RE.sub(" ", t)
    t = re.sub(r"[^a-z\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _rebalance_duplicate_cashflow_periods(
    rows: List[Dict[str, object]],
    *,
    missing_periods: Set[str],
) -> List[Dict[str, object]]:
    if not rows or not missing_periods:
        return [dict(r) for r in rows]

    missing_norm = sorted(str(p).strip() for p in missing_periods if str(p).strip())
    if not missing_norm:
        return [dict(r) for r in rows]

    out: List[Dict[str, object]] = []
    used_by_key: Dict[Tuple[int, str, str], Set[str]] = {}
    for rr in rows:
        r = dict(rr)
        metric = str(r.get("metric_base", r.get("metric", ""))).strip().lower()
        if metric not in {"operating_cash_flow", "capital_expenditure", "capex"}:
            out.append(r)
            continue
        page_num = int(r.get("page_number", r.get("table_page", 0)) or 0)
        label = _normalize_row_label_for_period_dedupe(_norm_text(r.get("row_label", ""), r.get("line", "")))
        if not label:
            label = metric
        key = (page_num, metric, label)
        used = used_by_key.setdefault(key, set())

        per_end = str(r.get("statement_period_end", "")).strip()
        if per_end and per_end not in used:
            used.add(per_end)
            out.append(r)
            continue

        # Duplicate/synthetic period: deterministically assign next candidate.
        md_hint = per_end[5:] if re.match(r"\d{4}-\d{2}-\d{2}", per_end) else ""
        candidate_pool = [p for p in missing_norm if p not in used]
        if md_hint:
            same_md = [p for p in candidate_pool if re.match(r"\d{4}-\d{2}-\d{2}", p) and p[5:] == md_hint]
            if same_md:
                candidate_pool = same_md
        if not candidate_pool:
            out.append(r)
            continue

        # Prefer chronologically latest remaining period.
        new_period = sorted(candidate_pool)[-1]
        r["statement_period_end"] = new_period
        if str(r.get("statement_period", "")).strip():
            r["statement_period"] = new_period
        elif str(r.get("period", "")).strip():
            r["period"] = new_period
        used.add(new_period)
        out.append(r)
    return out


def _has_competing_label(text: str) -> bool:
    t = str(text or "").strip().lower()
    if not t:
        return False
    if _is_capex_like_text(t):
        return False
    if any(tok in t for tok in ("notes", "reconciliation", "non-ifrs", "underlying", "adjusted")):
        return True
    heading_like = (
        "operating activities" in t
        or "investing activities" in t
        or "financing activities" in t
        or "statement of " in t
        or "cash flows from " in t
    )
    if heading_like:
        return True
    if _is_minimal_numeric_row_text(t) and NUMERIC_TOKEN_RE.findall(t):
        return False
    # Treat long alpha-rich rows as competing labels.
    alpha_count = sum(1 for ch in t if ch.isalpha())
    if alpha_count >= 12 and len(t.split()) >= 3:
        return True
    return False


def _stitch_cashflow_capex_rows(
    rows: List[Dict[str, object]],
    *,
    pdf: Path,
    source_kind: str,
    selected_cashflow_pages: Set[int],
    exclusion_fn,
) -> Tuple[List[Dict[str, object]], int, int, int, int, int]:
    if not CASHFLOW_ENABLE_HORIZONTAL_RECONSTRUCTION:
        return [dict(r) for r in rows], 0, 0, 0, 0, 0
    doc_type = _infer_cashflow_doc_type(pdf, source_kind)
    if doc_type not in {"statutory_annual", "half_year"}:
        return [dict(r) for r in rows], 0, 0, 0, 0, 0

    stitched_rows: List[Dict[str, object]] = []
    for r in rows:
        rr = dict(r)
        if "consumed_by_reconstruction" not in rr:
            rr["consumed_by_reconstruction"] = 0
        if "reconstruction_source_row_idx" not in rr:
            rr["reconstruction_source_row_idx"] = ""
        if "xy_pair_attempted" not in rr:
            rr["xy_pair_attempted"] = 0
        if "xy_pair_success" not in rr:
            rr["xy_pair_success"] = 0
        if "xy_pair_selected_source" not in rr:
            rr["xy_pair_selected_source"] = ""
        stitched_rows.append(rr)

    reconstructed_count = 0
    consumed_count = 0
    xy_paired_count = 0
    xy_candidate_total = 0
    xy_attempt_count = 0

    # Infer right-side numeric column band per page from mostly-numeric rows.
    page_numeric_col_min_x: Dict[int, Optional[float]] = {}
    if CASHFLOW_NUMERIC_COL_MIN_X_MODE == "auto":
        page_numeric_x0_values: Dict[int, List[float]] = {}
        for rr in stitched_rows:
            page_num = int(rr.get("page_number", rr.get("table_page", 0)) or 0)
            if page_num not in selected_cashflow_pages:
                continue
            text = _norm_text(rr.get("row_label", ""), rr.get("line", ""))
            tokens = _extract_numeric_values(rr)
            if not tokens:
                continue
            if not _is_minimal_numeric_row_text(text):
                continue
            x0 = _row_x0(rr)
            if x0 is None:
                continue
            page_numeric_x0_values.setdefault(page_num, []).append(float(x0))
        for page_num, xs in page_numeric_x0_values.items():
            page_numeric_col_min_x[page_num] = _quantile(xs, 0.6)

    for i in range(len(stitched_rows)):
        cur = stitched_rows[i]
        if int(cur.get("consumed_by_reconstruction", 0) or 0) == 1:
            continue
        page_num = int(cur.get("page_number", cur.get("table_page", 0)) or 0)
        if page_num not in selected_cashflow_pages:
            continue

        cur_text = _norm_text(cur.get("row_label", ""), cur.get("line", ""))
        cur_tokens = _extract_numeric_values(cur)
        cur_has_numeric = bool(cur_tokens) or _has_numeric_value(cur)
        if not _is_capex_like_text(cur_text) or cur_has_numeric:
            continue

        cur["xy_pair_attempted"] = 0
        cur["xy_pair_success"] = 0
        cur["xy_pair_selected_source"] = ""

        # 1) Same-block lookahead stitching.
        source_block = str(cur.get("block_id", "")).strip()
        merged_tokens: List[str] = []
        consumed_indices: List[int] = []
        competing_label_hit = False
        for j in range(i + 1, min(len(stitched_rows), i + 1 + int(CASHFLOW_RECON_LOOKAHEAD_ROWS))):
            nxt = stitched_rows[j]
            if int(nxt.get("consumed_by_reconstruction", 0) or 0) == 1:
                continue
            nxt_page = int(nxt.get("page_number", nxt.get("table_page", 0)) or 0)
            if nxt_page != page_num:
                break
            nxt_block = str(nxt.get("block_id", "")).strip()
            if source_block != nxt_block:
                break
            nxt_text = _norm_text(nxt.get("row_label", ""), nxt.get("line", ""))
            if exclusion_fn(nxt_text) or _is_cashflow_heading(nxt_text):
                break
            if _has_competing_label(nxt_text):
                competing_label_hit = True
                break
            nxt_tokens = _extract_numeric_values(nxt)
            if not nxt_tokens:
                continue
            if not _is_minimal_numeric_row_text(nxt_text):
                continue
            merged_tokens.extend(nxt_tokens)
            consumed_indices.append(j)

        if not competing_label_hit and merged_tokens:
            selected_raw = _select_numeric_token_for_cashflow_row(cur, merged_tokens)
            parsed = _parse_numeric_token(selected_raw) if selected_raw else None
            if selected_raw and parsed is not None:
                cur["raw_values"] = list(merged_tokens)
                cur["raw_value"] = selected_raw
                cur["value"] = parsed
                cur["numeric_parse_reason"] = "horizontal_table_reconstruction"
                cur["capex_row_reconstructed"] = 1
                reconstructed_count += 1
                for j in consumed_indices:
                    nxt = stitched_rows[j]
                    nxt["consumed_by_reconstruction"] = 1
                    nxt["reconstruction_source_row_idx"] = i
                    if not str(nxt.get("numeric_parse_reason", "")).strip():
                        nxt["numeric_parse_reason"] = "consumed_by_reconstruction"
                    consumed_count += 1
                continue

        # 2) Cross-block same-page XY pairing fallback.
        if not CASHFLOW_ENABLE_CROSS_BLOCK_PAIRING:
            continue

        cur["xy_pair_attempted"] = 1
        xy_attempt_count += 1
        cur_y = _row_center_y(cur)
        if cur_y is None:
            continue

        min_numeric_x = page_numeric_col_min_x.get(page_num)
        candidate_entries: List[Tuple[float, float, int, List[str]]] = []
        for j, nxt in enumerate(stitched_rows):
            if j == i:
                continue
            if int(nxt.get("consumed_by_reconstruction", 0) or 0) == 1:
                continue
            nxt_page = int(nxt.get("page_number", nxt.get("table_page", 0)) or 0)
            if nxt_page != page_num:
                continue
            nxt_text = _norm_text(nxt.get("row_label", ""), nxt.get("line", ""))
            if not nxt_text:
                continue
            if exclusion_fn(nxt_text) or _is_cashflow_heading(nxt_text):
                continue
            if _has_competing_label(nxt_text):
                continue
            nxt_tokens = _extract_numeric_values(nxt)
            if not nxt_tokens:
                continue
            if not _is_minimal_numeric_row_text(nxt_text):
                continue
            nxt_y = _row_center_y(nxt)
            if nxt_y is None:
                continue
            dy = abs(float(nxt_y) - float(cur_y))
            if dy > float(CASHFLOW_XY_PAIR_Y_TOL):
                continue
            nxt_x0 = _row_x0(nxt)
            if min_numeric_x is not None and nxt_x0 is not None and float(nxt_x0) < float(min_numeric_x):
                continue
            if nxt_x0 is None:
                nxt_x0 = -1e9
            candidate_entries.append((dy, -float(nxt_x0), j, list(nxt_tokens)))

        xy_candidate_total += len(candidate_entries)
        if not candidate_entries:
            continue

        candidate_entries.sort(key=lambda x: (x[0], x[1], x[2]))
        best = candidate_entries[0]
        best_j = int(best[2])
        merged_tokens = list(best[3])

        selected_raw = _select_numeric_token_for_cashflow_row(cur, merged_tokens)
        parsed = _parse_numeric_token(selected_raw) if selected_raw else None
        if not selected_raw or parsed is None:
            continue

        cur["raw_values"] = list(merged_tokens)
        cur["raw_value"] = selected_raw
        cur["value"] = parsed
        cur["numeric_parse_reason"] = "cross_block_xy_pairing"
        cur["capex_row_reconstructed"] = 1
        cur["xy_pair_success"] = 1
        source_block = str(stitched_rows[best_j].get("block_id", "")).strip()
        cur["xy_pair_selected_source"] = f"{source_block}:{best_j}"
        reconstructed_count += 1
        xy_paired_count += 1

        consumed_row = stitched_rows[best_j]
        consumed_row["consumed_by_reconstruction"] = 1
        consumed_row["reconstruction_source_row_idx"] = i
        if not str(consumed_row.get("numeric_parse_reason", "")).strip():
            consumed_row["numeric_parse_reason"] = "consumed_by_reconstruction"
        consumed_count += 1

    return (
        stitched_rows,
        reconstructed_count,
        consumed_count,
        xy_paired_count,
        xy_candidate_total,
        xy_attempt_count,
    )


def _apply_camelot_capex_fallback(
    rows: List[Dict[str, object]],
    *,
    pdf: Path,
    source_kind: str,
    selected_cashflow_pages: Set[int],
    exclusion_fn,
    capex_numeric_fail_page_counts: Dict[int, int],
    capex_rows_phrase_match: int,
    capex_rows_numeric_failed: int,
) -> Tuple[List[Dict[str, object]], int, int, int, Dict[str, int]]:
    """Recover CAPEX numeric values via Camelot lattice on scoped pages only."""
    out_rows = [dict(r) for r in rows]
    doc_type = _infer_cashflow_doc_type(pdf, source_kind)
    is_statutory_doc = doc_type in {"statutory_annual", "half_year"}

    diag: Dict[str, int] = {
        "capex_rows_phrase_match": 0,
        "capex_rows_numeric_failed": 0,
        "capex_rows_fallback_eligible": 0,
        "camelot_pages_with_eligible_rows": 0,
        "camelot_fallback_invocation_attempted": 0,
        "camelot_fallback_blocked_by_gate": 0,
        "fallback_block_reason_phrase_not_matched": 0,
        "fallback_block_reason_statutory_mismatch": 0,
        "fallback_block_reason_not_cashflow_page": 0,
        "fallback_block_reason_numeric_not_failed": 0,
        "fallback_block_reason_no_eligible_pages": 0,
    }
    diag["capex_rows_phrase_match"] = int(capex_rows_phrase_match)
    diag["capex_rows_numeric_failed"] = int(capex_rows_numeric_failed)

    eligible_page_counts: Dict[int, int] = {
        int(p): int(c)
        for p, c in capex_numeric_fail_page_counts.items()
        if int(c or 0) > 0 and int(p) in selected_cashflow_pages
    }
    dropped_non_cashflow_count = int(
        sum(
            int(c or 0)
            for p, c in capex_numeric_fail_page_counts.items()
            if int(c or 0) > 0 and int(p) not in selected_cashflow_pages
        )
    )
    diag["fallback_block_reason_not_cashflow_page"] = dropped_non_cashflow_count
    diag["fallback_block_reason_numeric_not_failed"] = int(max(0, int(capex_rows_phrase_match) - int(capex_rows_numeric_failed)))
    diag["capex_rows_fallback_eligible"] = int(sum(eligible_page_counts.values())) if is_statutory_doc else 0

    if not CASHFLOW_ENABLE_CAMELOT_FALLBACK or CASHFLOW_TABLE_FALLBACK is None:
        diag["camelot_fallback_blocked_by_gate"] += 1
        return out_rows, 0, 0, 0, diag
    if not is_statutory_doc:
        diag["camelot_fallback_blocked_by_gate"] += 1
        diag["fallback_block_reason_statutory_mismatch"] += int(capex_rows_phrase_match)
        return out_rows, 0, 0, 0, diag
    if not eligible_page_counts:
        diag["camelot_fallback_blocked_by_gate"] += 1
        diag["fallback_block_reason_no_eligible_pages"] += 1
        return out_rows, 0, 0, 0, diag

    pages_to_scan = sorted(eligible_page_counts.keys())[: int(CASHFLOW_CAMELOT_MAX_PAGES_PER_PDF)]
    diag["camelot_pages_with_eligible_rows"] = int(len(pages_to_scan))

    # Build template rows by page to inject recovered CAPEX rows even when
    # phrase rows are absent in the canonical candidate stream.
    template_by_page: Dict[int, Dict[str, object]] = {}
    for rr in out_rows:
        page_num = int(rr.get("page_number", rr.get("table_page", 0)) or 0)
        if page_num in pages_to_scan and page_num not in template_by_page:
            template_by_page[page_num] = dict(rr)

    pages_scanned = 0
    tables_found = 0
    recovered_count = 0
    for page_num in pages_to_scan:
        diag["camelot_fallback_invocation_attempted"] += 1
        pages_scanned += 1
        if hasattr(CASHFLOW_TABLE_FALLBACK, "extract_cashflow_table_rows_with_camelot_with_stats"):
            table_rows, stats = CASHFLOW_TABLE_FALLBACK.extract_cashflow_table_rows_with_camelot_with_stats(
                str(pdf), int(page_num)
            )
            tables_found += int(stats.get("tables_found", 0) or 0)
        else:
            table_rows = CASHFLOW_TABLE_FALLBACK.extract_cashflow_table_rows_with_camelot(str(pdf), int(page_num))
            table_ids = {
                str(r.get("table_id", "")).strip()
                for r in table_rows
                if str(r.get("table_id", "")).strip()
            }
            tables_found += int(len(table_ids))

        capex_rows: List[Dict[str, object]] = []
        for tr in table_rows:
            label = str(tr.get("raw_label", "")).strip()
            if not label:
                continue
            if exclusion_fn(label):
                continue
            lower = label.lower()
            if any(tok in lower for tok in CAPEX_EXCLUSION_TOKENS):
                continue
            if not _is_capex_like_text(label):
                continue
            tokens = [str(t).strip() for t in tr.get("numeric_tokens", []) if str(t).strip()]
            if not tokens:
                continue
            tr2 = dict(tr)
            tr2["numeric_tokens"] = tokens
            capex_rows.append(tr2)
        if not capex_rows:
            continue

        existing_keys = {
            (
                int(r.get("page_number", r.get("table_page", 0)) or 0),
                str(r.get("metric_base", r.get("metric", ""))).strip().lower(),
                str(r.get("raw_value", "")).strip(),
            )
            for r in out_rows
        }
        template = dict(template_by_page.get(page_num, {}))
        for tr in capex_rows:
            tokens = [str(t).strip() for t in tr.get("numeric_tokens", []) if str(t).strip()]
            selected_raw = _select_numeric_token_for_cashflow_row(template, tokens)
            parsed = _parse_numeric_token(selected_raw) if selected_raw else None
            if not selected_raw or parsed is None:
                continue
            dedupe_key = (int(page_num), "capital_expenditure", str(selected_raw))
            if dedupe_key in existing_keys:
                continue

            if template:
                rr = dict(template)
            else:
                rr = {
                    "file": str(pdf),
                    "statement_scope": _source_scope(source_kind),
                    "statement_type": _source_scope(source_kind),
                    "statement_family": "cash_flow",
                    "statement_title": "Consolidated statement of cash flows",
                    "table_header_text": "Consolidated statement of cash flows",
                }
            rr["row_label"] = str(tr.get("raw_label", "")).strip()
            rr["line"] = str(tr.get("raw_label", "")).strip()
            rr["raw_values"] = list(tokens)
            rr["raw_value"] = selected_raw
            rr["value"] = parsed
            rr["metric"] = "capital_expenditure"
            rr["metric_base"] = "capital_expenditure"
            camelot_source = str(tr.get("source", "camelot_lattice")).strip().lower() or "camelot_lattice"
            flavor = camelot_source if camelot_source.startswith("camelot_") else "camelot_lattice"
            rr["mapping_source"] = f"{flavor}_capex"
            rr["numeric_parse_reason"] = f"{flavor}_recovery"
            rr["source_mode"] = flavor
            rr["confidence"] = max(float(rr.get("confidence", 0.0) or 0.0), 3.0)
            rr["canonical_confidence_score"] = max(
                int(rr.get("canonical_confidence_score", 0) or 0),
                3,
            )
            rr["capex_row_reconstructed"] = 1
            rr["page_number"] = int(page_num)
            rr["table_page"] = int(page_num)
            rr["block_id"] = str(rr.get("block_id", f"camelot:p{int(page_num)}")).strip()
            rr["table_id"] = str(tr.get("table_id", f"camelot:p{int(page_num)}")).strip()
            out_rows.append(rr)
            existing_keys.add(dedupe_key)
            recovered_count += 1

    return out_rows, recovered_count, pages_scanned, tables_found, diag


def _append_audit_row(
    collector: Dict[str, object],
    rr: Dict[str, object],
    *,
    row_idx: int,
    scope_stage: str,
    scope: str = "",
    context_reason: str = "",
) -> None:
    pre_rows = collector.setdefault("pre_scope_rows", [])
    post_rows = collector.setdefault("post_scope_rows", [])
    written_rows = collector.setdefault("canonical_written_rows", [])

    target_periods = set(str(p) for p in collector.get("target_periods", []))
    target_pages = set(int(p) for p in collector.get("target_pages", []))
    page_number = int(rr.get("page_number", rr.get("table_page", 0)) or 0)
    if target_pages and page_number not in target_pages:
        return

    period_end = str(rr.get("statement_period_end", rr.get("period_end", ""))).strip()
    if target_periods and period_end and period_end not in target_periods:
        return

    metric = str(rr.get("metric", "")).strip()
    metric_base = str(rr.get("metric_base", metric)).strip()
    raw_text = _norm_text(rr.get("row_label", ""), rr.get("line", ""))
    if not raw_text:
        raw_text = str(rr.get("line", "")).strip()
    numbers = _extract_numeric_values(rr)
    raw_numeric_tokens = "|".join(numbers)
    chosen_value = str(rr.get("raw_value", "")).strip()
    if not chosen_value:
        value = rr.get("value")
        chosen_value = "" if value is None else str(value)

    chosen_numeric_value = chosen_value
    parse_ok = 1 if _parse_numeric_token(chosen_numeric_value) is not None else 0
    custom_reason = str(rr.get("numeric_parse_reason", "")).strip()
    if custom_reason:
        numeric_parse_reason = custom_reason
    elif not numbers:
        numeric_parse_reason = "no_numeric_found"
    elif len(numbers) > 1:
        numeric_parse_reason = "multiple_columns" if parse_ok else "ambiguous"
    else:
        numeric_parse_reason = "parsed_ok" if parse_ok else "ambiguous"

    row = {
        "run_id": str(collector.get("run_id", "")),
        "file_stem": str(collector.get("file_stem", "")),
        "pdf_path": str(collector.get("pdf_path", "")),
        "period_end": period_end,
        "page_number": page_number,
        "block_id": str(rr.get("block_id", "")),
        "row_idx": int(row_idx),
        "raw_text": raw_text,
        "raw_numeric_tokens": raw_numeric_tokens,
        "numeric_token_count": int(len(numbers)),
        "extracted_numeric_values": "|".join(numbers),
        "chosen_numeric_value": chosen_numeric_value,
        "chosen_value": chosen_value,
        "numeric_parse_ok": int(parse_ok),
        "numeric_parse_reason": numeric_parse_reason,
        "consumed_by_reconstruction": int(rr.get("consumed_by_reconstruction", 0) or 0),
        "reconstruction_source_row_idx": rr.get("reconstruction_source_row_idx", ""),
        "xy_pair_attempted": int(rr.get("xy_pair_attempted", 0) or 0),
        "xy_pair_success": int(rr.get("xy_pair_success", 0) or 0),
        "xy_pair_selected_source": str(rr.get("xy_pair_selected_source", "")),
        "metric": metric,
        "metric_base": metric_base,
        "scope_stage": scope_stage,
        "scope": scope,
        "context_reason": context_reason,
        "value": rr.get("value", ""),
        "canonical_confidence_score": rr.get("canonical_confidence_score", ""),
    }

    if scope_stage == "pre_scope":
        pre_rows.append(row)
    elif scope_stage == "post_scope":
        post_rows.append(row)
    elif scope_stage == "canonical_written":
        written_rows.append(row)


def _append_block_context_lines(
    collector: Dict[str, object],
    block: Dict[str, object],
    *,
    block_idx: int,
) -> None:
    context_text = str(block.get("context_text", "") or "")
    if not context_text.strip():
        return
    page_start = int(block.get("page_start", 0) or 0)
    block_id = str(block.get("block_id", ""))
    for row_idx, line in enumerate(context_text.splitlines()):
        txt = str(line).strip()
        if not txt:
            continue
        pseudo_row = {
            "page_number": page_start,
            "block_id": block_id,
            "row_label": txt,
            "line": txt,
            "raw_value": "",
            "value": "",
            "metric": "",
            "metric_base": "",
            "statement_period_end": "",
        }
        _append_audit_row(
            collector,
            pseudo_row,
            row_idx=(block_idx * 100000) + row_idx,
            scope_stage="pre_scope",
        )


def _phrase_map_metric(raw_text: str, *, has_numeric: bool) -> Tuple[str, str]:
    text = str(raw_text or "").strip().lower()
    if not text or not has_numeric:
        return "", ""
    # Guard: never remap total cash rows to OCF/CAPEX.
    if "total cash and cash equivalents" in text:
        return "", ""
    if "property, plant and equipment" in text and "impairment" in text:
        return "", ""
    capex_blocked = any(tok in text for tok in CAPEX_EXCLUSION_TOKENS)
    if not capex_blocked and any(p in text for p in CAPEX_PHRASE_PATTERNS):
        return "capital_expenditure", "cashflow_phrase_map_v2"
    if not capex_blocked and any(p in text for p in CAPEX_PHRASE_PATTERNS_V2):
        return "capital_expenditure", "cashflow_phrase_map_v2"
    if any(p in text for p in OPERATING_CF_PHRASE_PATTERNS):
        return "operating_cash_flow", "cashflow_minimal_phrase_map"
    return "", ""


def _best_nearby_numeric(lines: List[str], idx: int, window: int = 3) -> str:
    line = str(lines[idx]).strip()
    direct = NUMERIC_TOKEN_RE.findall(line)
    if direct:
        if len(direct) > 1 and CASHFLOW_USE_RIGHTMOST_NUMERIC_IF_MULTIPLE:
            return str(direct[-1]).strip()
        return str(direct[0]).strip()
    for dist in range(1, window + 1):
        for j in (idx + dist, idx - dist):
            if j < 0 or j >= len(lines):
                continue
            tokens = NUMERIC_TOKEN_RE.findall(str(lines[j]).strip())
            if tokens:
                if len(tokens) > 1 and CASHFLOW_USE_RIGHTMOST_NUMERIC_IF_MULTIPLE:
                    return str(tokens[-1]).strip()
                return str(tokens[0]).strip()
    return ""


def _context_line_candidates(
    *,
    pdf: Path,
    block: Dict[str, object],
    canonical_scope: str,
    missing_periods: Set[str],
    exclusion_fn,
    page_period_hint: Dict[int, str],
) -> List[Dict[str, object]]:
    context_text = str(block.get("context_text", "") or "")
    if not context_text.strip():
        return []
    page_num = int(block.get("page_start", 0) or 0)
    if page_num <= 0:
        return []
    lines = [str(x).strip() for x in context_text.splitlines() if str(x).strip()]
    out: List[Dict[str, object]] = []
    block_id = str(block.get("block_id", ""))
    title = str(block.get("title", "")).strip() or "Consolidated statement of cash flows"
    seen = set()
    for idx, line in enumerate(lines):
        if exclusion_fn(line):
            continue
        mapped_metric, mapped_source = _phrase_map_metric(line, has_numeric=True)
        numeric = _best_nearby_numeric(lines, idx, window=3)
        if not numeric:
            continue
        if not mapped_metric and _should_forward_map_to_operating_cf(lines, idx):
            mapped_metric = "operating_cash_flow"
            mapped_source = "cashflow_forward_label_map"
        parsed = _parse_numeric_token(numeric)
        if parsed is None:
            continue
        metric = mapped_metric
        if not metric and CASHFLOW_EMIT_UNMAPPED_NUMERIC_ROWS:
            metric = "cashflow_unmapped"
        if not metric:
            continue
        key = (page_num, idx, metric, numeric)
        if key in seen:
            continue
        seen.add(key)
        statement_period_end = page_period_hint.get(page_num, "")
        if (
            mapped_source == "cashflow_forward_label_map"
            and missing_periods
            and not statement_period_end
        ):
            statement_period_end = _latest_period(missing_periods)
        if not statement_period_end and len(missing_periods) == 1:
            statement_period_end = next(iter(missing_periods))
        row = {
            "file": str(pdf),
            "line_no": int(block.get("line_start", 0) or 0) + idx,
            "metric": metric,
            "metric_base": metric,
            "value_type": "amount",
            "raw_value": numeric,
            "value": parsed,
            "currency": "",
            "period": "",
            "statement_period": "",
            "statement_period_end": statement_period_end,
            "confidence": 0.0,
            "line": line,
            "row_label": line,
            "source_mode": "cashflow_context_line",
            "table_header_text": title,
            "statement_scope": canonical_scope,
            "statement_type": canonical_scope,
            "statement_family": "cash_flow",
            "statement_title": title,
            "block_id": block_id,
            "inside_table": True,
            "page_number": page_num,
            "table_page": page_num,
        }
        if metric in {"operating_cash_flow", "capital_expenditure", "capex"}:
            row["confidence"] = 3.0
            row["canonical_confidence_score"] = 3
        else:
            row["confidence"] = 0.0
            row["canonical_confidence_score"] = 0
        if mapped_source:
            row["mapping_source"] = mapped_source
        out.append(row)
    return out


def _collect_capex_fallback_page_failures(
    *,
    blocks: List[Dict[str, object]],
    rows: List[Dict[str, object]],
    selected_cashflow_pages: Set[int],
    exclusion_fn,
) -> Tuple[Dict[int, int], int, int]:
    """Collect CAPEX-like pre-scope phrase failures by page.

    This intentionally uses pre-scope signal sources (row stream + block context lines)
    rather than relying on CAPEX phrase presence in canonical-ready rows.
    """
    line_state: Dict[Tuple[int, str], bool] = {}

    def _observe(page_num: int, text: str, has_numeric: bool) -> None:
        if page_num not in selected_cashflow_pages:
            return
        raw = str(text or "").strip()
        if not raw:
            return
        if exclusion_fn(raw):
            return
        lower = raw.lower()
        if any(tok in lower for tok in CAPEX_EXCLUSION_TOKENS):
            return
        if not _is_capex_like_text(raw):
            return
        key = (int(page_num), raw)
        prev = line_state.get(key, False)
        line_state[key] = bool(prev or has_numeric)

    for rr in rows:
        page_num = int(rr.get("page_number", rr.get("table_page", 0)) or 0)
        row_text = _norm_text(rr.get("row_label", ""), rr.get("line", ""))
        has_num = bool(_extract_numeric_values(rr) or _has_numeric_value(rr))
        _observe(page_num, row_text, has_num)

    for block in blocks:
        page_num = int(block.get("page_start", 0) or 0)
        context_text = str(block.get("context_text", "") or "")
        if not context_text.strip():
            continue
        for line in context_text.splitlines():
            txt = str(line).strip()
            if not txt:
                continue
            has_num = bool(NUMERIC_TOKEN_RE.findall(txt))
            _observe(page_num, txt, has_num)

    phrase_count = int(len(line_state))
    fail_counts_by_page: Dict[int, int] = {}
    numeric_failed = 0
    for (page_num, _text), has_num in line_state.items():
        if has_num:
            continue
        numeric_failed += 1
        fail_counts_by_page[page_num] = int(fail_counts_by_page.get(page_num, 0) + 1)
    return fail_counts_by_page, phrase_count, int(numeric_failed)


def _repair_statement_period_end(extract_mod, rr: Dict[str, object]) -> None:
    if str(rr.get("statement_period_end", "")).strip():
        return
    period_hint = str(rr.get("statement_period", "")).strip() or str(rr.get("period", "")).strip()
    if not period_hint:
        return
    doc_date = extract_mod.infer_doc_date_from_path(str(rr.get("file", "")))
    period_end, _ = extract_mod.normalize_period_for_db(period_hint, doc_date=doc_date)
    if period_end:
        rr["statement_period_end"] = period_end


def _coerce_cashflow_metric(rr: Dict[str, object]) -> None:
    metric = str(rr.get("metric", "")).strip().lower()
    metric_base = str(rr.get("metric_base", metric)).strip().lower()
    mapping_source = str(rr.get("mapping_source", "")).strip()
    if mapping_source.startswith("camelot_") and mapping_source.endswith("_capex") and metric_base == "capital_expenditure":
        rr["metric"] = "capital_expenditure"
        rr["metric_base"] = "capital_expenditure"
        rr["balance_position"] = ""
        rr["balance_date"] = ""
        rr["canonical_confidence_score"] = max(int(rr.get("canonical_confidence_score", 0) or 0), 3)
        rr["confidence"] = max(float(rr.get("confidence", 0.0) or 0.0), 3.0)
        return
    row_txt = _norm_text(rr.get("row_label", ""), rr.get("line", "")).lower()
    phrase_metric, phrase_source = _phrase_map_metric(row_txt, has_numeric=_has_numeric_value(rr))
    if phrase_metric and metric_base in {
        "",
        "cashflow_unmapped",
        "cash_and_equivalents",
        "cash_and_equivalents_opening",
        "cash_and_equivalents_closing",
    }:
        rr["metric"] = phrase_metric
        rr["metric_base"] = phrase_metric
        rr["mapping_source"] = phrase_source
        rr["balance_position"] = ""
        rr["balance_date"] = ""
        rr["canonical_confidence_score"] = max(int(rr.get("canonical_confidence_score", 0) or 0), 3)
        rr["confidence"] = max(float(rr.get("confidence", 0.0) or 0.0), 3.0)
        return

    if metric in {"cash_and_equivalents", "cash_and_equivalents_opening", "cash_and_equivalents_closing"}:
        if any(tok in row_txt for tok in ROW_OPERATING_HINTS):
            rr["metric"] = "operating_cash_flow"
            rr["metric_base"] = "operating_cash_flow"
            rr["balance_position"] = ""
            rr["balance_date"] = ""
            rr["canonical_confidence_score"] = max(int(rr.get("canonical_confidence_score", 0) or 0), 3)
            rr["confidence"] = max(float(rr.get("confidence", 0.0) or 0.0), 3.0)
        elif any(tok in row_txt for tok in ROW_CAPEX_HINTS):
            rr["metric"] = "capex"
            rr["metric_base"] = "capex"
            rr["balance_position"] = ""
            rr["balance_date"] = ""
            rr["canonical_confidence_score"] = max(int(rr.get("canonical_confidence_score", 0) or 0), 3)
            rr["confidence"] = max(float(rr.get("confidence", 0.0) or 0.0), 3.0)
    elif metric_base in {"cash_and_equivalents", "cash_and_equivalents_opening", "cash_and_equivalents_closing"}:
        # Keep metric/base consistent if upstream only populated one field.
        rr["metric"] = metric_base


def _adapter_block_allowed(block: Dict[str, object], exclusion_fn) -> bool:
    title = str(block.get("title", ""))
    context = str(block.get("context_text", ""))
    family = str(block.get("statement_family", "")).strip().lower()
    signal_text = _norm_text(title, context).lower()
    if exclusion_fn(signal_text):
        return False
    if _is_cashflow_heading(signal_text):
        return True
    if family == "cash_flow" and _has_keep_token(signal_text):
        return True
    return False


def extract_cashflow_candidates(
    *,
    extract_mod,
    pdf: Path,
    source_kind: str,
    prepared_pages: Dict[int, List[Dict[str, object]]],
    selected_cashflow_pages: Set[int],
    missing_periods: Set[str],
    exclusion_fn,
    audit_collector: Optional[Dict[str, object]] = None,
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    """Run cashflow-only tolerant extraction and return canonical candidates."""
    stats = {
        "blocks_total": 0,
        "blocks_used": 0,
        "rows_raw": 0,
        "rows_context_line_candidates": 0,
        "rows_scoped": 0,
        "rows_after_split_canonical": 0,
        "rows_after_split_context": 0,
        "rows_recovered_scope_override": 0,
        "rows_emitted_unmapped_numeric": 0,
        "rows_mapped_to_capex": 0,
        "rows_mapped_to_capex_v2": 0,
        "capex_rows_stitched": 0,
        "capex_rows_reconstructed": 0,
        "capex_rows_consumed_following_lines": 0,
        "capex_rows_xy_paired": 0,
        "capex_xy_pair_candidates_considered_total": 0,
        "capex_xy_pair_attempt_count": 0,
        "capex_rows_recovered_via_table_fallback": 0,
        "camelot_pages_scanned": 0,
        "camelot_tables_found": 0,
        "capex_rows_phrase_match": 0,
        "capex_rows_numeric_failed": 0,
        "capex_rows_fallback_eligible": 0,
        "camelot_pages_with_eligible_rows": 0,
        "camelot_fallback_invocation_attempted": 0,
        "camelot_fallback_blocked_by_gate": 0,
        "fallback_block_reason_phrase_not_matched": 0,
        "fallback_block_reason_statutory_mismatch": 0,
        "fallback_block_reason_not_cashflow_page": 0,
        "fallback_block_reason_numeric_not_failed": 0,
        "fallback_block_reason_no_eligible_pages": 0,
        "rows_mapped_to_ocf": 0,
        "rows_returned": 0,
    }

    if not selected_cashflow_pages:
        return [], stats

    filtered_pages = {
        p: prepared_pages[p]
        for p in sorted(selected_cashflow_pages)
        if p in prepared_pages
    }
    if not filtered_pages:
        return [], stats

    blocks = extract_mod.segment_statement_blocks(
        pdf,
        source_kind=source_kind,
        prepared_pages=filtered_pages,
    )
    stats["blocks_total"] = len(blocks)
    blocks = [b for b in blocks if _adapter_block_allowed(b, exclusion_fn=exclusion_fn)]
    stats["blocks_used"] = len(blocks)
    if not blocks:
        return [], stats
    if audit_collector is not None:
        for block_idx, block in enumerate(blocks):
            _append_block_context_lines(audit_collector, block, block_idx=block_idx)

    rows = extract_mod.extract_metrics_from_blocks(
        pdf,
        blocks,
        # Adapter mode: relaxed row strictness only on cash-flow pages.
        strict_metric_rows_only=False,
        prepared_pages=filtered_pages,
    )
    stats["rows_raw"] = len(rows)
    rows, stitched_count, consumed_count, xy_paired_count, xy_candidate_total, xy_attempt_count = _stitch_cashflow_capex_rows(
        rows,
        pdf=pdf,
        source_kind=source_kind,
        selected_cashflow_pages=selected_cashflow_pages,
        exclusion_fn=exclusion_fn,
    )
    stats["capex_rows_stitched"] = int(stitched_count)
    stats["capex_rows_reconstructed"] = int(stitched_count)
    stats["capex_rows_consumed_following_lines"] = int(consumed_count)
    stats["capex_rows_xy_paired"] = int(xy_paired_count)
    stats["capex_xy_pair_candidates_considered_total"] = int(xy_candidate_total)
    stats["capex_xy_pair_attempt_count"] = int(xy_attempt_count)
    capex_fail_page_counts, capex_phrase_count, capex_numeric_failed_count = _collect_capex_fallback_page_failures(
        blocks=blocks,
        rows=rows,
        selected_cashflow_pages=selected_cashflow_pages,
        exclusion_fn=exclusion_fn,
    )
    rows, capex_recovered_via_table, camelot_pages_scanned, camelot_tables_found, camelot_diag = _apply_camelot_capex_fallback(
        rows,
        pdf=pdf,
        source_kind=source_kind,
        selected_cashflow_pages=selected_cashflow_pages,
        exclusion_fn=exclusion_fn,
        capex_numeric_fail_page_counts=capex_fail_page_counts,
        capex_rows_phrase_match=int(capex_phrase_count),
        capex_rows_numeric_failed=int(capex_numeric_failed_count),
    )
    stats["capex_rows_recovered_via_table_fallback"] = int(capex_recovered_via_table)
    stats["camelot_pages_scanned"] = int(camelot_pages_scanned)
    stats["camelot_tables_found"] = int(camelot_tables_found)
    for key in (
        "capex_rows_phrase_match",
        "capex_rows_numeric_failed",
        "capex_rows_fallback_eligible",
        "camelot_pages_with_eligible_rows",
        "camelot_fallback_invocation_attempted",
        "camelot_fallback_blocked_by_gate",
        "fallback_block_reason_phrase_not_matched",
        "fallback_block_reason_statutory_mismatch",
        "fallback_block_reason_not_cashflow_page",
        "fallback_block_reason_numeric_not_failed",
        "fallback_block_reason_no_eligible_pages",
    ):
        stats[key] = int(camelot_diag.get(key, 0) or 0)

    page_period_hint: Dict[int, str] = {}
    for rr in rows:
        tmp = dict(rr)
        _repair_statement_period_end(extract_mod, tmp)
        page_num = int(tmp.get("page_number", tmp.get("table_page", 0)) or 0)
        per = str(tmp.get("statement_period_end", "")).strip()
        if page_num > 0 and per and page_num not in page_period_hint:
            page_period_hint[page_num] = per

    scoped_rows: List[Dict[str, object]] = []
    canonical_scope = _source_scope(source_kind)
    for row_idx, row in enumerate(rows):
        rr = dict(row)
        page_num = int(rr.get("page_number", rr.get("table_page", 0)) or 0)
        if page_num not in selected_cashflow_pages:
            continue
        _ensure_numeric_value_for_cashflow_row(rr)
        _repair_statement_period_end(extract_mod, rr)
        if audit_collector is not None:
            _append_audit_row(
                audit_collector,
                rr,
                row_idx=row_idx,
                scope_stage="pre_scope",
            )
        if int(rr.get("consumed_by_reconstruction", 0) or 0) == 1:
            continue
        metric = str(rr.get("metric", "")).strip().lower()
        metric_base = str(rr.get("metric_base", metric)).strip().lower()
        if metric not in CASHFLOW_METRIC_ALLOWLIST and metric_base not in CASHFLOW_METRIC_ALLOWLIST:
            if CASHFLOW_EMIT_UNMAPPED_NUMERIC_ROWS and _has_numeric_value(rr):
                rr["metric"] = "cashflow_unmapped"
                rr["metric_base"] = "cashflow_unmapped"
                stats["rows_emitted_unmapped_numeric"] += 1
            else:
                continue

        row_text = _norm_text(rr.get("row_label", ""), rr.get("line", ""))
        title_text = _norm_text(rr.get("statement_title", ""), rr.get("table_header_text", ""))
        if exclusion_fn(_norm_text(row_text, title_text)):
            continue

        # Cashflow adapter scope coercion: keep section-specific rows in
        # canonical statement scope for split_rows_by_scope evaluation.
        rr["statement_scope"] = canonical_scope
        rr["statement_type"] = canonical_scope
        rr["statement_family"] = "cash_flow"
        if not str(rr.get("statement_title", "")).strip():
            rr["statement_title"] = "Consolidated statement of cash flows"

        _coerce_cashflow_metric(rr)
        metric_after = str(rr.get("metric_base", rr.get("metric", ""))).strip().lower()
        if metric_after == "capex":
            stats["rows_mapped_to_capex"] += 1
        if metric_after == "capital_expenditure":
            stats["rows_mapped_to_capex"] += 1
            if str(rr.get("mapping_source", "")).strip() == "cashflow_phrase_map_v2":
                stats["rows_mapped_to_capex_v2"] += 1
        if metric_after == "operating_cash_flow":
            if str(rr.get("mapping_source", "")).strip() == "cashflow_minimal_phrase_map":
                stats["rows_mapped_to_ocf"] += 1
        per_end = str(rr.get("statement_period_end", "")).strip()
        if missing_periods and per_end and per_end not in missing_periods:
            continue

        scoped_rows.append(rr)

    # Additional cashflow-only candidate pass from block context lines:
    # emit unmapped numeric rows and minimal CAPEX/OCF phrase matches.
    for block in blocks:
        context_rows = _context_line_candidates(
            pdf=pdf,
            block=block,
            canonical_scope=canonical_scope,
            missing_periods=missing_periods,
            exclusion_fn=exclusion_fn,
            page_period_hint=page_period_hint,
        )
        if not context_rows:
            continue
        stats["rows_context_line_candidates"] += len(context_rows)
        for row in context_rows:
            metric_base = str(row.get("metric_base", row.get("metric", ""))).strip().lower()
            if metric_base == "cashflow_unmapped":
                stats["rows_emitted_unmapped_numeric"] += 1
            elif metric_base in {"capex", "capital_expenditure"}:
                stats["rows_mapped_to_capex"] += 1
                if str(row.get("mapping_source", "")).strip() == "cashflow_phrase_map_v2":
                    stats["rows_mapped_to_capex_v2"] += 1
            elif metric_base == "operating_cash_flow":
                stats["rows_mapped_to_ocf"] += 1
            if audit_collector is not None:
                _append_audit_row(
                    audit_collector,
                    dict(row),
                    row_idx=int(row.get("line_no", 0) or 0),
                    scope_stage="pre_scope",
                )
            scoped_rows.append(row)

    stats["rows_scoped"] = len(scoped_rows)
    if not scoped_rows:
        return [], stats
    scoped_rows = _rebalance_duplicate_cashflow_periods(scoped_rows, missing_periods=missing_periods)

    split = extract_mod.split_rows_by_scope(scoped_rows)
    canonical_rows = list(split.get("canonical_rows", []))
    context_rows = list(split.get("context_rows", []))
    stats["rows_after_split_canonical"] = len(canonical_rows)
    stats["rows_after_split_context"] = len(context_rows)
    if audit_collector is not None:
        for idx, rr in enumerate(canonical_rows):
            _append_audit_row(
                audit_collector,
                dict(rr),
                row_idx=idx,
                scope_stage="post_scope",
                scope="primary",
                context_reason="",
            )
        for idx, rr in enumerate(context_rows):
            _append_audit_row(
                audit_collector,
                dict(rr),
                row_idx=idx,
                scope_stage="post_scope",
                scope="context",
                context_reason=str(rr.get("context_reason", "")).strip(),
            )

    # Cash-flow scope override: on cash-flow indexed pages, re-promote numeric
    # rows that were context-demoted for non-reconciliation reasons.
    recovered: List[Dict[str, object]] = []
    for rr in context_rows:
        reason = str(rr.get("context_reason", "")).strip().lower()
        metric = str(rr.get("metric", "")).strip().lower()
        if metric not in CASHFLOW_METRIC_ALLOWLIST:
            continue
        if metric == "cashflow_unmapped":
            continue
        if reason in CASHFLOW_SCOPE_BLOCKED_CONTEXT_REASONS:
            continue
        if int(rr.get("canonical_confidence_score", 0) or 0) < int(CASHFLOW_SCOPE_OVERRIDE_MIN_CANONICAL_CONFIDENCE):
            continue
        if not _has_numeric_value(rr):
            continue
        text = _norm_text(rr.get("row_label", ""), rr.get("line", ""), rr.get("table_header_text", ""))
        if exclusion_fn(text):
            continue
        out = dict(rr)
        out["statement_scope"] = canonical_scope
        out["statement_type"] = canonical_scope
        out["statement_family"] = "cash_flow"
        if not str(out.get("statement_title", "")).strip():
            out["statement_title"] = "Consolidated statement of cash flows"
        _coerce_cashflow_metric(out)
        _repair_statement_period_end(extract_mod, out)
        per_end = str(out.get("statement_period_end", "")).strip()
        if not per_end:
            continue
        if missing_periods and per_end and per_end not in missing_periods:
            continue
        recovered.append(out)

    stats["rows_recovered_scope_override"] = len(recovered)
    combined = extract_mod.dedupe(canonical_rows + recovered)
    filtered: List[Dict[str, object]] = []
    for rr in combined:
        metric = str(rr.get("metric_base", rr.get("metric", ""))).strip().lower()
        if CASHFLOW_EXCLUDE_UNMAPPED_FROM_CANONICAL and metric == "cashflow_unmapped":
            continue
        if int(rr.get("canonical_confidence_score", 0) or 0) < int(CASHFLOW_SCOPE_OVERRIDE_MIN_CANONICAL_CONFIDENCE):
            continue
        if not str(rr.get("statement_period_end", "")).strip():
            continue
        filtered.append(rr)
    combined = extract_mod.dedupe(filtered)
    if audit_collector is not None:
        for idx, rr in enumerate(combined):
            _append_audit_row(
                audit_collector,
                dict(rr),
                row_idx=idx,
                scope_stage="canonical_written",
                scope="primary",
                context_reason="",
            )
    stats["rows_returned"] = len(combined)
    return combined, stats
