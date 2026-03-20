#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from services.evaluation.anomaly import _HIGH_FLAGS, _MEDIUM_FLAGS, detect_anomalies


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALIBRATION_PATH = REPO_ROOT / "configs" / "extraction_calibration.json"
PROBE_METHOD = "financial_metrics_pdftotext"
FALLBACK_METHOD = "financial_metrics_docling"

DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_MIN_COVERAGE = 0.6
DEFAULT_REQUIRED_METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "net_income",
)
DEFAULT_PENALTIES = {
    "high": 0.3,
    "medium": 0.6,
    "low": 0.8,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_accuracy(method_payload: Mapping[str, Any] | None) -> float | None:
    if not isinstance(method_payload, Mapping):
        return None
    score = method_payload.get("score")
    if not isinstance(score, Mapping):
        return None
    if str(score.get("status") or "").upper() != "SUCCESS":
        return None
    aggregate = score.get("aggregate")
    if not isinstance(aggregate, Mapping):
        return None
    try:
        return float(aggregate.get("accuracy"))
    except (TypeError, ValueError):
        return None


def _first_diagnostics(method_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = method_payload.get("document_diagnostics")
    if isinstance(diagnostics, Sequence) and diagnostics:
        first = diagnostics[0]
        if isinstance(first, Mapping):
            return first
    return {}


def _metric_coverage(method_payload: Mapping[str, Any]) -> float:
    metric_coverage_rate = method_payload.get("metric_coverage_rate")
    if isinstance(metric_coverage_rate, (int, float)):
        return _clamp(float(metric_coverage_rate))
    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping):
        from services.evaluation.normalizer import canonical_metric_keys  # local import to avoid cycles

        denom = float(max(1, len(canonical_metric_keys())))
        return _clamp(float(len(canonical_metrics)) / denom)
    return 0.0


def _completeness_score(method_payload: Mapping[str, Any]) -> float:
    score = method_payload.get("score")
    if isinstance(score, Mapping) and str(score.get("status") or "").upper() == "SUCCESS":
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
    return _clamp((0.6 * row_component) + (0.4 * numeric_component))


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


def _missing_required_metrics(
    method_payload: Mapping[str, Any],
    required_metrics: Sequence[str] = DEFAULT_REQUIRED_METRICS,
) -> list[str]:
    canonical_metrics = method_payload.get("canonical_metrics")
    if not isinstance(canonical_metrics, Mapping):
        return [str(metric) for metric in required_metrics]
    missing: list[str] = []
    for metric in required_metrics:
        if metric not in canonical_metrics:
            missing.append(str(metric))
    return missing


def _has_inconsistent_values(method_payload: Mapping[str, Any]) -> bool:
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


def _effective_anomaly(
    method_payload: Mapping[str, Any],
    *,
    non_critical_flags: Sequence[str],
) -> dict[str, Any]:
    anomaly = detect_anomalies(dict(method_payload or {}))
    raw_flags = anomaly.get("flags")
    flags: list[str] = []
    if isinstance(raw_flags, Sequence):
        for flag in raw_flags:
            name = str(flag or "").strip()
            if name:
                flags.append(name)
    non_critical = {str(flag) for flag in non_critical_flags}
    critical_flags = sorted({flag for flag in flags if flag not in non_critical})
    if not critical_flags:
        return {"has_anomaly": False, "severity": "low", "flags": []}
    flag_set = set(critical_flags)
    if flag_set & set(_HIGH_FLAGS):
        severity = "high"
    elif flag_set & set(_MEDIUM_FLAGS):
        severity = "medium"
    else:
        severity = "low"
    return {
        "has_anomaly": True,
        "severity": severity,
        "flags": critical_flags,
    }


def _compute_confidence(
    method_payload: Mapping[str, Any],
    *,
    penalties: Mapping[str, float],
    non_critical_flags: Sequence[str],
) -> float:
    payload = dict(method_payload or {})
    if str(payload.get("status") or "").lower() not in {"ok", "success"}:
        return 0.0
    coverage = _metric_coverage(payload)
    completeness = _completeness_score(payload)
    rejected_penalty = _rejected_rows_penalty(payload)
    inconsistency_penalty = _inconsistency_penalty(payload)
    confidence = (
        (0.55 * coverage)
        + (0.35 * completeness)
        - (0.06 * rejected_penalty)
        - (0.04 * inconsistency_penalty)
    )
    anomaly = _effective_anomaly(payload, non_critical_flags=non_critical_flags)
    if bool(anomaly.get("has_anomaly")):
        severity = str(anomaly.get("severity") or "low").lower()
        confidence *= _safe_float(penalties.get(severity), _safe_float(penalties.get("low"), DEFAULT_PENALTIES["low"]))
    return round(_clamp(confidence), 6)


def _fallback_reasons(
    method_payload: Mapping[str, Any],
    *,
    confidence_threshold: float,
    min_coverage: float,
    required_metrics: Sequence[str],
    penalties: Mapping[str, float],
    non_critical_flags: Sequence[str],
) -> list[str]:
    payload = dict(method_payload or {})
    confidence = _compute_confidence(
        payload,
        penalties=penalties,
        non_critical_flags=non_critical_flags,
    )
    coverage = _metric_coverage(payload)
    missing = _missing_required_metrics(payload, required_metrics=required_metrics)
    anomaly = _effective_anomaly(payload, non_critical_flags=non_critical_flags)
    reasons: list[str] = []
    if confidence < float(confidence_threshold):
        reasons.append("low_confidence")
    if coverage < float(min_coverage):
        reasons.append("low_coverage")
    if missing:
        reasons.append("missing_required_metrics")
    if bool(anomaly.get("has_anomaly")) and str(anomaly.get("severity") or "").lower() == "high":
        reasons.append("financial_anomaly")
    if _has_inconsistent_values(payload):
        reasons.append("inconsistent_metric_values")
    return reasons


def _doc_key(document: Mapping[str, Any]) -> str:
    doc_id = str(document.get("doc_id") or "").strip()
    if doc_id:
        return doc_id
    return str(document.get("pdf") or "").strip()


def _extract_routing_documents(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    routing_docs = payload.get("routing_documents")
    if isinstance(routing_docs, Sequence):
        resolved: dict[str, Mapping[str, Any]] = {}
        for entry in routing_docs:
            if not isinstance(entry, Mapping):
                continue
            key = _doc_key(entry)
            if key:
                resolved[key] = entry
        return resolved
    documents = payload.get("documents")
    if isinstance(documents, Sequence):
        resolved = {}
        for entry in documents:
            if not isinstance(entry, Mapping):
                continue
            if "selected_method" not in entry and "fallback_triggered" not in entry:
                continue
            key = _doc_key(entry)
            if key:
                resolved[key] = entry
        return resolved
    return {}


def _extract_baseline_metrics(payload: Mapping[str, Any]) -> dict[str, float]:
    summary = payload.get("summary")
    if not isinstance(summary, Mapping):
        summary = {}
    routing_eval = summary.get("routing_evaluation")
    if not isinstance(routing_eval, Mapping):
        routing_eval = {}
    full_accuracy = routing_eval.get("full_accuracy")
    if full_accuracy is None:
        full_accuracy = routing_eval.get("full_benchmark_accuracy")
    if full_accuracy is None:
        full_accuracy = summary.get("full_accuracy")
    routed_accuracy = routing_eval.get("routed_accuracy")
    if routed_accuracy is None:
        routed_accuracy = routing_eval.get("accuracy_with_fallback")
    if routed_accuracy is None:
        routed_accuracy = summary.get("routed_accuracy")
    if routed_accuracy is None:
        routed_accuracy = summary.get("accuracy_with_fallback")
    fallback_rate = routing_eval.get("fallback_rate")
    if fallback_rate is None:
        fallback_rate = summary.get("fallback_rate")
    anomaly_rate = routing_eval.get("anomaly_rate")
    if anomaly_rate is None:
        anomaly_rate = summary.get("anomaly_rate")
    return {
        "full_accuracy": _optional_float(full_accuracy),
        "routed_accuracy": _optional_float(routed_accuracy),
        "fallback_rate": _optional_float(fallback_rate),
        "anomaly_rate": _optional_float(anomaly_rate),
    }


def _extract_method_records(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    routing_by_doc = _extract_routing_documents(payload)
    records: list[dict[str, Any]] = []
    documents = payload.get("documents")
    if not isinstance(documents, Sequence):
        return records
    for document in documents:
        if not isinstance(document, Mapping):
            continue
        methods = document.get("methods")
        if not isinstance(methods, Mapping):
            continue
        key = _doc_key(document)
        routed = routing_by_doc.get(key, {})
        for method_name, method_payload in methods.items():
            if not isinstance(method_payload, Mapping):
                continue
            anomaly = detect_anomalies(dict(method_payload))
            confidence = _compute_confidence(
                method_payload,
                penalties=DEFAULT_PENALTIES,
                non_critical_flags=(),
            )
            records.append(
                {
                    "doc_key": key,
                    "method": str(method_name),
                    "payload": dict(method_payload),
                    "accuracy": _score_accuracy(method_payload),
                    "confidence": confidence,
                    "anomaly_flags": list(anomaly.get("flags") or []),
                    "anomaly_severity": str(anomaly.get("severity") or "low"),
                    "selected_method": str(routed.get("selected_method") or ""),
                    "fallback_triggered": bool(routed.get("fallback_triggered")) if routed else False,
                }
            )
    return records


def _extract_routing_cases(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    documents = payload.get("documents")
    if not isinstance(documents, Sequence):
        return cases
    for document in documents:
        if not isinstance(document, Mapping):
            continue
        methods = document.get("methods")
        if not isinstance(methods, Mapping):
            continue
        probe_payload = methods.get(PROBE_METHOD)
        fallback_payload = methods.get(FALLBACK_METHOD)
        if not isinstance(probe_payload, Mapping):
            continue
        cases.append(
            {
                "doc_key": _doc_key(document),
                "probe_payload": dict(probe_payload),
                "fallback_payload": dict(fallback_payload) if isinstance(fallback_payload, Mapping) else None,
                "probe_accuracy": _score_accuracy(probe_payload),
                "fallback_accuracy": _score_accuracy(fallback_payload) if isinstance(fallback_payload, Mapping) else None,
            }
        )
    return cases


def _analyze_anomaly_flags(method_records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, float]], list[str]]:
    evaluated = [record for record in method_records if isinstance(record, Mapping) and record.get("accuracy") is not None]
    if not evaluated:
        return {}, []
    baseline_incorrect_rate = (
        sum(1.0 for record in evaluated if _safe_float(record.get("accuracy"), 1.0) < 0.5) / float(len(evaluated))
    )
    by_flag: dict[str, dict[str, float]] = {}
    for record in evaluated:
        accuracy = _safe_float(record.get("accuracy"), 0.0)
        is_incorrect = 1.0 if accuracy < 0.5 else 0.0
        raw_flags = record.get("anomaly_flags")
        if not isinstance(raw_flags, Sequence):
            continue
        for raw_flag in raw_flags:
            flag = str(raw_flag or "").strip()
            if not flag:
                continue
            bucket = by_flag.setdefault(flag, {"count": 0.0, "incorrect": 0.0})
            bucket["count"] += 1.0
            bucket["incorrect"] += is_incorrect
    non_critical_flags: list[str] = []
    total_records = float(max(1, len(evaluated)))
    stats: dict[str, dict[str, float]] = {}
    for flag in sorted(by_flag.keys()):
        count = _safe_float(by_flag[flag].get("count"))
        incorrect = _safe_float(by_flag[flag].get("incorrect"))
        incorrect_rate = incorrect / float(max(1.0, count))
        frequency = count / total_records
        correlation = incorrect_rate - baseline_incorrect_rate
        stats[flag] = {
            "frequency": round(frequency, 6),
            "incorrect_rate": round(incorrect_rate, 6),
            "correlation_with_incorrect": round(correlation, 6),
        }
        if incorrect_rate < 0.3:
            non_critical_flags.append(flag)
    return stats, sorted(non_critical_flags)


def _tune_penalties(method_records: Sequence[Mapping[str, Any]], non_critical_flags: Sequence[str]) -> dict[str, float]:
    severity_buckets: dict[str, list[float]] = {"high": [], "medium": [], "low": []}
    for record in method_records:
        if not isinstance(record, Mapping):
            continue
        accuracy = record.get("accuracy")
        payload = record.get("payload")
        if accuracy is None or not isinstance(payload, Mapping):
            continue
        anomaly = _effective_anomaly(payload, non_critical_flags=non_critical_flags)
        if not bool(anomaly.get("has_anomaly")):
            continue
        severity = str(anomaly.get("severity") or "low").lower()
        if severity not in severity_buckets:
            severity = "low"
        severity_buckets[severity].append(1.0 if _safe_float(accuracy, 0.0) < 0.5 else 0.0)

    penalties: dict[str, float] = dict(DEFAULT_PENALTIES)
    for severity, values in severity_buckets.items():
        if not values:
            continue
        incorrect_rate = sum(values) / float(len(values))
        if severity == "high":
            penalties[severity] = _clamp(1.0 - (0.9 * incorrect_rate), 0.25, 0.7)
        elif severity == "medium":
            penalties[severity] = _clamp(1.0 - (0.7 * incorrect_rate), 0.4, 0.85)
        else:
            penalties[severity] = _clamp(1.0 - (0.4 * incorrect_rate), 0.65, 0.95)

    high = min(penalties["high"], penalties["medium"], penalties["low"])
    medium = max(high, min(penalties["medium"], penalties["low"]))
    low = max(medium, penalties["low"])
    return {
        "high": round(high, 6),
        "medium": round(medium, 6),
        "low": round(low, 6),
    }


def _simulate_routing(
    cases: Sequence[Mapping[str, Any]],
    *,
    confidence_threshold: float,
    min_coverage: float,
    penalties: Mapping[str, float],
    non_critical_flags: Sequence[str],
) -> dict[str, float]:
    total_docs = float(max(1, len(cases)))
    fallback_count = 0.0
    anomaly_count = 0.0
    selected_accuracy_total = 0.0
    selected_accuracy_count = 0.0
    false_fallback_count = 0.0
    false_fallback_total = 0.0
    missed_fallback_count = 0.0
    missed_fallback_total = 0.0

    for case in cases:
        if not isinstance(case, Mapping):
            continue
        probe_payload = case.get("probe_payload")
        fallback_payload = case.get("fallback_payload")
        if not isinstance(probe_payload, Mapping):
            continue

        probe_accuracy = case.get("probe_accuracy")
        if probe_accuracy is not None:
            probe_accuracy = _safe_float(probe_accuracy)

        reasons = _fallback_reasons(
            probe_payload,
            confidence_threshold=confidence_threshold,
            min_coverage=min_coverage,
            required_metrics=DEFAULT_REQUIRED_METRICS,
            penalties=penalties,
            non_critical_flags=non_critical_flags,
        )
        fallback_triggered = bool(reasons)
        if fallback_triggered:
            fallback_count += 1.0

        selected_payload: Mapping[str, Any] = probe_payload
        selected_accuracy = probe_accuracy
        probe_confidence = _compute_confidence(
            probe_payload,
            penalties=penalties,
            non_critical_flags=non_critical_flags,
        )
        if fallback_triggered and isinstance(fallback_payload, Mapping):
            fallback_confidence = _compute_confidence(
                fallback_payload,
                penalties=penalties,
                non_critical_flags=non_critical_flags,
            )
            if fallback_confidence > probe_confidence:
                selected_payload = fallback_payload
                fallback_accuracy = case.get("fallback_accuracy")
                selected_accuracy = None if fallback_accuracy is None else _safe_float(fallback_accuracy)

        selected_anomaly = _effective_anomaly(
            selected_payload,
            non_critical_flags=non_critical_flags,
        )
        if bool(selected_anomaly.get("has_anomaly")):
            anomaly_count += 1.0

        if selected_accuracy is not None:
            selected_accuracy_total += float(selected_accuracy)
            selected_accuracy_count += 1.0

        if probe_accuracy is not None and probe_accuracy > 0.9:
            false_fallback_total += 1.0
            if fallback_triggered:
                false_fallback_count += 1.0
        if probe_accuracy is not None and probe_accuracy < 0.5:
            missed_fallback_total += 1.0
            if not fallback_triggered:
                missed_fallback_count += 1.0

    return {
        "accuracy": round(
            selected_accuracy_total / float(max(1.0, selected_accuracy_count)),
            6,
        ),
        "fallback_rate": round(fallback_count / total_docs, 6),
        "anomaly_rate": round(anomaly_count / total_docs, 6),
        "false_fallback_rate": round(false_fallback_count / float(max(1.0, false_fallback_total)), 6),
        "missed_fallback_rate": round(missed_fallback_count / float(max(1.0, missed_fallback_total)), 6),
    }


def _threshold_candidates() -> list[float]:
    values: list[float] = []
    step = 0
    while step <= 8:
        values.append(round(0.5 + (0.05 * step), 2))
        step += 1
    return values


def _coverage_candidates() -> list[float]:
    return [0.2, 0.3, 0.4, 0.5, 0.6]


def calibrate_thresholds(benchmark_json_path: str) -> dict[str, Any]:
    path = Path(benchmark_json_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))

    method_records = _extract_method_records(payload)
    routing_cases = _extract_routing_cases(payload)
    _, non_critical_flags = _analyze_anomaly_flags(method_records)
    penalties = _tune_penalties(method_records, non_critical_flags=non_critical_flags)

    baseline_simulation = _simulate_routing(
        routing_cases,
        confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
        min_coverage=DEFAULT_MIN_COVERAGE,
        penalties=DEFAULT_PENALTIES,
        non_critical_flags=(),
    )

    best_threshold = DEFAULT_CONFIDENCE_THRESHOLD
    best_min_coverage = DEFAULT_MIN_COVERAGE
    best_metrics = _simulate_routing(
        routing_cases,
        confidence_threshold=best_threshold,
        min_coverage=best_min_coverage,
        penalties=penalties,
        non_critical_flags=non_critical_flags,
    )
    best_key = (
        round(_safe_float(best_metrics.get("accuracy")), 6),
        -round(_safe_float(best_metrics.get("false_fallback_rate")) + _safe_float(best_metrics.get("missed_fallback_rate")), 6),
        -round(_safe_float(best_metrics.get("fallback_rate")), 6),
    )

    for threshold in _threshold_candidates():
        for min_coverage in _coverage_candidates():
            simulation = _simulate_routing(
                routing_cases,
                confidence_threshold=threshold,
                min_coverage=min_coverage,
                penalties=penalties,
                non_critical_flags=non_critical_flags,
            )
            candidate_key = (
                round(_safe_float(simulation.get("accuracy")), 6),
                -round(_safe_float(simulation.get("false_fallback_rate")) + _safe_float(simulation.get("missed_fallback_rate")), 6),
                -round(_safe_float(simulation.get("fallback_rate")), 6),
            )
            if candidate_key > best_key:
                best_key = candidate_key
                best_threshold = threshold
                best_min_coverage = min_coverage
                best_metrics = simulation
            elif candidate_key == best_key:
                if threshold < best_threshold or (
                    threshold == best_threshold and min_coverage < best_min_coverage
                ):
                    best_threshold = threshold
                    best_min_coverage = min_coverage
                    best_metrics = simulation

    baseline_from_payload = _extract_baseline_metrics(payload)
    baseline_fallback_payload = baseline_from_payload.get("fallback_rate")
    baseline_accuracy_payload = baseline_from_payload.get("routed_accuracy")
    baseline_fallback_rate = _safe_float(baseline_fallback_payload, _safe_float(baseline_simulation.get("fallback_rate")))
    baseline_accuracy = _safe_float(baseline_accuracy_payload, _safe_float(baseline_simulation.get("accuracy")))
    calibrated_fallback_rate = _safe_float(best_metrics.get("fallback_rate"))
    calibrated_accuracy = _safe_float(best_metrics.get("accuracy"))

    return {
        "confidence_threshold": round(float(best_threshold), 6),
        "min_coverage": round(float(best_min_coverage), 6),
        "penalties": {
            "high": round(_safe_float(penalties.get("high"), DEFAULT_PENALTIES["high"]), 6),
            "medium": round(_safe_float(penalties.get("medium"), DEFAULT_PENALTIES["medium"]), 6),
            "low": round(_safe_float(penalties.get("low"), DEFAULT_PENALTIES["low"]), 6),
        },
        "non_critical_flags": sorted({str(flag) for flag in non_critical_flags if str(flag)}),
        "metrics": {
            "baseline_fallback_rate": round(baseline_fallback_rate, 6),
            "calibrated_fallback_rate": round(calibrated_fallback_rate, 6),
            "baseline_accuracy": round(baseline_accuracy, 6),
            "calibrated_accuracy": round(calibrated_accuracy, 6),
        },
    }
