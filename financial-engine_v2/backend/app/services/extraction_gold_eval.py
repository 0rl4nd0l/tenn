"""Helpers for a real-document gold-eval pilot.

This module intentionally remains separate from the synthetic fixture harness.
It evaluates pre-produced extraction JSON payloads against hand-labelled real fixtures
using the same metric comparison logic as the synthetic scaffold, then derives a
small trust outcome for each fixture.

Trust semantics are deterministic and intentionally transparent:

- `trusted`: context matches and every required metric is `correct`.
- `abstain`: context matches but at least one required metric is
  `wrong`, `missing`, or `abstain`.
- `quarantine`: any context field mismatch (`period_end`, `period_type`,
  `currency`, or `scale`). All metrics for that fixture are marked `quarantine`.

For this pilot, real fixtures use required metrics only (no optional list), so a
required metric that is absent from extracted output is scored as `missing` (not
`abstain`).

The trusted/abstain/quarantine outcome is explicitly represented in fixture labels
when available but does not alter fixture discovery or synthetic evaluation.
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from app.services.extraction_eval import (
    ExtractionFixture,
    FixtureContext,
    MetricEvalStatus,
    FixtureEvaluation,
    MetricEvaluation,
    evaluate_fixture,
    summarize_provenance_summaries,
    str_or_none,
)
from app.services.multipass_extraction import METRIC_FIELDS


REAL_GOLD_METRIC_ALIASES = {
    "operating_cash_flow": "operating_cf",
}


class RealTrustOutcome(str, Enum):
    TRUSTED = "trusted"
    ABSTAIN = "abstain"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class RealGoldFixture:
    document_id: str
    context: FixtureContext
    metrics: dict[str, float | None]
    tolerances: dict[str, float]
    expected_trust: RealTrustOutcome | None


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
        )

        output.append(
            RealGoldFixture(
                document_id=document_id,
                context=context,
                metrics=metrics,
                tolerances=tolerances,
                expected_trust=expected_trust,
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

    evaluation = evaluate_fixture(synthetic_fixture, metric_payload, extracted_payload)
    trust, trust_triggers = _derive_trust_outcome(evaluation)
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

    metric_counts: dict[str, int] = {
        "correct": 0,
        "wrong": 0,
        "missing": 0,
        "abstain": 0,
        "quarantine": 0,
    }

    for evaluation in evaluations:
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

        for metric_eval in evaluation.metrics:
            if metric_eval.status == MetricEvalStatus.CORRECT:
                metric_counts["correct"] += 1
            elif metric_eval.status == MetricEvalStatus.WRONG:
                metric_counts["wrong"] += 1
            elif metric_eval.status == MetricEvalStatus.MISSING:
                metric_counts["missing"] += 1
            elif metric_eval.status == MetricEvalStatus.ABSTAIN:
                metric_counts["abstain"] += 1
            elif metric_eval.status == MetricEvalStatus.QUARANTINE:
                metric_counts["quarantine"] += 1

        fixture_summaries.append(
            {
                "document_id": evaluation.document_id,
                "trust": evaluation.trust.value,
                "trust_triggers": evaluation.trust_triggers,
                "expected_trust": evaluation.expected_trust.value
                if evaluation.expected_trust is not None
                else None,
                "trust_matches_expected": evaluation.trust_matches_expected,
                "context_ok": evaluation.context_ok,
                "context_mismatches": evaluation.context_mismatches,
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

    return {
        "total_fixture_count": len(fixtures),
        "total_metric_expectations": sum(
            item["metric_count"] for item in fixture_summaries
        ),
        "trusted_count": summary["trusted"],
        "abstained_count": summary["abstain"],
        "quarantined_count": summary["quarantine"],
        "trust_check_summary": trust_checks,
        "metric_status_counts": metric_counts,
        "provenance_summary": summarize_provenance_summaries(
            evaluation.provenance_summary for evaluation in evaluations
        ),
        "fixture_summaries": fixture_summaries,
    }


def _derive_trust_outcome(
    evaluation: FixtureEvaluation,
) -> tuple[RealTrustOutcome, list[str]]:
    if not evaluation.context_ok:
        return RealTrustOutcome.QUARANTINE, [
            f"context_mismatch:{field}" for field in evaluation.context_mismatches
        ]

    triggers: list[str] = []
    for metric in evaluation.metrics:
        if metric.status in (
            MetricEvalStatus.WRONG,
            MetricEvalStatus.MISSING,
            MetricEvalStatus.ABSTAIN,
        ):
            triggers.append(f"{metric.metric}:{metric.status.value}")
    if triggers:
        return RealTrustOutcome.ABSTAIN, triggers

    return RealTrustOutcome.TRUSTED, []


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
