#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pdftotext_row_count(method_results: Mapping[str, Any] | None) -> int:
    if not isinstance(method_results, Mapping):
        return 0
    pdftotext = method_results.get("financial_metrics_pdftotext")
    if not isinstance(pdftotext, Mapping):
        return 0
    completeness = pdftotext.get("completeness")
    if not isinstance(completeness, Mapping):
        return 0
    return _safe_int(completeness.get("row_count"))


def classify_pdf(
    document_diagnostics: Mapping[str, Any] | None,
    method_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = dict(document_diagnostics or {})
    classifier = diagnostics.get("document_classifier")
    if not isinstance(classifier, Mapping):
        classifier = {}

    document_type = str(classifier.get("document_type") or "unknown").strip() or "unknown"
    is_financial = bool(classifier.get("is_financial"))
    context_rows = _safe_int(diagnostics.get("context_rows"))
    rejected_rows = _safe_int(diagnostics.get("rejected_rows"))
    tsr_tables_processed = _safe_int(diagnostics.get("tsr_tables_processed"))
    statement_type_counts = diagnostics.get("table_statement_type_counts")
    statement_type_count = len(statement_type_counts) if isinstance(statement_type_counts, Mapping) else 0
    row_count = _pdftotext_row_count(method_results)

    table_density = min(1.0, float(tsr_tables_processed) / float(max(1, context_rows)))
    rejected_component = min(1.0, float(rejected_rows) / 60.0)
    table_component = min(1.0, float(tsr_tables_processed) / 20.0)
    statement_component = min(1.0, float(statement_type_count) / 4.0)
    context_component = min(1.0, float(context_rows) / 120.0)
    row_component = min(1.0, float(row_count) / 80.0)
    complexity_score = (
        0.30 * rejected_component
        + 0.25 * table_component
        + 0.15 * statement_component
        + 0.15 * context_component
        + 0.15 * row_component
    )
    if not is_financial:
        complexity_score *= 0.5
    complexity_score = round(min(1.0, max(0.0, complexity_score)), 6)

    return {
        "document_type": document_type,
        "complexity_score": complexity_score,
        "table_density": round(table_density, 6),
        "is_financial": is_financial,
        "features": {
            "context_rows": context_rows,
            "rejected_rows": rejected_rows,
            "tsr_tables_processed": tsr_tables_processed,
            "statement_type_count": statement_type_count,
            "pdftotext_row_count": row_count,
        },
    }
