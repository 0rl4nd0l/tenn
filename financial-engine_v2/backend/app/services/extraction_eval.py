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
from typing import Any, Iterable, Mapping

from app.services.multipass_extraction import METRIC_FIELDS
from app.services.provenance import (
    from_extraction_payload,
    validate_provenance_collection,
)


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
    provenance_summary: dict[str, Any]

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
    provenance_summary = _build_provenance_summary(extracted_payload)
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
            provenance_summary=provenance_summary,
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
        provenance_summary=provenance_summary,
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


def build_fixture_scorecard(
    fixtures_dir: str | Path,
    extracted_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a stable JSON-serializable scorecard for all fixtures.

    The scorecard is deterministic: fixtures are processed and serialized in
    sorted order, and every field is present even when empty.
    """

    fixtures = load_fixtures(fixtures_dir)
    fixture_payloads: dict[str, dict[str, Any]] = extracted_payloads or {}
    evaluations = classify_fixtures_against_payloads(fixtures, fixture_payloads)

    status_counts = {
        "correct": 0,
        "wrong": 0,
        "missing": 0,
        "abstain": 0,
        "quarantine": 0,
    }
    fixture_summaries: list[dict[str, Any]] = []

    for eval_result in evaluations:
        summary = _summarize_fixture_eval(eval_result)
        fixture_summaries.append(summary)
        for status in status_counts:
            status_counts[status] += summary[status + "_count"]

    total_metric_expectations = sum(v["metric_count"] for v in fixture_summaries)
    period_summary = _build_context_summary(fixtures, fixture_payloads, "period_end")
    period_type_summary = _build_context_summary(
        fixtures, fixture_payloads, "period_type"
    )
    currency_summary = _build_context_summary(fixtures, fixture_payloads, "currency")
    scale_summary = _build_context_summary(fixtures, fixture_payloads, "scale")
    provenance_summary = summarize_provenance_summaries(
        evaluation.provenance_summary for evaluation in evaluations
    )

    return {
        "total_fixture_count": len(fixtures),
        "total_metric_expectations": total_metric_expectations,
        "correct_count": status_counts["correct"],
        "wrong_count": status_counts["wrong"],
        "missing_count": status_counts["missing"],
        "abstained_count": status_counts["abstain"],
        "quarantined_count": status_counts["quarantine"],
        "period_correctness_summary": period_summary,
        "period_type_correctness_summary": period_type_summary,
        "currency_correctness_summary": currency_summary,
        "scale_correctness_summary": scale_summary,
        "provenance_summary": provenance_summary,
        "fixture_summaries": fixture_summaries,
        "status_summary": {
            "correct": status_counts["correct"],
            "wrong": status_counts["wrong"],
            "missing": status_counts["missing"],
            "abstain": status_counts["abstain"],
            "quarantine": status_counts["quarantine"],
        },
    }


def summarize_provenance_summaries(
    summaries: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    aggregated_status_counts: dict[str, int] = {}
    available_fixture_count = 0
    clean_fixture_count = 0
    fixture_with_issues_count = 0
    unavailable_fixture_count = 0
    record_count = 0
    issue_count = 0
    error_count = 0
    warning_count = 0

    for summary in summaries:
        if summary.get("available"):
            available_fixture_count += 1
            if summary.get("issue_count", 0):
                fixture_with_issues_count += 1
            else:
                clean_fixture_count += 1
        else:
            unavailable_fixture_count += 1

        record_count += int(summary.get("record_count", 0))
        issue_count += int(summary.get("issue_count", 0))
        error_count += int(summary.get("error_count", 0))
        warning_count += int(summary.get("warning_count", 0))

        status_counts = summary.get("status_counts", {})
        if isinstance(status_counts, dict):
            for status, count in status_counts.items():
                aggregated_status_counts[str(status)] = aggregated_status_counts.get(
                    str(status), 0
                ) + int(count)

    aggregate_status = "unavailable"
    if available_fixture_count:
        aggregate_status = "issues_detected" if issue_count else "clean"

    return {
        "status": aggregate_status,
        "available_fixture_count": available_fixture_count,
        "clean_fixture_count": clean_fixture_count,
        "fixture_with_issues_count": fixture_with_issues_count,
        "unavailable_fixture_count": unavailable_fixture_count,
        "record_count": record_count,
        "issue_count": issue_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "status_counts": dict(sorted(aggregated_status_counts.items())),
    }


def _status_score(status: MetricEvalStatus) -> float | None:
    if status == MetricEvalStatus.CORRECT:
        return 1.0
    if status == MetricEvalStatus.ABSTAIN:
        return 0.5
    if status in (MetricEvalStatus.WRONG, MetricEvalStatus.MISSING):
        return 0.0
    return None


def _summarize_fixture_eval(evaluation: FixtureEvaluation) -> dict[str, Any]:
    """Return a compact per-fixture status summary."""

    metric_count = len(evaluation.metrics)
    status_counts = {
        "correct_count": 0,
        "wrong_count": 0,
        "missing_count": 0,
        "abstain_count": 0,
        "quarantine_count": 0,
    }

    for metric_eval in evaluation.metrics:
        if metric_eval.status == MetricEvalStatus.CORRECT:
            status_counts["correct_count"] += 1
        elif metric_eval.status == MetricEvalStatus.WRONG:
            status_counts["wrong_count"] += 1
        elif metric_eval.status == MetricEvalStatus.MISSING:
            status_counts["missing_count"] += 1
        elif metric_eval.status == MetricEvalStatus.ABSTAIN:
            status_counts["abstain_count"] += 1
        elif metric_eval.status == MetricEvalStatus.QUARANTINE:
            status_counts["quarantine_count"] += 1

    provenance = evaluation.provenance_summary
    return {
        "fixture_id": evaluation.fixture_id,
        "context_ok": evaluation.context_ok,
        "context_mismatches": evaluation.context_mismatches,
        "metric_count": metric_count,
        **status_counts,
        "overall_score": evaluation.overall_score,
        "provenance_available": provenance["available"],
        "provenance_status": provenance["status"],
        "provenance_record_count": provenance["record_count"],
        "provenance_issue_count": provenance["issue_count"],
        "provenance_error_count": provenance["error_count"],
        "provenance_warning_count": provenance["warning_count"],
        "provenance_status_counts": provenance["status_counts"],
        "provenance_issues": provenance["issues"],
    }


def _build_provenance_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    field_provenance = payload.get("field_provenance")
    provenance = payload.get("provenance")
    if not isinstance(field_provenance, Mapping) and not isinstance(
        provenance, Mapping
    ):
        return {
            "available": False,
            "status": "unavailable",
            "ok": True,
            "record_count": 0,
            "issue_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "status_counts": {},
            "issues": [],
            "metric_summaries": [],
        }

    metric_names: list[str] = []
    for source_map in (field_provenance, provenance):
        if not isinstance(source_map, Mapping):
            continue
        for metric_name in source_map:
            metric_names.append(str(metric_name))
    metric_names = list(dict.fromkeys(metric_names))
    records = from_extraction_payload(
        payload,
        source_document_id=str_or_none(payload.get("source_document_id")),
    )
    validation = validate_provenance_collection(records)

    status_counts: dict[str, int] = {}
    metric_summaries: list[dict[str, Any]] = []
    for metric_name, record, result in zip(
        metric_names,
        records,
        validation["record_results"],
        strict=False,
    ):
        status_counts[record.provenance_status] = (
            status_counts.get(record.provenance_status, 0) + 1
        )
        metric_summaries.append(
            {
                "metric": metric_name,
                "provenance_status": record.provenance_status,
                "ok": result["ok"],
                "issue_codes": [issue["code"] for issue in result["issues"]],
                "error_count": result["error_count"],
                "warning_count": result["warning_count"],
            }
        )

    issues: list[dict[str, Any]] = []
    for issue in validation["issues"]:
        indexed_issue = dict(issue)
        index = issue.get("record_index")
        if isinstance(index, int) and 0 <= index < len(metric_names):
            indexed_issue["metric"] = metric_names[index]
        issues.append(indexed_issue)

    return {
        "available": True,
        "status": "issues_detected" if issues else "clean",
        "ok": validation["ok"],
        "record_count": validation["record_count"],
        "issue_count": len(issues),
        "error_count": validation["error_count"],
        "warning_count": validation["warning_count"],
        "status_counts": dict(sorted(status_counts.items())),
        "issues": issues,
        "metric_summaries": metric_summaries,
    }


def _build_context_summary(
    fixtures: Iterable[ExtractionFixture],
    extracted_payloads: dict[str, dict[str, Any]],
    field_name: str,
) -> dict[str, int]:
    """Return stable match/mismatch counts for one fixture context field."""

    expected_total = 0
    matched = 0
    mismatched = 0
    missing = 0

    for fixture in fixtures:
        expected_raw = str_or_none(
            getattr(fixture.context, field_name, None),
        )
        if expected_raw is None:
            continue

        expected_total += 1
        actual_payload = extracted_payloads.get(fixture.fixture_id, {})
        actual_raw = str_or_none(actual_payload.get(field_name))

        if actual_raw is None:
            missing += 1
            mismatched += 1
            continue

        if actual_raw.lower() == expected_raw.lower():
            matched += 1
        else:
            mismatched += 1

    return {
        "expected_count": expected_total,
        "matched_count": matched,
        "mismatched_count": mismatched,
        "missing_count": missing,
    }


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
        "period_type": (context.period_type, str_or_none(payload.get("period_type"))),
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
