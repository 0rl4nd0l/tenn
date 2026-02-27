#!/usr/bin/env python3
"""Provenance and candidate-contract utilities for extraction orchestration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

DOC_ID_SUFFIX_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.IGNORECASE)

PASS_PRIORITY: Dict[str, int] = {
    "native_table": 0,
    "bbox_layout": 1,
    "stream_table": 2,
    "ocr": 3,
}

PASS_CONFIDENCE_FLOOR: Dict[str, float] = {
    "native_table": 1.5,
    "bbox_layout": 1.75,
    "stream_table": 2.0,
    "ocr": 3.0,
}

UNIT_SCALE_BUCKETS = (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _norm_text(*parts: object) -> str:
    return " ".join(str(p or "").strip() for p in parts if str(p or "").strip())


def _parse_numeric_text(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-.", "--"}:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if negative and parsed > 0:
        parsed = -parsed
    return parsed


def infer_unit_scale_from_row(row: Dict[str, object]) -> float:
    explicit = _to_float(row.get("unit_scale"), 0.0)
    if explicit > 0:
        return explicit

    raw_num = _parse_numeric_text(row.get("raw_value"))
    value_num = _to_float(row.get("value"), 0.0)
    if raw_num is None or value_num == 0.0 or raw_num == 0.0:
        return 1.0

    ratio = abs(value_num / raw_num)
    best = min(UNIT_SCALE_BUCKETS, key=lambda s: abs(ratio - s) / s)
    relative_err = abs(ratio - best) / best
    if relative_err <= 0.05:
        return float(best)
    return 1.0


def infer_doc_id_from_pdf_path(pdf_path: str) -> str:
    stem = Path(str(pdf_path or "")).stem
    if not stem:
        return ""
    m = DOC_ID_SUFFIX_RE.search(stem)
    if m:
        return str(m.group(1)).lower()
    return stem


def infer_ticker_from_pdf_path(pdf_path: str) -> str:
    p = Path(str(pdf_path or ""))
    parts = list(p.parts)
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return str(parts[idx + 1]).upper()
    return ""


def infer_pass_name_from_row(row: Dict[str, object]) -> str:
    source_mode = str(row.get("source_mode", "")).strip().lower()
    mapping_source = str(row.get("mapping_source", "")).strip().lower()
    if "ocr" in source_mode or "ocr" in mapping_source:
        return "ocr"
    if source_mode in {"table_bbox", "bbox_layout", "bbox_text"}:
        return "bbox_layout"
    if source_mode == "camelot_stream" or "camelot_stream" in mapping_source:
        return "stream_table"
    if source_mode == "camelot_lattice" or "camelot_lattice" in mapping_source:
        return "native_table"
    return "native_table"


def source_type_for_candidate(pass_name: str, row: Dict[str, object]) -> str:
    p = str(pass_name or "").strip().lower()
    if p == "ocr":
        return "ocr_text"
    if p == "bbox_layout":
        return "bbox_text"
    if p in {"native_table", "stream_table"}:
        source_mode = str(row.get("source_mode", "")).strip().lower()
        if source_mode.startswith("camelot_"):
            return "camelot_table"
        return "native_text"
    return "native_text"


def _normalize_bbox(value: object) -> List[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return []
    out: List[float] = []
    for item in value:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            return []
    return out


def provenance_depth_score(provenance: Dict[str, object]) -> int:
    score = 0
    page = _to_int(provenance.get("page", 0), 0)
    if page > 0:
        score += 1
    if _normalize_bbox(provenance.get("bbox")):
        score += 2
    if str(provenance.get("table_id", "")).strip():
        score += 2
    row_idx = provenance.get("row_index")
    col_idx = provenance.get("col_index")
    if row_idx is not None:
        score += 1
    if col_idx is not None:
        score += 1
    if str(provenance.get("raw_snippet", "")).strip():
        score += 1
    if str(provenance.get("row_text_raw", "")).strip() or str(provenance.get("cell_text_raw", "")).strip():
        score += 1
    return score


def validate_provenance(provenance: Dict[str, object]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    source_type = str(provenance.get("source_type", "")).strip()
    page = _to_int(provenance.get("page", 0), 0)
    if not source_type:
        issues.append("missing_source_type")
    if page <= 0:
        issues.append("missing_page")
    if source_type == "camelot_table" and not str(provenance.get("table_id", "")).strip():
        issues.append("camelot_missing_table_id")
    return len(issues) == 0, issues


def normalize_candidate_row(row: Dict[str, object], pass_name: str | None = None) -> Dict[str, object]:
    raw = dict(row)
    p = str(pass_name or infer_pass_name_from_row(raw)).strip().lower() or "native_table"

    pdf_path = str(raw.get("file", raw.get("pdf_path", ""))).strip()
    doc_id = str(raw.get("doc_id", "")).strip() or infer_doc_id_from_pdf_path(pdf_path)
    ticker = str(raw.get("ticker", "")).strip().upper() or infer_ticker_from_pdf_path(pdf_path)

    metric = str(raw.get("metric_base", raw.get("metric", ""))).strip().lower()
    metric_name_canonical = "" if metric in {"", "cashflow_unmapped", "unknown", "other"} else metric
    metric_name_candidate = metric or str(raw.get("row_label", raw.get("line", ""))).strip().lower()

    page = _to_int(raw.get("page_number", raw.get("table_page", raw.get("page", 0))), 0)
    period_end = str(raw.get("statement_period_end", raw.get("period_end_date", raw.get("period_end", "")))).strip()
    period_type = str(raw.get("statement_period", raw.get("period", ""))).strip()
    scope = str(raw.get("statement_scope", raw.get("scope", ""))).strip() or "unknown"
    statement_type = str(raw.get("statement_family", raw.get("statement_type", ""))).strip().lower() or "unknown"
    currency = str(raw.get("currency", "")).strip() or "UNKNOWN"

    confidence = max(
        _to_float(raw.get("confidence", 0.0), 0.0),
        _to_float(raw.get("canonical_confidence_score", 0.0), 0.0),
    )

    reasons: List[str] = []
    for key in ("context_reason", "statement_scope_reason", "parse_error"):
        val = str(raw.get(key, "")).strip()
        if val:
            reasons.append(val)

    bbox = _normalize_bbox(raw.get("table_bbox")) or _normalize_bbox(raw.get("bbox"))
    source_mode = str(raw.get("source_mode", "")).strip().lower()
    extraction_flavor = ""
    if source_mode.startswith("camelot_"):
        extraction_flavor = source_mode

    provenance = {
        "source_type": source_type_for_candidate(p, raw),
        "page": page,
        "bbox": bbox,
        "table_id": str(raw.get("table_id", "")).strip(),
        "row_index": raw.get("table_row_idx", raw.get("row_index")),
        "col_index": raw.get("col_index"),
        "raw_snippet": _norm_text(raw.get("line", ""), raw.get("row_label", ""))[:300],
        "row_text_raw": str(raw.get("row_label", "")).strip()[:300],
        "cell_text_raw": str(raw.get("raw_value", "")).strip()[:120],
        "extraction_flavor": extraction_flavor,
    }

    normalized = {
        "doc_id": doc_id,
        "ticker": ticker,
        "pdf_path": pdf_path,
        "page": page,
        "pass_name": p,
        "statement_type": statement_type,
        "metric_name_canonical": metric_name_canonical,
        "metric_name_candidate": metric_name_candidate,
        "value": _to_float(raw.get("value", raw.get("raw_value", 0.0)), 0.0),
        "unit_scale": infer_unit_scale_from_row(raw),
        "currency": currency,
        "period_end": period_end,
        "period_type": period_type,
        "scope": scope,
        "confidence": confidence,
        "reasons": reasons,
        "provenance": provenance,
        "_raw": raw,
    }
    return normalized


def validate_candidate_contract(candidate: Dict[str, object]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    for key in ("doc_id", "pdf_path", "page", "pass_name", "statement_type", "period_end", "scope"):
        val = candidate.get(key)
        if key == "page":
            if _to_int(val, 0) <= 0:
                issues.append(f"missing_{key}")
        elif not str(val or "").strip():
            issues.append(f"missing_{key}")

    if not str(candidate.get("metric_name_canonical", "")).strip() and not str(
        candidate.get("metric_name_candidate", "")
    ).strip():
        issues.append("missing_metric_name")

    ok_prov, prov_issues = validate_provenance(candidate.get("provenance", {}))
    if not ok_prov:
        issues.extend(prov_issues)

    return len(issues) == 0, issues


def pass_priority(pass_name: str) -> int:
    return int(PASS_PRIORITY.get(str(pass_name or "").strip().lower(), 99))


def pass_confidence_floor(pass_name: str) -> float:
    return float(PASS_CONFIDENCE_FLOOR.get(str(pass_name or "").strip().lower(), 2.0))


def candidate_sort_key(candidate: Dict[str, object]) -> Tuple[float, int, int, str]:
    provenance = candidate.get("provenance", {})
    return (
        float(candidate.get("confidence", 0.0) or 0.0),
        -pass_priority(str(candidate.get("pass_name", ""))),
        provenance_depth_score(provenance if isinstance(provenance, dict) else {}),
        str(candidate.get("pdf_path", "")),
    )
