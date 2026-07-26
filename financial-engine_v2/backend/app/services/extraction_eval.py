"""Pure extraction evaluation helpers for synthetic fixture harnesses.

The utilities here are intentionally side-effect free:
- they only transform in-memory payloads,
- they do not call LLMs,
- they do not touch the DB, queue, or vector store.

This keeps the scaffold deterministic and fast for unit-level hardening work.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from numbers import Real
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.services.financial_metric_contract import (
    METRIC_CONTRACT_BY_CANONICAL_FIELD,
    MetricContractStatus,
    ProvenanceRequirement,
)
from app.services.multipass_extraction import METRIC_FIELDS, SCALE_MULTIPLIERS
from app.services.provenance import (
    from_extraction_payload,
    validate_provenance_collection,
)


_CELL_NUMERIC_RE = re.compile(
    r"^(?:(?:[A-Za-z]{1,3})?\$|[£€])?\s*"
    r"(?P<number>[+-]?(?:\d+(?:,\d{3})*|\d+)(?:\.\d+)?)"
    r"\s*(?P<suffix>k|thousand|thousands|m|mn|million|millions|"
    r"b|bn|billion|billions|t|tn|trillion|trillions)?$",
    re.IGNORECASE,
)
_CELL_SUFFIX_MULTIPLIERS = {
    "k": Decimal(1_000),
    "thousand": Decimal(1_000),
    "thousands": Decimal(1_000),
    "m": Decimal(1_000_000),
    "mn": Decimal(1_000_000),
    "million": Decimal(1_000_000),
    "millions": Decimal(1_000_000),
    "b": Decimal(1_000_000_000),
    "bn": Decimal(1_000_000_000),
    "billion": Decimal(1_000_000_000),
    "billions": Decimal(1_000_000_000),
    "t": Decimal(1_000_000_000_000),
    "tn": Decimal(1_000_000_000_000),
    "trillion": Decimal(1_000_000_000_000),
    "trillions": Decimal(1_000_000_000_000),
}


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
    accounting_basis: str | None = None


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
            accounting_basis=str_or_none(payload.get("accounting_basis")),
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
    *,
    expected_source_document_id: str | None = None,
    require_structured_provenance: bool = False,
) -> FixtureEvaluation:
    """Evaluate one fixture against one extracted metric payload."""

    extracted_payload = extracted_payload or {}
    _validate_fixture_numeric_values(fixture)
    _validate_extracted_metric_values(extracted_metrics)
    provenance_summary = _build_provenance_summary(
        extracted_payload,
        expected_context=fixture.context,
        expected_source_document_id=expected_source_document_id,
        require_structured=require_structured_provenance,
    )
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


def summarize_numeric_quality(
    evaluations: Iterable[FixtureEvaluation],
) -> dict[str, dict[str, int | float | None]]:
    """Report present-value precision separately from supported-metric recall.

    Precision considers supported numeric outputs that were eligible for value
    comparison. Recall considers every supported non-null metric expectation,
    including missing and context-quarantined expectations.
    """

    accepted_count = 0
    accepted_correct_count = 0
    supported_expected_count = 0
    supported_correct_count = 0

    for evaluation in evaluations:
        for metric in evaluation.metrics:
            contract = METRIC_CONTRACT_BY_CANONICAL_FIELD.get(metric.metric)
            if (
                contract is None
                or contract.declared_status != MetricContractStatus.SUPPORTED
            ):
                continue

            if metric.expected is not None:
                supported_expected_count += 1
                if metric.status == MetricEvalStatus.CORRECT:
                    supported_correct_count += 1

            if metric.actual is not None and metric.status in {
                MetricEvalStatus.CORRECT,
                MetricEvalStatus.WRONG,
            }:
                accepted_count += 1
                if metric.status == MetricEvalStatus.CORRECT:
                    accepted_correct_count += 1

    return {
        "accepted_numeric_precision": {
            "correct_count": accepted_correct_count,
            "accepted_count": accepted_count,
            "value": _safe_ratio(accepted_correct_count, accepted_count),
        },
        "supported_metric_recall": {
            "correct_count": supported_correct_count,
            "expected_count": supported_expected_count,
            "value": _safe_ratio(supported_correct_count, supported_expected_count),
        },
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
    numeric_quality = summarize_numeric_quality(evaluations)
    accounting_basis_summary = _build_context_summary(
        fixtures, fixture_payloads, "accounting_basis"
    )

    return {
        "evaluation_lane": "synthetic",
        "total_fixture_count": len(fixtures),
        "total_metric_expectations": total_metric_expectations,
        "correct_count": status_counts["correct"],
        "wrong_count": status_counts["wrong"],
        "missing_count": status_counts["missing"],
        "abstained_count": status_counts["abstain"],
        "quarantined_count": status_counts["quarantine"],
        "period_correctness_summary": period_summary,
        "period_end_correctness_summary": period_summary,
        "period_type_correctness_summary": period_type_summary,
        "period_basis_correctness_summary": period_type_summary,
        "currency_correctness_summary": currency_summary,
        "scale_correctness_summary": scale_summary,
        "accounting_basis_correctness_summary": accounting_basis_summary,
        **numeric_quality,
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
    canonical_required_record_count = 0
    canonical_valid_record_count = 0
    canonical_invalid_record_count = 0

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
        canonical_required_record_count += int(
            summary.get("canonical_required_record_count", 0)
        )
        canonical_valid_record_count += int(
            summary.get("canonical_valid_record_count", 0)
        )
        canonical_invalid_record_count += int(
            summary.get("canonical_invalid_record_count", 0)
        )

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
        "canonical_required_record_count": canonical_required_record_count,
        "canonical_valid_record_count": canonical_valid_record_count,
        "canonical_invalid_record_count": canonical_invalid_record_count,
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
        "provenance_canonical_required_record_count": provenance[
            "canonical_required_record_count"
        ],
        "provenance_canonical_valid_record_count": provenance[
            "canonical_valid_record_count"
        ],
        "provenance_canonical_invalid_record_count": provenance[
            "canonical_invalid_record_count"
        ],
        "provenance_status_counts": provenance["status_counts"],
        "provenance_issues": provenance["issues"],
    }


def _build_provenance_summary(
    payload: Mapping[str, Any],
    *,
    expected_context: FixtureContext | None = None,
    expected_source_document_id: str | None = None,
    require_structured: bool = False,
) -> dict[str, Any]:
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
            "canonical_required_record_count": 0,
            "canonical_valid_record_count": 0,
            "canonical_invalid_record_count": 0,
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
    canonical_required_record_count = 0
    canonical_valid_record_count = 0
    for metric_name, record, result in zip(
        metric_names,
        records,
        validation["record_results"],
        strict=False,
    ):
        canonical_provenance = _evaluate_canonical_provenance(
            metric_name,
            record,
            result,
            payload=payload,
            actual_value=_payload_metric_value(payload, metric_name),
            expected_context=expected_context,
            expected_source_document_id=expected_source_document_id,
            require_structured=require_structured,
        )
        if canonical_provenance["required"]:
            canonical_required_record_count += 1
            if canonical_provenance["valid"]:
                canonical_valid_record_count += 1
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
                "canonical_provenance_required": canonical_provenance["required"],
                "canonical_provenance_valid": canonical_provenance["valid"],
                "canonical_provenance_reason": canonical_provenance["reason"],
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
        "canonical_required_record_count": canonical_required_record_count,
        "canonical_valid_record_count": canonical_valid_record_count,
        "canonical_invalid_record_count": (
            canonical_required_record_count - canonical_valid_record_count
        ),
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
        "accounting_basis": (
            context.accounting_basis,
            str_or_none(payload.get("accounting_basis")),
        ),
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
        if not _is_real_number(value):
            raise ValueError(f"tolerance for {path}:{metric} must be numeric")
        parsed[metric] = float(value)
    return parsed


def _coerce_metric_value(metric: str, raw: Any, path: Path) -> float | None:
    if raw is None:
        return None
    if _is_real_number(raw):
        return float(raw)
    raise ValueError(f"metric {metric} in {path} must be numeric or null")


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if _is_real_number(value):
        return float(value)
    return None


def _is_real_number(value: Any) -> bool:
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _validate_fixture_numeric_values(fixture: ExtractionFixture) -> None:
    for metric, value in fixture.metrics.items():
        if value is not None and not _is_real_number(value):
            raise ValueError(f"metric {metric} fixture value must be numeric or null")
    for metric, tolerance in fixture.tolerances.items():
        if not _is_real_number(tolerance):
            raise ValueError(f"tolerance for {metric} must be numeric")


def _validate_extracted_metric_values(extracted_metrics: Mapping[str, Any]) -> None:
    for metric, value in extracted_metrics.items():
        if metric not in METRIC_FIELDS or value is None:
            continue
        if not _is_real_number(value):
            raise ValueError(f"metric {metric} actual value must be numeric or null")


def _payload_metric_value(payload: Mapping[str, Any], metric_name: str) -> Any:
    metrics = payload.get("metrics")
    if isinstance(metrics, Mapping):
        return metrics.get(metric_name)
    return payload.get(metric_name)


def _validate_metric_names(path: Path, values: Iterable[str]) -> None:
    known = set(METRIC_FIELDS)
    for metric in values:
        if metric not in known:
            raise ValueError(f"unknown metric '{metric}' in {path}")


def _evaluate_canonical_provenance(
    metric_name: str,
    record: Any,
    validation: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    actual_value: Any,
    expected_context: FixtureContext | None,
    expected_source_document_id: str | None,
    require_structured: bool,
) -> dict[str, bool | str]:
    contract = METRIC_CONTRACT_BY_CANONICAL_FIELD.get(metric_name)
    required = bool(
        contract is not None
        and contract.declared_status == MetricContractStatus.SUPPORTED
        and contract.provenance_requirement != ProvenanceRequirement.NOT_CANONICAL
    )
    if not required:
        return {"required": False, "valid": True, "reason": "not_required"}

    if require_structured:
        strict_reason = _strict_provenance_failure_reason(
            contract=contract,
            record=record,
            payload=payload,
            actual_value=actual_value,
            expected_context=expected_context,
            expected_source_document_id=expected_source_document_id,
        )
        if strict_reason is not None:
            return {
                "required": True,
                "valid": False,
                "reason": strict_reason,
            }

    if not record.source_document_id:
        return {
            "required": True,
            "valid": False,
            "reason": "source_document_id_missing",
        }
    if not validation.get("ok"):
        return {
            "required": True,
            "valid": False,
            "reason": "provenance_validation_error",
        }
    if record.provenance_status == "precise":
        return {"required": True, "valid": True, "reason": "direct_source"}

    if record.provenance_status == "derived" and contract is not None:
        derivation_identity = _explicit_derivation_identity(record.raw_reference)
        if any(
            derivation.value == derivation_identity
            for derivation in contract.authorized_derivations
        ):
            return {
                "required": True,
                "valid": True,
                "reason": "authorized_derivation",
            }

    return {
        "required": True,
        "valid": False,
        "reason": f"invalid_status:{record.provenance_status}",
    }


def _explicit_derivation_identity(raw_reference: Any) -> str | None:
    if isinstance(raw_reference, Mapping):
        return str_or_none(
            raw_reference.get("derivation_identity")
            or raw_reference.get("authorized_derivation")
        )
    if not isinstance(raw_reference, str):
        return None
    parts = raw_reference.strip().lower().split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "derived" or not parts[1]:
        return None
    return parts[2]


def _strict_provenance_failure_reason(
    *,
    contract: Any,
    record: Any,
    payload: Mapping[str, Any],
    actual_value: Any,
    expected_context: FixtureContext | None,
    expected_source_document_id: str | None,
) -> str | None:
    expected_source = str_or_none(expected_source_document_id)
    if expected_source is None:
        return "fixture_source_document_id_missing"

    payload_source = str_or_none(payload.get("source_document_id"))
    if payload_source is None:
        return "source_document_id_missing"
    if payload_source != expected_source:
        return "source_document_id_mismatch"

    raw = record.raw_reference
    if not isinstance(raw, Mapping):
        return "structured_provenance_missing"
    raw_source_document_id = str_or_none(raw.get("source_document_id"))
    if raw_source_document_id is None:
        return "source_document_id_missing"
    if raw_source_document_id != expected_source:
        return "source_document_id_mismatch"

    expected_fields = {
        "period_end": (
            str_or_none(expected_context.period_end) if expected_context else None
        ),
        "period_type": (
            str_or_none(expected_context.period_type) if expected_context else None
        ),
        "currency": (
            str_or_none(expected_context.currency) if expected_context else None
        ),
        "scale": str_or_none(expected_context.scale) if expected_context else None,
    }
    for field_name, expected_value in expected_fields.items():
        if expected_value is None:
            return f"fixture_{field_name}_missing"

    source = str_or_none(raw.get("source"))
    derived_source = source.removeprefix("derived:") if source else None
    allowed_sources = {
        statement_context.value for statement_context in contract.statement_contexts
    }
    if derived_source not in allowed_sources:
        return "statement_context_not_allowed"

    page = str_or_none(raw.get("page_tag") or raw.get("page_number"))
    if page is None or page.lower() == "unknown":
        return "page_binding_missing"
    if not _has_table_or_region_binding(raw):
        return "table_or_region_binding_missing"

    for field_name, expected_value in expected_fields.items():
        actual_context_value = str_or_none(raw.get(field_name))
        if actual_context_value is None:
            return f"{field_name}_missing"
        if actual_context_value.lower() != expected_value.lower():
            return f"{field_name}_mismatch"

    if record.provenance_status == "derived":
        if contract.direct_source_required and not contract.authorized_derivations:
            return "unauthorized_derivation"
        derivation_identity = _explicit_derivation_identity(raw)
        if not any(
            derivation.value == derivation_identity
            for derivation in contract.authorized_derivations
        ):
            return "unauthorized_derivation"
        if derived_source != "cashflow_statement":
            return "statement_context_not_allowed"
        if not _has_explicit_source_row_refs(raw):
            return "source_row_refs_missing"
        cell_failure = _structured_source_cells_failure_reason(
            raw,
            plural=True,
            expected_period_end=expected_fields["period_end"],
            expected_value=actual_value,
            expected_scale=expected_fields["scale"],
        )
        if cell_failure is not None:
            return cell_failure
        return None

    row_ref = str_or_none(raw.get("row_ref"))
    if row_ref is None or row_ref.lower() == "unknown":
        return "row_binding_missing"
    cell_failure = _structured_source_cells_failure_reason(
        raw,
        plural=False,
        expected_period_end=expected_fields["period_end"],
        expected_value=actual_value,
        expected_scale=expected_fields["scale"],
    )
    if cell_failure is not None:
        return cell_failure
    return None


def _has_table_or_region_binding(raw: Mapping[str, Any]) -> bool:
    return any(
        str_or_none(raw.get(field_name)) is not None
        for field_name in ("table_label", "table_ref", "region_ref", "region")
    )


def _has_explicit_source_row_refs(raw: Mapping[str, Any]) -> bool:
    row_refs = raw.get("source_row_refs")
    return bool(
        isinstance(row_refs, list)
        and len(row_refs) >= 2
        and all(
            (value := str_or_none(row_ref)) is not None and value.lower() != "unknown"
            for row_ref in row_refs
        )
    )


def _structured_source_cells_failure_reason(
    raw: Mapping[str, Any],
    *,
    plural: bool,
    expected_period_end: str,
    expected_value: Any,
    expected_scale: str,
) -> str | None:
    if plural:
        source_cells = raw.get("source_cells")
        if not isinstance(source_cells, list):
            return "cell_binding_missing"
        cells = source_cells
        source_row_refs = _explicit_source_row_refs(raw)
        if len(cells) != len(source_row_refs):
            return "source_row_cell_count_mismatch"
        if len(cells) < 2:
            return "cell_binding_missing"
    else:
        cells = [raw.get("source_cell")]
        source_row_refs = [str_or_none(raw.get("row_ref"))]

    parent_source_document_id = str_or_none(raw.get("source_document_id"))
    parent_page = _normalized_page_reference(
        raw.get("page_number") or raw.get("page_tag")
    )
    parent_bindings = _normalized_table_or_region_bindings(raw)
    normalized_values: list[Decimal] = []

    for index, cell in enumerate(cells):
        if not isinstance(cell, Mapping):
            return "cell_binding_missing"
        if not all(
            str_or_none(cell.get(field_name)) is not None
            for field_name in (
                "page_number",
                "row_index",
                "column_index",
                "raw_value",
                "header_cell",
            )
        ):
            return "cell_binding_missing"

        cell_period_end = str_or_none(cell.get("requested_period_end"))
        if cell_period_end is None:
            return "cell_period_missing"
        if cell_period_end.lower() != expected_period_end.lower():
            return "cell_period_mismatch"

        cell_source_document_id = str_or_none(cell.get("source_document_id"))
        if cell_source_document_id is None:
            return "cell_source_document_id_missing"
        if cell_source_document_id != parent_source_document_id:
            return "cell_source_document_id_mismatch"

        cell_page = _normalized_page_reference(cell.get("page_number"))
        if parent_page is None or cell_page != parent_page:
            return "cell_page_mismatch"

        cell_bindings = _normalized_table_or_region_bindings(cell)
        if not cell_bindings:
            return "cell_table_or_region_missing"
        if parent_bindings.isdisjoint(cell_bindings):
            return "cell_table_or_region_mismatch"

        expected_row = source_row_refs[index]
        cell_row = str_or_none(cell.get("row_label") or cell.get("row_ref"))
        if expected_row is None or cell_row is None:
            return "cell_binding_missing"
        if _normalized_evidence_text(cell_row) != _normalized_evidence_text(
            expected_row
        ):
            return "source_row_cell_mismatch" if plural else "cell_row_mismatch"

        header_cell = str_or_none(cell.get("header_cell"))
        if header_cell is None or not _header_matches_period(
            header_cell,
            expected_period_end,
        ):
            return "cell_header_period_mismatch"

        normalized_value = _normalized_source_cell_value(cell, expected_scale)
        if normalized_value is None:
            return "cell_value_invalid"
        normalized_values.append(normalized_value)

    expected_numeric = _decimal_from_real(expected_value)
    if expected_numeric is None:
        return "metric_value_missing_or_invalid"
    reproduced_value = (
        sum(normalized_values, start=Decimal(0)) if plural else normalized_values[0]
    )
    if reproduced_value != expected_numeric:
        return "derived_value_mismatch" if plural else "cell_value_mismatch"
    return None


def _explicit_source_row_refs(raw: Mapping[str, Any]) -> list[str]:
    row_refs = raw.get("source_row_refs")
    if not isinstance(row_refs, list):
        return []
    return [
        value for row_ref in row_refs if (value := str_or_none(row_ref)) is not None
    ]


def _normalized_page_reference(value: Any) -> int | None:
    text = str_or_none(value)
    if text is None:
        return None
    matches = re.findall(r"\d+", text)
    if len(matches) != 1:
        return None
    return int(matches[0])


def _normalized_table_or_region_bindings(raw: Mapping[str, Any]) -> set[str]:
    return {
        normalized
        for field_name in ("table_label", "table_ref", "region_ref", "region")
        if (value := str_or_none(raw.get(field_name))) is not None
        and (normalized := _normalized_evidence_text(value))
    }


def _normalized_evidence_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _header_matches_period(header: str, expected_period_end: str) -> bool:
    try:
        period = date.fromisoformat(expected_period_end)
    except ValueError:
        return False
    day = period.strftime("%d")
    month = period.strftime("%m")
    year = period.strftime("%Y")
    month_names = "|".join(
        re.escape(value) for value in (period.strftime("%B"), period.strftime("%b"))
    )
    patterns = (
        rf"(?<!\d){year}[-/]{month}[-/]{day}(?!\d)",
        rf"(?<!\d){day}[-/]{month}[-/]{year}(?!\d)",
        rf"(?<!\d){day}\s+(?:{month_names})\s+{year}(?!\d)",
    )
    return any(re.search(pattern, header, re.IGNORECASE) for pattern in patterns)


def _normalized_source_cell_value(
    cell: Mapping[str, Any],
    expected_scale: str,
) -> Decimal | None:
    parsed = _parse_source_cell_number(cell.get("raw_value"))
    if parsed is None:
        return None
    value, explicit_units = parsed
    if explicit_units:
        return value
    multiplier = SCALE_MULTIPLIERS.get(expected_scale.lower())
    if multiplier is None:
        return None
    return value * Decimal(multiplier)


def _parse_source_cell_number(value: Any) -> tuple[Decimal, bool] | None:
    if not _is_real_number(value) and not isinstance(value, str):
        return None
    text = str(value).strip()
    negative_parentheses = text.startswith("(") and text.endswith(")")
    if negative_parentheses:
        text = text[1:-1].strip()
    match = _CELL_NUMERIC_RE.fullmatch(text)
    if match is None:
        return None
    try:
        parsed = Decimal(match.group("number").replace(",", ""))
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    if negative_parentheses:
        parsed = -abs(parsed)
    suffix = str(match.group("suffix") or "").lower()
    if suffix:
        return parsed * _CELL_SUFFIX_MULTIPLIERS[suffix], True
    return parsed, False


def _decimal_from_real(value: Any) -> Decimal | None:
    if not _is_real_number(value):
        return None
    parsed = Decimal(str(value))
    return parsed if parsed.is_finite() else None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value).strip() or None
