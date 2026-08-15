"""Fail-closed contracts and scoring for the broad extraction benchmark.

This module is deliberately pure: it validates already-adjudicated metadata and
scores supplied extraction observations.  It does not read source documents,
run extraction, or promote results to Financial Truth.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

CORPUS_SIZE = 20
METRICS = (
    "revenue",
    "explicit_ebitda",
    "npat_attributable",
    "operating_cash_flow",
    "capital_expenditure",
    "cash_and_equivalents",
    "total_debt",
    "shares_outstanding",
    "dividend_per_share",
    "segment_revenue",
)
OUTCOMES = (
    "correct",
    "incorrect",
    "abstained",
    "unsupported",
    "data_missing",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_NON_CURRENCY_METRICS = ("shares_outstanding",)
_IDENTITY_FIELDS = (
    ("raw_value", "raw_value"),
    ("scale", "scale"),
    ("normalized_value", "normalized"),
    ("period", "period"),
    ("currency", "currency"),
    ("source", "source"),
    ("provenance", "provenance"),
)


class BenchmarkContractError(ValueError):
    """Raised when benchmark inputs cannot be scored safely."""


@dataclass(frozen=True)
class CorpusDocument:
    document_id: str
    issuer_id: str
    document_class: str
    period_type: str
    period_end: str
    admission_status: str
    source_path: str | None
    source_sha256: str | None


@dataclass(frozen=True)
class ExpectedCell:
    document_id: str
    metric: str
    applicability: str
    adjudication_status: str
    raw_value: str | None = None
    raw_unit: str | None = None
    currency: str | None = None
    normalized_value: str | None = None
    evidence_location: str | None = None


@dataclass(frozen=True)
class ActualCell:
    document_id: str
    metric: str
    status: str
    raw_value: str | None = None
    raw_unit: str | None = None
    normalized_value: str | None = None
    period_type: str | None = None
    period_end: str | None = None
    currency: str | None = None
    source_sha256: str | None = None
    evidence_location: str | None = None


@dataclass(frozen=True)
class BenchmarkScore:
    corpus_digest: str
    contract_digest: str
    document_count: int
    applicable_cells: int
    outcome_counts: Mapping[str, int]
    baseline_outcome_counts: Mapping[str, int] | None
    identity_mismatch_counts: Mapping[str, int]
    baseline_identity_mismatch_counts: Mapping[str, int] | None
    exact_accuracy: float | None
    coverage: float | None
    raw_value_mismatch_count: int
    scale_mismatch_count: int
    normalized_value_mismatch_count: int
    currency_mismatch_count: int
    provenance_mismatch_count: int
    period_swap_count: int
    source_binding_rate: float | None
    provenance_binding_rate: float | None
    newly_correct_count: int
    regression_count: int
    gate_passed: bool
    repair_gate_passed: bool
    rows: tuple[Mapping[str, object], ...]


def score_benchmark(
    documents: Iterable[CorpusDocument],
    expectations: Iterable[ExpectedCell],
    actuals: Iterable[ActualCell],
    *,
    baseline_actuals: Iterable[ActualCell] | None = None,
) -> BenchmarkScore:
    """Validate and score a complete frozen corpus deterministically."""

    docs = tuple(documents)
    expected = tuple(expectations)
    observed = tuple(actuals)
    baseline = tuple(baseline_actuals or ())
    comparison_enabled = baseline_actuals is not None
    document_errors = _validate_documents(docs)
    if document_errors:
        raise BenchmarkContractError("; ".join(sorted(set(document_errors))))
    document_by_id = {item.document_id: item for item in docs}
    errors = _validate_expectations(expected, document_by_id)
    errors.extend(_validate_actuals(observed, document_by_id, label="actuals"))
    errors.extend(_validate_actuals(baseline, document_by_id, label="baseline_actuals"))
    if errors:
        raise BenchmarkContractError("; ".join(sorted(set(errors))))

    actual_by_key = {(item.document_id, item.metric): item for item in observed}
    baseline_by_key = {(item.document_id, item.metric): item for item in baseline}
    counts: Counter[str] = Counter()
    baseline_counts: Counter[str] = Counter()
    identity_mismatches: Counter[str] = Counter()
    baseline_identity_mismatches: Counter[str] = Counter()
    rows: list[Mapping[str, object]] = []
    bound = 0
    provenance_bound = 0
    newly_correct = 0
    regressions = 0
    applicable = 0
    for cell in sorted(expected, key=lambda item: (item.document_id, item.metric)):
        document = document_by_id[cell.document_id]
        actual = actual_by_key.get((cell.document_id, cell.metric))
        identity = _identity(document, cell, actual)
        outcome = _classify(document, cell, actual, identity)
        baseline_actual = baseline_by_key.get((cell.document_id, cell.metric))
        baseline_outcome = None
        if comparison_enabled:
            baseline_identity = _identity(document, cell, baseline_actual)
            baseline_outcome = _classify(
                document,
                cell,
                baseline_actual,
                baseline_identity,
            )
            baseline_counts[baseline_outcome] += 1
            baseline_scoreable_accepted = bool(
                baseline_actual
                and baseline_actual.status == "accepted"
                and document.admission_status == "admitted"
                and cell.applicability == "applicable"
                and cell.adjudication_status == "verified"
            )
            if baseline_scoreable_accepted:
                for count_name, identity_name in _IDENTITY_FIELDS:
                    if not getattr(baseline_identity, identity_name):
                        baseline_identity_mismatches[count_name] += 1
        regressed = baseline_outcome == "correct" and outcome != "correct"
        recovered = (
            comparison_enabled
            and baseline_outcome != "correct"
            and outcome == "correct"
        )
        if recovered:
            newly_correct += 1
        if regressed:
            regressions += 1
        counts[outcome] += 1
        is_applicable = cell.applicability == "applicable"
        if is_applicable:
            applicable += 1
        scoreable_accepted = bool(
            actual
            and actual.status == "accepted"
            and document.admission_status == "admitted"
            and cell.applicability == "applicable"
            and cell.adjudication_status == "verified"
        )
        if scoreable_accepted:
            for count_name, identity_name in _IDENTITY_FIELDS:
                if not getattr(identity, identity_name):
                    identity_mismatches[count_name] += 1
        raw_value_mismatch = scoreable_accepted and not identity.raw_value
        scale_mismatch = scoreable_accepted and not identity.scale
        normalized_value_mismatch = scoreable_accepted and not identity.normalized
        currency_mismatch = scoreable_accepted and not identity.currency
        provenance_mismatch = scoreable_accepted and not identity.provenance
        period_swap = scoreable_accepted and not identity.period
        source_bound = scoreable_accepted and identity.source
        if source_bound:
            bound += 1
        provenance_bound_cell = scoreable_accepted and identity.provenance
        if provenance_bound_cell:
            provenance_bound += 1
        rows.append(
            MappingProxyType(
                {
                    "document_id": cell.document_id,
                    "issuer_id": document.issuer_id,
                    "document_class": document.document_class,
                    "metric": cell.metric,
                    "applicability": cell.applicability,
                    "outcome": outcome,
                    "baseline_outcome": baseline_outcome,
                    "newly_correct": recovered,
                    "regressed": regressed,
                    "raw_value_mismatch": raw_value_mismatch,
                    "scale_mismatch": scale_mismatch,
                    "normalized_value_mismatch": normalized_value_mismatch,
                    "currency_mismatch": currency_mismatch,
                    "provenance_mismatch": provenance_mismatch,
                    "period_swap": period_swap,
                    "source_bound": source_bound,
                    "provenance_bound": provenance_bound_cell,
                }
            )
        )

    correct = counts["correct"]
    incorrect = counts["incorrect"]
    accepted = correct + incorrect
    coverage = correct / applicable if applicable else None
    accuracy = correct / accepted if accepted else None
    source_rate = bound / accepted if accepted else None
    provenance_rate = provenance_bound / accepted if accepted else None
    period_swaps = identity_mismatches["period"]
    digest = hashlib.sha256(
        json.dumps(
            [asdict(item) for item in sorted(docs, key=lambda item: item.document_id)],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    contract_digest = hashlib.sha256(
        json.dumps(
            {
                "documents": [
                    asdict(item)
                    for item in sorted(docs, key=lambda item: item.document_id)
                ],
                "expectations": [
                    asdict(item)
                    for item in sorted(
                        expected,
                        key=lambda item: (item.document_id, item.metric),
                    )
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    gate = bool(
        coverage is not None
        and accuracy is not None
        and source_rate is not None
        and provenance_rate is not None
        and coverage >= 0.95
        and accuracy >= 0.99
        and period_swaps == 0
        and source_rate == 1.0
        and provenance_rate == 1.0
        and counts["data_missing"] == 0
        and regressions == 0
    )
    repair_gate = bool(
        comparison_enabled
        and newly_correct > 0
        and regressions == 0
        and counts["incorrect"] <= baseline_counts["incorrect"]
        and period_swaps == 0
        and source_rate == 1.0
        and provenance_rate == 1.0
        and all(
            identity_mismatches[name] <= baseline_identity_mismatches[name]
            for name, _ in _IDENTITY_FIELDS
        )
    )
    return BenchmarkScore(
        corpus_digest=digest,
        contract_digest=contract_digest,
        document_count=len(docs),
        applicable_cells=applicable,
        outcome_counts=MappingProxyType({name: counts[name] for name in OUTCOMES}),
        baseline_outcome_counts=(
            MappingProxyType({name: baseline_counts[name] for name in OUTCOMES})
            if comparison_enabled
            else None
        ),
        identity_mismatch_counts=MappingProxyType(
            {name: identity_mismatches[name] for name, _ in _IDENTITY_FIELDS}
        ),
        baseline_identity_mismatch_counts=(
            MappingProxyType(
                {
                    name: baseline_identity_mismatches[name]
                    for name, _ in _IDENTITY_FIELDS
                }
            )
            if comparison_enabled
            else None
        ),
        exact_accuracy=accuracy,
        coverage=coverage,
        raw_value_mismatch_count=identity_mismatches["raw_value"],
        scale_mismatch_count=identity_mismatches["scale"],
        normalized_value_mismatch_count=identity_mismatches["normalized_value"],
        currency_mismatch_count=identity_mismatches["currency"],
        provenance_mismatch_count=identity_mismatches["provenance"],
        period_swap_count=period_swaps,
        source_binding_rate=source_rate,
        provenance_binding_rate=provenance_rate,
        newly_correct_count=newly_correct,
        regression_count=regressions,
        gate_passed=gate,
        repair_gate_passed=repair_gate,
        rows=tuple(rows),
    )


def _validate_documents(documents: tuple[CorpusDocument, ...]) -> list[str]:
    errors: list[str] = []
    if len(documents) != CORPUS_SIZE:
        errors.append(f"corpus must contain exactly {CORPUS_SIZE} documents")
    ids: list[str] = []
    issuers: list[str] = []
    for index, item in enumerate(documents):
        where = f"documents[{index}]"
        if not isinstance(item, CorpusDocument):
            errors.append(f"{where}: expected CorpusDocument")
            continue
        valid_document_id = _matches(_ID_RE, item.document_id)
        valid_issuer_id = _matches(_ID_RE, item.issuer_id)
        if not valid_document_id or not valid_issuer_id:
            errors.append(f"{where}: invalid document or issuer identifier")
        else:
            ids.append(item.document_id)
            issuers.append(item.issuer_id)
        if not isinstance(item.period_type, str) or item.period_type not in (
            "A",
            "H",
            "Q",
        ):
            errors.append(f"{where}.period_type: unsupported period type")
        if not _is_iso_date(item.period_end):
            errors.append(f"{where}.period_end: invalid period end")
        if not _matches(_ID_RE, item.document_class):
            errors.append(f"{where}.document_class: invalid document class")
        if not isinstance(item.admission_status, str) or item.admission_status not in (
            "admitted",
            "data_missing",
        ):
            errors.append(f"{where}.admission_status: unsupported status")
        has_source = item.source_path is not None or item.source_sha256 is not None
        if item.admission_status == "admitted":
            if (
                not _nonempty_string(item.source_path)
                or not item.source_sha256
                or not _matches(_SHA256_RE, item.source_sha256)
            ):
                errors.append(f"{where}: admitted document requires path and SHA-256")
        elif has_source:
            errors.append(
                f"{where}: DATA_MISSING document must not claim source evidence"
            )
    if len(ids) != len(set(ids)):
        errors.append("duplicate document IDs")
    if len(issuers) != len(set(issuers)):
        errors.append("corpus must contain 20 distinct issuers")
    return errors


def _validate_expectations(
    expectations: tuple[ExpectedCell, ...], documents: Mapping[str, CorpusDocument]
) -> list[str]:
    errors: list[str] = []
    keys: list[tuple[str, str]] = []
    for index, item in enumerate(expectations):
        where = f"expectations[{index}]"
        if not isinstance(item, ExpectedCell):
            errors.append(f"{where}: expected ExpectedCell")
            continue
        valid_key = isinstance(item.document_id, str) and isinstance(item.metric, str)
        if valid_key:
            keys.append((item.document_id, item.metric))
        document = (
            documents.get(item.document_id)
            if isinstance(item.document_id, str)
            else None
        )
        if document is None:
            errors.append(f"{where}: unknown document")
        elif (
            document.admission_status == "data_missing"
            and item.adjudication_status == "verified"
        ):
            errors.append(
                f"{where}: DATA_MISSING document cannot have verified expectations"
            )
        if item.metric not in METRICS:
            errors.append(f"{where}: metric outside ten-metric contract")
        if not isinstance(item.applicability, str) or item.applicability not in (
            "applicable",
            "inapplicable",
            "unresolved",
        ):
            errors.append(f"{where}: invalid applicability")
        if not isinstance(
            item.adjudication_status, str
        ) or item.adjudication_status not in ("verified", "unresolved"):
            errors.append(f"{where}: invalid adjudication status")
        if (
            item.applicability == "applicable"
            and item.adjudication_status == "verified"
        ):
            if any(
                value is None
                for value in (
                    item.raw_value,
                    item.raw_unit,
                    item.normalized_value,
                    item.evidence_location,
                )
            ):
                errors.append(
                    f"{where}: verified applicable cell lacks raw value, unit, "
                    "normalized value, or evidence"
                )
            elif (
                _decimal(item.raw_value) is None
                or _decimal(item.normalized_value) is None
            ):
                errors.append(f"{where}: invalid raw or normalized numeric value")
            if not _nonempty_string(item.raw_unit) or not _nonempty_string(
                item.evidence_location
            ):
                errors.append(
                    f"{where}: verified applicable cell requires non-empty raw unit and evidence"
                )
            if item.metric not in _NON_CURRENCY_METRICS and item.currency is None:
                errors.append(f"{where}: verified monetary cell requires currency")
            elif item.currency is not None and not _matches(
                _CURRENCY_RE, item.currency
            ):
                errors.append(f"{where}: invalid currency")
    required = {
        (document_id, metric) for document_id in documents for metric in METRICS
    }
    if set(keys) != required or len(keys) != len(required):
        errors.append(
            "expectations must declare every document/metric cell exactly once"
        )
    return errors


def _validate_actuals(
    actuals: tuple[ActualCell, ...],
    documents: Mapping[str, CorpusDocument],
    *,
    label: str,
) -> list[str]:
    errors: list[str] = []
    keys: list[tuple[str, str]] = []
    for index, item in enumerate(actuals):
        where = f"{label}[{index}]"
        if not isinstance(item, ActualCell):
            errors.append(f"{where}: expected ActualCell")
            continue
        valid_key = isinstance(item.document_id, str) and isinstance(item.metric, str)
        if valid_key:
            keys.append((item.document_id, item.metric))
        document = (
            documents.get(item.document_id)
            if isinstance(item.document_id, str)
            else None
        )
        if document is None or item.metric not in METRICS:
            errors.append(f"{where}: outside corpus contract")
        elif document.admission_status == "data_missing":
            errors.append(
                f"{where}: DATA_MISSING document cannot have extraction observations"
            )
        if not isinstance(item.status, str) or item.status not in (
            "accepted",
            "abstained",
            "unsupported",
        ):
            errors.append(f"{where}: invalid extraction status")
        if item.status == "accepted" and any(
            value is None
            for value in (
                item.raw_value,
                item.raw_unit,
                item.normalized_value,
                item.period_type,
                item.period_end,
                item.source_sha256,
                item.evidence_location,
            )
        ):
            errors.append(
                f"{where}: accepted result lacks raw, normalized, period, or provenance identity"
            )
        elif item.status == "accepted" and (
            _decimal(item.raw_value) is None or _decimal(item.normalized_value) is None
        ):
            errors.append(
                f"{where}: accepted result has invalid raw or normalized numeric value"
            )
        elif item.status == "accepted" and (
            not _nonempty_string(item.raw_unit)
            or not _nonempty_string(item.evidence_location)
        ):
            errors.append(
                f"{where}: accepted result requires non-empty raw unit and evidence"
            )
        elif item.status == "accepted" and (
            not item.source_sha256 or not _matches(_SHA256_RE, item.source_sha256)
        ):
            errors.append(f"{where}: accepted result has invalid source SHA-256")
        elif item.status == "accepted" and (
            not isinstance(item.period_type, str)
            or item.period_type not in ("A", "H", "Q")
            or not _is_iso_date(item.period_end)
        ):
            errors.append(f"{where}: accepted result has invalid period identity")
        elif (
            item.status == "accepted"
            and item.metric not in _NON_CURRENCY_METRICS
            and item.currency is None
        ):
            errors.append(f"{where}: accepted monetary result requires currency")
        elif (
            item.status == "accepted"
            and item.currency is not None
            and not _matches(_CURRENCY_RE, item.currency)
        ):
            errors.append(f"{where}: accepted result has invalid currency")
    if len(keys) != len(set(keys)):
        errors.append("duplicate actual document/metric cell")
    return errors


def _classify(
    document: CorpusDocument,
    expected: ExpectedCell,
    actual: ActualCell | None,
    identity: _CellIdentity,
) -> str:
    if document.admission_status == "data_missing":
        return "data_missing"
    if (
        expected.applicability != "applicable"
        or expected.adjudication_status != "verified"
    ):
        if actual is not None and actual.status == "accepted":
            return "incorrect"
        return "unsupported"
    if actual is None or actual.status == "abstained":
        return "abstained"
    if actual.status == "unsupported":
        return "unsupported"
    return "correct" if identity.matches else "incorrect"


@dataclass(frozen=True)
class _CellIdentity:
    raw_value: bool
    scale: bool
    normalized: bool
    period: bool
    currency: bool
    source: bool
    provenance: bool

    @property
    def matches(self) -> bool:
        return all(asdict(self).values())


def _identity(
    document: CorpusDocument, expected: ExpectedCell, actual: ActualCell | None
) -> _CellIdentity:
    accepted = bool(actual and actual.status == "accepted")
    return _CellIdentity(
        raw_value=accepted
        and _decimal(actual.raw_value) == _decimal(expected.raw_value),
        scale=accepted and actual.raw_unit == expected.raw_unit,
        normalized=accepted
        and _decimal(actual.normalized_value) == _decimal(expected.normalized_value),
        period=accepted
        and actual.period_type == document.period_type
        and actual.period_end == document.period_end,
        currency=accepted and actual.currency == expected.currency,
        source=accepted and actual.source_sha256 == document.source_sha256,
        provenance=accepted and actual.evidence_location == expected.evidence_location,
    )


def _decimal(value: str | None) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _is_iso_date(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
