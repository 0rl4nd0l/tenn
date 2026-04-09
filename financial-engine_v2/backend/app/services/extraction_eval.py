"""Pure extraction evaluation helpers for synthetic fixture harnesses.

The utilities here are intentionally side-effect free:
- they only transform in-memory payloads,
- they do not call LLMs,
- they do not touch the DB, queue, or vector store.

This keeps the scaffold deterministic and fast for unit-level hardening work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from app.services.multipass_extraction import METRIC_FIELDS


class MetricEvalStatus(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    MISSING = "missing"
    ABSTAIN = "abstain"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class FixtureContext:
    period_end: str | None
    period_type: str | None
    currency: str | None
    scale: str | None


@dataclass(frozen=True)
class ExtractionFixture:
    fixture_id: str
    context: FixtureContext
    metrics: dict[str, float | None]
    expected_nulls: list[str]
    optional_metrics: list[str]
    tolerances: dict[str, float]


@dataclass(frozen=True)
class MetricEvaluation:
    fixture_id: str
    metric: str
    status: MetricEvalStatus
    expected: float | None
    actual: float | None
    tolerance: float
    score: float | None
    reason: str


@dataclass(frozen=True)
class FixtureEvaluation:
    fixture_id: str
    context_ok: bool
    context_mismatches: list[str]
    metrics: list[MetricEvaluation]

    @property
    def overall_score(self) -> float:
        values = [m.score for m in self.metrics if m.score is not None]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def metric_status(self, metric: str) -> MetricEvalStatus:
        for item in self.metrics:
            if item.metric == metric:
                return item.status
        raise KeyError(metric)


def _parse_fixture_path(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"fixture {path} must be a JSON object")
    return data


def load_fixtures(fixtures_dir: str | Path) -> list[ExtractionFixture]:
    """Load synthetic extraction fixtures from a directory of JSON files."""

    fixture_dir = Path(fixtures_dir)
    if not fixture_dir.exists():
        return []

    output: list[ExtractionFixture] = []
    for path in sorted(fixture_dir.glob("*.json")):
        payload = _parse_fixture_path(path)
        fixture_id = str(payload.get("fixture_id") or path.stem)
        metrics = _coerce_metric_map(payload.get("metrics", {}), path)
        optional_metrics = _coerce_metric_list(
            payload.get("optional_metrics", []), path
        )
        expected_nulls = _coerce_metric_list(payload.get("expected_nulls", []), path)
        tolerances = _coerce_tolerances(payload.get("tolerances", {}), path)

        _validate_metric_names(path, [*metrics, *expected_nulls, *optional_metrics])

        context = FixtureContext(
            period_end=str_or_none(payload.get("period_end")),
            period_type=str_or_none(payload.get("period_type")),
            currency=str_or_none(payload.get("currency")),
            scale=str_or_none(payload.get("scale")),
        )
        output.append(
            ExtractionFixture(
                fixture_id=fixture_id,
                context=context,
                metrics=metrics,
                expected_nulls=expected_nulls,
                optional_metrics=optional_metrics,
                tolerances=tolerances,
            )
        )

    return output


def classify_fixtures_against_payloads(
    fixtures: Iterable[ExtractionFixture],
    extracted_payloads: dict[str, dict[str, Any]],
) -> list[FixtureEvaluation]:
    """Evaluate each fixture against a corresponding extracted payload."""

    results = []
    payload_map = dict(extracted_payloads)
    for fixture in fixtures:
        payload = payload_map.get(fixture.fixture_id, {})
        metrics = payload.get("metrics", payload)
        if not isinstance(metrics, dict):
            metrics = {}
        results.append(evaluate_fixture(fixture, metrics, payload))
    return results


def evaluate_fixture(
    fixture: ExtractionFixture,
    extracted_metrics: dict[str, Any],
    extracted_payload: dict[str, Any] | None = None,
) -> FixtureEvaluation:
    """Evaluate one fixture against one extracted metric payload."""

    extracted_payload = extracted_payload or {}
    context_mismatches = _validate_context(fixture.context, extracted_payload)

    # If we cannot trust extracted context, mark every metric as quarantine.
    if context_mismatches:
        quarantine_statuses = [
            MetricEvaluation(
                fixture_id=fixture.fixture_id,
                metric=metric,
                status=MetricEvalStatus.QUARANTINE,
                expected=fixture.metrics.get(metric),
                actual=_safe_float(extracted_metrics.get(metric)),
                tolerance=fixture.tolerances.get(metric, 0.01),
                score=None,
                reason="Context mismatch; fixture marked quarantine",
            )
            for metric in _ordered_metric_keys(fixture)
        ]
        return FixtureEvaluation(
            fixture_id=fixture.fixture_id,
            context_ok=False,
            context_mismatches=context_mismatches,
            metrics=quarantine_statuses,
        )

    evaluated: list[MetricEvaluation] = []
    for metric in _ordered_metric_keys(fixture):
        expected = _fixture_expected_value(fixture, metric)
        actual = _safe_float(extracted_metrics.get(metric))
        tolerance = fixture.tolerances.get(metric, 0.01)

        if (
            metric in fixture.optional_metrics
            and metric not in fixture.metrics
            and metric not in fixture.expected_nulls
        ):
            if actual is None:
                status = MetricEvalStatus.ABSTAIN
                score = _status_score(status)
                reason = "Optional metric missing from extraction"
            else:
                # Optional values are treated as abstain when not explicitly expected.
                status = MetricEvalStatus.ABSTAIN
                score = _status_score(status)
                reason = "Optional metric present but not explicitly expected"
            evaluated.append(
                MetricEvaluation(
                    fixture_id=fixture.fixture_id,
                    metric=metric,
                    status=status,
                    expected=expected,
                    actual=actual,
                    tolerance=tolerance,
                    score=score,
                    reason=reason,
                )
            )
            continue

        if expected is None:
            status = _compare_expected_null(metric, actual)
        elif actual is None:
            status = MetricEvalStatus.MISSING
        else:
            status = _compare_numeric(
                metric,
                expected,
                actual,
                tolerance,
            )

        score = _status_score(status)
        reason = _status_reason(metric, status, expected, actual, tolerance)

        evaluated.append(
            MetricEvaluation(
                fixture_id=fixture.fixture_id,
                metric=metric,
                status=status,
                expected=expected,
                actual=actual,
                tolerance=tolerance,
                score=score,
                reason=reason,
            )
        )

    return FixtureEvaluation(
        fixture_id=fixture.fixture_id,
        context_ok=True,
        context_mismatches=[],
        metrics=evaluated,
    )


def summarize_overall_score(evaluations: Iterable[FixtureEvaluation]) -> dict[str, Any]:
    """Return fixture-level and metric-level aggregate score summaries."""

    fixture_scores: dict[str, float] = {}
    metric_scores: dict[str, list[float]] = {}
    considered = 0
    total_score = 0.0

    for fixture_eval in evaluations:
        fixture_scores[fixture_eval.fixture_id] = fixture_eval.overall_score
        for metric_eval in fixture_eval.metrics:
            if metric_eval.score is None:
                continue
            metric_scores.setdefault(metric_eval.metric, []).append(metric_eval.score)
            total_score += metric_eval.score
            considered += 1

    metric_summary = {
        metric: round(sum(values) / len(values), 4) if values else 0.0
        for metric, values in metric_scores.items()
    }
    overall = round(total_score / considered, 4) if considered else 0.0
    return {
        "overall_score": overall,
        "fixture_scores": fixture_scores,
        "metric_scores": metric_summary,
        "considered_items": considered,
    }


def _status_score(status: MetricEvalStatus) -> float | None:
    if status == MetricEvalStatus.CORRECT:
        return 1.0
    if status == MetricEvalStatus.ABSTAIN:
        return 0.5
    if status in (MetricEvalStatus.WRONG, MetricEvalStatus.MISSING):
        return 0.0
    return None


def _compare_expected_null(metric: str, actual: float | None) -> MetricEvalStatus:
    if actual is None:
        return MetricEvalStatus.CORRECT
    return MetricEvalStatus.WRONG


def _compare_numeric(
    metric: str,
    expected: float,
    actual: float,
    tolerance: float,
) -> MetricEvalStatus:
    if expected == 0:
        return (
            MetricEvalStatus.CORRECT
            if abs(actual) <= max(1.0, abs(expected) * tolerance)
            else MetricEvalStatus.WRONG
        )
    if abs((actual - expected) / expected) <= tolerance:
        return MetricEvalStatus.CORRECT
    return MetricEvalStatus.WRONG


def _status_reason(
    metric: str,
    status: MetricEvalStatus,
    expected: float | None,
    actual: float | None,
    tolerance: float,
) -> str:
    if status == MetricEvalStatus.CORRECT:
        return "Within tolerance"
    if status == MetricEvalStatus.ABSTAIN:
        return "Optional metric not required for this fixture"
    if status == MetricEvalStatus.MISSING:
        return "Expected metric was absent"
    if status == MetricEvalStatus.WRONG:
        if expected is None:
            return "Expected null was not null"
        return f"Value outside tolerance={tolerance}"
    return "Context mismatch"


def _validate_context(context: FixtureContext, payload: dict[str, Any]) -> list[str]:
    checks = {
        "period_end": (context.period_end, str_or_none(payload.get("period_end"))),
        "currency": (context.currency, str_or_none(payload.get("currency"))),
        "scale": (context.scale, str_or_none(payload.get("scale"))),
    }

    mismatches = []
    for key, (expected_val, extracted_val) in checks.items():
        if expected_val is None:
            continue
        if extracted_val is None:
            mismatches.append(key)
            continue
        if expected_val.lower() != extracted_val.lower():
            mismatches.append(key)
    return mismatches


def _ordered_metric_keys(fixture: ExtractionFixture) -> list[str]:
    ordered = list(fixture.metrics.keys())
    for metric in fixture.expected_nulls:
        if metric not in ordered:
            ordered.append(metric)
    for metric in fixture.optional_metrics:
        if metric not in ordered:
            ordered.append(metric)
    return ordered


def _fixture_expected_value(fixture: ExtractionFixture, metric: str) -> float | None:
    if metric in fixture.metrics:
        return fixture.metrics[metric]
    if metric in fixture.expected_nulls:
        return None
    return None


def _coerce_metric_map(raw: Any, path: Path) -> dict[str, float | None]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"metrics for {path} must be an object")

    parsed: dict[str, float | None] = {}
    for metric, value in raw.items():
        parsed[metric] = _coerce_metric_value(metric, value, path)
    return parsed


def _coerce_metric_list(raw: Any, path: Path) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"expected list in fixture {path}")

    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"non-string metric name in {path}: {item!r}")
        values.append(item)
    return values


def _coerce_tolerances(raw: Any, path: Path) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"tolerances for {path} must be an object")

    parsed: dict[str, float] = {}
    for metric, value in raw.items():
        if not isinstance(value, int | float):
            raise ValueError(f"tolerance for {path}:{metric} must be numeric")
        parsed[metric] = float(value)
    return parsed


def _coerce_metric_value(metric: str, raw: Any, path: Path) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or isinstance(raw, (int, float)):
        return float(raw)
    raise ValueError(f"metric {metric} in {path} must be numeric or null")


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _validate_metric_names(path: Path, values: Iterable[str]) -> None:
    known = set(METRIC_FIELDS)
    for metric in values:
        if metric not in known:
            raise ValueError(f"unknown metric '{metric}' in {path}")


def str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value).strip() or None
