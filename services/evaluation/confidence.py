#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from services.evaluation.anomaly import _HIGH_FLAGS, _MEDIUM_FLAGS, detect_anomalies


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALIBRATION_PATH = REPO_ROOT / "configs" / "extraction_calibration.json"

DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_MIN_COVERAGE = 0.6
DEFAULT_PENALTIES = {
    "high": 0.3,
    "medium": 0.6,
    "low": 0.8,
}
REQUIRED_METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "net_income",
)
DOC_TYPE_THRESHOLDS: dict[str, dict[str, float]] = {
    "structured_financial_reports": {
        "confidence_threshold": 0.6,
        "min_coverage": 0.4,
    },
    "semi_structured_presentations": {
        "confidence_threshold": 0.5,
        "min_coverage": 0.3,
    },
    "complex_ocr_heavy": {
        "confidence_threshold": 0.75,
        "min_coverage": 0.6,
    },
}
DOC_TYPE_PROFILE_MAP: dict[str, str] = {
    "appendix_report": "structured_financial_reports",
    "annual_report": "structured_financial_reports",
    "half_year_report": "structured_financial_reports",
    "quarterly_report": "structured_financial_reports",
    "structured_financial_reports": "structured_financial_reports",
    "investor_update": "semi_structured_presentations",
    "announcement": "semi_structured_presentations",
    "presentation": "semi_structured_presentations",
    "semi_structured_presentations": "semi_structured_presentations",
    "scanned_financial": "complex_ocr_heavy",
    "ocr_heavy": "complex_ocr_heavy",
    "complex_ocr_heavy": "complex_ocr_heavy",
}


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


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _canonical_metric_count(method_payload: Mapping[str, Any]) -> int:
    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping):
        return len(canonical_metrics)
    return 0


def _row_count(method_payload: Mapping[str, Any]) -> int:
    completeness = method_payload.get("completeness")
    if isinstance(completeness, Mapping):
        return _safe_int(completeness.get("row_count"))
    return 0


def _doc_type_profile(doc_type: str | None, complexity_bucket: str | None = None) -> str | None:
    normalized = str(doc_type or "").strip().lower()
    if normalized in DOC_TYPE_PROFILE_MAP:
        return DOC_TYPE_PROFILE_MAP[normalized]
    if str(complexity_bucket or "").strip().lower() == "high":
        return "complex_ocr_heavy"
    return None


def _resolve_thresholds(
    *,
    doc_type: str | None,
    complexity_bucket: str | None,
    confidence_threshold: float,
    min_coverage: float,
) -> tuple[float, float]:
    profile = _doc_type_profile(doc_type, complexity_bucket=complexity_bucket)
    if profile is None:
        return float(confidence_threshold), float(min_coverage)
    override = DOC_TYPE_THRESHOLDS.get(profile) or {}
    resolved_confidence = float(override.get("confidence_threshold", confidence_threshold))
    resolved_coverage = float(override.get("min_coverage", min_coverage))
    return resolved_confidence, resolved_coverage


def _effective_required_metrics(required_metrics: Sequence[str], doc_type: str | None, is_financial: bool | None) -> tuple[str, ...]:
    normalized = str(doc_type or "").strip().lower()
    if is_financial is False and normalized == "unknown":
        return ()
    return tuple(str(metric) for metric in required_metrics)


def _defer_non_financial_unknown_fallback(
    *,
    doc_type: str | None,
    is_financial: bool | None,
    canonical_metric_count: int,
    row_count: int,
    coverage: float,
    anomaly: Mapping[str, Any],
) -> bool:
    if is_financial is not False:
        return False
    if str(doc_type or "").strip().lower() != "unknown":
        return False
    if canonical_metric_count > 0 or row_count > 0:
        return False
    if float(coverage) > 0.05:
        return False
    if bool(anomaly.get("has_anomaly")) and str(anomaly.get("severity") or "").lower() == "high":
        return False
    return True


def _default_calibration() -> dict[str, Any]:
    return {
        "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
        "min_coverage": DEFAULT_MIN_COVERAGE,
        "penalties": dict(DEFAULT_PENALTIES),
        "non_critical_flags": [],
        "metrics": {
            "baseline_fallback_rate": 0.0,
            "calibrated_fallback_rate": 0.0,
            "baseline_accuracy": 0.0,
            "calibrated_accuracy": 0.0,
        },
    }


def load_calibration(calibration_path: str | None = None) -> dict[str, Any]:
    calibration = _default_calibration()
    path = Path(calibration_path).expanduser().resolve() if calibration_path else DEFAULT_CALIBRATION_PATH
    if not path.exists() or not path.is_file():
        return calibration
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return calibration
    if not isinstance(payload, Mapping):
        return calibration

    penalties = payload.get("penalties")
    if isinstance(penalties, Mapping):
        calibration["penalties"] = {
            "high": _clamp(_float_or_default(penalties.get("high"), DEFAULT_PENALTIES["high"])),
            "medium": _clamp(_float_or_default(penalties.get("medium"), DEFAULT_PENALTIES["medium"])),
            "low": _clamp(_float_or_default(penalties.get("low"), DEFAULT_PENALTIES["low"])),
        }
    non_critical = payload.get("non_critical_flags")
    if isinstance(non_critical, Sequence) and not isinstance(non_critical, (str, bytes)):
        calibration["non_critical_flags"] = sorted({str(flag) for flag in non_critical if str(flag)})
    metrics = payload.get("metrics")
    if isinstance(metrics, Mapping):
        calibration["metrics"] = {
            "baseline_fallback_rate": _clamp(_float_or_default(metrics.get("baseline_fallback_rate"), 0.0)),
            "calibrated_fallback_rate": _clamp(_float_or_default(metrics.get("calibrated_fallback_rate"), 0.0)),
            "baseline_accuracy": _clamp(_float_or_default(metrics.get("baseline_accuracy"), 0.0)),
            "calibrated_accuracy": _clamp(_float_or_default(metrics.get("calibrated_accuracy"), 0.0)),
        }

    calibration["confidence_threshold"] = _clamp(
        _float_or_default(payload.get("confidence_threshold"), DEFAULT_CONFIDENCE_THRESHOLD),
    )
    calibration["min_coverage"] = _clamp(
        _float_or_default(payload.get("min_coverage"), DEFAULT_MIN_COVERAGE),
    )
    return calibration


CALIBRATED = load_calibration()
CONFIDENCE_THRESHOLD = _clamp(
    _float_or_default(CALIBRATED.get("confidence_threshold"), DEFAULT_CONFIDENCE_THRESHOLD),
)
MIN_COVERAGE = _clamp(
    _float_or_default(CALIBRATED.get("min_coverage"), DEFAULT_MIN_COVERAGE),
)
ANOMALY_PENALTIES = {
    "high": _clamp(_float_or_default((CALIBRATED.get("penalties") or {}).get("high"), DEFAULT_PENALTIES["high"])),
    "medium": _clamp(_float_or_default((CALIBRATED.get("penalties") or {}).get("medium"), DEFAULT_PENALTIES["medium"])),
    "low": _clamp(_float_or_default((CALIBRATED.get("penalties") or {}).get("low"), DEFAULT_PENALTIES["low"])),
}
NON_CRITICAL_FLAGS = set(str(flag) for flag in (CALIBRATED.get("non_critical_flags") or []))


def _first_diagnostics(method_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    diagnostics = method_payload.get("document_diagnostics")
    if isinstance(diagnostics, Sequence) and diagnostics:
        first = diagnostics[0]
        if isinstance(first, Mapping):
            return first
    return {}


def metric_coverage(method_payload: Mapping[str, Any]) -> float:
    val = method_payload.get("metric_coverage_rate")
    if isinstance(val, (int, float)):
        return _clamp(float(val))

    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping) and canonical_metrics:
        return _clamp(float(len(canonical_metrics)) / 5.0)

    score = method_payload.get("score")
    if isinstance(score, Mapping):
        aggregate = score.get("aggregate")
        if isinstance(aggregate, Mapping):
            completeness = aggregate.get("completeness")
            if isinstance(completeness, (int, float)):
                return _clamp(float(completeness))

    return 0.3


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


def _effective_anomaly(method_payload: Mapping[str, Any]) -> dict[str, Any]:
    anomaly = detect_anomalies(dict(method_payload or {}))
    raw_flags = anomaly.get("flags")
    flags: list[str] = []
    if isinstance(raw_flags, Sequence) and not isinstance(raw_flags, (str, bytes)):
        for flag in raw_flags:
            name = str(flag or "").strip()
            if name and name not in NON_CRITICAL_FLAGS:
                flags.append(name)
    critical_flags = sorted(set(flags))
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


def compute_confidence(method_payload: dict[str, Any]) -> float:
    payload = dict(method_payload or {})
    status = str(payload.get("status") or "").lower()
    if status in {"error", "failed", "crash"}:
        return 0.0
    coverage = metric_coverage(payload)
    if coverage is None:
        coverage = 0.3
    canonical_metric_count = _canonical_metric_count(payload)
    row_count = _row_count(payload)
    completeness = _completeness_score(payload)
    rejected_penalty = _rejected_rows_penalty(payload)
    inconsistency_penalty = _inconsistency_penalty(payload)

    confidence = (
        0.55 * coverage
        + 0.35 * completeness
        - 0.06 * rejected_penalty
        - 0.04 * inconsistency_penalty
    )
    if confidence <= 0.0:
        confidence = (0.1 * coverage) + 0.1
    anomaly = _effective_anomaly(payload)
    if (
        canonical_metric_count >= 3
        and row_count >= 8
        and str(anomaly.get("severity") or "").lower() != "high"
    ):
        confidence += 0.05
        if row_count >= 20:
            confidence += 0.03
    if bool(anomaly.get("has_anomaly")):
        severity = str(anomaly.get("severity") or "low").lower()
        penalty = _clamp(_float_or_default(ANOMALY_PENALTIES.get(severity), ANOMALY_PENALTIES["low"]))
        confidence *= penalty
    verification_ratio = _clamp(_float_or_default(payload.get("verification_ratio"), 1.0))
    confidence *= verification_ratio
    confidence = max(confidence, 0.05)
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
    doc_type: str | None = None,
    complexity_bucket: str | None = None,
    is_financial: bool | None = None,
) -> list[str]:
    payload = dict(method_payload or {})
    reasons: list[str] = []
    confidence = compute_confidence(payload)
    coverage = metric_coverage(payload)
    if coverage is None:
        coverage = 0.3
    canonical_metric_count = _canonical_metric_count(payload)
    row_count = _row_count(payload)
    anomaly = _effective_anomaly(payload)
    resolved_confidence_threshold, resolved_min_coverage = _resolve_thresholds(
        doc_type=doc_type,
        complexity_bucket=complexity_bucket,
        confidence_threshold=float(confidence_threshold),
        min_coverage=float(min_coverage),
    )
    effective_required_metrics = _effective_required_metrics(required_metrics, doc_type=doc_type, is_financial=is_financial)
    missing = missing_required_metrics(payload, required_metrics=effective_required_metrics)

    if _defer_non_financial_unknown_fallback(
        doc_type=doc_type,
        is_financial=is_financial,
        canonical_metric_count=canonical_metric_count,
        row_count=row_count,
        coverage=float(coverage),
        anomaly=anomaly,
    ):
        if bool(anomaly.get("has_anomaly")) and str(anomaly.get("severity") or "").lower() == "high":
            reasons.append("financial_anomaly")
        if has_inconsistent_values(payload):
            reasons.append("inconsistent_metric_values")
        return reasons

    if confidence < float(resolved_confidence_threshold):
        reasons.append("low_confidence")
    if coverage is not None and coverage < float(resolved_min_coverage) and confidence < 0.5:
        reasons.append("low_coverage")
    missing_count = len(missing)
    if missing_count:
        if missing_count >= 2 or confidence < 0.5:
            reasons.append("missing_required_metrics")
        elif missing_count == 1 and not (confidence >= 0.65 and canonical_metric_count >= 3):
            reasons.append("missing_required_metrics")
    if bool(anomaly.get("has_anomaly")) and str(anomaly.get("severity") or "").lower() == "high":
        reasons.append("financial_anomaly")
    if has_inconsistent_values(payload):
        reasons.append("inconsistent_metric_values")
    return reasons
