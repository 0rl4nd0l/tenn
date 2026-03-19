"""Regression guard for baseline-protected metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegressionViolation:
    metric: str
    baseline: float
    current: float
    allowed: float
    direction: str


@dataclass(frozen=True)
class RegressionResult:
    passed: bool
    violations: list[RegressionViolation]
    decision: str
    stop_retries: bool
    baseline_path: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_direction(metric: str) -> str:
    lowered = metric.lower()
    if any(token in lowered for token in ("error", "latency", "duration", "violat", "fail")):
        return "min"
    return "max"


def load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return None
    return payload


def _normalize_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, raw in metrics.items():
        try:
            normalized[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return normalized


def compare(
    current_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
    tolerances: dict[str, float],
    protected_metrics: tuple[str, ...],
    baseline_path: str,
) -> RegressionResult:
    current_norm = _normalize_metrics(current_metrics)
    baseline_norm = _normalize_metrics(baseline_metrics)
    metrics_to_check = list(protected_metrics) if protected_metrics else sorted(baseline_norm.keys())
    violations: list[RegressionViolation] = []

    for metric in metrics_to_check:
        if metric not in baseline_norm or metric not in current_norm:
            continue
        baseline_value = baseline_norm[metric]
        current_value = current_norm[metric]
        tolerance = float(tolerances.get(metric, 0.0))
        direction = _default_direction(metric)
        if direction == "max":
            allowed = baseline_value - tolerance
            if current_value < allowed:
                violations.append(
                    RegressionViolation(
                        metric=metric,
                        baseline=baseline_value,
                        current=current_value,
                        allowed=allowed,
                        direction=direction,
                    )
                )
        else:
            allowed = baseline_value + tolerance
            if current_value > allowed:
                violations.append(
                    RegressionViolation(
                        metric=metric,
                        baseline=baseline_value,
                        current=current_value,
                        allowed=allowed,
                        direction=direction,
                    )
                )

    return RegressionResult(
        passed=not violations,
        violations=violations,
        decision="pass" if not violations else "fail",
        stop_retries=False,
        baseline_path=baseline_path,
    )


def _write_baseline(
    baseline_path: Path,
    current_metrics: dict[str, Any],
    run_id: str | None,
) -> None:
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "created_at": _utc_now_iso(),
        "source_run_id": run_id,
        "metrics": _normalize_metrics(current_metrics),
    }
    baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def maybe_initialize_baseline(
    current_metrics: dict[str, Any],
    allow_init_flag: bool,
    baseline_path: Path,
    run_id: str | None = None,
) -> RegressionResult:
    if baseline_path.exists():
        return RegressionResult(
            passed=True,
            violations=[],
            decision="pass",
            stop_retries=False,
            baseline_path=str(baseline_path),
        )
    if not allow_init_flag:
        return RegressionResult(
            passed=False,
            violations=[],
            decision="baseline_init_blocked",
            stop_retries=True,
            baseline_path=str(baseline_path),
        )
    _write_baseline(baseline_path, current_metrics=current_metrics, run_id=run_id)
    return RegressionResult(
        passed=True,
        violations=[],
        decision="baseline_initialized",
        stop_retries=False,
        baseline_path=str(baseline_path),
    )


def evaluate_regression(
    current_metrics: dict[str, Any],
    baseline_path: Path,
    tolerances: dict[str, float],
    protected_metrics: tuple[str, ...],
    allow_baseline_init: bool,
    allow_baseline_update: bool,
    gates_passed: bool,
    run_id: str | None = None,
) -> RegressionResult:
    baseline = load_baseline(baseline_path)
    if baseline is None:
        if not gates_passed:
            return RegressionResult(
                passed=False,
                violations=[],
                decision="baseline_missing",
                stop_retries=False,
                baseline_path=str(baseline_path),
            )
        return maybe_initialize_baseline(
            current_metrics=current_metrics,
            allow_init_flag=(allow_baseline_init and gates_passed),
            baseline_path=baseline_path,
            run_id=run_id,
        )

    baseline_metrics = baseline.get("metrics", {})
    result = compare(
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        tolerances=tolerances,
        protected_metrics=protected_metrics,
        baseline_path=str(baseline_path),
    )
    if result.passed and allow_baseline_update and gates_passed:
        _write_baseline(baseline_path, current_metrics=current_metrics, run_id=run_id)
        return RegressionResult(
            passed=True,
            violations=[],
            decision="baseline_updated",
            stop_retries=False,
            baseline_path=str(baseline_path),
        )
    return result

