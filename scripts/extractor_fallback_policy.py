#!/usr/bin/env python3
"""Docling-first fallback policy for table extraction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

try:
    from financial_consistency_engine import evaluate_financial_consistency
except Exception:
    _CONSISTENCY_PATH = Path(__file__).resolve().with_name("financial_consistency_engine.py")
    _CONSISTENCY_SPEC = importlib.util.spec_from_file_location("financial_consistency_engine", str(_CONSISTENCY_PATH))
    if _CONSISTENCY_SPEC is None or _CONSISTENCY_SPEC.loader is None:
        raise RuntimeError(f"failed to load module: {_CONSISTENCY_PATH}")
    _CONSISTENCY_MODULE = importlib.util.module_from_spec(_CONSISTENCY_SPEC)
    _CONSISTENCY_SPEC.loader.exec_module(_CONSISTENCY_MODULE)
    evaluate_financial_consistency = _CONSISTENCY_MODULE.evaluate_financial_consistency

try:
    from metric_ontology_mapper import canonicalize_metric_name
except Exception:
    _MAPPER_PATH = Path(__file__).resolve().with_name("metric_ontology_mapper.py")
    _MAPPER_SPEC = importlib.util.spec_from_file_location("metric_ontology_mapper", str(_MAPPER_PATH))
    if _MAPPER_SPEC is None or _MAPPER_SPEC.loader is None:
        raise RuntimeError(f"failed to load module: {_MAPPER_PATH}")
    _MAPPER_MODULE = importlib.util.module_from_spec(_MAPPER_SPEC)
    _MAPPER_SPEC.loader.exec_module(_MAPPER_MODULE)
    canonicalize_metric_name = _MAPPER_MODULE.canonicalize_metric_name


CRITICAL_METRICS = {
    "capital_expenditure",
    "ebit",
    "ebitda",
    "free_cash_flow",
    "operating_cash_flow",
    "revenue",
    "total_assets",
    "total_equity",
    "total_liabilities",
}
CRITICAL_METRICS_FALLBACK_ROW_THRESHOLD = 10


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _canonical_metrics(rows: Iterable[Dict[str, object]]) -> List[str]:
    metrics = {
        canonicalize_metric_name(row.get("metric_base") or row.get("metric"))
        for row in rows
        if canonicalize_metric_name(row.get("metric_base") or row.get("metric"))
    }
    return sorted(metrics)


def should_fallback(
    docling_rows: int,
    context_rows: int,
    tsr_tables: int,
    critical_metrics_missing: bool,
    consistency_failed: bool,
) -> bool:
    # HARD failure only if nothing usable exists.
    if docling_rows == 0:
        return True

    if context_rows == 0 and tsr_tables == 0:
        return True

    if critical_metrics_missing:
        return False

    # Do not fallback just because metrics are missing.
    if consistency_failed:
        return context_rows < 3

    return False


def evaluate_docling_fallback(split: Dict[str, Sequence[Dict[str, object]]]) -> Dict[str, object]:
    """Decide whether Docling results should fall back to pdftotext."""
    canonical_rows = list(split.get("canonical_rows", []))
    diagnostics = split.get("diagnostics", {})
    consistency_report = evaluate_financial_consistency(canonical_rows)
    consistency_failed = bool(consistency_report.get("failed_checks"))
    metrics_present = set(_canonical_metrics(canonical_rows))
    money_rows = [
        row
        for row in canonical_rows
        if str(row.get("value_type", "")).strip().lower() in {"", "amount"}
    ]
    docling_row_count_before_filtering = 0
    if isinstance(diagnostics, dict):
        docling_row_count_before_filtering = _safe_int(diagnostics.get("docling_row_count_before_filtering"))
        context_rows = list(split.get("context_rows", []) or [])
        tsr_tables = _safe_int(diagnostics.get("tsr_tables_processed"))
    else:
        context_rows = []
        tsr_tables = 0
    context_rows_count = len(context_rows)

    reasons: List[str] = []
    if consistency_failed:
        reasons.append("financial_consistency_failed")
    if money_rows and not any(str(row.get("currency", "")).strip().upper() not in {"", "UNKNOWN"} for row in money_rows):
        reasons.append("currency_detection_failed")

    critical_metrics_missing = not metrics_present.intersection(CRITICAL_METRICS)
    fallback_suppressed = False
    fallback_suppression_reason = None
    if critical_metrics_missing:
        reasons.append("critical_metrics_missing")

    fallback_triggered = should_fallback(
        docling_row_count_before_filtering,
        context_rows_count,
        tsr_tables,
        critical_metrics_missing,
        consistency_failed,
    )

    if critical_metrics_missing and not fallback_triggered and docling_row_count_before_filtering >= CRITICAL_METRICS_FALLBACK_ROW_THRESHOLD:
        fallback_suppressed = True
        fallback_suppression_reason = "sufficient_docling_rows"

    if fallback_triggered and not reasons:
        reasons.append("hard_failure")

    if not fallback_triggered and critical_metrics_missing:
        reasons = [r for r in reasons if r != "critical_metrics_missing"]

    return {
        "should_fallback": bool(fallback_triggered),
        "fallback_reason": reasons[0] if fallback_triggered and reasons else None,
        "reasons": reasons,
        "fallback_suppressed": fallback_suppressed,
        "fallback_suppression_reason": fallback_suppression_reason,
        "consistency_report": consistency_report,
        "critical_metrics_present": sorted(metrics_present.intersection(CRITICAL_METRICS)),
        "docling_row_count_before_filtering": docling_row_count_before_filtering,
    }
