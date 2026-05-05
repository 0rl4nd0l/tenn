"""Read-only scorecard profile helpers for extraction evaluation.

This module defines profile metadata separately from the real-gold evaluator so
canonical trust semantics remain unchanged. The confirmed metric coverage
profile is intentionally conservative: broader fixture labels are scored only
when they are source-evidenced, schema-supported, and not marked ambiguous.
Everything else is reported for review instead of promoted to gold truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.services.extraction_eval import (
    ExtractionFixture,
    FixtureContext,
    MetricEvalStatus,
    evaluate_fixture,
    str_or_none,
)
from app.services.multipass_extraction import METRIC_FIELDS


PROFILE_VERSION = "2026-05-05"

CANONICAL_CORE_DOC_IDS = (
    "bhp_a_2021-06-30_difficult",
    "bhp_a_2025-06-30",
    "eqr_q_2025-12-31",
    "gre_q_2024-12-31",
    "gre_q_2025-09-30",
    "min_h_2025-12-31",
    "qbe_h_2025-06-30",
    "rio_a_2023-12-31",
    "rio_a_2024-12-31",
    "tls_h_2025-12-31",
)

PROFILE_DEFINITIONS = {
    "canonical_core": {
        "profile": "canonical_core",
        "description": "Existing 10-doc no-regression anchor.",
        "fixture_source": "financial-engine_v2/data/extraction_gold_real",
        "document_ids": list(CANONICAL_CORE_DOC_IDS),
        "expected_document_count": 10,
        "expected_metric_checks": 24,
        "mutates_canonical_trust": False,
        "trust_semantics": "unchanged",
    },
    "expanded_required": {
        "profile": "expanded_required",
        "description": "Existing full real-gold required subset.",
        "fixture_source": "financial-engine_v2/data/extraction_gold_real",
        "expected_document_count": 15,
        "expected_metric_checks": 39,
        "mutates_canonical_trust": False,
        "trust_semantics": "unchanged",
    },
    "confirmed_metric_coverage": {
        "profile": "confirmed_metric_coverage",
        "description": (
            "Read-only broader metric coverage profile over confirmed, "
            "source-evidenced, schema-supported fixture labels."
        ),
        "fixture_source": "financial-engine_v2/backend/tests/eval_fixtures",
        "mutates_canonical_trust": False,
        "trust_semantics": "separate coverage reporting only",
    },
}

METRIC_NAME_MAP = {
    "revenue": "revenue",
    "ebit": "ebit",
    "np_attributable": "np_attributable",
    "operating_cf": "operating_cf",
    "operating_cash_flow": "operating_cf",
    "investing_cf": "investing_cf",
    "financing_cf": "financing_cf",
    "capex": "capex",
    "cash_end": "cash_end",
    "net_debt": "net_debt",
    "shares_outstanding": "shares_outstanding",
}

PRODUCTION_RELEVANCE_TIERS = {
    "revenue": "core",
    "ebit": "core",
    "np_attributable": "core",
    "operating_cf": "core",
    "net_debt": "core",
    "cash_end": "cash_flow",
    "investing_cf": "cash_flow",
    "financing_cf": "cash_flow",
    "capex": "cash_flow",
    "shares_outstanding": "capital_structure",
}


class FixtureEvidenceStatus(str, Enum):
    CONFIRMED_SOURCE_EVIDENCED = "CONFIRMED_SOURCE_EVIDENCED"
    CANDIDATE_REVIEW_REQUIRED = "CANDIDATE_REVIEW_REQUIRED"
    MISSING_SOURCE_EVIDENCE = "MISSING_SOURCE_EVIDENCE"


class CoverageSupportStatus(str, Enum):
    SCORED = "scored"
    CANDIDATE_REVIEW_REQUIRED = "candidate_review_required"
    MISSING_SOURCE_EVIDENCE = "missing_source_evidence"
    UNSUPPORTED_SCHEMA = "unsupported_schema"
    AMBIGUOUS_LABEL = "ambiguous_label"


@dataclass(frozen=True)
class CoverageExpectation:
    fixture_id: str
    document_id: str
    fixture_path: str
    fixture_name: str
    metric_name: str
    canonical_field: str | None
    expectation_type: str
    expected_value: float | None
    tolerance: float
    schema_supported: bool
    extractor_output_supported: bool
    evaluator_supported: bool
    source_evidence_available: bool
    source_pdf_exists: bool | None
    source_status: FixtureEvidenceStatus
    support_status: CoverageSupportStatus
    ambiguity: str | None
    tier: str
    recommendation: str

    @property
    def should_score(self) -> bool:
        return self.support_status == CoverageSupportStatus.SCORED


def get_scorecard_profiles() -> dict[str, dict[str, Any]]:
    """Return deterministic metadata for all extraction scorecard profiles."""

    return {key: dict(value) for key, value in PROFILE_DEFINITIONS.items()}


def metric_mapping_table() -> list[dict[str, Any]]:
    """Return the broader fixture metric mapping into extractor schema fields."""

    rows: list[dict[str, Any]] = []
    for fixture_name, canonical_field in sorted(METRIC_NAME_MAP.items()):
        schema_supported = canonical_field in METRIC_FIELDS
        rows.append(
            {
                "fixture_name": fixture_name,
                "canonical_field": canonical_field,
                "schema_supported": schema_supported,
                "extractor_output_supported": schema_supported,
                "evaluator_supported": schema_supported,
                "source_evidence_available": "fixture-dependent",
                "production_relevance_tier": PRODUCTION_RELEVANCE_TIERS.get(
                    canonical_field, "DATA_MISSING"
                ),
                "ambiguity_risk": _mapping_ambiguity_risk(fixture_name),
            }
        )
    return rows


def build_confirmed_metric_coverage_scorecard(
    fixtures_dir: str | Path,
    extracted_payloads: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    financial_engine_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build the read-only confirmed metric coverage profile.

    When extracted_payloads is omitted, the result is a deterministic inventory
    and support-status report. When payloads are supplied, only expectations with
    support_status == "scored" are evaluated.
    """

    fixture_dir = Path(fixtures_dir)
    payloads = dict(extracted_payloads or {})
    root = (
        Path(financial_engine_root)
        if financial_engine_root is not None
        else Path(__file__).resolve().parents[3]
    )

    fixture_payloads = _load_fixture_payloads(fixture_dir)
    expectations: list[CoverageExpectation] = []
    fixture_summaries: list[dict[str, Any]] = []

    for path, payload in fixture_payloads:
        fixture_expectations = _expectations_for_payload(path, payload, root)
        expectations.extend(fixture_expectations)
        fixture_summaries.append(
            _fixture_summary(path, payload, fixture_expectations)
        )

    evaluated = (
        _evaluate_scored_expectations(fixture_payloads, expectations, payloads)
        if extracted_payloads is not None
        else {}
    )
    metric_family_summary = _metric_family_summary(expectations, evaluated)
    support_summary = _support_summary(expectations)
    status_summary = _status_summary(evaluated, support_summary["scored"])

    return {
        "profile": "confirmed_metric_coverage",
        "profile_version": PROFILE_VERSION,
        "fixtures_dir": str(fixture_dir),
        "total_fixture_count": len(fixture_payloads),
        "total_metric_expectations": len(expectations),
        "scored_metric_expectations": support_summary["scored"],
        "candidate_review_required_count": support_summary[
            "candidate_review_required"
        ],
        "missing_source_evidence_count": support_summary["missing_source_evidence"],
        "unsupported_metric_count": support_summary["unsupported_schema"],
        "ambiguous_metric_count": support_summary["ambiguous_label"],
        "source_status_counts": _source_status_counts(fixture_summaries),
        "status_summary": status_summary,
        "metric_family_summary": metric_family_summary,
        "fixture_summaries": fixture_summaries,
        "metric_expectations": [
            _expectation_to_dict(expectation, evaluated)
            for expectation in expectations
        ],
        "canonical_trust_semantics": {
            "canonical_core_unchanged": True,
            "expanded_required_unchanged": True,
            "mutates_canonical_trust": False,
        },
    }


def _load_fixture_payloads(fixture_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not fixture_dir.exists():
        return []

    payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(fixture_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"fixture {path} must be a JSON object")
        payloads.append((path, payload))
    return payloads


def _expectations_for_payload(
    path: Path,
    payload: Mapping[str, Any],
    financial_engine_root: Path,
) -> list[CoverageExpectation]:
    document_id = str(payload.get("document_id") or path.stem)
    source_status = classify_fixture_source_status(payload)
    source_pdf_exists = _source_pdf_exists(payload, financial_engine_root)
    fixture_name = path.name

    raw_metrics = payload.get("metrics", {})
    if raw_metrics is None:
        raw_metrics = {}
    if not isinstance(raw_metrics, Mapping):
        raise ValueError(f"metrics for {path} must be an object")

    expected_nulls = payload.get("expected_nulls", [])
    if expected_nulls is None:
        expected_nulls = []
    if not isinstance(expected_nulls, list):
        raise ValueError(f"expected_nulls for {path} must be a list")

    tolerances = payload.get("tolerances", {})
    if tolerances is None:
        tolerances = {}
    if not isinstance(tolerances, Mapping):
        raise ValueError(f"tolerances for {path} must be an object")

    ordered_names = list(raw_metrics.keys())
    for metric in expected_nulls:
        if metric not in ordered_names:
            ordered_names.append(metric)

    expectations = []
    for raw_metric in ordered_names:
        if not isinstance(raw_metric, str):
            raise ValueError(f"metric names for {path} must be strings")

        canonical_field = METRIC_NAME_MAP.get(raw_metric)
        expected_value = _coerce_metric_value(raw_metrics.get(raw_metric), path)
        expectation_type = (
            "expected_null"
            if raw_metric in expected_nulls or expected_value is None
            else "value"
        )
        tolerance = _coerce_tolerance(tolerances.get(raw_metric), path, raw_metric)
        schema_supported = canonical_field in METRIC_FIELDS
        source_available = (
            source_status == FixtureEvidenceStatus.CONFIRMED_SOURCE_EVIDENCED
        )
        ambiguity = _metric_ambiguity(raw_metric, expected_value, payload)
        support_status = _support_status(
            schema_supported=schema_supported,
            source_status=source_status,
            ambiguity=ambiguity,
        )

        expectations.append(
            CoverageExpectation(
                fixture_id=document_id,
                document_id=document_id,
                fixture_path=str(path),
                fixture_name=fixture_name,
                metric_name=raw_metric,
                canonical_field=canonical_field,
                expectation_type=expectation_type,
                expected_value=expected_value,
                tolerance=tolerance,
                schema_supported=schema_supported,
                extractor_output_supported=schema_supported,
                evaluator_supported=schema_supported,
                source_evidence_available=source_available,
                source_pdf_exists=source_pdf_exists,
                source_status=source_status,
                support_status=support_status,
                ambiguity=ambiguity,
                tier=PRODUCTION_RELEVANCE_TIERS.get(
                    canonical_field or "", "DATA_MISSING"
                ),
                recommendation=_recommendation(support_status),
            )
        )
    return expectations


def classify_fixture_source_status(
    payload: Mapping[str, Any],
) -> FixtureEvidenceStatus:
    source = str(payload.get("_source") or "").strip()
    verification = str(payload.get("_verification") or "").strip().lower()
    confidence = str(payload.get("_verification_confidence") or "").strip().lower()
    source_lower = source.lower()

    if not source:
        return FixtureEvidenceStatus.MISSING_SOURCE_EVIDENCE
    if "not hand-verified" in confidence or "lower" in confidence:
        return FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED
    if verification.startswith("claude") or "claude" in verification:
        return FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED
    if "medium" in confidence or "attribution is complex" in confidence:
        return FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED
    if "hand-verified" in verification or "hand-verified" in source_lower:
        return FixtureEvidenceStatus.CONFIRMED_SOURCE_EVIDENCED
    return FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED


def _source_pdf_exists(
    payload: Mapping[str, Any],
    financial_engine_root: Path,
) -> bool | None:
    raw_path = str(payload.get("pdf_path") or payload.get("source_file") or "").strip()
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.exists()
    return (financial_engine_root / candidate).exists()


def _coerce_metric_value(raw: Any, path: Path) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"metric value in {path} must be numeric or null")
    return float(raw)


def _coerce_tolerance(raw: Any, path: Path, metric: str) -> float:
    if raw is None:
        return 0.01
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"tolerance for {path}:{metric} must be numeric")
    return float(raw)


def _metric_ambiguity(
    metric: str,
    expected_value: float | None,
    payload: Mapping[str, Any],
) -> str | None:
    notes = payload.get("notes", {})
    metric_note = ""
    if isinstance(notes, Mapping):
        metric_note = str(notes.get(metric) or "")
    confidence = str(payload.get("_verification_confidence") or "")
    source = str(payload.get("_source") or "")
    text = f"{metric_note}\n{confidence}\n{source}".lower()

    ambiguous_terms = (
        "ambiguous",
        "unresolved",
        "attribution is complex",
        "should be hand-checked",
        "not hand-verified",
    )
    for term in ambiguous_terms:
        if term in text:
            return term

    if expected_value is None:
        return None

    if metric == "net_debt":
        debt_text = f"{metric_note}\n{source}".lower()
        if "explicit net debt" in debt_text or "net drawn debt" in debt_text:
            return None
        if (
            "borrowings" in debt_text
            or "financial debt" in debt_text
            or "total debt" in debt_text
            or "net_debt =" in debt_text
        ):
            return "net_debt_derivation_risk"

    return None


def _support_status(
    *,
    schema_supported: bool,
    source_status: FixtureEvidenceStatus,
    ambiguity: str | None,
) -> CoverageSupportStatus:
    if not schema_supported:
        return CoverageSupportStatus.UNSUPPORTED_SCHEMA
    if source_status == FixtureEvidenceStatus.MISSING_SOURCE_EVIDENCE:
        return CoverageSupportStatus.MISSING_SOURCE_EVIDENCE
    if source_status == FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED:
        return CoverageSupportStatus.CANDIDATE_REVIEW_REQUIRED
    if ambiguity:
        return CoverageSupportStatus.AMBIGUOUS_LABEL
    return CoverageSupportStatus.SCORED


def _recommendation(status: CoverageSupportStatus) -> str:
    if status == CoverageSupportStatus.SCORED:
        return "score_in_confirmed_metric_coverage"
    if status == CoverageSupportStatus.CANDIDATE_REVIEW_REQUIRED:
        return "request_human_source_evidence_review"
    if status == CoverageSupportStatus.MISSING_SOURCE_EVIDENCE:
        return "add_source_evidence_before_scoring"
    if status == CoverageSupportStatus.UNSUPPORTED_SCHEMA:
        return "do_not_score_until_schema_supported"
    return "exclude_or_mark_ambiguous_until_resolved"


def _evaluate_scored_expectations(
    fixture_payloads: Iterable[tuple[Path, Mapping[str, Any]]],
    expectations: list[CoverageExpectation],
    extracted_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    expectations_by_fixture: dict[str, list[CoverageExpectation]] = {}
    for expectation in expectations:
        if expectation.should_score:
            expectations_by_fixture.setdefault(expectation.fixture_id, []).append(
                expectation
            )

    evaluated: dict[tuple[str, str], dict[str, Any]] = {}
    for path, payload in fixture_payloads:
        fixture_id = str(payload.get("document_id") or path.stem)
        fixture_expectations = expectations_by_fixture.get(fixture_id, [])
        if not fixture_expectations:
            continue

        fixture = ExtractionFixture(
            fixture_id=fixture_id,
            context=FixtureContext(
                period_end=str_or_none(payload.get("period_end")),
                period_type=str_or_none(payload.get("period_type")),
                currency=str_or_none(payload.get("currency")),
                scale=str_or_none(payload.get("scale")),
            ),
            metrics={
                item.canonical_field: item.expected_value
                for item in fixture_expectations
                if item.canonical_field is not None and item.expected_value is not None
            },
            expected_nulls=[
                item.canonical_field
                for item in fixture_expectations
                if item.canonical_field is not None and item.expected_value is None
            ],
            optional_metrics=[],
            tolerances={
                item.canonical_field: item.tolerance
                for item in fixture_expectations
                if item.canonical_field is not None
            },
        )

        extracted_payload = _resolve_extracted_payload(
            extracted_payloads, fixture_id, path
        )
        if extracted_payload is None:
            continue
        normalized_payload = _normalize_extracted_payload(extracted_payload)
        normalized_metrics = normalized_payload.get("metrics", {})
        if not isinstance(normalized_metrics, dict):
            normalized_metrics = {}
        fixture_eval = evaluate_fixture(
            fixture, normalized_metrics, normalized_payload
        )

        for metric_eval in fixture_eval.metrics:
            raw_metric = _raw_metric_for_canonical(
                fixture_expectations, metric_eval.metric
            )
            evaluated[(fixture_id, raw_metric)] = {
                "status": metric_eval.status.value,
                "expected": metric_eval.expected,
                "actual": metric_eval.actual,
                "score": metric_eval.score,
                "reason": metric_eval.reason,
            }

    return evaluated


def _resolve_extracted_payload(
    extracted_payloads: Mapping[str, Mapping[str, Any]],
    fixture_id: str,
    path: Path,
) -> Mapping[str, Any] | None:
    if fixture_id in extracted_payloads:
        return extracted_payloads[fixture_id]
    if path.stem in extracted_payloads:
        return extracted_payloads[path.stem]
    return None


def _normalize_extracted_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    raw_metrics = normalized.get("metrics", normalized)
    metrics = raw_metrics if isinstance(raw_metrics, Mapping) else {}
    normalized_metrics: dict[str, Any] = {}
    for metric, value in metrics.items():
        canonical = METRIC_NAME_MAP.get(str(metric), str(metric))
        normalized_metrics[canonical] = value
    normalized["metrics"] = normalized_metrics
    return normalized


def _raw_metric_for_canonical(
    expectations: list[CoverageExpectation],
    canonical_field: str,
) -> str:
    for expectation in expectations:
        if expectation.canonical_field == canonical_field:
            return expectation.metric_name
    return canonical_field


def _fixture_summary(
    path: Path,
    payload: Mapping[str, Any],
    expectations: list[CoverageExpectation],
) -> dict[str, Any]:
    source_status = classify_fixture_source_status(payload)
    return {
        "fixture": path.name,
        "document_id": str(payload.get("document_id") or path.stem),
        "source_status": source_status.value,
        "source_pdf_exists": expectations[0].source_pdf_exists
        if expectations
        else _source_pdf_exists(payload, Path(__file__).resolve().parents[3]),
        "metric_expectation_count": len(expectations),
        "scored_count": sum(1 for item in expectations if item.should_score),
        "candidate_review_required_count": sum(
            1
            for item in expectations
            if item.support_status == CoverageSupportStatus.CANDIDATE_REVIEW_REQUIRED
        ),
        "missing_source_evidence_count": sum(
            1
            for item in expectations
            if item.support_status == CoverageSupportStatus.MISSING_SOURCE_EVIDENCE
        ),
        "unsupported_metric_count": sum(
            1
            for item in expectations
            if item.support_status == CoverageSupportStatus.UNSUPPORTED_SCHEMA
        ),
        "ambiguous_metric_count": sum(
            1
            for item in expectations
            if item.support_status == CoverageSupportStatus.AMBIGUOUS_LABEL
        ),
    }


def _support_summary(expectations: Iterable[CoverageExpectation]) -> dict[str, int]:
    counts = {
        "scored": 0,
        "candidate_review_required": 0,
        "missing_source_evidence": 0,
        "unsupported_schema": 0,
        "ambiguous_label": 0,
    }
    for expectation in expectations:
        counts[expectation.support_status.value] += 1
    return counts


def _source_status_counts(fixture_summaries: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {
        FixtureEvidenceStatus.CONFIRMED_SOURCE_EVIDENCED.value: 0,
        FixtureEvidenceStatus.CANDIDATE_REVIEW_REQUIRED.value: 0,
        FixtureEvidenceStatus.MISSING_SOURCE_EVIDENCE.value: 0,
    }
    for summary in fixture_summaries:
        status = str(summary.get("source_status") or "")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _status_summary(
    evaluated: Mapping[tuple[str, str], dict[str, Any]],
    scored_count: int,
) -> dict[str, int]:
    counts = {
        "correct": 0,
        "wrong": 0,
        "missing": 0,
        "abstain": 0,
        "quarantine": 0,
        "not_evaluated": 0,
    }
    for result in evaluated.values():
        status = str(result.get("status") or "not_evaluated")
        counts[status] = counts.get(status, 0) + 1
    counts["not_evaluated"] = max(scored_count - len(evaluated), 0)
    return counts


def _metric_family_summary(
    expectations: Iterable[CoverageExpectation],
    evaluated: Mapping[tuple[str, str], dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for expectation in expectations:
        metric = expectation.canonical_field or expectation.metric_name
        row = summary.setdefault(
            metric,
            {
                "total_expectations": 0,
                "value_expectations": 0,
                "expected_null_expectations": 0,
                "scored": 0,
                "candidate_review_required": 0,
                "missing_source_evidence": 0,
                "unsupported_schema": 0,
                "ambiguous_label": 0,
                "correct": 0,
                "wrong": 0,
                "missing": 0,
                "abstain": 0,
                "quarantine": 0,
                "not_evaluated": 0,
            },
        )
        row["total_expectations"] += 1
        if expectation.expectation_type == "expected_null":
            row["expected_null_expectations"] += 1
        else:
            row["value_expectations"] += 1
        row[expectation.support_status.value] += 1

        result = evaluated.get((expectation.fixture_id, expectation.metric_name))
        if result is None:
            if expectation.should_score:
                row["not_evaluated"] += 1
            continue
        status = str(result.get("status") or "not_evaluated")
        row[status] = row.get(status, 0) + 1

    return dict(sorted(summary.items()))


def _expectation_to_dict(
    expectation: CoverageExpectation,
    evaluated: Mapping[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    result = evaluated.get((expectation.fixture_id, expectation.metric_name), {})
    return {
        "fixture_id": expectation.fixture_id,
        "document_id": expectation.document_id,
        "fixture": expectation.fixture_name,
        "metric_name": expectation.metric_name,
        "canonical_field": expectation.canonical_field,
        "expectation_type": expectation.expectation_type,
        "expected_value": expectation.expected_value,
        "tolerance": expectation.tolerance,
        "schema_supported": expectation.schema_supported,
        "extractor_output_supported": expectation.extractor_output_supported,
        "evaluator_supported": expectation.evaluator_supported,
        "source_evidence_available": expectation.source_evidence_available,
        "source_pdf_exists": expectation.source_pdf_exists,
        "source_status": expectation.source_status.value,
        "support_status": expectation.support_status.value,
        "ambiguity": expectation.ambiguity,
        "tier": expectation.tier,
        "recommendation": expectation.recommendation,
        "evaluation_status": result.get("status"),
        "actual_value": result.get("actual"),
        "score": result.get("score"),
        "reason": result.get("reason"),
    }


def _mapping_ambiguity_risk(fixture_name: str) -> str:
    if fixture_name == "operating_cash_flow":
        return "alias_only"
    if fixture_name == "net_debt":
        return "medium: explicit net-debt labels only; debt-minus-cash labels need review"
    if fixture_name == "capex":
        return "medium: PP&E-only vs broader investing spend convention"
    if fixture_name == "shares_outstanding":
        return "medium: count scale requires evidence"
    return "low"


def supported_metric_names() -> list[str]:
    return sorted(METRIC_NAME_MAP)


def metric_status_names() -> list[str]:
    return sorted(status.value for status in MetricEvalStatus)
