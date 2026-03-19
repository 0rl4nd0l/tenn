#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.evaluation.anomaly import detect_anomalies
from services.evaluation.normalizer import normalize_metric_name
from services.extraction.router import REJECTED_ROWS_THRESHOLD

SUCCESS_STATUSES = frozenset({"ok", "success"})

FAILURE_CLASSES = frozenset(
    {
        "no_metric_candidates",
        "label_only_candidates",
        "numeric_unverified",
        "non_canonical_only",
        "extractor_runtime_failure",
        "likely_non_financial",
        "ambiguity_conflict",
        "success",
    }
)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _first_diagnostics(method_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = method_payload.get("document_diagnostics")
    if isinstance(diagnostics, Sequence) and diagnostics:
        first = diagnostics[0]
        if isinstance(first, Mapping):
            return first
    return {}


def _normalized_row_metric_partition(normalized_metrics: Sequence[Mapping[str, Any]] | None) -> tuple[int, int]:
    known = 0
    unknown = 0
    for row in normalized_metrics or ():
        if not isinstance(row, Mapping):
            continue
        raw = row.get("metric_base") or row.get("metric") or ""
        if not str(raw).strip():
            continue
        if normalize_metric_name(raw) is None:
            unknown += 1
        else:
            known += 1
    return known, unknown


def _conflict_rejection_total(diagnostics: Mapping[str, Any]) -> int:
    rejection_reasons = diagnostics.get("rejection_reasons")
    if not isinstance(rejection_reasons, Mapping):
        return 0
    total = 0
    for key in ("canonical_conflict_same_period", "statement_type_metric_conflict", "metric_statement_mismatch"):
        total += _safe_int(rejection_reasons.get(key))
    return total


def _rejected_numeric_only_count(rejected_metrics: Mapping[str, Any] | None) -> int:
    count = 0
    for detail in dict(rejected_metrics or {}).values():
        if not isinstance(detail, Mapping):
            continue
        if bool(detail.get("numeric_match")) and not bool(detail.get("context_match")):
            count += 1
    return count


def _rejected_other_count(rejected_metrics: Mapping[str, Any] | None) -> int:
    total = len(dict(rejected_metrics or {}))
    return max(0, total - _rejected_numeric_only_count(rejected_metrics))


def build_failure_analysis(
    *,
    selected_payload: Mapping[str, Any],
    verification: Mapping[str, Any],
    strict_truth_mode: bool,
    fallback_triggered: bool,
    docling_executed: bool,
    selected_method: str,
    document_type: str,
    is_financial: bool,
    probe_method_payload: Mapping[str, Any],
    probe_coverage: float,
) -> dict[str, Any]:
    """Deterministic per-document fault taxonomy for routed extraction outputs."""
    status_raw = str(selected_payload.get("status") or "").strip().lower()
    status_ok = status_raw in SUCCESS_STATUSES

    canonical_metrics = dict(selected_payload.get("canonical_metrics") or {})
    normalized_metrics = list(selected_payload.get("normalized_metrics") or [])
    completeness = dict(selected_payload.get("completeness") or {})
    row_count = _safe_int(completeness.get("row_count"))
    rows_with_numeric = _safe_int(completeness.get("rows_with_numeric_value"))

    verified = dict(verification.get("verified") or {})
    rejected_metrics = dict(verification.get("rejected") or {})
    verified_count = _safe_int(verification.get("verified_count"))
    rejected_count = _safe_int(verification.get("rejected_count"))
    verification_ratio = float(verification.get("verification_ratio") or 0.0)

    diagnostics = _first_diagnostics(selected_payload)
    rejected_rows_diag = _safe_int(diagnostics.get("rejected_rows"))
    consistency_failures = _safe_int(diagnostics.get("consistency_failures"))
    identity_conflicts = _safe_int(diagnostics.get("identity_resolution_conflicts"))
    conflict_rejections = _conflict_rejection_total(diagnostics)

    known_metric_rows, unknown_metric_rows = _normalized_row_metric_partition(normalized_metrics)

    selected_anomaly = detect_anomalies(dict(selected_payload))
    anomaly_flags = list(selected_anomaly.get("flags") or [])
    if not isinstance(anomaly_flags, list):
        anomaly_flags = []

    doc_type_l = str(document_type or "").strip().lower()
    probe_canonical = dict(probe_method_payload.get("canonical_metrics") or {})
    probe_row_count = _safe_int(dict(probe_method_payload.get("completeness") or {}).get("row_count"))

    stage_signals: dict[str, Any] = {
        "extractor_status_ok": bool(status_ok),
        "fallback_triggered": bool(fallback_triggered),
        "docling_executed": bool(docling_executed),
        "docling_selected": str(selected_method).strip() == "financial_metrics_docling",
        "strict_truth_mode": bool(strict_truth_mode),
        "canonical_metric_count": len(canonical_metrics),
        "normalized_row_count": len(normalized_metrics),
        "normalized_known_metric_rows": known_metric_rows,
        "normalized_unknown_metric_rows": unknown_metric_rows,
        "completeness_row_count": row_count,
        "completeness_rows_with_numeric": rows_with_numeric,
        "verified_count": verified_count,
        "rejected_count": rejected_count,
        "rejected_numeric_only_count": _rejected_numeric_only_count(rejected_metrics),
        "rejected_other_count": _rejected_other_count(rejected_metrics),
        "verification_ratio": round(float(verification_ratio), 6),
        "diagnostics_rejected_rows": rejected_rows_diag,
        "diagnostics_consistency_failures": consistency_failures,
        "diagnostics_identity_resolution_conflicts": identity_conflicts,
        "diagnostics_conflict_rejection_total": conflict_rejections,
        "anomaly_flag_count": len(anomaly_flags),
        "classifier_is_financial": bool(is_financial),
    }

    failure_reasons: list[str] = []
    failure_class = "success"
    recommended_action = "Use routed metrics as-is for downstream evaluation."

    if not status_ok:
        failure_class = "extractor_runtime_failure"
        failure_reasons.append(f"extractor_status_{status_raw or 'missing'}")
        recommended_action = "Inspect extractor subprocess logs, timeouts, and PDF validity; retry after fixing the runtime error."
    elif (
        is_financial is False
        and doc_type_l in {"", "unknown", "other"}
        and len(canonical_metrics) == 0
        and len(probe_canonical) == 0
        and probe_row_count == 0
        and float(probe_coverage) <= 0.05
        and not (bool(selected_anomaly.get("has_anomaly")) and str(selected_anomaly.get("severity") or "").lower() == "high")
    ):
        failure_class = "likely_non_financial"
        failure_reasons.append("classifier_non_financial_with_empty_probe_signal")
        recommended_action = "Treat as non-financial for metric scoring or force extraction only if business rules require it."
    elif (
        identity_conflicts > 0
        or consistency_failures > 0
        or conflict_rejections > 0
        or rejected_rows_diag >= REJECTED_ROWS_THRESHOLD
        or _rejected_numeric_only_count(rejected_metrics) >= 2
        or "assets_liabilities_equity_inconsistency" in set(anomaly_flags)
    ):
        failure_class = "ambiguity_conflict"
        if identity_conflicts > 0:
            failure_reasons.append("identity_resolution_conflicts")
        if consistency_failures > 0:
            failure_reasons.append("consistency_failures")
        if conflict_rejections > 0:
            failure_reasons.append("routing_rejection_reason_conflicts")
        if rejected_rows_diag >= REJECTED_ROWS_THRESHOLD:
            failure_reasons.append("rejected_rows_high")
        if _rejected_numeric_only_count(rejected_metrics) >= 2:
            failure_reasons.append("evidence_numeric_without_label_context")
        if "assets_liabilities_equity_inconsistency" in set(anomaly_flags):
            failure_reasons.append("balance_sheet_identity_inconsistency")
        recommended_action = "Manually reconcile conflicting rows, statement scope, and identity resolution before trusting metrics."
    elif len(canonical_metrics) == 0 and len(normalized_metrics) == 0 and row_count == 0:
        failure_class = "no_metric_candidates"
        failure_reasons.append("no_normalized_rows_and_empty_canonical_metrics")
        recommended_action = "Try higher-recall extraction (e.g. Docling/OCR) or verify the PDF has a usable text layer."
    elif len(canonical_metrics) == 0 and known_metric_rows == 0 and unknown_metric_rows > 0:
        failure_class = "non_canonical_only"
        failure_reasons.append("normalized_rows_do_not_map_to_canonical_metric_aliases")
        recommended_action = "Extend metric aliases or normalize labels so rows map into the canonical metric schema."
    elif len(canonical_metrics) == 0 and row_count > 0 and rows_with_numeric == 0:
        failure_class = "label_only_candidates"
        failure_reasons.append("table_rows_without_numeric_values_in_completeness")
        recommended_action = "Improve table/number parsing; confirm values are present in the extracted text."
    elif len(canonical_metrics) == 0 and known_metric_rows > 0:
        failure_class = "label_only_candidates"
        failure_reasons.append("known_metric_rows_present_but_canonical_metrics_empty")
        recommended_action = "Repair numeric normalization for labeled rows or inspect unit/scale handling."
    elif len(canonical_metrics) == 0 and len(normalized_metrics) > 0 and known_metric_rows == 0 and unknown_metric_rows == 0:
        failure_class = "no_metric_candidates"
        failure_reasons.append("normalized_rows_missing_metric_fields")
        recommended_action = "Improve metric labeling in table extraction so rows bind to named metrics."
    elif len(canonical_metrics) > 0 and (rejected_count > 0 or verification_ratio < 1.0):
        failure_class = "numeric_unverified"
        failure_reasons.append("canonical_metrics_not_fully_grounded_in_pdf_text")
        if strict_truth_mode:
            failure_reasons.append("strict_truth_mode_drops_unverified_metrics")
        recommended_action = "Ground numbers in source text (OCR/layout), tighten verification windows, or accept manual review for unverified fields."
    else:
        if len(canonical_metrics) == 0:
            failure_class = "no_metric_candidates"
            failure_reasons = ["unclassified_empty_canonical_metrics"]
            recommended_action = "Try higher-recall extraction or verify the PDF content matches financial tables."
        else:
            failure_class = "success"
            failure_reasons.append("extractor_ok_and_metrics_pass_evidence_checks")
            recommended_action = "Use routed metrics as-is for downstream evaluation."

    if failure_class not in FAILURE_CLASSES:
        failure_class = "success"

    return {
        "failure_class": failure_class,
        "failure_reasons": failure_reasons,
        "stage_signals": stage_signals,
        "recommended_action": recommended_action,
    }


__all__ = [
    "FAILURE_CLASSES",
    "SUCCESS_STATUSES",
    "build_failure_analysis",
]
