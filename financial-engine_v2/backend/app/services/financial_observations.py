from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy.dialects.postgresql import insert

from app.models.financial_observations import FinancialObservation
from app.services.financial_metric_contract import (
    CANONICAL_METRIC_FIELDS,
    METRIC_CONTRACT_BY_CANONICAL_FIELD,
    MetricUnitKind,
)


_PROVENANCE_FIELDS = (
    "metric",
    "source",
    "page_number",
    "row_ref",
    "period_type",
    "period_end",
    "currency",
    "scale",
)
_PERIOD_BASES = frozenset({"Q", "H", "A"})
_SOURCE_SCALES = frozenset(
    {"units", "thousands", "millions", "billions", "trillions"}
)
_NATIVE_CURRENCIES = frozenset(
    {"AUD", "CAD", "CNY", "EUR", "GBP", "HKD", "IDR", "JPY", "NZD", "SGD", "USD"}
)
_NON_STATUTORY_MARKERS = (
    "adjusted",
    "underlying",
    "non-statutory",
    "non statutory",
    "pro forma",
)
_EXPLICIT_PERIOD_REASONS = frozenset(
    {
        "year_ended_source_phrase",
        "half_year_source_phrase",
        "six_months_ended_source_phrase",
    }
)
_EXPLICIT_PERIOD_END_REASONS = frozenset(
    {
        "year_ended_explicit_date",
        "half_year_ended_explicit_date",
        "current_period_explicit_range",
    }
)


def _observation_id(
    *,
    source_document_id: Any,
    extractor_version: str,
    ticker: str,
    metric: str,
    period_end: date,
    period_basis: str,
    accounting_basis: str,
    currency: str,
    scale: str,
) -> uuid.UUID:
    """Map the database source-context identity to a stable UUID."""
    identity = json.dumps(
        [
            "financial-observation-source-context-v1",
            str(source_document_id),
            extractor_version,
            ticker,
            metric,
            period_end.isoformat(),
            period_basis,
            accounting_basis,
            currency,
            scale,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return uuid.uuid5(uuid.NAMESPACE_URL, identity)


def _required_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _numeric(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _period_end(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _has_source_text_hit(
    evidence: Any, *, period_basis: str, reasons: frozenset[str]
) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    hits = evidence.get("hits")
    if not isinstance(hits, list):
        return False
    return any(
        isinstance(hit, Mapping)
        and hit.get("source") == "source_text"
        and hit.get("period_type") == period_basis
        and hit.get("reason") in reasons
        for hit in hits
    )


def _accepted_metric_context(
    document: Any, structured: Mapping[str, Any], metric: str
) -> dict[str, Any] | None:
    metrics = structured.get("metrics")
    provenance_by_metric = structured.get("field_provenance")
    if not isinstance(metrics, Mapping) or not isinstance(
        provenance_by_metric, Mapping
    ):
        return None

    contract = METRIC_CONTRACT_BY_CANONICAL_FIELD[metric]
    value = _numeric(metrics.get(metric))
    period_end = _period_end(structured.get("period_end"))
    period_basis = _required_text(structured.get("period_type"))
    native_currency = _required_text(structured.get("currency"))
    provenance = provenance_by_metric.get(metric)
    source_period_type = _required_text(structured.get("source_period_type"))
    source_period_evidence = structured.get("source_period_evidence")
    period_end_evidence = structured.get("source_period_end_evidence")
    extraction_status = _required_text(
        structured.get("_observation_extraction_status")
    )
    claimed_accounting_basis = structured.get("accounting_basis")
    claimed_trust_state = structured.get("trust_state")
    if (
        value is None
        or period_end is None
        or period_basis not in _PERIOD_BASES
        or extraction_status != "ok"
        or claimed_accounting_basis not in (None, "statutory")
        or claimed_trust_state not in (None, "accepted")
        or source_period_type != period_basis
        or not isinstance(source_period_evidence, Mapping)
        or source_period_evidence.get("period_type") != period_basis
        or not _has_source_text_hit(
            source_period_evidence,
            period_basis=period_basis,
            reasons=_EXPLICIT_PERIOD_REASONS,
        )
        or not isinstance(provenance, Mapping)
        or any(field not in provenance for field in _PROVENANCE_FIELDS)
        or any(
            provenance[field] in (None, "", "unknown")
            for field in _PROVENANCE_FIELDS
        )
    ):
        return None

    is_share_count = contract.unit_kind == MetricUnitKind.SHARE_COUNT_ABSOLUTE
    provenance_unit = _required_text(provenance["currency"])
    if is_share_count:
        if provenance_unit != "shares":
            return None
        observation_unit = "shares"
    else:
        if (
            contract.unit_kind != MetricUnitKind.CURRENCY_ABSOLUTE
            or native_currency not in _NATIVE_CURRENCIES
            or provenance_unit != native_currency
        ):
            return None
        observation_unit = native_currency

    document_id = getattr(document, "document_id", None)
    source = _required_text(provenance["source"])
    row_ref = _required_text(provenance["row_ref"])
    source_scale = _required_text(provenance["scale"])
    scale_source = _required_text(provenance.get("scale_source"))
    source_cell = provenance.get("source_cell")
    source_evidence_text = " ".join(
        str(value)
        for value in (
            row_ref,
            source_cell.get("row_label") if isinstance(source_cell, Mapping) else "",
            source_cell.get("header_cell") if isinstance(source_cell, Mapping) else "",
            source_cell.get("raw_value") if isinstance(source_cell, Mapping) else "",
        )
    ).lower()
    bound_period_end = None
    if isinstance(period_end_evidence, Mapping):
        bound_period_end = _period_end(period_end_evidence.get("period_end"))
    if (
        document_id is None
        or (
            provenance.get("source_document_id") is not None
            and str(provenance["source_document_id"]) != str(document_id)
        )
        or provenance["metric"] != metric
        or source not in {context.value for context in contract.statement_contexts}
        or row_ref is None
        or "statutory" not in source_evidence_text
        or any(marker in source_evidence_text for marker in _NON_STATUTORY_MARKERS)
        or str(provenance["period_type"]) != period_basis
        or str(provenance["period_end"]) != period_end.isoformat()
        or source_scale not in _SOURCE_SCALES
        or scale_source in (None, "unknown")
        or not isinstance(source_cell, Mapping)
        or source_cell.get("raw_value") in (None, "")
        or source_cell.get("header_cell") in (None, "")
        or observation_unit.lower() not in source_evidence_text
        or bound_period_end != period_end
        or not _has_source_text_hit(
            period_end_evidence,
            period_basis=period_basis,
            reasons=_EXPLICIT_PERIOD_END_REASONS,
        )
    ):
        return None

    bound_provenance = dict(provenance)
    bound_provenance["source_document_id"] = str(document_id)
    bound_provenance["source_scale"] = source_scale
    bound_provenance["normalized_scale"] = "units"
    bound_provenance["unit_kind"] = contract.unit_kind.value
    return {
        "value": value,
        "period_end": period_end,
        "period_basis": period_basis,
        "accounting_basis": "statutory",
        "currency": observation_unit,
        "scale": "units",
        "trust_state": "accepted",
        "provenance": bound_provenance,
    }


def stage_financial_observations(
    db,
    *,
    document: Any,
    extraction_run: Any,
    structured: Mapping[str, Any],
) -> tuple[FinancialObservation, ...]:
    """Stage independently accepted statutory metrics; caller owns transaction."""
    document_id = getattr(document, "document_id", None)
    run_id = getattr(extraction_run, "run_id", None)
    extractor_version = _required_text(
        getattr(extraction_run, "extractor_version", None)
    )
    ticker = _required_text(getattr(document, "ticker", None))
    if (
        document_id is None
        or run_id is None
        or extractor_version is None
        or ticker is None
    ):
        return ()

    staged = []
    for metric in CANONICAL_METRIC_FIELDS:
        context = _accepted_metric_context(document, structured, metric)
        if context is None:
            continue
        observation = FinancialObservation(
            observation_id=_observation_id(
                source_document_id=document_id,
                extractor_version=extractor_version,
                ticker=ticker,
                metric=metric,
                period_end=context["period_end"],
                period_basis=context["period_basis"],
                accounting_basis=context["accounting_basis"],
                currency=context["currency"],
                scale=context["scale"],
            ),
            source_document_id=document_id,
            extraction_run_id=run_id,
            extractor_version=extractor_version,
            ticker=ticker,
            metric=metric,
            **context,
        )
        values = {
            column.name: getattr(observation, column.name)
            for column in FinancialObservation.__table__.columns
        }
        statement = (
            insert(FinancialObservation)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_financial_observation_source_context"
            )
        )
        if db.execute(statement).rowcount:
            staged.append(observation)
    return tuple(staged)


def stage_revenue_observation(
    db,
    *,
    document: Any,
    extraction_run: Any,
    structured: Mapping[str, Any],
) -> FinancialObservation | None:
    """Compatibility wrapper for Ticket 05 revenue-only callers."""
    revenue_payload = dict(structured)
    metrics = structured.get("metrics")
    provenance = structured.get("field_provenance")
    revenue_payload["metrics"] = (
        {"revenue": metrics.get("revenue")}
        if isinstance(metrics, Mapping)
        else metrics
    )
    revenue_payload["field_provenance"] = (
        {"revenue": provenance.get("revenue")}
        if isinstance(provenance, Mapping)
        else provenance
    )
    observations = stage_financial_observations(
        db,
        document=document,
        extraction_run=extraction_run,
        structured=revenue_payload,
    )
    return next(
        (item for item in observations if item.metric == "revenue"),
        None,
    )


def accepted_statutory_overrides(
    db,
    *,
    ticker: str,
    legacy_contexts: Mapping[
        tuple[date, str], Mapping[str, tuple[str | None, str]]
    ],
) -> dict[tuple[date, str], dict[str, Decimal]]:
    """Return uncontested metric overlays by legacy read identity."""
    rows = (
        db.query(FinancialObservation)
        .filter(
            FinancialObservation.ticker == ticker,
            FinancialObservation.metric.in_(CANONICAL_METRIC_FIELDS),
            FinancialObservation.accounting_basis == "statutory",
            FinancialObservation.trust_state == "accepted",
        )
        .all()
    )
    candidates: dict[
        tuple[date, str, str], set[tuple[Decimal, str, str]]
    ] = {}
    for row in rows:
        key = (row.period_end, row.period_basis, row.metric)
        candidates.setdefault(key, set()).add(
            (Decimal(row.value), row.currency, row.scale)
        )

    overrides: dict[tuple[date, str], dict[str, Decimal]] = {}
    for key, truths in candidates.items():
        read_key = key[:2]
        metric = key[2]
        legacy_context = legacy_contexts.get(read_key, {}).get(metric)
        if len(truths) == 1 and legacy_context is not None:
            value, currency, scale = next(iter(truths))
            if legacy_context != (currency, scale):
                continue
            overrides.setdefault(read_key, {})[metric] = value
    return overrides


def accepted_revenue_overrides(
    db,
    *,
    ticker: str,
    legacy_contexts: Mapping[tuple[date, str], tuple[str | None, str]],
) -> dict[tuple[date, str], Decimal]:
    """Compatibility wrapper retaining the Ticket 05 return shape."""
    overrides = accepted_statutory_overrides(
        db,
        ticker=ticker,
        legacy_contexts={
            key: {"revenue": context}
            for key, context in legacy_contexts.items()
        },
    )
    return {
        key: metrics["revenue"]
        for key, metrics in overrides.items()
        if "revenue" in metrics
    }
