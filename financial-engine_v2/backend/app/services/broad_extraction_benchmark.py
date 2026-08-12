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
    normalized_value: str | None = None
    period_type: str | None = None
    period_end: str | None = None
    currency: str | None = None
    source_sha256: str | None = None


@dataclass(frozen=True)
class BenchmarkScore:
    corpus_digest: str
    document_count: int
    applicable_cells: int
    outcome_counts: Mapping[str, int]
    exact_accuracy: float | None
    coverage: float | None
    period_swap_count: int
    source_binding_rate: float | None
    gate_passed: bool
    rows: tuple[Mapping[str, object], ...]


def score_benchmark(
    documents: Iterable[CorpusDocument],
    expectations: Iterable[ExpectedCell],
    actuals: Iterable[ActualCell],
) -> BenchmarkScore:
    """Validate and score a complete frozen corpus deterministically."""

    docs = tuple(documents)
    expected = tuple(expectations)
    observed = tuple(actuals)
    errors = _validate_documents(docs)
    document_by_id = {item.document_id: item for item in docs}
    errors.extend(_validate_expectations(expected, document_by_id))
    errors.extend(_validate_actuals(observed, document_by_id))
    if errors:
        raise BenchmarkContractError("; ".join(sorted(set(errors))))

    actual_by_key = {(item.document_id, item.metric): item for item in observed}
    counts: Counter[str] = Counter()
    rows: list[Mapping[str, object]] = []
    period_swaps = 0
    bound = 0
    applicable = 0
    for cell in sorted(expected, key=lambda item: (item.document_id, item.metric)):
        document = document_by_id[cell.document_id]
        actual = actual_by_key.get((cell.document_id, cell.metric))
        outcome = _classify(document, cell, actual)
        counts[outcome] += 1
        is_applicable = cell.applicability == "applicable"
        if is_applicable:
            applicable += 1
        period_swap = bool(
            actual
            and actual.status == "accepted"
            and (
                actual.period_type != document.period_type
                or actual.period_end != document.period_end
            )
        )
        if period_swap:
            period_swaps += 1
        source_bound = bool(
            actual
            and actual.status == "accepted"
            and actual.source_sha256 == document.source_sha256
        )
        if source_bound:
            bound += 1
        rows.append(
            MappingProxyType(
                {
                    "document_id": cell.document_id,
                    "metric": cell.metric,
                    "applicability": cell.applicability,
                    "outcome": outcome,
                    "period_swap": period_swap,
                    "source_bound": source_bound,
                }
            )
        )

    correct = counts["correct"]
    incorrect = counts["incorrect"]
    accepted = correct + incorrect
    coverage = correct / applicable if applicable else None
    accuracy = correct / accepted if accepted else None
    source_rate = bound / accepted if accepted else None
    digest = hashlib.sha256(
        json.dumps(
            [asdict(item) for item in sorted(docs, key=lambda item: item.document_id)],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    gate = bool(
        coverage is not None
        and accuracy is not None
        and source_rate is not None
        and coverage >= 0.95
        and accuracy >= 0.99
        and period_swaps == 0
        and source_rate == 1.0
    )
    return BenchmarkScore(
        corpus_digest=digest,
        document_count=len(docs),
        applicable_cells=applicable,
        outcome_counts=MappingProxyType({name: counts[name] for name in OUTCOMES}),
        exact_accuracy=accuracy,
        coverage=coverage,
        period_swap_count=period_swaps,
        source_binding_rate=source_rate,
        gate_passed=gate,
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
        ids.append(item.document_id)
        issuers.append(item.issuer_id)
        if not _ID_RE.fullmatch(item.document_id) or not _ID_RE.fullmatch(
            item.issuer_id
        ):
            errors.append(f"{where}: invalid document or issuer identifier")
        if item.period_type not in {"A", "H", "Q"}:
            errors.append(f"{where}.period_type: unsupported period type")
        if item.admission_status not in {"admitted", "data_missing"}:
            errors.append(f"{where}.admission_status: unsupported status")
        has_source = item.source_path is not None or item.source_sha256 is not None
        if item.admission_status == "admitted":
            if (
                not item.source_path
                or not item.source_sha256
                or not _SHA256_RE.fullmatch(item.source_sha256)
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
        keys.append((item.document_id, item.metric))
        if item.document_id not in documents:
            errors.append(f"{where}: unknown document")
        if item.metric not in METRICS:
            errors.append(f"{where}: metric outside ten-metric contract")
        if item.applicability not in {"applicable", "inapplicable", "unresolved"}:
            errors.append(f"{where}: invalid applicability")
        if item.adjudication_status not in {"verified", "unresolved"}:
            errors.append(f"{where}: invalid adjudication status")
        if (
            item.applicability == "applicable"
            and item.adjudication_status == "verified"
        ):
            if item.normalized_value is None or item.evidence_location is None:
                errors.append(
                    f"{where}: verified applicable cell lacks value or evidence"
                )
            if item.currency is not None and not _CURRENCY_RE.fullmatch(item.currency):
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
    actuals: tuple[ActualCell, ...], documents: Mapping[str, CorpusDocument]
) -> list[str]:
    errors: list[str] = []
    keys: list[tuple[str, str]] = []
    for index, item in enumerate(actuals):
        where = f"actuals[{index}]"
        if not isinstance(item, ActualCell):
            errors.append(f"{where}: expected ActualCell")
            continue
        keys.append((item.document_id, item.metric))
        if item.document_id not in documents or item.metric not in METRICS:
            errors.append(f"{where}: outside corpus contract")
        if item.status not in {"accepted", "abstained", "unsupported"}:
            errors.append(f"{where}: invalid extraction status")
        if item.status == "accepted" and any(
            value is None
            for value in (
                item.normalized_value,
                item.period_type,
                item.period_end,
                item.source_sha256,
            )
        ):
            errors.append(
                f"{where}: accepted result lacks value, period, or source binding"
            )
    if len(keys) != len(set(keys)):
        errors.append("duplicate actual document/metric cell")
    return errors


def _classify(
    document: CorpusDocument, expected: ExpectedCell, actual: ActualCell | None
) -> str:
    if document.admission_status == "data_missing":
        return "data_missing"
    if (
        expected.applicability != "applicable"
        or expected.adjudication_status != "verified"
    ):
        return "unsupported"
    if actual is None or actual.status == "abstained":
        return "abstained"
    if actual.status == "unsupported":
        return "unsupported"
    matches = (
        _decimal(actual.normalized_value) == _decimal(expected.normalized_value)
        and actual.period_type == document.period_type
        and actual.period_end == document.period_end
        and actual.currency == expected.currency
        and actual.source_sha256 == document.source_sha256
    )
    return "correct" if matches else "incorrect"


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None
