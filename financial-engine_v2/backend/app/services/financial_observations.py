from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy.dialects.postgresql import insert

from app.models.financial_observations import FinancialObservation


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


def _accepted_revenue_context(
    document: Any, structured: Mapping[str, Any]
) -> dict[str, Any] | None:
    metrics = structured.get("metrics")
    provenance_by_metric = structured.get("field_provenance")
    if not isinstance(metrics, Mapping) or not isinstance(
        provenance_by_metric, Mapping
    ):
        return None

    value = _numeric(metrics.get("revenue"))
    period_end = _period_end(structured.get("period_end"))
    period_basis = _required_text(structured.get("period_type"))
    currency = _required_text(structured.get("currency"))
    provenance = provenance_by_metric.get("revenue")
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
        or currency not in _NATIVE_CURRENCIES
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
        or provenance["metric"] != "revenue"
        or source != "income_statement"
        or row_ref is None
        or "statutory" not in source_evidence_text
        or any(marker in source_evidence_text for marker in _NON_STATUTORY_MARKERS)
        or str(provenance["period_type"]) != period_basis
        or str(provenance["period_end"]) != period_end.isoformat()
        or str(provenance["currency"]) != currency
        or source_scale not in _SOURCE_SCALES
        or scale_source in (None, "unknown")
        or not isinstance(source_cell, Mapping)
        or source_cell.get("raw_value") in (None, "")
        or source_cell.get("header_cell") in (None, "")
        or currency.lower() not in source_evidence_text
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
    return {
        "value": value,
        "period_end": period_end,
        "period_basis": period_basis,
        "accounting_basis": "statutory",
        "currency": currency,
        "scale": "units",
        "trust_state": "accepted",
        "provenance": bound_provenance,
    }


def stage_revenue_observation(
    db,
    *,
    document: Any,
    extraction_run: Any,
    structured: Mapping[str, Any],
) -> FinancialObservation | None:
    """Stage accepted statutory revenue; the caller owns flush and commit."""
    context = _accepted_revenue_context(document, structured)
    document_id = getattr(document, "document_id", None)
    run_id = getattr(extraction_run, "run_id", None)
    extractor_version = _required_text(
        getattr(extraction_run, "extractor_version", None)
    )
    ticker = _required_text(getattr(document, "ticker", None))
    if (
        context is None
        or document_id is None
        or run_id is None
        or extractor_version is None
        or ticker is None
    ):
        return None

    observation = FinancialObservation(
        observation_id=uuid.uuid4(),
        source_document_id=document_id,
        extraction_run_id=run_id,
        extractor_version=extractor_version,
        ticker=ticker,
        metric="revenue",
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
    result = db.execute(statement)
    return observation if result.rowcount else None


def accepted_revenue_overrides(
    db,
    *,
    ticker: str,
    legacy_contexts: Mapping[tuple[date, str], tuple[str | None, str]],
) -> dict[tuple[date, str], Decimal]:
    """Return deterministic statutory revenue values by legacy read identity."""
    rows = (
        db.query(FinancialObservation)
        .filter(
            FinancialObservation.ticker == ticker,
            FinancialObservation.metric == "revenue",
            FinancialObservation.accounting_basis == "statutory",
            FinancialObservation.trust_state == "accepted",
        )
        .all()
    )
    candidates: dict[tuple[date, str], set[tuple[Decimal, str, str]]] = {}
    for row in rows:
        key = (row.period_end, row.period_basis)
        candidates.setdefault(key, set()).add(
            (Decimal(row.value), row.currency, row.scale)
        )

    overrides: dict[tuple[date, str], Decimal] = {}
    for key, truths in candidates.items():
        legacy_context = legacy_contexts.get(key)
        if len(truths) == 1 and legacy_context is not None:
            value, currency, scale = next(iter(truths))
            if legacy_context != (currency, scale):
                continue
            overrides[key] = value
    return overrides
