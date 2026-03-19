#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from services.extraction.pdf_classifier import classify_pdf


DEFAULT_EXTRACTOR = "financial_metrics_pdftotext"
DOCLING_EXTRACTOR = "financial_metrics_docling"
REJECTED_ROWS_THRESHOLD = 25
TABLE_COMPLEXITY_THRESHOLD = 0.55
TABLE_DENSITY_THRESHOLD = 0.25


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coverage(method_payload: Mapping[str, Any] | None) -> float:
    if not isinstance(method_payload, Mapping):
        return 0.0
    metric_coverage = method_payload.get("metric_coverage_rate")
    if isinstance(metric_coverage, (int, float)):
        return float(metric_coverage)
    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping):
        return float(len(canonical_metrics)) / 5.0
    return 0.0


def select_extractor_with_reason(
    document_diagnostics: Mapping[str, Any] | None,
    method_results: Mapping[str, Any] | None,
) -> dict[str, Any]:
    diagnostics = dict(document_diagnostics or {})
    methods = dict(method_results or {})
    classifier = classify_pdf(diagnostics, methods)
    document_type = str(classifier.get("document_type") or "unknown").strip().lower()
    complexity_score = float(classifier.get("complexity_score") or 0.0)

    if document_type == "appendix_report" and complexity_score < 0.3:
        return {
            "selected_extractor": DEFAULT_EXTRACTOR,
            "reason": "appendix_report_low_complexity_prefers_pdftotext",
            "classifier": classifier,
        }

    pdftotext_payload = methods.get(DEFAULT_EXTRACTOR)
    docling_payload = methods.get(DOCLING_EXTRACTOR)
    pdftotext_coverage = _coverage(pdftotext_payload if isinstance(pdftotext_payload, Mapping) else None)
    docling_coverage = _coverage(docling_payload if isinstance(docling_payload, Mapping) else None)

    if docling_coverage > pdftotext_coverage:
        return {
            "selected_extractor": DOCLING_EXTRACTOR,
            "reason": "docling_coverage_exceeds_pdftotext",
            "classifier": classifier,
        }

    rejected_rows = _safe_int(diagnostics.get("rejected_rows"))
    if rejected_rows >= REJECTED_ROWS_THRESHOLD:
        return {
            "selected_extractor": DOCLING_EXTRACTOR,
            "reason": "rejected_rows_high",
            "classifier": classifier,
        }

    if complexity_score >= TABLE_COMPLEXITY_THRESHOLD:
        return {
            "selected_extractor": DOCLING_EXTRACTOR,
            "reason": "table_complexity_high",
            "classifier": classifier,
        }

    table_density = float(classifier.get("table_density") or 0.0)
    if table_density >= TABLE_DENSITY_THRESHOLD:
        return {
            "selected_extractor": DOCLING_EXTRACTOR,
            "reason": "table_density_high",
            "classifier": classifier,
        }

    docling_row_count_before_filtering = _safe_int(diagnostics.get("docling_row_count_before_filtering"))
    pdftotext_row_count = 0
    if isinstance(pdftotext_payload, Mapping):
        completeness = pdftotext_payload.get("completeness")
        if isinstance(completeness, Mapping):
            pdftotext_row_count = _safe_int(completeness.get("row_count"))
    if docling_row_count_before_filtering > pdftotext_row_count > 0:
        return {
            "selected_extractor": DOCLING_EXTRACTOR,
            "reason": "docling_pre_filter_rows_exceed_pdftotext_rows",
            "classifier": classifier,
        }

    return {
        "selected_extractor": DEFAULT_EXTRACTOR,
        "reason": "default_pdftotext",
        "classifier": classifier,
    }


def select_extractor(
    document_diagnostics: Mapping[str, Any] | None,
    method_results: Mapping[str, Any] | None,
) -> str:
    return str(select_extractor_with_reason(document_diagnostics, method_results).get("selected_extractor") or DEFAULT_EXTRACTOR)
