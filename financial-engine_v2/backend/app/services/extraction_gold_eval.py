"""Helpers for a real-document gold-eval pilot.

This module intentionally remains separate from the synthetic fixture harness.
It evaluates pre-produced extraction JSON payloads against hand-labelled real fixtures
using the same metric comparison logic as the synthetic scaffold, then derives a
small trust outcome for each fixture.

Trust semantics are deterministic and intentionally transparent:

- `trusted`: context matches, every required metric is `correct`, and every
  present supported metric has complete fixture-bound provenance.
- `abstain`: context matches but at least one required metric is
  `wrong`, `missing`, or `abstain`.
- `quarantine`: any context field mismatch (`period_end`, `period_type`,
  `currency`, `scale`, or `accounting_basis`). All metrics for that fixture are
  marked `quarantine`, while provenance failures remain independently reported.

For this pilot, real fixtures use required metrics only (no optional list), so a
required metric that is absent from extracted output is scored as `missing` (not
`abstain`).

The trusted/abstain/quarantine outcome is explicitly represented in fixture labels
when available but does not alter fixture discovery or synthetic evaluation.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.services.extraction_eval import (
    ExtractionFixture,
    FixtureContext,
    MetricEvalStatus,
    FixtureEvaluation,
    MetricEvaluation,
    evaluate_fixture,
    summarize_numeric_quality,
    summarize_provenance_summaries,
    str_or_none,
)
from app.services.financial_metric_contract import (
    METRIC_CONTRACT_BY_CANONICAL_FIELD,
    REAL_GOLD_METRIC_ALIASES,
    MetricContractStatus,
    ProvenanceRequirement,
)
from app.services.multipass_extraction import METRIC_FIELDS


class RealTrustOutcome(str, Enum):
    TRUSTED = "trusted"
    ABSTAIN = "abstain"
    QUARANTINE = "quarantine"


class ASXDocumentClass(str, Enum):
    ANNUAL = "annual"
    HALF_YEAR = "half_year"
    QUARTERLY = "quarterly"


SUPPORTED_ASX_DOCUMENT_CLASSES = tuple(item.value for item in ASXDocumentClass)


@dataclass(frozen=True)
class RealGoldFixture:
    document_id: str
    context: FixtureContext
    metrics: dict[str, float | None]
    tolerances: dict[str, float]
    expected_trust: RealTrustOutcome | None
    document_class: ASXDocumentClass | None = None
    source_document_id: str | None = None


@dataclass(frozen=True)
class RealGoldFixtureEvaluation:
    document_id: str
    context_ok: bool
    context_mismatches: list[str]
    metrics: list[MetricEvaluation]
    provenance_summary: dict[str, Any]
    trust: RealTrustOutcome
    trust_triggers: list[str]
    expected_trust: RealTrustOutcome | None
    trust_matches_expected: bool | None
    provenance_trust_failures: list[str] = field(default_factory=list)


def _parse_fixture_path(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    return _safe_load_fixture_json(path, raw)


def load_real_gold_fixtures(fixtures_dir: str | Path) -> list[RealGoldFixture]:
    fixture_dir = Path(fixtures_dir)
    if not fixture_dir.exists():
        return []

    output: list[RealGoldFixture] = []
    for path in sorted(fixture_dir.glob("*.json")):
        payload = _parse_fixture_path(path)
        document_id = str(payload.get("document_id") or path.stem)

        metrics = _coerce_metric_map(payload.get("metrics", {}), path)
        tolerances = _coerce_tolerances(payload.get("tolerances", {}), path)
        _validate_metric_names(path, metrics)

        raw_expected_trust = payload.get("expected_trust")
        expected_trust = None
        if raw_expected_trust is not None:
            if isinstance(raw_expected_trust, str):
                try:
                    expected_trust = RealTrustOutcome(raw_expected_trust.lower())
                except ValueError as exc:
                    raise ValueError(
                        f"invalid expected_trust in {path}: {raw_expected_trust!r}"
                    ) from exc
            else:
                raise ValueError(f"expected_trust in {path} must be a string")

        context = FixtureContext(
            period_end=str_or_none(payload.get("period_end")),
            period_type=str_or_none(payload.get("period_type")),
            currency=str_or_none(payload.get("currency")),
            scale=str_or_none(payload.get("scale")),
            accounting_basis=str_or_none(payload.get("accounting_basis")),
        )
        document_class = _declared_document_class(payload.get("document_class"))

        output.append(
            RealGoldFixture(
                document_id=document_id,
                context=context,
                metrics=metrics,
                tolerances=tolerances,
                expected_trust=expected_trust,
                document_class=document_class,
                source_document_id=str_or_none(payload.get("source_document_id")),
            )
        )
    return output


def evaluate_real_gold_fixture(
    fixture: RealGoldFixture,
    extracted_payload: dict[str, Any] | None,
) -> RealGoldFixtureEvaluation:
    """Evaluate one real fixture against one extraction payload."""

    extracted_payload = extracted_payload or {}
    metric_payload = extracted_payload.get("metrics", extracted_payload)
    if not isinstance(metric_payload, dict):
        metric_payload = {}

    synthetic_fixture = ExtractionFixture(
        fixture_id=fixture.document_id,
        context=fixture.context,
        metrics=fixture.metrics,
        expected_nulls=[],
        optional_metrics=[],
        tolerances=fixture.tolerances,
    )

    evaluation = evaluate_fixture(
        synthetic_fixture,
        metric_payload,
        extracted_payload,
        expected_source_document_id=fixture.source_document_id,
        require_structured_provenance=True,
    )
    trust, trust_triggers, provenance_trust_failures = _derive_trust_outcome(evaluation)
    expected_trust = fixture.expected_trust
    trust_matches_expected = (
        trust == expected_trust if expected_trust is not None else None
    )

    return RealGoldFixtureEvaluation(
        document_id=fixture.document_id,
        context_ok=evaluation.context_ok,
        context_mismatches=evaluation.context_mismatches,
        metrics=evaluation.metrics,
        provenance_summary=evaluation.provenance_summary,
        trust=trust,
        trust_triggers=trust_triggers,
        expected_trust=expected_trust,
        trust_matches_expected=trust_matches_expected,
        provenance_trust_failures=provenance_trust_failures,
    )


def classify_real_gold_fixtures(
    fixtures: list[RealGoldFixture],
    extracted_payloads: dict[str, dict[str, Any]],
) -> list[RealGoldFixtureEvaluation]:
    evaluations: list[RealGoldFixtureEvaluation] = []
    for fixture in fixtures:
        evaluations.append(
            evaluate_real_gold_fixture(
                fixture, extracted_payloads.get(fixture.document_id)
            )
        )
    return evaluations


def build_real_gold_scorecard(
    fixtures_dir: str | Path,
    extracted_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fixtures = load_real_gold_fixtures(fixtures_dir)
    extracted_payloads = extracted_payloads or {}
    evaluations = classify_real_gold_fixtures(fixtures, extracted_payloads)
    return summarize_real_gold_evaluations(
        fixtures,
        evaluations,
        extracted_payloads,
    )


def summarize_real_gold_evaluations(
    fixtures: Iterable[RealGoldFixture],
    evaluations: Iterable[RealGoldFixtureEvaluation],
    extracted_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic no-write scorecard from in-memory real evaluations."""

    fixture_list = sorted(fixtures, key=lambda item: item.document_id)
    evaluation_list = sorted(evaluations, key=lambda item: item.document_id)
    fixture_ids = [fixture.document_id for fixture in fixture_list]
    evaluation_ids = [evaluation.document_id for evaluation in evaluation_list]
    duplicate_fixture_ids = _duplicate_document_ids(fixture_ids)
    if duplicate_fixture_ids:
        raise ValueError(
            "duplicate fixture document IDs: " + ", ".join(duplicate_fixture_ids)
        )
    duplicate_evaluation_ids = _duplicate_document_ids(evaluation_ids)
    if duplicate_evaluation_ids:
        raise ValueError(
            "duplicate evaluation document IDs: " + ", ".join(duplicate_evaluation_ids)
        )
    fixture_id_set = set(fixture_ids)
    evaluation_id_set = set(evaluation_ids)
    if fixture_id_set != evaluation_id_set:
        missing_evaluations = sorted(fixture_id_set - evaluation_id_set)
        unexpected_evaluations = sorted(evaluation_id_set - fixture_id_set)
        raise ValueError(
            "fixture/evaluation document ID sets differ: "
            f"missing evaluations={missing_evaluations}; "
            f"unexpected evaluations={unexpected_evaluations}"
        )

    fixture_by_id = {fixture.document_id: fixture for fixture in fixture_list}
    summary: dict[str, int] = {
        "trusted": 0,
        "abstain": 0,
        "quarantine": 0,
    }
    trust_checks = {
        "expected_present": 0,
        "matches": 0,
        "mismatches": 0,
    }
    fixture_summaries: list[dict[str, Any]] = []
    metric_counts = _metric_status_counts(evaluation_list)

    for evaluation in evaluation_list:
        fixture = fixture_by_id[evaluation.document_id]
        payload = extracted_payloads.get(evaluation.document_id, {})
        if evaluation.trust == RealTrustOutcome.TRUSTED:
            summary["trusted"] += 1
        elif evaluation.trust == RealTrustOutcome.ABSTAIN:
            summary["abstain"] += 1
        else:
            summary["quarantine"] += 1

        if evaluation.expected_trust is not None:
            trust_checks["expected_present"] += 1
            if evaluation.trust_matches_expected:
                trust_checks["matches"] += 1
            else:
                trust_checks["mismatches"] += 1

        document_class = _document_class_value(fixture.document_class)
        numeric_quality = summarize_numeric_quality([evaluation])
        fixture_summaries.append(
            {
                "evaluation_lane": "real_document",
                "document_id": evaluation.document_id,
                "document_class": document_class,
                "document_class_supported": (
                    document_class in SUPPORTED_ASX_DOCUMENT_CLASSES
                ),
                "trust": evaluation.trust.value,
                "trust_triggers": evaluation.trust_triggers,
                "provenance_trust_failures": (evaluation.provenance_trust_failures),
                "expected_trust": evaluation.expected_trust.value
                if evaluation.expected_trust is not None
                else None,
                "trust_matches_expected": evaluation.trust_matches_expected,
                "context_ok": evaluation.context_ok,
                "context_mismatches": evaluation.context_mismatches,
                "context_correctness": _context_correctness_detail(
                    fixture.context,
                    payload,
                ),
                **numeric_quality,
                "metric_count": len(evaluation.metrics),
                "correct_count": sum(
                    1
                    for metric in evaluation.metrics
                    if metric.status == MetricEvalStatus.CORRECT
                ),
                "wrong_count": sum(
                    1
                    for metric in evaluation.metrics
                    if metric.status == MetricEvalStatus.WRONG
                ),
                "missing_count": sum(
                    1
                    for metric in evaluation.metrics
                    if metric.status == MetricEvalStatus.MISSING
                ),
                "abstain_count": sum(
                    1
                    for metric in evaluation.metrics
                    if metric.status == MetricEvalStatus.ABSTAIN
                ),
                "quarantine_count": sum(
                    1
                    for metric in evaluation.metrics
                    if metric.status == MetricEvalStatus.QUARANTINE
                ),
                "provenance_available": evaluation.provenance_summary["available"],
                "provenance_status": evaluation.provenance_summary["status"],
                "provenance_record_count": evaluation.provenance_summary[
                    "record_count"
                ],
                "provenance_issue_count": evaluation.provenance_summary["issue_count"],
                "provenance_error_count": evaluation.provenance_summary["error_count"],
                "provenance_warning_count": evaluation.provenance_summary[
                    "warning_count"
                ],
                "provenance_status_counts": evaluation.provenance_summary[
                    "status_counts"
                ],
                "provenance_issues": evaluation.provenance_summary["issues"],
            }
        )

    context_summaries = _context_correctness_summaries(
        fixture_list,
        extracted_payloads,
    )
    numeric_quality = summarize_numeric_quality(evaluation_list)
    provenance_trust_failure_count = sum(
        len(evaluation.provenance_trust_failures) for evaluation in evaluation_list
    )
    return {
        "evaluation_lane": "real_document",
        "total_fixture_count": len(fixture_list),
        "total_metric_expectations": sum(
            item["metric_count"] for item in fixture_summaries
        ),
        "trusted_count": summary["trusted"],
        "abstained_count": summary["abstain"],
        "quarantined_count": summary["quarantine"],
        "trust_check_summary": trust_checks,
        "metric_status_counts": metric_counts,
        **numeric_quality,
        **context_summaries,
        "provenance_trust_failure_count": provenance_trust_failure_count,
        "provenance_trust_failure_document_count": sum(
            bool(evaluation.provenance_trust_failures) for evaluation in evaluation_list
        ),
        "provenance_summary": summarize_provenance_summaries(
            evaluation.provenance_summary for evaluation in evaluation_list
        ),
        "document_class_groups": _build_document_class_groups(
            fixture_list,
            evaluation_list,
            extracted_payloads,
        ),
        "document_class_grouping": {
            "supported_classes": list(SUPPORTED_ASX_DOCUMENT_CLASSES),
            "classification_is_metric_evidence": False,
            "classification_is_metric_authority": False,
        },
        "fixture_summaries": fixture_summaries,
    }


def _derive_trust_outcome(
    evaluation: FixtureEvaluation,
) -> tuple[RealTrustOutcome, list[str], list[str]]:
    provenance_trust_failures = _required_provenance_failures(evaluation)
    if not evaluation.context_ok:
        return (
            RealTrustOutcome.QUARANTINE,
            [f"context_mismatch:{field}" for field in evaluation.context_mismatches],
            provenance_trust_failures,
        )

    triggers: list[str] = []
    for metric in evaluation.metrics:
        if metric.status in (
            MetricEvalStatus.WRONG,
            MetricEvalStatus.MISSING,
            MetricEvalStatus.ABSTAIN,
        ):
            triggers.append(f"{metric.metric}:{metric.status.value}")
    if triggers:
        return RealTrustOutcome.ABSTAIN, triggers, provenance_trust_failures

    if provenance_trust_failures:
        return (
            RealTrustOutcome.ABSTAIN,
            provenance_trust_failures,
            provenance_trust_failures,
        )

    return RealTrustOutcome.TRUSTED, [], []


def _required_provenance_failures(
    evaluation: FixtureEvaluation,
) -> list[str]:
    by_metric = {
        str(summary.get("metric")): summary
        for summary in evaluation.provenance_summary.get("metric_summaries", [])
        if isinstance(summary, Mapping)
    }
    failures: list[str] = []
    for metric in evaluation.metrics:
        if metric.actual is None:
            continue
        contract = METRIC_CONTRACT_BY_CANONICAL_FIELD.get(metric.metric)
        required = bool(
            contract is not None
            and contract.declared_status == MetricContractStatus.SUPPORTED
            and contract.provenance_requirement != ProvenanceRequirement.NOT_CANONICAL
        )
        if not required:
            continue

        summary = by_metric.get(metric.metric)
        if summary is None:
            failures.append(f"{metric.metric}:provenance_missing")
            continue
        if not summary.get("canonical_provenance_valid"):
            reason = str(summary.get("canonical_provenance_reason") or "invalid")
            failures.append(f"{metric.metric}:provenance_invalid:{reason}")
    return failures


def _duplicate_document_ids(document_ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for document_id in document_ids:
        if document_id in seen:
            duplicates.add(document_id)
        seen.add(document_id)
    return sorted(duplicates)


def _metric_status_counts(
    evaluations: Iterable[RealGoldFixtureEvaluation],
) -> dict[str, int]:
    counts = {
        "correct": 0,
        "wrong": 0,
        "missing": 0,
        "abstain": 0,
        "quarantine": 0,
    }
    for evaluation in evaluations:
        for metric in evaluation.metrics:
            counts[metric.status.value] += 1
    return counts


def _context_correctness_detail(
    expected: FixtureContext,
    actual: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    fields = {
        "period_end": ("period_end", expected.period_end),
        "period_basis": ("period_type", expected.period_type),
        "currency": ("currency", expected.currency),
        "scale": ("scale", expected.scale),
        "accounting_basis": (
            "accounting_basis",
            expected.accounting_basis,
        ),
    }
    detail: dict[str, dict[str, Any]] = {}
    for public_name, (payload_name, expected_value) in fields.items():
        actual_value = str_or_none(actual.get(payload_name))
        matched: bool | None = None
        if expected_value is not None:
            matched = bool(
                actual_value is not None
                and actual_value.lower() == expected_value.lower()
            )
        detail[public_name] = {
            "expected": expected_value,
            "actual": actual_value,
            "matched": matched,
        }
    return detail


def _context_correctness_summaries(
    fixtures: Iterable[RealGoldFixture],
    extracted_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    fixture_list = list(fixtures)
    fields = {
        "period_end_correctness_summary": ("period_end", "period_end"),
        "period_basis_correctness_summary": ("period_type", "period_type"),
        "currency_correctness_summary": ("currency", "currency"),
        "scale_correctness_summary": ("scale", "scale"),
        "accounting_basis_correctness_summary": (
            "accounting_basis",
            "accounting_basis",
        ),
    }
    output: dict[str, dict[str, int]] = {}
    for public_name, (context_name, payload_name) in fields.items():
        expected_count = 0
        matched_count = 0
        mismatched_count = 0
        missing_count = 0
        for fixture in fixture_list:
            expected = str_or_none(getattr(fixture.context, context_name))
            if expected is None:
                continue
            expected_count += 1
            payload = extracted_payloads.get(fixture.document_id, {})
            actual = str_or_none(payload.get(payload_name))
            if actual is None:
                missing_count += 1
                mismatched_count += 1
            elif actual.lower() == expected.lower():
                matched_count += 1
            else:
                mismatched_count += 1
        output[public_name] = {
            "expected_count": expected_count,
            "matched_count": matched_count,
            "mismatched_count": mismatched_count,
            "missing_count": missing_count,
        }
    return output


def _build_document_class_groups(
    fixtures: list[RealGoldFixture],
    evaluations: list[RealGoldFixtureEvaluation],
    extracted_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    evaluation_by_id = {
        evaluation.document_id: evaluation for evaluation in evaluations
    }
    grouped: dict[str, list[RealGoldFixture]] = {
        document_class: [] for document_class in SUPPORTED_ASX_DOCUMENT_CLASSES
    }
    for fixture in fixtures:
        document_class = _document_class_value(fixture.document_class)
        grouped.setdefault(document_class, []).append(fixture)

    output: dict[str, dict[str, Any]] = {}
    for document_class in sorted(grouped):
        class_fixtures = grouped[document_class]
        class_evaluations = [
            evaluation_by_id[fixture.document_id] for fixture in class_fixtures
        ]
        class_payloads = {
            fixture.document_id: extracted_payloads.get(fixture.document_id, {})
            for fixture in class_fixtures
        }
        trust_counts = {
            outcome.value: sum(
                evaluation.trust == outcome for evaluation in class_evaluations
            )
            for outcome in RealTrustOutcome
        }
        output[document_class] = {
            "document_count": len(class_fixtures),
            "document_class_supported": (
                document_class in SUPPORTED_ASX_DOCUMENT_CLASSES
            ),
            "classification_is_metric_authority": False,
            "trusted_count": trust_counts["trusted"],
            "abstained_count": trust_counts["abstain"],
            "quarantined_count": trust_counts["quarantine"],
            "metric_status_counts": _metric_status_counts(class_evaluations),
            **summarize_numeric_quality(class_evaluations),
            **_context_correctness_summaries(
                class_fixtures,
                class_payloads,
            ),
            "provenance_trust_failure_count": sum(
                len(evaluation.provenance_trust_failures)
                for evaluation in class_evaluations
            ),
        }
    return output


def _declared_document_class(raw: Any) -> ASXDocumentClass | None:
    if raw is None:
        return None
    normalized = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "annual": ASXDocumentClass.ANNUAL,
        "annual_report": ASXDocumentClass.ANNUAL,
        "half_year": ASXDocumentClass.HALF_YEAR,
        "half_year_report": ASXDocumentClass.HALF_YEAR,
        "quarterly": ASXDocumentClass.QUARTERLY,
        "quarterly_report": ASXDocumentClass.QUARTERLY,
    }
    return aliases.get(normalized)


def _document_class_value(
    document_class: ASXDocumentClass | str | None,
) -> str:
    if isinstance(document_class, ASXDocumentClass):
        return document_class.value
    declared = _declared_document_class(document_class)
    return declared.value if declared is not None else "unclassified"


def _safe_load_fixture_json(path: Path, raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"fixture {path} must be a JSON object")
    return data


def _coerce_metric_map(raw: Any, path: Path) -> dict[str, float | None]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"metrics for {path} must be an object")

    parsed: dict[str, float | None] = {}
    for metric, value in raw.items():
        normalized_metric = REAL_GOLD_METRIC_ALIASES.get(metric, metric)
        if value is None:
            parsed[normalized_metric] = None
        elif isinstance(value, bool) or isinstance(value, (int, float)):
            parsed[normalized_metric] = float(value)
        else:
            raise ValueError(f"metric {metric} in {path} must be numeric or null")
    return parsed


def _coerce_tolerances(raw: Any, path: Path) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"tolerances for {path} must be an object")

    parsed: dict[str, float] = {}
    for metric, value in raw.items():
        normalized_metric = REAL_GOLD_METRIC_ALIASES.get(metric, metric)
        if not isinstance(value, int | float):
            raise ValueError(f"tolerance for {path}:{metric} must be numeric")
        parsed[normalized_metric] = float(value)
    return parsed


def _validate_metric_names(path: Path, metrics: dict[str, float | None]) -> None:
    for metric in metrics:
        if metric not in METRIC_FIELDS:
            raise ValueError(f"unknown metric '{metric}' in {path}")
