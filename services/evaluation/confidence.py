#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.evaluation.anomaly import detect_anomalies


CONFIDENCE_THRESHOLD = 0.75
MIN_COVERAGE = 0.6
REQUIRED_METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "net_income",
)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _first_diagnostics(method_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = method_payload.get("document_diagnostics")
    if isinstance(diagnostics, Sequence) and diagnostics:
        first = diagnostics[0]
        if isinstance(first, Mapping):
            return first
    return {}


def metric_coverage(method_payload: Mapping[str, Any]) -> float:
    metric_coverage_rate = method_payload.get("metric_coverage_rate")
    if isinstance(metric_coverage_rate, (int, float)):
        return _clamp(float(metric_coverage_rate))
    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping):
        return _clamp(float(len(canonical_metrics)) / 5.0)
    return 0.0


def _completeness_score(method_payload: Mapping[str, Any]) -> float:
    score = method_payload.get("score")
    if isinstance(score, Mapping) and str(score.get("status") or "") == "SUCCESS":
        aggregate = score.get("aggregate")
        if isinstance(aggregate, Mapping):
            return _clamp(_safe_float(aggregate.get("completeness")))

    completeness = method_payload.get("completeness")
    if not isinstance(completeness, Mapping):
        return 0.0
    row_count = _safe_int(completeness.get("row_count"))
    rows_with_numeric = _safe_int(completeness.get("rows_with_numeric_value"))
    row_component = _clamp(float(row_count) / 20.0)
    numeric_component = _clamp(float(rows_with_numeric) / float(max(1, row_count)))
    return _clamp(0.6 * row_component + 0.4 * numeric_component)


def _rejected_rows_penalty(method_payload: Mapping[str, Any]) -> float:
    diagnostics = _first_diagnostics(method_payload)
    rejected_rows = _safe_int(diagnostics.get("rejected_rows"))
    return _clamp(float(rejected_rows) / 60.0)


def _inconsistency_penalty(method_payload: Mapping[str, Any]) -> float:
    diagnostics = _first_diagnostics(method_payload)
    consistency_failures = _safe_int(diagnostics.get("consistency_failures"))
    normalization_corrections = _safe_int(diagnostics.get("normalization_corrections"))
    identity_conflicts = _safe_int(diagnostics.get("identity_resolution_conflicts"))
    rejection_reasons = diagnostics.get("rejection_reasons")
    conflict_rejections = 0
    if isinstance(rejection_reasons, Mapping):
        for key in ("canonical_conflict_same_period", "statement_type_metric_conflict", "metric_statement_mismatch"):
            conflict_rejections += _safe_int(rejection_reasons.get(key))
    composite = consistency_failures + normalization_corrections + identity_conflicts + conflict_rejections
    return _clamp(float(composite) / 80.0)


def compute_confidence(method_payload: dict[str, Any]) -> float:
    payload = dict(method_payload or {})
    if str(payload.get("status") or "").lower() not in {"ok", "success"}:
        return 0.0
    coverage = metric_coverage(payload)
    completeness = _completeness_score(payload)
    rejected_penalty = _rejected_rows_penalty(payload)
    inconsistency_penalty = _inconsistency_penalty(payload)

    confidence = (
        0.55 * coverage
        + 0.35 * completeness
        - 0.06 * rejected_penalty
        - 0.04 * inconsistency_penalty
    )
    anomaly = detect_anomalies(payload)
    if bool(anomaly.get("has_anomaly")):
        severity = str(anomaly.get("severity") or "").lower()
        if severity == "high":
            confidence *= 0.3
        elif severity == "medium":
            confidence *= 0.6
        else:
            confidence *= 0.8
    return round(_clamp(confidence), 6)


def missing_required_metrics(method_payload: Mapping[str, Any], required_metrics: Sequence[str] = REQUIRED_METRICS) -> list[str]:
    canonical_metrics = method_payload.get("canonical_metrics")
    if not isinstance(canonical_metrics, Mapping):
        return list(required_metrics)
    missing: list[str] = []
    for metric in required_metrics:
        if metric not in canonical_metrics:
            missing.append(str(metric))
    return missing


def has_inconsistent_values(method_payload: Mapping[str, Any]) -> bool:
    canonical_metrics = method_payload.get("canonical_metrics")
    if not isinstance(canonical_metrics, Mapping):
        return False
    revenue = canonical_metrics.get("revenue")
    assets = canonical_metrics.get("assets")
    liabilities = canonical_metrics.get("liabilities")
    if isinstance(revenue, (int, float)) and float(revenue) < 0.0:
        return True
    if isinstance(assets, (int, float)) and float(assets) < 0.0:
        return True
    if isinstance(liabilities, (int, float)) and float(liabilities) < 0.0:
        return True
    return False


def fallback_reasons(
    method_payload: Mapping[str, Any],
    *,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    min_coverage: float = MIN_COVERAGE,
    required_metrics: Sequence[str] = REQUIRED_METRICS,
) -> list[str]:
    payload = dict(method_payload or {})
    reasons: list[str] = []
    confidence = compute_confidence(payload)
    coverage = metric_coverage(payload)
    missing = missing_required_metrics(payload, required_metrics=required_metrics)
    anomaly = detect_anomalies(payload)
    if confidence < float(confidence_threshold):
        reasons.append("low_confidence")
    if coverage < float(min_coverage):
        reasons.append("low_coverage")
    if missing:
        reasons.append("missing_required_metrics")
    if bool(anomaly.get("has_anomaly")):
        reasons.append("financial_anomaly")
    if has_inconsistent_values(payload):
        reasons.append("inconsistent_metric_values")
    return reasons
