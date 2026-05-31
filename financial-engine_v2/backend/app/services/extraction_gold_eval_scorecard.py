"""Read-only scorecard profile helpers for extraction evaluation.

This module defines profile metadata separately from the real-gold evaluator so
canonical trust semantics remain unchanged. The confirmed metric coverage
profile is intentionally conservative: broader fixture labels are scored only
when they are source-evidenced, schema-supported, and not marked ambiguous.
Everything else is reported for review instead of promoted to gold truth.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Iterable as IterableABC
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from app.services.extraction_eval import (
    ExtractionFixture,
    FixtureContext,
    MetricEvalStatus,
    evaluate_fixture,
    str_or_none,
)
from app.services.multipass_extraction import (
    EXTRACTOR_VERSION,
    METRIC_FIELDS,
    classify_source_document,
)


PROFILE_VERSION = "2026-05-05"
METRIC_ONTOLOGY_VERSION = "metric_ontology_v1"

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


PERSISTED_METRIC_FIELD_EXCLUSIONS = {
    "ticker",
    "period_end",
    "period_type",
    "period_start",
    "currency",
    "source_document_id",
    "confidence_metrics",
    "created_at",
    "updated_at",
}

ACTUAL_PAYLOAD_NON_METRIC_KEYS = PERSISTED_METRIC_FIELD_EXCLUSIONS | {
    "document_id",
    "evidence",
    "metric_evidence",
    "metadata",
    "metrics",
    "_method_provenance",
    "method_provenance",
    "provenance",
    "row_refs",
    "scale",
    "source_file",
}

METRIC_CONTRACT_ARTIFACT_TYPE = "metric_contract_parity_matrix_v1"


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


class PayloadScoreStatus(str, Enum):
    PRESENT_CORRECT = "present_correct"
    MISSING_EXPECTED_METRIC = "missing_expected_metric"
    PRESENT_WRONG_VALUE = "present_wrong_value"
    WRONG_UNIT_CURRENCY_SCALE = "wrong_unit_currency_scale"
    WRONG_PERIOD = "wrong_period"
    MISSING_EVIDENCE = "missing_evidence"
    UNSUPPORTED_CORRECTLY_ABSTAINED = "unsupported_correctly_abstained"
    AMBIGUOUS_QUARANTINED = "ambiguous_quarantined"
    NOT_EVALUATED_NO_ACTUAL = "not_evaluated_no_actual_payload"


PRE_PERSISTENCE_SCORECARD_GATE_VERSION = "pre_persistence_scorecard_gate_v1"
_PRE_PERSISTENCE_ALLOWED_RESULT_CLASSES = (
    PayloadScoreStatus.PRESENT_CORRECT.value,
    PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED.value,
)
_PRE_PERSISTENCE_BLOCKING_RESULT_CLASSES = tuple(
    status.value
    for status in PayloadScoreStatus
    if status.value not in _PRE_PERSISTENCE_ALLOWED_RESULT_CLASSES
)


class MetricContractStatus(str, Enum):
    SUPPORTED = "supported"
    EXTRACTOR_SUPPORTED = "extractor_supported"
    EVALUATOR_SUPPORTED = "evaluator_supported"
    PERSISTED_ONLY = "persisted_only"
    GOLD_ONLY = "gold_only"
    PLANNED = "planned"
    INTERNAL_ONLY = "internal_only"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS_REQUIRES_POLICY = "ambiguous_requires_policy"


class SourceAssetResolutionStatus(str, Enum):
    PRESENT_VERIFIED = "present_verified"
    PRESENT_UNVERIFIED = "present_unverified"
    PRESENT_METADATA_MISMATCH = "present_metadata_mismatch"
    MISSING = "missing"
    MANIFEST_ERROR = "manifest_error"


class TerminalExtractionCandidateClass(str, Enum):
    MISSING_HOST_FILE = "missing_host_file"
    FILE_EXISTS_NO_CURRENT_TERMINAL_RUN = "file_exists_no_current_terminal_run"
    STALE_EXTRACTOR_VERSION = "stale_extractor_version"
    COMPLETED_WITH_ROWS = "completed_with_rows"
    COMPLETED_WITHOUT_ROWS = "completed_without_rows"
    SKIPPED = "skipped"
    FAILED_PARSER_ERROR = "failed_parser_error"
    QUEUED_RUNNING_ORPHANED = "queued_running_orphaned"
    UNKNOWN_NEEDS_AUDIT = "unknown_needs_audit"


class TerminalExtractionRecommendedAction(str, Enum):
    SKIP = "skip"
    REVIEW = "review"
    CANARY_CANDIDATE = "canary_candidate"
    RETRY_CANDIDATE = "retry_candidate"
    BLOCKED_MISSING_ASSET = "blocked_missing_asset"


TERMINAL_EXTRACTION_CLASS_DEFINITIONS = {
    TerminalExtractionCandidateClass.MISSING_HOST_FILE.value: (
        "PDF path is recorded, but the host source file is known missing."
    ),
    TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN.value: (
        "Host source file exists, but no current-version terminal run is known."
    ),
    TerminalExtractionCandidateClass.STALE_EXTRACTOR_VERSION.value: (
        "A terminal extraction run exists, but not for the current extractor version."
    ),
    TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS.value: (
        "Current or supplied terminal status completed and financial rows are present."
    ),
    TerminalExtractionCandidateClass.COMPLETED_WITHOUT_ROWS.value: (
        "Current or supplied terminal status completed but financial rows are absent."
    ),
    TerminalExtractionCandidateClass.SKIPPED.value: (
        "Extraction was intentionally skipped for the supplied terminal state."
    ),
    TerminalExtractionCandidateClass.FAILED_PARSER_ERROR.value: (
        "The supplied terminal run failed or ended in parser_error."
    ),
    TerminalExtractionCandidateClass.QUEUED_RUNNING_ORPHANED.value: (
        "The supplied state is queued, running, pending, or orphaned."
    ),
    TerminalExtractionCandidateClass.UNKNOWN_NEEDS_AUDIT.value: (
        "Metadata is insufficient to classify the document safely."
    ),
}

TERMINAL_EXTRACTION_RECOMMENDED_ACTION_DEFINITIONS = {
    TerminalExtractionRecommendedAction.SKIP.value: (
        "Do not queue for extraction from this manifest."
    ),
    TerminalExtractionRecommendedAction.REVIEW.value: (
        "Manual/operator review is required before any extraction decision."
    ),
    TerminalExtractionRecommendedAction.CANARY_CANDIDATE.value: (
        "Eligible only for an operator-approved bounded canary run."
    ),
    TerminalExtractionRecommendedAction.RETRY_CANDIDATE.value: (
        "Eligible only for an operator-approved bounded retry/canary run."
    ),
    TerminalExtractionRecommendedAction.BLOCKED_MISSING_ASSET.value: (
        "Blocked until source asset availability is repaired or reviewed."
    ),
}

TERMINAL_EXTRACTION_EXCLUSION_REASON_DEFINITIONS = {
    "advisory_only_document": (
        "Document metadata indicates an advisory-only announcement, so it is "
        "quarantined before canary candidate inclusion."
    ),
}

_ACTIVE_OR_OWNERSHIP_STATUSES = {
    "created",
    "pending",
    "queued",
    "running",
    "started",
    "processing",
    "in_progress",
    "orphaned",
}
_COMPLETED_STATUSES = {"ok", "ok_low_confidence", "completed", "succeeded", "success"}
_FAILED_STATUSES = {"failed", "parser_error"}


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


@dataclass(frozen=True)
class MetricContractFamily:
    family: str
    canonical_field: str | None
    aliases: tuple[str, ...]
    planned: bool = False
    internal_only: bool = False
    ambiguous_requires_policy: bool = False
    notes: str = ""


METRIC_CONTRACT_FAMILIES = (
    MetricContractFamily(
        family="revenue",
        canonical_field="revenue",
        aliases=("sales_revenue", "top_line_revenue"),
        notes="Top-line revenue family.",
    ),
    MetricContractFamily(
        family="operating_cash_flow",
        canonical_field="operating_cf",
        aliases=("operating_cf", "cash_flow_from_operations"),
        notes="Fixture/gold alias maps to the extractor field operating_cf.",
    ),
    MetricContractFamily(
        family="net_debt",
        canonical_field="net_debt",
        aliases=("net_borrowings", "net_cash"),
        notes="Canonical only when explicit net-debt evidence or approved derivation gates pass.",
    ),
    MetricContractFamily(
        family="total_equity",
        canonical_field="total_equity",
        aliases=("shareholders_equity", "equity_attributable"),
        notes="Persisted field exists, but extractor/evaluator support is not approved.",
    ),
    MetricContractFamily(
        family="interest_expense",
        canonical_field="interest_expense",
        aliases=("interest_cost", "interest_paid"),
        notes="Persisted field exists, but extractor/evaluator support is not approved.",
    ),
    MetricContractFamily(
        family="finance_costs",
        canonical_field=None,
        aliases=("finance_cost", "finance_expense"),
        ambiguous_requires_policy=True,
        notes="Potential interest_expense alias, but finance costs can include non-interest items.",
    ),
    MetricContractFamily(
        family="cash",
        canonical_field="cash_end",
        aliases=("cash_end", "cash_and_cash_equivalents", "closing_cash"),
        notes="Canonical family is period-end cash/cash equivalents.",
    ),
    MetricContractFamily(
        family="debt_borrowings",
        canonical_field="total_debt",
        aliases=("debt", "borrowings", "total_borrowings"),
        internal_only=True,
        notes="Internal balance-sheet capture used only for guarded net_debt derivation.",
    ),
    MetricContractFamily(
        family="capex",
        canonical_field="capex",
        aliases=("capital_expenditure", "payments_for_ppe"),
        notes="Supported with convention-specific source evidence requirements.",
    ),
    MetricContractFamily(
        family="eps",
        canonical_field=None,
        aliases=("earnings_per_share", "basic_eps", "diluted_eps"),
        planned=True,
        notes="Broad metric catalogue candidate; not canonical extraction output.",
    ),
    MetricContractFamily(
        family="dividends",
        canonical_field=None,
        aliases=("dividend", "dividends_paid", "dividend_per_share"),
        planned=True,
        notes="Broad metric catalogue candidate; not canonical extraction output.",
    ),
    MetricContractFamily(
        family="np_attributable",
        canonical_field="np_attributable",
        aliases=("npat", "profit_attributable", "profit attributable"),
        notes="Profit attributable to ordinary/security holders family.",
    ),
    MetricContractFamily(
        family="ebit",
        canonical_field="ebit",
        aliases=("operating_profit", "profit_before_tax"),
        notes="Supported, but source label policy remains stricter than generic PBT.",
    ),
    MetricContractFamily(
        family="investing_cf",
        canonical_field="investing_cf",
        aliases=("investing_cash_flow",),
        notes="Extractor field for cash-flow statement support.",
    ),
    MetricContractFamily(
        family="financing_cf",
        canonical_field="financing_cf",
        aliases=("financing_cash_flow",),
        notes="Extractor field for cash-flow statement support.",
    ),
    MetricContractFamily(
        family="shares_outstanding",
        canonical_field="shares_outstanding",
        aliases=("shares_on_issue", "ordinary_shares_on_issue"),
        notes="Supported when the source reports period-end share count, not weighted-average EPS denominator.",
    ),
    MetricContractFamily(
        family="total_assets",
        canonical_field=None,
        aliases=("assets",),
        notes="Unsupported in the current extraction/evaluation contract.",
    ),
)


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
                "ontology_version": METRIC_ONTOLOGY_VERSION,
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


def build_metric_contract_parity_matrix(
    *,
    confirmed_fixtures_dir: str | Path | None = None,
    real_gold_fixtures_dir: str | Path | None = None,
    financial_engine_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a report-local metric contract parity matrix.

    The matrix is diagnostic only. It does not mutate schema, extractor prompts,
    gold labels, canonical financial rows, or data stores.
    """

    root = (
        Path(financial_engine_root)
        if financial_engine_root is not None
        else Path(__file__).resolve().parents[3]
    )
    confirmed_dir = (
        Path(confirmed_fixtures_dir)
        if confirmed_fixtures_dir is not None
        else root / "backend" / "tests" / "eval_fixtures"
    )
    real_gold_dir = (
        Path(real_gold_fixtures_dir)
        if real_gold_fixtures_dir is not None
        else root / "data" / "extraction_gold_real"
    )

    persisted_fields = _persisted_periodic_financial_metric_fields()
    extractor_fields = set(METRIC_FIELDS)
    internal_extractor_fields = _internal_extractor_metric_fields()
    evaluator_fields = _evaluator_supported_metric_fields()
    expectation_counts = _metric_expectation_counts(
        confirmed_dir=confirmed_dir,
        real_gold_dir=real_gold_dir,
    )

    specs = {spec.family: spec for spec in METRIC_CONTRACT_FAMILIES}
    rows = [
        _metric_contract_row(
            spec,
            persisted_fields=persisted_fields,
            extractor_fields=extractor_fields,
            internal_extractor_fields=internal_extractor_fields,
            evaluator_fields=evaluator_fields,
            expectation_count=expectation_counts.get(spec.family, 0),
        )
        for spec in METRIC_CONTRACT_FAMILIES
    ]

    for family, count in sorted(expectation_counts.items()):
        if family in specs:
            continue
        rows.append(
            _metric_contract_row(
                MetricContractFamily(
                    family=family,
                    canonical_field=None,
                    aliases=(),
                    notes="Observed only in fixture/gold expectations; no contract support exists.",
                ),
                persisted_fields=persisted_fields,
                extractor_fields=extractor_fields,
                internal_extractor_fields=internal_extractor_fields,
                evaluator_fields=evaluator_fields,
                expectation_count=count,
            )
        )

    rows = sorted(rows, key=lambda row: row["family"])
    status_counts = Counter(str(row["status"]) for row in rows)
    policy_assertions = {
        "total_equity_not_promoted": _row_not_promoted(rows, "total_equity"),
        "interest_expense_not_promoted": _row_not_promoted(rows, "interest_expense"),
        "broad_catalogue_not_automatically_canonical": all(
            not row["canonical_use_allowed"]
            for row in rows
            if row["family"] in {"eps", "dividends", "finance_costs", "total_assets"}
        ),
    }

    return {
        "artifact_type": METRIC_CONTRACT_ARTIFACT_TYPE,
        "profile_version": PROFILE_VERSION,
        "metric_ontology_version": METRIC_ONTOLOGY_VERSION,
        "diagnostic_only": True,
        "canonical_promotion_allowed": False,
        "sources": {
            "persisted_model": "app.models.asx_financials.ASXPeriodicFinancial",
            "extractor_output_fields": "app.services.multipass_extraction.METRIC_FIELDS",
            "internal_extractor_fields": "app.services.multipass_extraction._METRIC_SCHEMA_BY_TABLE",
            "evaluator_mapping": "app.services.extraction_gold_eval_scorecard.METRIC_NAME_MAP",
            "confirmed_fixtures_dir": str(confirmed_dir),
            "real_gold_fixtures_dir": str(real_gold_dir),
        },
        "status_class_legend": _metric_contract_status_legend(),
        "summary": {
            "metric_family_count": len(rows),
            "status_counts": {
                status.value: status_counts.get(status.value, 0)
                for status in MetricContractStatus
            },
            "persisted_metric_fields": sorted(persisted_fields),
            "extractor_output_fields": sorted(extractor_fields),
            "internal_extractor_fields": sorted(internal_extractor_fields),
            "evaluator_supported_fields": sorted(evaluator_fields),
            "gold_or_confirmed_expectation_families": dict(
                sorted(expectation_counts.items())
            ),
        },
        "policy_assertions": policy_assertions,
        "metric_rows": rows,
        "promotion_policy": (
            "A metric family is canonical-use eligible only when persisted, final "
            "extractor output, evaluator support, and explicit contract policy all agree."
        ),
        "remaining_blockers": [
            "Define source/evaluator policy before promoting persisted-only metrics.",
            "Keep broad metric-family scoring report-local until approved actual payloads exist.",
            "Keep source reviewability blocked until durable source asset resolver work is complete.",
        ],
    }


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


def build_confirmed_metric_payload_scorecard(
    fixtures_dir: str | Path,
    actual_payloads: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    financial_engine_root: str | Path | None = None,
) -> dict[str, Any]:
    """Score confirmed metric expectations against pre-supplied actual payloads.

    This builder is report-local evaluation only. It never runs extraction and
    never treats fixture/source openability as extraction correctness.
    """

    fixture_dir = Path(fixtures_dir)
    root = (
        Path(financial_engine_root)
        if financial_engine_root is not None
        else Path(__file__).resolve().parents[3]
    )
    payloads = dict(actual_payloads or {})
    actual_payload_supplied = actual_payloads is not None

    fixture_payloads = _load_fixture_payloads(fixture_dir)
    rows: list[dict[str, Any]] = []
    fixture_summaries: list[dict[str, Any]] = []
    expectations: list[CoverageExpectation] = []

    for path, fixture_payload in fixture_payloads:
        fixture_expectations = _expectations_for_payload(path, fixture_payload, root)
        expectations.extend(fixture_expectations)
        actual_payload = (
            _resolve_extracted_payload(payloads, str(fixture_payload.get("document_id") or path.stem), path)
            if actual_payload_supplied
            else None
        )
        fixture_rows = [
            _payload_score_row(
                expectation,
                actual_payload,
                actual_payload_supplied=actual_payload_supplied,
            )
            for expectation in fixture_expectations
        ]
        if actual_payload_supplied and actual_payload is not None:
            fixture_rows.extend(
                _unexpected_actual_metric_rows(
                    fixture_payload=fixture_payload,
                    fixture_path=path,
                    expectations=fixture_expectations,
                    actual_payload=actual_payload,
                    financial_engine_root=root,
                )
            )
        rows.extend(fixture_rows)
        fixture_summaries.append(
            _payload_fixture_summary(path, fixture_payload, fixture_expectations, fixture_rows)
        )

    result_class_summary = _payload_result_class_summary(rows)
    return {
        "artifact_type": "confirmed_metric_payload_scorecard_v1",
        "profile": "confirmed_metric_coverage",
        "profile_version": PROFILE_VERSION,
        "scorecard_scope": "report_local_actual_payloads_only",
        "fixtures_dir": str(fixture_dir),
        "actual_payload_supplied": actual_payload_supplied,
        "actual_payload_document_count": len(payloads),
        "total_fixture_count": len(fixture_payloads),
        "total_metric_expectations": len(expectations),
        "scored_metric_expectations": sum(1 for item in expectations if item.should_score),
        "result_class_summary": result_class_summary,
        "source_pdf_summary": _source_pdf_summary(expectations),
        "fixture_summaries": fixture_summaries,
        "metric_results": rows,
        "profile_boundaries": {
            "canonical_core": "no_regression_baseline_only",
            "expanded_required": "existing_real_gold_required_subset",
            "confirmed_metric_coverage": "broader_report_local_payload_scorecard",
            "mutates_canonical_trust": False,
            "narrow_core_is_final_product_goal": False,
        },
        "forbidden_actions": {
            "ran_production_extraction": False,
            "mutated_canonical_truth": False,
            "mutated_gold_labels": False,
            "mutated_db_qdrant_news_memory": False,
        },
    }


def build_pre_persistence_scorecard_gate(
    scorecard: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize whether a report-local payload scorecard blocks promotion.

    The gate is an evaluation-readiness artifact. It never grants canonical
    write permission and never runs extraction.
    """

    rows = [
        row
        for row in scorecard.get("metric_results", [])
        if isinstance(row, Mapping)
    ]
    result_class_summary = _gate_result_class_summary(scorecard, rows)
    actual_payload_supplied = scorecard.get("actual_payload_supplied") is True
    scored_metric_expectations = _safe_int(
        scorecard.get("scored_metric_expectations")
    )
    blocking_result_counts = {
        result_class: result_class_summary.get(result_class, 0)
        for result_class in _PRE_PERSISTENCE_BLOCKING_RESULT_CLASSES
        if result_class_summary.get(result_class, 0) > 0
    }

    blockers: list[dict[str, Any]] = []
    if not actual_payload_supplied:
        blockers.append(
            {
                "code": "actual_payload_not_supplied",
                "count": 1,
                "policy": "pre-persistence gate requires actual extracted payloads",
            }
        )
    if scored_metric_expectations <= 0:
        blockers.append(
            {
                "code": "no_scoreable_metric_expectations",
                "count": 1,
                "policy": "pre-persistence gate cannot pass without scoreable metrics",
            }
        )
    if not rows:
        blockers.append(
            {
                "code": "metric_results_missing",
                "count": 1,
                "policy": "pre-persistence gate requires metric result rows",
            }
        )
    for result_class, count in blocking_result_counts.items():
        blockers.append(
            {
                "code": result_class,
                "count": count,
                "policy": "result class blocks pre-persistence promotion",
            }
        )

    gate_passed = not blockers
    return {
        "artifact_type": PRE_PERSISTENCE_SCORECARD_GATE_VERSION,
        "gate_version": PRE_PERSISTENCE_SCORECARD_GATE_VERSION,
        "input_artifact_type": scorecard.get("artifact_type"),
        "profile": scorecard.get("profile"),
        "scorecard_scope": scorecard.get("scorecard_scope"),
        "gate_status": "pass" if gate_passed else "fail",
        "passed": gate_passed,
        "decision": "operator_review_eligible" if gate_passed else "blocked",
        "operator_approval_required_for_canary": True,
        "canonical_write_allowed": False,
        "broad_backfill_authorized": False,
        "actual_payload_supplied": actual_payload_supplied,
        "actual_payload_document_count": _safe_int(
            scorecard.get("actual_payload_document_count")
        ),
        "metric_result_count": len(rows),
        "total_metric_expectations": _safe_int(
            scorecard.get("total_metric_expectations")
        ),
        "scored_metric_expectations": scored_metric_expectations,
        "allowed_result_classes": list(_PRE_PERSISTENCE_ALLOWED_RESULT_CLASSES),
        "blocking_result_classes": list(_PRE_PERSISTENCE_BLOCKING_RESULT_CLASSES),
        "result_class_summary": result_class_summary,
        "blocking_result_class_summary": blocking_result_counts,
        "allowed_noncanonical_abstention_count": result_class_summary.get(
            PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED.value, 0
        ),
        "blockers": blockers,
        "blocking_examples": _gate_blocking_examples(rows),
        "policy_assertions": {
            "runs_extraction": False,
            "mutates_canonical_truth": False,
            "mutates_gold_labels": False,
            "mutates_db_qdrant_news_memory": False,
            "source_openability_is_correctness": False,
        },
    }


def load_source_asset_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Load and validate the metadata-only source asset manifest."""

    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"source asset manifest must be a JSON object: {path}")
    _validate_source_asset_manifest(payload)
    return payload


def resolve_source_asset_manifest(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path | None = None,
    extra_source_roots: Iterable[str | Path] | None = None,
    verify_hash: bool = True,
) -> dict[str, Any]:
    """Resolve a metadata-only source asset manifest against local candidates."""

    manifest = load_source_asset_manifest(manifest_path)
    return resolve_source_asset_manifest_payload(
        manifest,
        workspace_root=workspace_root,
        extra_source_roots=extra_source_roots,
        verify_hash=verify_hash,
    )


def resolve_source_asset_manifest_payload(
    manifest: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
    extra_source_roots: Iterable[str | Path] | None = None,
    verify_hash: bool = True,
) -> dict[str, Any]:
    """Return source asset reviewability status without scoring extraction quality."""

    _validate_source_asset_manifest(manifest)
    root = (
        Path(workspace_root).resolve(strict=False)
        if workspace_root is not None
        else Path.cwd().resolve(strict=False)
    )
    source_roots = _source_asset_roots(
        manifest,
        workspace_root=root,
        extra_source_roots=extra_source_roots,
    )

    results = [
        _resolve_source_asset_entry(
            asset,
            workspace_root=root,
            source_roots=source_roots,
            verify_hash=verify_hash,
        )
        for asset in manifest.get("assets", [])
    ]
    status_counts = {status.value: 0 for status in SourceAssetResolutionStatus}
    for result in results:
        status = str(result.get("resolution_status") or "")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "artifact_type": "source_asset_resolution_v1",
        "manifest_id": manifest.get("manifest_id"),
        "schema_version": manifest.get("schema_version"),
        "dataset": manifest.get("dataset"),
        "asset_policy": manifest.get("asset_policy"),
        "workspace_root": str(root),
        "source_roots": [
            {"root_id": root_id, "path": str(path)}
            for root_id, path in source_roots.items()
        ],
        "total_asset_count": len(results),
        "status_counts": dict(sorted(status_counts.items())),
        "reviewability_only": True,
        "source_openability_counts_as_metric_correctness": False,
        "extraction_correctness_impact": "none",
        "assets": results,
    }


def classify_terminal_extraction_candidate(
    record: Mapping[str, Any],
    *,
    current_extractor_version: str = EXTRACTOR_VERSION,
) -> dict[str, Any]:
    """Classify one read-only document metadata row for terminal-state review."""

    status = _terminal_status(record)
    extractor_version = _string_or_none(
        record.get("extractor_version") or record.get("run_extractor_version")
    )
    current_version_status = _terminal_current_version_status(
        record,
        extractor_version=extractor_version,
        current_extractor_version=current_extractor_version,
    )
    host_file_exists = _terminal_host_file_exists(record)
    has_financial_rows = _terminal_has_financial_rows(record)
    candidate_class = _terminal_candidate_class(
        status=status,
        current_version_status=current_version_status,
        host_file_exists=host_file_exists,
        has_financial_rows=has_financial_rows,
        extractor_version=extractor_version,
        current_extractor_version=current_extractor_version,
    )
    recommended_action = _terminal_recommended_action(candidate_class)

    return {
        "document_id": _string_or_none(record.get("document_id")),
        "ticker": _string_or_none(record.get("ticker")),
        "filing_document_type": _first_nonempty(
            record,
            "filing_document_type",
            "document_type",
            "filing_type",
            "doc_type",
            "doc_class",
            "doc_subtype",
        ),
        "pdf_path": _first_nonempty(record, "pdf_path", "source_file"),
        "host_file_exists": host_file_exists,
        "extraction_status": status,
        "current_version_status": current_version_status,
        "extractor_version": extractor_version,
        "current_extractor_version": current_extractor_version,
        "prior_error_status_reason": _first_nonempty(
            record,
            "prior_error_status_reason",
            "prior_error",
            "status_reason",
            "failure_code",
            "error",
        ),
        "candidate_class": candidate_class.value,
        "recommended_action": recommended_action.value,
        "required_preconditions": _terminal_required_preconditions(candidate_class),
        "source_asset_manifest_link": _source_asset_manifest_link(record),
        "scorecard_readiness_notes": _terminal_scorecard_readiness_notes(
            candidate_class
        ),
        "source_reviewability_only": True,
        "source_openability_counts_as_metric_correctness": False,
        "terminal_state_counts_as_metric_correctness": False,
        "payload_scoreability_counts_as_terminal_state": False,
        "broad_backfill_authorized": False,
    }


def build_terminal_extraction_candidate_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    current_extractor_version: str = EXTRACTOR_VERSION,
    manifest_scope: str = "report_local_terminal_state_candidate_manifest",
    input_sources: Iterable[str] | None = None,
    context: Mapping[str, Any] | None = None,
    data_missing: Iterable[str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a report-local terminal extraction candidate manifest.

    The manifest is a triage artifact only. It never authorizes broad backfill
    and it does not score extraction correctness.
    """

    rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    for record in records:
        exclusion = _terminal_extraction_exclusion(
            record,
            current_extractor_version=current_extractor_version,
        )
        if exclusion is not None:
            excluded_rows.append(exclusion)
            continue
        rows.append(
            classify_terminal_extraction_candidate(
                record,
                current_extractor_version=current_extractor_version,
            )
        )
    class_counts = {status.value: 0 for status in TerminalExtractionCandidateClass}
    action_counts = {action.value: 0 for action in TerminalExtractionRecommendedAction}
    for row in rows:
        row_class = str(row.get("candidate_class") or "")
        action = str(row.get("recommended_action") or "")
        class_counts[row_class] = class_counts.get(row_class, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1
    exclusion_reason_counts: dict[str, int] = {}
    for row in excluded_rows:
        reason = str(row.get("exclusion_reason") or "")
        exclusion_reason_counts[reason] = exclusion_reason_counts.get(reason, 0) + 1

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "artifact_type": "terminal_extraction_candidate_manifest_v1",
        "schema_version": 1,
        "manifest_scope": manifest_scope,
        "generated_at": generated_at,
        "current_extractor_version": current_extractor_version,
        "production_data_access": False,
        "broad_backfill_authorized": False,
        "source_reviewability_separate_from_extraction_correctness": True,
        "payload_scoreability_separate_from_terminal_state": True,
        "source_openability_counts_as_metric_correctness": False,
        "terminal_state_counts_as_metric_correctness": False,
        "input_sources": list(input_sources or []),
        "context": dict(context or {}),
        "data_missing": list(data_missing or []),
        "total_input_document_count": len(rows) + len(excluded_rows),
        "total_document_count": len(rows) + len(excluded_rows),
        "candidate_document_count": len(rows),
        "excluded_document_count": len(excluded_rows),
        "exclusion_reason_counts": dict(sorted(exclusion_reason_counts.items())),
        "exclusion_reason_definitions": dict(
            sorted(TERMINAL_EXTRACTION_EXCLUSION_REASON_DEFINITIONS.items())
        ),
        "candidate_class_counts": dict(sorted(class_counts.items())),
        "recommended_action_counts": dict(sorted(action_counts.items())),
        "candidate_class_definitions": dict(
            sorted(TERMINAL_EXTRACTION_CLASS_DEFINITIONS.items())
        ),
        "recommended_action_definitions": dict(
            sorted(TERMINAL_EXTRACTION_RECOMMENDED_ACTION_DEFINITIONS.items())
        ),
        "excluded_candidates": excluded_rows,
        "candidates": rows,
    }


def terminal_extraction_candidate_manifest_to_csv(
    manifest: Mapping[str, Any],
) -> str:
    """Render terminal extraction candidates as deterministic CSV text."""

    fieldnames = [
        "document_id",
        "ticker",
        "filing_document_type",
        "pdf_path",
        "host_file_exists",
        "extraction_status",
        "current_version_status",
        "extractor_version",
        "current_extractor_version",
        "prior_error_status_reason",
        "candidate_class",
        "recommended_action",
        "required_preconditions",
        "source_asset_manifest_link",
        "scorecard_readiness_notes",
        "source_openability_counts_as_metric_correctness",
        "terminal_state_counts_as_metric_correctness",
        "payload_scoreability_counts_as_terminal_state",
        "broad_backfill_authorized",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in manifest.get("candidates", []):
        if not isinstance(row, Mapping):
            continue
        writer.writerow(
            {
                field: _csv_cell(row.get(field))
                for field in fieldnames
            }
        )
    return output.getvalue()


def _validate_source_asset_manifest(manifest: Mapping[str, Any]) -> None:
    required_keys = {
        "schema_version",
        "manifest_id",
        "dataset",
        "asset_policy",
        "source_roots",
        "assets",
    }
    missing = sorted(key for key in required_keys if key not in manifest)
    if missing:
        raise ValueError(f"source asset manifest missing keys: {', '.join(missing)}")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("source asset manifest assets must be a list")
    source_roots = manifest.get("source_roots")
    if not isinstance(source_roots, list):
        raise ValueError("source asset manifest source_roots must be a list")

    asset_ids: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise ValueError(f"source asset at index {index} must be an object")
        asset_id = str(asset.get("asset_id") or "").strip()
        if not asset_id:
            raise ValueError(f"source asset at index {index} is missing asset_id")
        if asset_id in asset_ids:
            raise ValueError(f"duplicate source asset_id: {asset_id}")
        asset_ids.add(asset_id)
        candidates = asset.get("local_candidate_paths")
        if not isinstance(candidates, list) or not all(
            isinstance(candidate, str) for candidate in candidates
        ):
            raise ValueError(
                f"source asset {asset_id} local_candidate_paths must be a string list"
            )
        for field in ("sha256", "size_bytes"):
            value = asset.get(field)
            if value is not None and field == "sha256":
                _validate_sha256(asset_id, value)
            if value is not None and field == "size_bytes":
                _validate_size(asset_id, value)


def _source_asset_roots(
    manifest: Mapping[str, Any],
    *,
    workspace_root: Path,
    extra_source_roots: Iterable[str | Path] | None,
) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for entry in manifest.get("source_roots", []):
        if not isinstance(entry, Mapping):
            raise ValueError("source_roots entries must be objects")
        root_id = str(entry.get("root_id") or "").strip()
        root_path = str(entry.get("path") or "").strip()
        if not root_id or not root_path:
            raise ValueError("source_roots entries require root_id and path")
        roots[root_id] = _resolve_manifest_path(root_path, workspace_root)

    for index, root_path in enumerate(extra_source_roots or ()):
        roots[f"extra_{index}"] = _resolve_manifest_path(
            str(root_path),
            workspace_root,
        )
    return roots


def _resolve_source_asset_entry(
    asset: Mapping[str, Any],
    *,
    workspace_root: Path,
    source_roots: Mapping[str, Path],
    verify_hash: bool,
) -> dict[str, Any]:
    issues: list[str] = []
    candidate_results: list[dict[str, Any]] = []
    selected: tuple[str | None, Path] | None = None

    for raw_candidate in asset.get("local_candidate_paths", []):
        candidate = str(raw_candidate or "").strip()
        try:
            path = _safe_source_candidate_path(candidate, workspace_root)
            root_id = _matching_source_root(path, source_roots)
            if root_id is None:
                raise PermissionError("candidate path is outside source roots")
        except (ValueError, PermissionError) as exc:
            candidate_results.append(
                {
                    "candidate_path": candidate,
                    "safe": False,
                    "exists": False,
                    "root_id": None,
                    "issue": str(exc),
                }
            )
            issues.append(f"{candidate}: {exc}")
            continue

        exists = path.exists() and path.is_file()
        candidate_results.append(
            {
                "candidate_path": candidate,
                "resolved_path": str(path),
                "safe": True,
                "exists": exists,
                "root_id": root_id,
            }
        )
        if exists and selected is None:
            selected = (root_id, path)

    if selected is None:
        status = (
            SourceAssetResolutionStatus.MANIFEST_ERROR
            if issues and not any(item.get("safe") for item in candidate_results)
            else SourceAssetResolutionStatus.MISSING
        )
        return _source_asset_result(
            asset,
            status=status,
            matched_path=None,
            root_id=None,
            candidate_results=candidate_results,
            actual_size_bytes=None,
            actual_sha256=None,
            size_status="not_checked",
            sha256_status="not_checked",
            issues=issues or _missing_issues(asset),
        )

    root_id, path = selected
    actual_size = path.stat().st_size
    expected_size = asset.get("size_bytes")
    expected_sha = asset.get("sha256")
    size_status = _metadata_match_status(expected_size, actual_size)
    actual_sha = None
    sha_status = "not_provided"
    if expected_sha is not None and verify_hash:
        actual_sha = _sha256_file(path)
        sha_status = "matched" if str(expected_sha).lower() == actual_sha else "mismatch"
    elif expected_sha is not None:
        sha_status = "not_checked"

    if size_status == "mismatch" or sha_status == "mismatch":
        status = SourceAssetResolutionStatus.PRESENT_METADATA_MISMATCH
        if size_status == "mismatch":
            issues.append("size_bytes mismatch")
        if sha_status == "mismatch":
            issues.append("sha256 mismatch")
    elif expected_size is not None or (expected_sha is not None and verify_hash):
        status = SourceAssetResolutionStatus.PRESENT_VERIFIED
    else:
        status = SourceAssetResolutionStatus.PRESENT_UNVERIFIED

    return _source_asset_result(
        asset,
        status=status,
        matched_path=path,
        root_id=root_id,
        candidate_results=candidate_results,
        actual_size_bytes=actual_size,
        actual_sha256=actual_sha,
        size_status=size_status,
        sha256_status=sha_status,
        issues=issues,
    )


def _source_asset_result(
    asset: Mapping[str, Any],
    *,
    status: SourceAssetResolutionStatus,
    matched_path: Path | None,
    root_id: str | None,
    candidate_results: list[dict[str, Any]],
    actual_size_bytes: int | None,
    actual_sha256: str | None,
    size_status: str,
    sha256_status: str,
    issues: list[str],
) -> dict[str, Any]:
    return {
        "asset_id": asset.get("asset_id"),
        "ticker": asset.get("ticker"),
        "document_id": asset.get("document_id"),
        "fixture_id": asset.get("fixture_id"),
        "source_kind": asset.get("source_kind"),
        "expected_filename": asset.get("expected_filename"),
        "logical_source_name": asset.get("logical_source_name"),
        "reviewability_status": asset.get("reviewability_status"),
        "missing_reason": asset.get("missing_reason"),
        "resolution_status": status.value,
        "present": matched_path is not None,
        "matched_path": str(matched_path) if matched_path is not None else None,
        "resolved_root_id": root_id,
        "expected_size_bytes": asset.get("size_bytes"),
        "actual_size_bytes": actual_size_bytes,
        "size_bytes_status": size_status,
        "expected_sha256": asset.get("sha256"),
        "actual_sha256": actual_sha256,
        "sha256_status": sha256_status,
        "candidate_results": candidate_results,
        "issues": issues,
        "reviewability_only": True,
        "source_openability_counts_as_metric_correctness": False,
    }


def _resolve_manifest_path(raw_path: str, workspace_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve(strict=False)
    return (workspace_root / path).resolve(strict=False)


def _safe_source_candidate_path(candidate: str, workspace_root: Path) -> Path:
    if not candidate:
        raise ValueError("candidate path is empty")
    if "\x00" in candidate:
        raise ValueError("candidate path contains NUL")
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("candidate path must be local")
    if "\\" in candidate:
        raise ValueError("candidate path must use POSIX separators")
    path = Path(candidate)
    if path.suffix.lower() != ".pdf":
        raise ValueError("candidate path must reference a PDF")
    if path.is_absolute():
        return path.resolve(strict=False)
    posix_path = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in posix_path.parts):
        raise ValueError("candidate path must be a safe relative path")
    return (workspace_root / posix_path.as_posix()).resolve(strict=False)


def _matching_source_root(path: Path, source_roots: Mapping[str, Path]) -> str | None:
    for root_id, root in source_roots.items():
        try:
            path.relative_to(root)
            return root_id
        except ValueError:
            continue
    return None


def _metadata_match_status(expected: Any, actual: int) -> str:
    if expected is None:
        return "not_provided"
    return "matched" if int(expected) == actual else "mismatch"


def _validate_sha256(asset_id: str, value: Any) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"source asset {asset_id} sha256 must be a 64-char hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(
            f"source asset {asset_id} sha256 must be a 64-char hex string"
        ) from exc


def _validate_size(asset_id: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"source asset {asset_id} size_bytes must be a non-negative int")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _missing_issues(asset: Mapping[str, Any]) -> list[str]:
    missing_reason = str(asset.get("missing_reason") or "").strip()
    if missing_reason:
        return [missing_reason]
    return ["DATA_MISSING: no local source PDF candidate exists"]


def _terminal_status(record: Mapping[str, Any]) -> str | None:
    return _string_or_none(
        record.get("extraction_status")
        or record.get("terminal_status")
        or record.get("run_status")
        or record.get("status")
    )


def _terminal_current_version_status(
    record: Mapping[str, Any],
    *,
    extractor_version: str | None,
    current_extractor_version: str,
) -> str:
    explicit = _string_or_none(record.get("current_version_status"))
    if explicit is not None:
        return explicit

    has_current_terminal = _coerce_optional_bool(record.get("has_current_terminal_run"))
    if has_current_terminal is True:
        return "current_version_terminal_run"
    if has_current_terminal is False:
        return "no_current_terminal_run"

    if extractor_version is None:
        return "DATA_MISSING"
    if extractor_version == current_extractor_version:
        return "current_version"
    return "stale_version"


def _terminal_host_file_exists(record: Mapping[str, Any]) -> bool | None:
    direct = _coerce_optional_bool(record.get("host_file_exists"))
    if direct is not None:
        return direct

    source_resolution = _string_or_none(record.get("source_asset_resolution_status"))
    if source_resolution in {
        SourceAssetResolutionStatus.PRESENT_VERIFIED.value,
        SourceAssetResolutionStatus.PRESENT_UNVERIFIED.value,
        SourceAssetResolutionStatus.PRESENT_METADATA_MISMATCH.value,
    }:
        return True
    if source_resolution == SourceAssetResolutionStatus.MISSING.value:
        return False
    return None


def _terminal_has_financial_rows(record: Mapping[str, Any]) -> bool | None:
    for key in ("has_financial_rows", "financial_rows_exist"):
        value = _coerce_optional_bool(record.get(key))
        if value is not None:
            return value

    for key in (
        "financial_rows_written",
        "financial_row_count",
        "persisted_financial_rows",
        "rows_count",
        "row_count",
    ):
        if key not in record:
            continue
        value = record.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        text = str(value or "").strip()
        if text.isdigit():
            return int(text) > 0
    return None


def _terminal_extraction_exclusion(
    record: Mapping[str, Any],
    *,
    current_extractor_version: str,
) -> dict[str, Any] | None:
    title = _terminal_advisory_title(record)
    first_page_text = _terminal_advisory_first_page_text(record)
    source_classification = classify_source_document(title, first_page_text)
    if source_classification.extraction_candidate_allowed:
        return None

    return {
        "document_id": _string_or_none(record.get("document_id")),
        "ticker": _string_or_none(record.get("ticker")),
        "filing_document_type": _first_nonempty(
            record,
            "filing_document_type",
            "document_type",
            "filing_type",
            "doc_type",
            "doc_class",
            "doc_subtype",
        ),
        "pdf_path": _first_nonempty(record, "pdf_path", "source_file"),
        "title": title,
        "current_extractor_version": current_extractor_version,
        "exclusion_reason": source_classification.reason,
        "quarantine_reason": source_classification.reason,
        "source_document_gate": source_classification.reason,
        "source_document_classification": source_classification.to_dict(),
        "recommended_action": "exclude_from_canary_candidate_manifest",
        "required_preconditions": [
            "manifest_is_report_local_only",
            "broad_backfill_not_authorized",
            "do_not_submit_to_canary_from_this_manifest",
            "operator_review_required_before_any_extraction_decision",
        ],
        "reason_detail": (
            "Title or first-page metadata matched the shared advisory-only "
            "document gate."
        ),
        "source_reviewability_only": True,
        "source_openability_counts_as_metric_correctness": False,
        "terminal_state_counts_as_metric_correctness": False,
        "payload_scoreability_counts_as_terminal_state": False,
        "broad_backfill_authorized": False,
    }


def _terminal_advisory_title(record: Mapping[str, Any]) -> str | None:
    return _first_nonempty(
        record,
        "title",
        "announcement_title",
        "document_title",
        "headline",
        "name",
    )


def _terminal_advisory_first_page_text(record: Mapping[str, Any]) -> str | None:
    direct = _first_nonempty(
        record,
        "first_page_text",
        "first_page",
        "source_text",
        "document_text",
        "text",
        "description",
    )
    if direct is not None:
        return direct

    sections = record.get("sections")
    if not isinstance(sections, list):
        return None

    page_text: list[str] = []
    fallback_text: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        text = _string_or_none(section.get("text"))
        if text is None:
            continue
        fallback_text.append(text)
        page = section.get("page")
        if isinstance(page, bool):
            continue
        if isinstance(page, (int, float)) and page <= 1:
            page_text.append(text)

    if page_text:
        return " ".join(page_text)
    if fallback_text:
        return " ".join(fallback_text[:3])
    return None


def _terminal_candidate_class(
    *,
    status: str | None,
    current_version_status: str,
    host_file_exists: bool | None,
    has_financial_rows: bool | None,
    extractor_version: str | None,
    current_extractor_version: str,
) -> TerminalExtractionCandidateClass:
    if status in _ACTIVE_OR_OWNERSHIP_STATUSES:
        return TerminalExtractionCandidateClass.QUEUED_RUNNING_ORPHANED

    stale = (
        "stale" in current_version_status
        or (
            extractor_version is not None
            and extractor_version != current_extractor_version
        )
    )
    if stale and status in {
        *_COMPLETED_STATUSES,
        *_FAILED_STATUSES,
        "skipped",
    }:
        return TerminalExtractionCandidateClass.STALE_EXTRACTOR_VERSION

    if status in _COMPLETED_STATUSES:
        if has_financial_rows is True:
            return TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS
        if has_financial_rows is False:
            return TerminalExtractionCandidateClass.COMPLETED_WITHOUT_ROWS
        return TerminalExtractionCandidateClass.UNKNOWN_NEEDS_AUDIT

    if status == "skipped":
        return TerminalExtractionCandidateClass.SKIPPED

    if status in _FAILED_STATUSES:
        return TerminalExtractionCandidateClass.FAILED_PARSER_ERROR

    if host_file_exists is False:
        return TerminalExtractionCandidateClass.MISSING_HOST_FILE

    if host_file_exists is True and (
        status is None
        or current_version_status in {"no_current_terminal_run", "missing"}
    ):
        return TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN

    return TerminalExtractionCandidateClass.UNKNOWN_NEEDS_AUDIT


def _terminal_recommended_action(
    candidate_class: TerminalExtractionCandidateClass,
) -> TerminalExtractionRecommendedAction:
    if candidate_class == TerminalExtractionCandidateClass.MISSING_HOST_FILE:
        return TerminalExtractionRecommendedAction.BLOCKED_MISSING_ASSET
    if candidate_class == TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN:
        return TerminalExtractionRecommendedAction.CANARY_CANDIDATE
    if candidate_class in {
        TerminalExtractionCandidateClass.STALE_EXTRACTOR_VERSION,
        TerminalExtractionCandidateClass.FAILED_PARSER_ERROR,
    }:
        return TerminalExtractionRecommendedAction.RETRY_CANDIDATE
    if candidate_class in {
        TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS,
        TerminalExtractionCandidateClass.SKIPPED,
    }:
        return TerminalExtractionRecommendedAction.SKIP
    return TerminalExtractionRecommendedAction.REVIEW


def _terminal_required_preconditions(
    candidate_class: TerminalExtractionCandidateClass,
) -> list[str]:
    shared = ["manifest_is_report_local_only", "broad_backfill_not_authorized"]
    if candidate_class == TerminalExtractionCandidateClass.MISSING_HOST_FILE:
        return [
            *shared,
            "repair_or_review_source_asset_before_any_extraction",
            "source_asset_reviewability_does_not_imply_metric_correctness",
        ]
    if candidate_class == TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN:
        return [
            *shared,
            "operator_approval_required_for_bounded_canary",
            "confirm_source_asset_reviewability",
            "confirm_metric_contract_and_scorecard_readiness",
        ]
    if candidate_class == TerminalExtractionCandidateClass.STALE_EXTRACTOR_VERSION:
        return [
            *shared,
            "operator_approval_required_for_versioned_retry",
            "confirm_prior_run_is_not_current_version",
            "confirm_source_asset_reviewability",
        ]
    if candidate_class == TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS:
        return [
            *shared,
            "do_not_requeue_from_this_manifest",
            "use_payload_scorecard_for_correctness_review",
        ]
    if candidate_class == TerminalExtractionCandidateClass.COMPLETED_WITHOUT_ROWS:
        return [
            *shared,
            "review_completed_run_without_rows_before_retry",
            "confirm_whether_zero_rows_is_expected_for_document_type",
        ]
    if candidate_class == TerminalExtractionCandidateClass.SKIPPED:
        return [
            *shared,
            "review_skip_reason_before_override",
            "do_not_requeue_intentional_skips_by_default",
        ]
    if candidate_class == TerminalExtractionCandidateClass.FAILED_PARSER_ERROR:
        return [
            *shared,
            "separate_transient_retry_from_deterministic_parser_failure",
            "operator_approval_required_for_bounded_retry",
            "confirm_source_asset_reviewability",
        ]
    if candidate_class == TerminalExtractionCandidateClass.QUEUED_RUNNING_ORPHANED:
        return [
            *shared,
            "clear_scheduler_or_queue_ownership_before_any_retry",
            "do_not_duplicate_running_or_orphaned_work",
        ]
    return [
        *shared,
        "read_only_db_metadata_needed_or_existing_audit_manifest_required",
        "operator_review_required_before_any_extraction_decision",
    ]


def _terminal_scorecard_readiness_notes(
    candidate_class: TerminalExtractionCandidateClass,
) -> str:
    if candidate_class == TerminalExtractionCandidateClass.COMPLETED_WITH_ROWS:
        return (
            "terminal state is complete; correctness still requires #97 payload "
            "scorecard actuals, #98 metric contract parity, and #99 source "
            "reviewability"
        )
    if candidate_class == TerminalExtractionCandidateClass.COMPLETED_WITHOUT_ROWS:
        return "not payload-scorecard ready until zero-row anomaly is reviewed"
    if candidate_class in {
        TerminalExtractionCandidateClass.FILE_EXISTS_NO_CURRENT_TERMINAL_RUN,
        TerminalExtractionCandidateClass.STALE_EXTRACTOR_VERSION,
        TerminalExtractionCandidateClass.FAILED_PARSER_ERROR,
    }:
        return (
            "not payload-scorecard ready until an operator-approved bounded run "
            "produces extracted actuals"
        )
    if candidate_class == TerminalExtractionCandidateClass.MISSING_HOST_FILE:
        return "blocked before scorecard readiness because source asset is missing"
    if candidate_class == TerminalExtractionCandidateClass.SKIPPED:
        return "skip state is terminal triage only; payload correctness is not inferred"
    return "DATA_MISSING: scorecard readiness cannot be inferred from supplied metadata"


def _source_asset_manifest_link(record: Mapping[str, Any]) -> str | None:
    explicit = _string_or_none(record.get("source_asset_manifest_link"))
    if explicit is not None:
        return explicit
    asset_id = _string_or_none(record.get("source_asset_id") or record.get("asset_id"))
    if asset_id is None:
        return None
    return (
        "financial-engine_v2/backend/tests/eval_source_assets/"
        f"confirmed_metric_coverage_source_assets.json#asset_id={asset_id}"
    )


def _first_nonempty(record: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _string_or_none(record.get(key))
        if value is not None:
            return value
    return None


def _string_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text.lower() if text.lower() in {
        *_ACTIVE_OR_OWNERSHIP_STATUSES,
        *_COMPLETED_STATUSES,
        *_FAILED_STATUSES,
        "skipped",
    } else text


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return str(value)


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


def _persisted_periodic_financial_metric_fields() -> set[str]:
    from app.models.asx_financials import ASXPeriodicFinancial

    return {
        column.name
        for column in ASXPeriodicFinancial.__table__.columns
        if column.name not in PERSISTED_METRIC_FIELD_EXCLUSIONS
    }


def _internal_extractor_metric_fields() -> set[str]:
    from app.services import multipass_extraction

    schema = getattr(multipass_extraction, "_METRIC_SCHEMA_BY_TABLE", {})
    fields: set[str] = set()
    if isinstance(schema, Mapping):
        for values in schema.values():
            if isinstance(values, IterableABC) and not isinstance(values, str):
                fields.update(str(value) for value in values)
    return fields - set(METRIC_FIELDS)


def _evaluator_supported_metric_fields() -> set[str]:
    return set(METRIC_FIELDS) | {
        canonical
        for canonical in METRIC_NAME_MAP.values()
        if canonical in METRIC_FIELDS
    }


def _metric_expectation_counts(
    *,
    confirmed_dir: Path,
    real_gold_dir: Path,
) -> Counter[str]:
    lookup = _metric_family_lookup()
    counts: Counter[str] = Counter()
    for fixture_dir in (confirmed_dir, real_gold_dir):
        counts.update(_fixture_metric_counts(fixture_dir, lookup))
    return counts


def _fixture_metric_counts(
    fixture_dir: Path,
    lookup: Mapping[str, str],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not fixture_dir.exists():
        return counts

    for path in sorted(fixture_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            continue
        raw_metrics = payload.get("metrics", {})
        if not isinstance(raw_metrics, Mapping):
            raw_metrics = {}
        expected_nulls = payload.get("expected_nulls", [])
        if not isinstance(expected_nulls, list):
            expected_nulls = []

        ordered_names = [str(metric) for metric in raw_metrics]
        for metric in expected_nulls:
            if isinstance(metric, str) and metric not in ordered_names:
                ordered_names.append(metric)

        for metric in ordered_names:
            counts[_normalise_contract_family(metric, lookup)] += 1
    return counts


def _metric_family_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in METRIC_CONTRACT_FAMILIES:
        names = (spec.family, *spec.aliases)
        if spec.canonical_field is not None:
            names = (*names, spec.canonical_field)
        for name in names:
            lookup[_normalise_metric_name(name)] = spec.family
    for alias, canonical in METRIC_NAME_MAP.items():
        lookup.setdefault(
            _normalise_metric_name(alias),
            lookup.get(_normalise_metric_name(canonical), canonical),
        )
    return lookup


def _normalise_contract_family(metric: str, lookup: Mapping[str, str]) -> str:
    normalised = _normalise_metric_name(metric)
    return lookup.get(normalised, normalised)


def _normalise_metric_name(metric: str) -> str:
    return metric.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def _metric_contract_row(
    spec: MetricContractFamily,
    *,
    persisted_fields: set[str],
    extractor_fields: set[str],
    internal_extractor_fields: set[str],
    evaluator_fields: set[str],
    expectation_count: int,
) -> dict[str, Any]:
    canonical = spec.canonical_field
    persisted = canonical in persisted_fields if canonical is not None else False
    extractor_supported = canonical in extractor_fields if canonical is not None else False
    internal_extractor_supported = (
        canonical in internal_extractor_fields if canonical is not None else False
    )
    evaluator_supported = canonical in evaluator_fields if canonical is not None else False
    gold_or_confirmed = expectation_count > 0
    status = _metric_contract_status(
        persisted=persisted,
        extractor_supported=extractor_supported,
        internal_extractor_supported=internal_extractor_supported,
        evaluator_supported=evaluator_supported,
        gold_or_confirmed=gold_or_confirmed,
        planned=spec.planned,
        internal_only=spec.internal_only,
        ambiguous_requires_policy=spec.ambiguous_requires_policy,
    )
    canonical_use_allowed = status == MetricContractStatus.SUPPORTED
    return {
        "family": spec.family,
        "canonical_field": canonical,
        "aliases": list(spec.aliases),
        "status": status.value,
        "persisted": persisted,
        "persisted_field": canonical if persisted else None,
        "extractor_supported": extractor_supported,
        "extractor_output_field": canonical if extractor_supported else None,
        "internal_extractor_supported": internal_extractor_supported,
        "internal_extractor_field": canonical if internal_extractor_supported else None,
        "evaluator_supported": evaluator_supported,
        "gold_or_confirmed_expectation_count": expectation_count,
        "gold_or_confirmed_family": gold_or_confirmed,
        "planned": spec.planned,
        "internal_only": spec.internal_only,
        "ambiguous_requires_policy": spec.ambiguous_requires_policy,
        "canonical_use_allowed": canonical_use_allowed,
        "promotion_gate": _metric_contract_promotion_gate(status),
        "notes": spec.notes,
    }


def _metric_contract_row_for_actual_metric(metric_name: str) -> dict[str, Any]:
    lookup = _metric_family_lookup()
    family = _normalise_contract_family(metric_name, lookup)
    spec = next(
        (
            candidate
            for candidate in METRIC_CONTRACT_FAMILIES
            if candidate.family == family
        ),
        None,
    )
    if spec is None:
        canonical_field = metric_name if metric_name in METRIC_FIELDS else None
        spec = MetricContractFamily(
            family=family,
            canonical_field=canonical_field,
            aliases=(),
            notes="Observed only in actual payload metrics; no contract family exists.",
        )

    return _metric_contract_row(
        spec,
        persisted_fields=_persisted_periodic_financial_metric_fields(),
        extractor_fields=set(METRIC_FIELDS),
        internal_extractor_fields=_internal_extractor_metric_fields(),
        evaluator_fields=_evaluator_supported_metric_fields(),
        expectation_count=0,
    )


def _metric_contract_status(
    *,
    persisted: bool,
    extractor_supported: bool,
    internal_extractor_supported: bool,
    evaluator_supported: bool,
    gold_or_confirmed: bool,
    planned: bool,
    internal_only: bool,
    ambiguous_requires_policy: bool,
) -> MetricContractStatus:
    if ambiguous_requires_policy:
        return MetricContractStatus.AMBIGUOUS_REQUIRES_POLICY
    if internal_only or internal_extractor_supported:
        return MetricContractStatus.INTERNAL_ONLY
    if planned:
        return MetricContractStatus.PLANNED
    if persisted and extractor_supported and evaluator_supported:
        return MetricContractStatus.SUPPORTED
    if persisted and not extractor_supported and not evaluator_supported:
        return MetricContractStatus.PERSISTED_ONLY
    if gold_or_confirmed and not persisted and not extractor_supported and not evaluator_supported:
        return MetricContractStatus.GOLD_ONLY
    if extractor_supported and not persisted:
        return MetricContractStatus.EXTRACTOR_SUPPORTED
    if evaluator_supported and not persisted and not extractor_supported:
        return MetricContractStatus.EVALUATOR_SUPPORTED
    return MetricContractStatus.UNSUPPORTED


def _metric_contract_promotion_gate(status: MetricContractStatus) -> str:
    if status == MetricContractStatus.SUPPORTED:
        return "eligible_for_report_local_scoring; canonical use still requires source evidence per fixture"
    if status == MetricContractStatus.PERSISTED_ONLY:
        return "do_not_promote_until_extractor_and_evaluator_contracts_exist"
    if status == MetricContractStatus.INTERNAL_ONLY:
        return "do_not_surface_as_canonical_metric"
    if status == MetricContractStatus.PLANNED:
        return "future_metric_requires_source_extractor_evaluator_contract"
    if status == MetricContractStatus.GOLD_ONLY:
        return "fixture_label_requires_contract_review_before_scoring"
    if status == MetricContractStatus.AMBIGUOUS_REQUIRES_POLICY:
        return "requires_semantic_policy_before_mapping_or_scoring"
    if status == MetricContractStatus.EXTRACTOR_SUPPORTED:
        return "requires_persistence_and_evaluator_contract_before_canonical_use"
    if status == MetricContractStatus.EVALUATOR_SUPPORTED:
        return "requires_extractor_and_persistence_contract_before_canonical_use"
    return "unsupported; do_not_score_or_promote"


def _row_not_promoted(rows: Iterable[Mapping[str, Any]], family: str) -> bool:
    for row in rows:
        if row.get("family") == family:
            return (
                row.get("status") == MetricContractStatus.PERSISTED_ONLY.value
                and row.get("canonical_use_allowed") is False
                and row.get("extractor_supported") is False
                and row.get("evaluator_supported") is False
            )
    return False


def _metric_contract_status_legend() -> dict[str, str]:
    return {
        MetricContractStatus.SUPPORTED.value: (
            "Persisted, final extractor output, and evaluator support all exist."
        ),
        MetricContractStatus.EXTRACTOR_SUPPORTED.value: (
            "Final extractor output exists, but another canonical gate is missing."
        ),
        MetricContractStatus.EVALUATOR_SUPPORTED.value: (
            "Evaluator support exists, but extractor or persistence support is missing."
        ),
        MetricContractStatus.PERSISTED_ONLY.value: (
            "Database/model field exists, but final extractor and evaluator support do not."
        ),
        MetricContractStatus.GOLD_ONLY.value: (
            "Fixture/gold expectation exists without explicit contract support."
        ),
        MetricContractStatus.PLANNED.value: (
            "Long-term metric candidate with no current canonical support."
        ),
        MetricContractStatus.INTERNAL_ONLY.value: (
            "Internal extractor capture only; not final payload or canonical metric."
        ),
        MetricContractStatus.UNSUPPORTED.value: "No current contract support.",
        MetricContractStatus.AMBIGUOUS_REQUIRES_POLICY.value: (
            "Semantic mapping is unresolved and requires policy before scoring."
        ),
    }


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


def _payload_score_row(
    expectation: CoverageExpectation,
    actual_payload: Mapping[str, Any] | None,
    *,
    actual_payload_supplied: bool,
) -> dict[str, Any]:
    context = _actual_context(actual_payload)
    expected_context = _expectation_context(expectation)
    result_class, reason, actual_value, evidence_available = _payload_result(
        expectation,
        actual_payload,
        actual_payload_supplied=actual_payload_supplied,
        expected_context=expected_context,
    )
    extraction_correctness_status = _payload_correctness_status(result_class)
    return {
        "fixture_id": expectation.fixture_id,
        "document_id": expectation.document_id,
        "fixture": expectation.fixture_name,
        "metric_name": expectation.metric_name,
        "canonical_field": expectation.canonical_field,
        "expectation_type": expectation.expectation_type,
        "expected_value": expectation.expected_value,
        "actual_value": actual_value,
        "tolerance": expectation.tolerance,
        "support_status": expectation.support_status.value,
        "source_status": expectation.source_status.value,
        "source_pdf_exists": expectation.source_pdf_exists,
        "source_openability_is_correctness": False,
        "evidence_available": evidence_available,
        "expected_context": expected_context,
        "actual_context": context,
        "result_class": result_class.value,
        "extraction_correctness_status": extraction_correctness_status,
        "score": _payload_score(result_class),
        "reason": reason,
        "tier": expectation.tier,
        "recommendation": expectation.recommendation,
    }


def _unexpected_actual_metric_rows(
    *,
    fixture_payload: Mapping[str, Any],
    fixture_path: Path,
    expectations: list[CoverageExpectation],
    actual_payload: Mapping[str, Any],
    financial_engine_root: Path,
) -> list[dict[str, Any]]:
    metrics = _normalized_actual_metric_items(actual_payload)
    if not metrics:
        return []

    expected_keys = _expected_actual_metric_keys(expectations)
    fixture_id = str(fixture_payload.get("document_id") or fixture_path.stem)
    source_status = classify_fixture_source_status(fixture_payload)
    source_pdf_exists = (
        expectations[0].source_pdf_exists
        if expectations
        else _source_pdf_exists(fixture_payload, financial_engine_root)
    )
    expected_context = {
        "period_end": str_or_none(fixture_payload.get("period_end")),
        "period_type": str_or_none(fixture_payload.get("period_type")),
        "currency": str_or_none(fixture_payload.get("currency")),
        "scale": str_or_none(fixture_payload.get("scale")),
    }
    actual_context = _actual_context(actual_payload)

    rows: list[dict[str, Any]] = []
    for metric_name, raw_value in sorted(metrics.items()):
        normalized_metric = _normalise_metric_name(metric_name)
        if normalized_metric in expected_keys:
            continue

        actual_value, supplied = _actual_metric_supplied_value(raw_value)
        if not supplied:
            continue

        contract_row = _metric_contract_row_for_actual_metric(metric_name)
        result_class = (
            PayloadScoreStatus.MISSING_EVIDENCE
            if contract_row.get("canonical_use_allowed") is True
            else PayloadScoreStatus.AMBIGUOUS_QUARANTINED
        )
        if contract_row.get("canonical_use_allowed") is True:
            reason = (
                "Actual payload supplied a source-supported metric that has no "
                "fixture expectation in this scorecard"
            )
        else:
            reason = (
                "Actual payload supplied a metric outside the approved canonical "
                "contract for this scorecard"
            )

        canonical_field = contract_row.get("canonical_field")
        canonical_field_text = (
            str(canonical_field) if isinstance(canonical_field, str) else None
        )
        rows.append(
            {
                "fixture_id": fixture_id,
                "document_id": fixture_id,
                "fixture": fixture_path.name,
                "metric_name": metric_name,
                "canonical_field": canonical_field_text,
                "expectation_type": "unexpected_actual_metric",
                "expected_value": None,
                "actual_value": actual_value,
                "tolerance": 0.0,
                "support_status": "unexpected_actual_metric",
                "source_status": source_status.value,
                "source_pdf_exists": source_pdf_exists,
                "source_openability_is_correctness": False,
                "evidence_available": _metric_key_has_evidence(
                    actual_payload,
                    metric_name,
                    canonical_field_text,
                ),
                "expected_context": expected_context,
                "actual_context": actual_context,
                "result_class": result_class.value,
                "extraction_correctness_status": _payload_correctness_status(
                    result_class
                ),
                "score": _payload_score(result_class),
                "reason": reason,
                "tier": PRODUCTION_RELEVANCE_TIERS.get(
                    canonical_field_text or metric_name, "DATA_MISSING"
                ),
                "recommendation": (
                    "remove_unexpected_actual_metric_or_add_source_evidenced_policy"
                ),
                "contract_family": contract_row.get("family"),
                "metric_contract_status": contract_row.get("status"),
                "canonical_use_allowed": contract_row.get("canonical_use_allowed"),
                "promotion_gate": contract_row.get("promotion_gate"),
            }
        )

    return rows


def _payload_result(
    expectation: CoverageExpectation,
    actual_payload: Mapping[str, Any] | None,
    *,
    actual_payload_supplied: bool,
    expected_context: Mapping[str, str | None],
) -> tuple[PayloadScoreStatus, str, float | None, bool]:
    if expectation.support_status == CoverageSupportStatus.MISSING_SOURCE_EVIDENCE:
        return (
            PayloadScoreStatus.MISSING_EVIDENCE,
            "Expectation lacks source evidence; extraction correctness is not scored",
            None,
            False,
        )
    if expectation.support_status in (
        CoverageSupportStatus.CANDIDATE_REVIEW_REQUIRED,
        CoverageSupportStatus.AMBIGUOUS_LABEL,
    ):
        return (
            PayloadScoreStatus.AMBIGUOUS_QUARANTINED,
            "Expectation requires review or has ambiguous label evidence",
            None,
            False,
        )
    if expectation.support_status == CoverageSupportStatus.UNSUPPORTED_SCHEMA:
        actual_value = _actual_metric_value(actual_payload, expectation)
        if actual_value is None:
            return (
                PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED,
                "Unsupported metric was not supplied as scoreable extracted output",
                None,
                False,
            )
        return (
            PayloadScoreStatus.AMBIGUOUS_QUARANTINED,
            "Unsupported metric appeared in actual payload; scorecard quarantines it",
            actual_value,
            _metric_has_evidence(actual_payload, expectation),
        )

    if not actual_payload_supplied or actual_payload is None:
        return (
            PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL,
            "No actual extracted payload supplied for this document",
            None,
            False,
        )

    context_mismatches = _payload_context_mismatches(
        expected_context, actual_payload
    )
    actual_value = _actual_metric_value(actual_payload, expectation)
    evidence_available = _metric_has_evidence(actual_payload, expectation)

    if any(item in context_mismatches for item in ("period_end", "period_type")):
        return (
            PayloadScoreStatus.WRONG_PERIOD,
            "Actual payload period_end or period_type does not match expected period",
            actual_value,
            evidence_available,
        )
    if any(item in context_mismatches for item in ("currency", "scale")):
        return (
            PayloadScoreStatus.WRONG_UNIT_CURRENCY_SCALE,
            "Actual payload currency or scale does not match expectation",
            actual_value,
            evidence_available,
        )
    if actual_value is None and expectation.expected_value is not None:
        return (
            PayloadScoreStatus.MISSING_EXPECTED_METRIC,
            "Expected metric is absent from actual payload",
            None,
            evidence_available,
        )
    if expectation.expected_value is not None and not evidence_available:
        return (
            PayloadScoreStatus.MISSING_EVIDENCE,
            "Actual metric value is present but lacks payload evidence",
            actual_value,
            False,
        )
    if _payload_value_matches(expectation, actual_value):
        return (
            PayloadScoreStatus.PRESENT_CORRECT,
            "Actual payload matches expectation within tolerance",
            actual_value,
            evidence_available,
        )
    return (
        PayloadScoreStatus.PRESENT_WRONG_VALUE,
        "Actual payload value does not match expectation within tolerance",
        actual_value,
        evidence_available,
    )


def _actual_metrics(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    raw_metrics = payload.get("metrics", payload)
    return raw_metrics if isinstance(raw_metrics, Mapping) else {}


def _normalized_actual_metric_items(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_metrics = _actual_metrics(payload)
    normalized: dict[str, Any] = {}
    for raw_metric, value in raw_metrics.items():
        metric = str(raw_metric)
        if metric in ACTUAL_PAYLOAD_NON_METRIC_KEYS:
            continue
        canonical = METRIC_NAME_MAP.get(metric, metric)
        normalized[canonical] = value
    return normalized


def _expected_actual_metric_keys(
    expectations: Iterable[CoverageExpectation],
) -> set[str]:
    keys: set[str] = set()
    for expectation in expectations:
        for metric in (expectation.metric_name, expectation.canonical_field):
            if metric is None:
                continue
            keys.add(_normalise_metric_name(METRIC_NAME_MAP.get(metric, metric)))
    return keys


def _actual_metric_supplied_value(raw: Any) -> tuple[float | None, bool]:
    if isinstance(raw, Mapping):
        raw = raw.get("value")
    if raw is None or isinstance(raw, bool):
        return None, False
    if isinstance(raw, (int, float)):
        return float(raw), True
    if isinstance(raw, str):
        if not raw.strip():
            return None, False
        return None, True
    return None, True


def _actual_metric_value(
    payload: Mapping[str, Any] | None,
    expectation: CoverageExpectation,
) -> float | None:
    metrics = _actual_metrics(payload)
    keys = [expectation.metric_name]
    if expectation.canonical_field is not None:
        keys.append(expectation.canonical_field)
    for key in keys:
        if key not in metrics:
            continue
        value = metrics.get(key)
        if isinstance(value, Mapping):
            value = value.get("value")
        return _safe_payload_float(value)
    return None


def _safe_payload_float(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _metric_has_evidence(
    payload: Mapping[str, Any] | None,
    expectation: CoverageExpectation,
) -> bool:
    if not isinstance(payload, Mapping):
        return False
    keys = [expectation.metric_name]
    if expectation.canonical_field is not None:
        keys.append(expectation.canonical_field)

    metrics = _actual_metrics(payload)
    for key in keys:
        value = metrics.get(key)
        if isinstance(value, Mapping) and _truthy_evidence(value.get("evidence")):
            return True

    for field in ("provenance", "evidence", "metric_evidence"):
        evidence_map = payload.get(field)
        if not isinstance(evidence_map, Mapping):
            continue
        for key in keys:
            if _truthy_evidence(evidence_map.get(key)):
                return True
    return False


def _metric_key_has_evidence(
    payload: Mapping[str, Any] | None,
    metric_name: str,
    canonical_field: str | None,
) -> bool:
    if not isinstance(payload, Mapping):
        return False
    keys = {metric_name, METRIC_NAME_MAP.get(metric_name, metric_name)}
    if canonical_field is not None:
        keys.add(canonical_field)

    metrics = _actual_metrics(payload)
    for key in keys:
        value = metrics.get(key)
        if isinstance(value, Mapping) and _truthy_evidence(value.get("evidence")):
            return True

    for field in ("provenance", "evidence", "metric_evidence"):
        evidence_map = payload.get(field)
        if not isinstance(evidence_map, Mapping):
            continue
        for key in keys:
            if _truthy_evidence(evidence_map.get(key)):
                return True
    return False


def _truthy_evidence(raw: Any) -> bool:
    if raw is None:
        return False
    if isinstance(raw, str):
        return bool(raw.strip())
    if isinstance(raw, Mapping):
        return bool(raw)
    if isinstance(raw, list):
        return bool(raw)
    return True


def _payload_context_mismatches(
    expected: Mapping[str, str | None],
    payload: Mapping[str, Any],
) -> list[str]:
    mismatches = []
    for key, expected_val in expected.items():
        if expected_val is None:
            continue
        actual_val = str_or_none(payload.get(key))
        if actual_val is None or expected_val.lower() != actual_val.lower():
            mismatches.append(key)
    return mismatches


def _expectation_context(expectation: CoverageExpectation) -> dict[str, str | None]:
    path = Path(expectation.fixture_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "period_end": str_or_none(payload.get("period_end")),
        "period_type": str_or_none(payload.get("period_type")),
        "currency": str_or_none(payload.get("currency")),
        "scale": str_or_none(payload.get("scale")),
    }


def _actual_context(payload: Mapping[str, Any] | None) -> dict[str, str | None]:
    if not isinstance(payload, Mapping):
        return {"period_end": None, "period_type": None, "currency": None, "scale": None}
    return {
        "period_end": str_or_none(payload.get("period_end")),
        "period_type": str_or_none(payload.get("period_type")),
        "currency": str_or_none(payload.get("currency")),
        "scale": str_or_none(payload.get("scale")),
    }


def _payload_value_matches(
    expectation: CoverageExpectation,
    actual_value: float | None,
) -> bool:
    if expectation.expected_value is None:
        return actual_value is None
    if actual_value is None:
        return False
    tolerance = abs(expectation.expected_value) * expectation.tolerance
    return abs(actual_value - expectation.expected_value) <= tolerance


def _payload_correctness_status(status: PayloadScoreStatus) -> str:
    if status == PayloadScoreStatus.PRESENT_CORRECT:
        return "correct"
    if status == PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL:
        return "not_evaluated"
    if status == PayloadScoreStatus.AMBIGUOUS_QUARANTINED:
        return "quarantine"
    if status == PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED:
        return "abstain"
    if status == PayloadScoreStatus.MISSING_EXPECTED_METRIC:
        return "missing"
    return "wrong"


def _payload_score(status: PayloadScoreStatus) -> float | None:
    if status == PayloadScoreStatus.PRESENT_CORRECT:
        return 1.0
    if status == PayloadScoreStatus.UNSUPPORTED_CORRECTLY_ABSTAINED:
        return 0.5
    if status == PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL:
        return None
    if status == PayloadScoreStatus.AMBIGUOUS_QUARANTINED:
        return None
    return 0.0


def _payload_result_class_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts = {status.value: 0 for status in PayloadScoreStatus}
    for row in rows:
        result_class = str(row.get("result_class") or "")
        counts[result_class] = counts.get(result_class, 0) + 1
    return counts


def _gate_result_class_summary(
    scorecard: Mapping[str, Any],
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    row_counts = _payload_result_class_summary(rows)
    if sum(row_counts.values()) > 0:
        return row_counts

    raw_summary = scorecard.get("result_class_summary")
    if isinstance(raw_summary, Mapping):
        counts = {status.value: 0 for status in PayloadScoreStatus}
        for key, raw_count in raw_summary.items():
            counts[str(key)] = _safe_int(raw_count)
        return counts
    return _payload_result_class_summary(rows)


def _safe_int(raw: Any) -> int:
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0


def _gate_blocking_examples(
    rows: Iterable[Mapping[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    blocking_classes = set(_PRE_PERSISTENCE_BLOCKING_RESULT_CLASSES)
    for row in rows:
        result_class = str(row.get("result_class") or "")
        if result_class not in blocking_classes:
            continue
        examples.append(
            {
                "document_id": row.get("document_id"),
                "metric_name": row.get("metric_name"),
                "canonical_field": row.get("canonical_field"),
                "result_class": result_class,
                "reason": row.get("reason"),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _source_pdf_summary(expectations: Iterable[CoverageExpectation]) -> dict[str, int]:
    counts = {"exists": 0, "missing": 0, "not_declared": 0}
    seen: dict[str, bool | None] = {}
    for expectation in expectations:
        seen.setdefault(expectation.document_id, expectation.source_pdf_exists)
    for exists in seen.values():
        if exists is True:
            counts["exists"] += 1
        elif exists is False:
            counts["missing"] += 1
        else:
            counts["not_declared"] += 1
    return counts


def _payload_fixture_summary(
    path: Path,
    payload: Mapping[str, Any],
    expectations: list[CoverageExpectation],
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    result_counts = _payload_result_class_summary(rows)
    return {
        "fixture": path.name,
        "document_id": str(payload.get("document_id") or path.stem),
        "source_pdf_exists": expectations[0].source_pdf_exists if expectations else None,
        "metric_expectation_count": len(expectations),
        "result_class_summary": result_counts,
        "correctness_count": result_counts[PayloadScoreStatus.PRESENT_CORRECT.value],
        "not_evaluated_count": result_counts[
            PayloadScoreStatus.NOT_EVALUATED_NO_ACTUAL.value
        ],
    }


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


def metric_contract_status_names() -> list[str]:
    return sorted(status.value for status in MetricContractStatus)
