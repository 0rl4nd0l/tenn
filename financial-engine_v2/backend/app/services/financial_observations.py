from __future__ import annotations

import json
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy.dialects.postgresql import insert

from app.models.financial_observations import (
    FinancialObservation,
    FinancialObservationSupersession,
    FinancialResultDisclosure,
)
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
    "period_end",
    "currency",
    "scale",
    "accounting_basis",
    "consolidation_scope",
)
_LEGACY_PERIOD_BASES = frozenset({"Q", "H", "A"})
_QUARTER_PERIOD_ROLES = {
    "period_only": "current_quarter",
    "year_to_date": "year_to_date",
}
_PERIOD_BASES = _LEGACY_PERIOD_BASES | frozenset(_QUARTER_PERIOD_ROLES)
_SOURCE_SCALES = frozenset(
    {"units", "thousands", "millions", "billions", "trillions"}
)
_NATIVE_CURRENCIES = frozenset(
    {"AUD", "CAD", "CNY", "EUR", "GBP", "HKD", "IDR", "JPY", "NZD", "SGD", "USD"}
)
_NON_STATUTORY_MARKERS = (
    "adjusted",
    "underlying",
    "normalized",
    "normalised",
    "non-statutory",
    "non statutory",
    "pro forma",
    "pro-forma",
)
_DISCLOSURE_BASES = {
    "adjusted": ("adjusted",),
    "underlying": ("underlying",),
    "normalized": ("normalized", "normalised"),
    "pro_forma": ("pro forma", "pro-forma"),
}
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
_QUARTER_PERIOD_REASON_BY_BASIS = {
    "period_only": frozenset({"period_only_source_phrase"}),
    "year_to_date": frozenset({"year_to_date_source_phrase"}),
}
_QUARTER_PERIOD_END_REASONS = frozenset(
    {"reporting_period_end_explicit_date"}
)
_COMPARATIVE_QUARTER_TERMS = frozenset(
    {
        "comparative",
        "prior",
        "previous",
        "corresponding",
        "preceding",
        "pcp",
    }
)
_METADATA_DATE_HEADERS = frozenset(
    {
        "date",
        "announcement date",
        "lodgement date",
        "release date",
        "publication date",
        "report date",
    }
)
_EXPLICIT_METADATA_DATE_LABELS = _METADATA_DATE_HEADERS - {"date"}
_SUPERSESSION_TYPES = frozenset({"amendment", "restatement"})
_SUPERSESSION_EVIDENCE_FIELDS = (
    "source",
    "page_number",
    "row_ref",
    "matched_text",
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


def _supersession_id(
    superseding_observation_id: uuid.UUID,
    superseded_observation_id: uuid.UUID,
    relationship_type: str,
) -> uuid.UUID:
    identity = json.dumps(
        [
            "financial-observation-supersession-v1",
            str(superseding_observation_id),
            str(superseded_observation_id),
            relationship_type,
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


def _contains_label_term(label: str, term: str) -> bool:
    """Match a management-measure term as complete label words."""
    return re.search(
        rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
        label,
        flags=re.IGNORECASE,
    ) is not None


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
    evidence: Any,
    *,
    period_basis: str,
    reasons: frozenset[str],
    allow_legacy_period_type: bool,
    period_end: date | None = None,
) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    hits = evidence.get("hits")
    if not isinstance(hits, list):
        return False
    if allow_legacy_period_type:
        source_text_hits = [
            hit
            for hit in hits
            if isinstance(hit, Mapping) and hit.get("source") == "source_text"
        ]
        return any(
            (
                hit.get("period_basis", hit.get("period_type"))
                == period_basis
            )
            and hit.get("reason") in reasons
            for hit in source_text_hits
        )

    return all(
        isinstance(hit, Mapping)
        and hit.get("source") == "source_text"
        and hit.get("period_basis") == period_basis
        and hit.get("reason") in reasons
        and (
            period_end is None
            or _period_end(hit.get("period_end")) == period_end
        )
        and _quarter_quote_authenticates(
            hit.get("matched_text"),
            period_basis=period_basis,
            period_end=period_end,
        )
        for hit in hits
    ) and bool(hits)



def _quarter_period_semantics(value: Any) -> str | None:
    """Classify explicit quarter-column semantics, failing closed."""
    text = _required_text(value)
    if text is None:
        return None
    normalized = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    words = frozenset(normalized.split())
    if (
        words & _COMPARATIVE_QUARTER_TERMS
        or any(
            normalized == metadata_header
            or normalized.startswith(f"{metadata_header} ")
            for metadata_header in _METADATA_DATE_HEADERS
        )
    ):
        return None

    period_only = (
        re.search(r"\b(?:current quarter|quarter only|quarter ended)\b", normalized)
        is not None
        or re.search(
            r"\b(?:3|three) month(?:s)?(?: period| ended)?\b",
            normalized,
        )
        is not None
    )
    year_to_date = (
        "year to date" in normalized
        or "ytd" in words
        or "cumulative" in words
        or re.search(
            r"\b(?:6|six|9|nine|12|twelve) month(?:s)?"
            r"(?: cumulative| period| ended)?\b",
            normalized,
        )
        is not None
    )
    if period_only == year_to_date:
        return None
    return "period_only" if period_only else "year_to_date"


def _slash_date_status(value: str, period_end: date) -> tuple[bool, bool]:
    slash_dates = re.findall(
        r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)",
        value,
    )
    matched = False
    for first_text, second_text, year_text in slash_dates:
        first = int(first_text)
        second = int(second_text)
        year = int(year_text)
        candidates = set()
        for month, day in ((second, first), (first, second)):
            try:
                candidates.add(date(year, month, day))
            except ValueError:
                pass
        if len(candidates) > 1:
            return True, False
        if candidates == {period_end}:
            matched = True
    return False, matched


def _text_expresses_period_end(value: str, period_end: date) -> bool:
    month_name = period_end.strftime("%B")
    month_abbr = period_end.strftime("%b")
    day = str(period_end.day)
    year = str(period_end.year)
    numeric_date_patterns = (
        rf"{year}[-/.]0?{period_end.month}[-/.]0?{period_end.day}",
        rf"0?{period_end.day}[-.]0?{period_end.month}[-.]{year}",
        rf"0?{period_end.month}[-.]0?{period_end.day}[-.]{year}",
    )
    english_date_patterns = (
        rf"{day}(?:st|nd|rd|th)?\s+{month_name}\s+{year}",
        rf"{day}(?:st|nd|rd|th)?\s+{month_abbr}\.?\s+{year}",
        rf"{month_name}\s+{day}(?:st|nd|rd|th)?(?:,)?\s+{year}",
        rf"{month_abbr}\.?\s+{day}(?:st|nd|rd|th)?(?:,)?\s+{year}",
    )
    ambiguous_slash_date, matching_slash_date = _slash_date_status(
        value, period_end
    )
    return not ambiguous_slash_date and (
        matching_slash_date
        or any(
            re.search(rf"(?<!\d){pattern}(?!\d)", value, re.IGNORECASE)
            is not None
            for pattern in (*numeric_date_patterns, *english_date_patterns)
        )
    )


def _quarter_quote_authenticates(
    value: Any,
    *,
    period_basis: str,
    period_end: date | None,
) -> bool:
    quote = _required_text(value)
    normalized = (
        " ".join(re.findall(r"[a-z0-9]+", quote.lower()))
        if quote is not None
        else ""
    )
    return (
        quote is not None
        and not any(
            re.search(rf"\b{re.escape(label)}\b", normalized)
            for label in _EXPLICIT_METADATA_DATE_LABELS
        )
        and _quarter_period_semantics(quote) == period_basis
        and (
            period_end is None
            or _text_expresses_period_end(quote, period_end)
        )
    )


def _accepted_metric_context(
    document: Any,
    structured: Mapping[str, Any],
    metric: str,
    *,
    allow_legacy_period_type: bool,
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
    period_basis = _required_text(
        structured.get("period_basis")
        if not allow_legacy_period_type
        else structured.get("period_basis", structured.get("period_type"))
    )
    native_currency = _required_text(structured.get("currency"))
    provenance = provenance_by_metric.get(metric)
    source_period_type = _required_text(structured.get("source_period_type"))
    source_period_evidence = structured.get("source_period_evidence")
    period_end_evidence = structured.get("source_period_end_evidence")
    extraction_status = _required_text(
        structured.get("_observation_extraction_status")
    )
    claimed_accounting_basis = structured.get("accounting_basis")
    claimed_consolidation_scope = structured.get("consolidation_scope")
    claimed_trust_state = structured.get("trust_state")
    provenance_period_field = (
        "period_type" if allow_legacy_period_type else "period_basis"
    )
    if (
        value is None
        or period_end is None
        or period_basis not in _PERIOD_BASES
        or extraction_status != "ok"
        or claimed_accounting_basis not in (None, "statutory")
        or claimed_consolidation_scope not in (None, "consolidated")
        or claimed_trust_state not in (None, "accepted")
        or source_period_type != period_basis
        or not isinstance(source_period_evidence, Mapping)
        or (
            source_period_evidence.get("period_basis")
            if not allow_legacy_period_type
            else source_period_evidence.get(
                "period_basis", source_period_evidence.get("period_type")
            )
        )
        != period_basis
        or not _has_source_text_hit(
            source_period_evidence,
            period_basis=period_basis,
            reasons=(
                _QUARTER_PERIOD_REASON_BY_BASIS[period_basis]
                if period_basis in _QUARTER_PERIOD_ROLES
                else _EXPLICIT_PERIOD_REASONS
            ),
            allow_legacy_period_type=allow_legacy_period_type,
        )
        or not isinstance(provenance, Mapping)
        or any(
            field not in provenance
            for field in (*_PROVENANCE_FIELDS, provenance_period_field)
        )
        or any(
            provenance[field] in (None, "", "unknown")
            for field in (*_PROVENANCE_FIELDS, provenance_period_field)
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
    column_index = (
        source_cell.get("column_index")
        if isinstance(source_cell, Mapping)
        else None
    )
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
    bound_period_basis = None
    if isinstance(period_end_evidence, Mapping):
        bound_period_end = _period_end(period_end_evidence.get("period_end"))
        bound_period_basis = (
            period_end_evidence.get("period_basis")
            if not allow_legacy_period_type
            else period_end_evidence.get(
                "period_basis", period_end_evidence.get("period_type")
            )
        )
    if (
        document_id is None
        or (
            provenance.get("source_document_id") is not None
            and str(provenance["source_document_id"]) != str(document_id)
        )
        or provenance["metric"] != metric
        or provenance["accounting_basis"] != "statutory"
        or provenance["consolidation_scope"] != "consolidated"
        or source not in {context.value for context in contract.statement_contexts}
        or row_ref is None
        or "statutory" not in source_evidence_text
        or "consolidated" not in source_evidence_text
        or any(marker in source_evidence_text for marker in _NON_STATUTORY_MARKERS)
        or str(provenance[provenance_period_field]) != period_basis
        or str(provenance["period_end"]) != period_end.isoformat()
        or source_scale not in _SOURCE_SCALES
        or scale_source in (None, "unknown")
        or not isinstance(source_cell, Mapping)
        or (
            source_cell.get("raw_value") in (None, "")
            if allow_legacy_period_type
            else _required_text(source_cell.get("raw_value")) is None
        )
        or (
            source_cell.get("header_cell") in (None, "")
            if allow_legacy_period_type
            else _required_text(source_cell.get("header_cell")) is None
        )
        or (
            period_basis in _QUARTER_PERIOD_ROLES
            and (
                not isinstance(column_index, int)
                or isinstance(column_index, bool)
                or column_index < 0
                or source_cell.get("column_role")
                != _QUARTER_PERIOD_ROLES[period_basis]
                or _quarter_period_semantics(source_cell.get("header_cell"))
                != period_basis
            )
        )
        or observation_unit.lower() not in source_evidence_text
        or bound_period_end != period_end
        or (
            not allow_legacy_period_type
            and bound_period_basis != period_basis
        )
        or not _has_source_text_hit(
            period_end_evidence,
            period_basis=period_basis,
            reasons=(
                _QUARTER_PERIOD_END_REASONS
                if period_basis in _QUARTER_PERIOD_ROLES
                else _EXPLICIT_PERIOD_END_REASONS
            ),
            allow_legacy_period_type=allow_legacy_period_type,
            period_end=period_end,
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


def _accepted_disclosure_context(
    document: Any,
    disclosure: Mapping[str, Any],
) -> dict[str, Any] | None:
    metric = _required_text(disclosure.get("metric"))
    value = _numeric(disclosure.get("value"))
    period_end = _period_end(disclosure.get("period_end"))
    period_basis = _required_text(disclosure.get("period_basis"))
    accounting_basis = _required_text(disclosure.get("accounting_basis"))
    consolidation_scope = _required_text(disclosure.get("consolidation_scope"))
    source_label = _required_text(disclosure.get("source_label"))
    currency = _required_text(disclosure.get("currency"))
    scale = _required_text(disclosure.get("scale"))
    provenance = disclosure.get("provenance")
    reconciliation = disclosure.get("reconciliation_evidence")
    markers = _DISCLOSURE_BASES.get(accounting_basis or "")
    items = (
        reconciliation.get("items")
        if isinstance(reconciliation, Mapping)
        else None
    )
    document_id = getattr(document, "document_id", None)
    contract = (
        METRIC_CONTRACT_BY_CANONICAL_FIELD.get(metric)
        if metric is not None
        else None
    )
    valid_unit = (
        currency == "shares"
        if contract is not None
        and contract.unit_kind == MetricUnitKind.SHARE_COUNT_ABSOLUTE
        else currency in _NATIVE_CURRENCIES
    )
    if (
        metric not in CANONICAL_METRIC_FIELDS
        or value is None
        or period_end is None
        or period_basis not in _PERIOD_BASES
        or markers is None
        or consolidation_scope != "consolidated"
        or source_label is None
        or len(source_label) > 256
        or not any(_contains_label_term(source_label, marker) for marker in markers)
        or not valid_unit
        or scale != "units"
        or document_id is None
        or not isinstance(provenance, Mapping)
        or str(provenance.get("source_document_id")) != str(document_id)
        or provenance.get("metric") != metric
        or provenance.get("source_label") != source_label
        or provenance.get("accounting_basis") != accounting_basis
        or provenance.get("consolidation_scope") != consolidation_scope
        or not isinstance(reconciliation, Mapping)
        or reconciliation.get("source_label") != source_label
        or not isinstance(items, list)
        or not items
        or any(
            not isinstance(item, Mapping)
            or _required_text(item.get("label")) is None
            or _numeric(item.get("value")) is None
            or _required_text(item.get("source_ref")) is None
            for item in items
        )
    ):
        return None
    return {
        "metric": metric,
        "value": value,
        "period_end": period_end,
        "period_basis": period_basis,
        "accounting_basis": accounting_basis,
        "consolidation_scope": consolidation_scope,
        "source_label": source_label,
        "currency": currency,
        "scale": scale,
        "provenance": dict(provenance),
        "reconciliation_evidence": dict(reconciliation),
        "trust_state": "disclosed",
    }


def stage_financial_result_disclosures(
    db,
    *,
    document: Any,
    extraction_run: Any,
    structured: Mapping[str, Any],
) -> tuple[FinancialResultDisclosure, ...]:
    """Stage source-labelled non-statutory results outside canonical truth."""
    document_id = getattr(document, "document_id", None)
    run_id = getattr(extraction_run, "run_id", None)
    extractor_version = _required_text(
        getattr(extraction_run, "extractor_version", None)
    )
    ticker = _required_text(getattr(document, "ticker", None))
    candidates = structured.get("result_disclosures")
    if (
        document_id is None
        or run_id is None
        or extractor_version is None
        or ticker is None
        or not isinstance(candidates, list)
    ):
        return ()

    staged = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        context = _accepted_disclosure_context(document, candidate)
        if context is None:
            continue
        identity = _observation_id(
            source_document_id=document_id,
            extractor_version=extractor_version,
            ticker=ticker,
            metric=context["metric"],
            period_end=context["period_end"],
            period_basis=context["period_basis"],
            accounting_basis=(
                f'{context["accounting_basis"]}:{context["source_label"]}'
            ),
            currency=context["currency"],
            scale=context["scale"],
        )
        disclosure = FinancialResultDisclosure(
            disclosure_id=identity,
            source_document_id=document_id,
            extraction_run_id=run_id,
            extractor_version=extractor_version,
            ticker=ticker,
            **context,
        )
        values = {
            column.name: getattr(disclosure, column.name)
            for column in FinancialResultDisclosure.__table__.columns
        }
        statement = (
            insert(FinancialResultDisclosure)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_financial_result_disclosure_source_context"
            )
        )
        if db.execute(statement).rowcount:
            staged.append(disclosure)
    return tuple(staged)


def _explicit_supersession_evidence(
    value: Any,
    *,
    relationship_type: str,
    superseded_source_document_id: uuid.UUID,
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if any(
        value.get(field) in (None, "", "unknown")
        for field in _SUPERSESSION_EVIDENCE_FIELDS
    ):
        return None
    if str(value.get("superseded_source_document_id")) != str(
        superseded_source_document_id
    ):
        return None
    matched_text = _required_text(value.get("matched_text"))
    if matched_text is None:
        return None
    marker = "restat" if relationship_type == "restatement" else "amend"
    if re.search(rf"\b{marker}[a-z]*\b", matched_text, re.IGNORECASE) is None:
        return None
    return dict(value)


def stage_observation_supersessions(
    db,
    *,
    superseding_observations: tuple[FinancialObservation, ...],
    structured: Mapping[str, Any],
) -> tuple[FinancialObservationSupersession, ...]:
    """Stage explicit supersessions; the caller retains transaction ownership."""
    candidates = structured.get("observation_supersessions")
    if not isinstance(candidates, list):
        return ()

    staged = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        relationship_type = _required_text(candidate.get("relationship_type"))
        try:
            superseded_source_document_id = uuid.UUID(
                str(candidate.get("superseded_source_document_id"))
            )
        except (ValueError, AttributeError):
            continue
        metric = _required_text(candidate.get("metric"))
        period_end = _period_end(candidate.get("period_end"))
        period_basis = _required_text(candidate.get("period_basis"))
        matching_superseding = [
            observation
            for observation in superseding_observations
            if observation.metric == metric
            and observation.period_end == period_end
            and observation.period_basis == period_basis
        ]
        evidence = _explicit_supersession_evidence(
            candidate.get("evidence"),
            relationship_type=relationship_type or "",
            superseded_source_document_id=superseded_source_document_id,
        )
        if (
            relationship_type not in _SUPERSESSION_TYPES
            or len(matching_superseding) != 1
            or evidence is None
        ):
            continue
        superseding = matching_superseding[0]

        superseded_rows = (
            db.query(FinancialObservation)
            .filter(
                FinancialObservation.source_document_id
                == superseded_source_document_id,
                FinancialObservation.ticker == superseding.ticker,
                FinancialObservation.metric == superseding.metric,
                FinancialObservation.period_end == superseding.period_end,
                FinancialObservation.period_basis == superseding.period_basis,
                FinancialObservation.accounting_basis
                == superseding.accounting_basis,
                FinancialObservation.currency == superseding.currency,
                FinancialObservation.scale == superseding.scale,
                FinancialObservation.trust_state == "accepted",
            )
            .all()
        )
        if len(superseded_rows) != 1:
            continue
        superseded = superseded_rows[0]
        superseding_id = superseding.observation_id
        superseded_id = superseded.observation_id
        identity_fields = (
            "ticker",
            "metric",
            "period_end",
            "period_basis",
            "accounting_basis",
            "currency",
            "scale",
        )
        if (
            any(
                getattr(superseding, field) != getattr(superseded, field)
                for field in identity_fields
            )
            or superseding_id == superseded_id
            or getattr(superseded, "trust_state", None) != "accepted"
        ):
            continue

        relationship = FinancialObservationSupersession(
            supersession_id=_supersession_id(
                superseding_id, superseded_id, relationship_type
            ),
            superseding_observation_id=superseding_id,
            superseded_observation_id=superseded_id,
            relationship_type=relationship_type,
            evidence=evidence,
        )
        values = {
            column.name: getattr(relationship, column.name)
            for column in FinancialObservationSupersession.__table__.columns
        }
        statement = (
            insert(FinancialObservationSupersession)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_financial_observation_superseded_once"
            )
        )
        if db.execute(statement).rowcount:
            staged.append(relationship)
    return tuple(staged)


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

    period_members = structured.get("period_observations")
    if isinstance(period_members, list):
        members = tuple(
            member for member in period_members if isinstance(member, Mapping)
        )
        allow_legacy_period_type = False
    else:
        if structured.get("period_basis") in _QUARTER_PERIOD_ROLES:
            return ()
        members = (structured,)
        allow_legacy_period_type = True

    staged = []
    for member in members:
        for metric in CANONICAL_METRIC_FIELDS:
            context = _accepted_metric_context(
                document,
                member,
                metric,
                allow_legacy_period_type=allow_legacy_period_type,
            )
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
    stage_financial_result_disclosures(
        db,
        document=document,
        extraction_run=extraction_run,
        structured=structured,
    )
    stage_observation_supersessions(
        db,
        superseding_observations=tuple(staged),
        structured=structured,
    )
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
    revenue_payload.pop("result_disclosures", None)

    def revenue_only(payload: Mapping[str, Any]) -> dict[str, Any]:
        narrowed = dict(payload)
        narrowed.pop("result_disclosures", None)
        metrics = payload.get("metrics")
        provenance = payload.get("field_provenance")
        narrowed["metrics"] = (
            {"revenue": metrics.get("revenue")}
            if isinstance(metrics, Mapping)
            else metrics
        )
        narrowed["field_provenance"] = (
            {"revenue": provenance.get("revenue")}
            if isinstance(provenance, Mapping)
            else provenance
        )
        return narrowed

    members = structured.get("period_observations")
    if isinstance(members, list):
        revenue_payload["period_observations"] = [
            revenue_only(member)
            for member in members
            if isinstance(member, Mapping)
        ]
    else:
        revenue_payload = revenue_only(structured)
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


def _valid_supersessions(
    observations: list[Any],
    relationships: list[Any],
) -> dict[uuid.UUID, Any]:
    by_id = {
        observation.observation_id: observation
        for observation in observations
        if isinstance(getattr(observation, "observation_id", None), uuid.UUID)
    }
    identity_fields = (
        "ticker",
        "metric",
        "period_end",
        "period_basis",
        "accounting_basis",
        "currency",
        "scale",
    )
    valid = {}
    for relationship in relationships:
        superseded = by_id.get(
            getattr(relationship, "superseded_observation_id", None)
        )
        superseding = by_id.get(
            getattr(relationship, "superseding_observation_id", None)
        )
        relationship_type = getattr(relationship, "relationship_type", None)
        if (
            superseded is None
            or superseding is None
            or relationship_type not in _SUPERSESSION_TYPES
            or any(
                getattr(superseding, field) != getattr(superseded, field)
                for field in identity_fields
            )
            or _explicit_supersession_evidence(
                getattr(relationship, "evidence", None),
                relationship_type=relationship_type or "",
                superseded_source_document_id=superseded.source_document_id,
            )
            is None
        ):
            continue
        valid[superseded.observation_id] = relationship
    return valid


def _superseded_observation_ids(db, observations: list[Any]) -> set[uuid.UUID]:
    relationships = db.query(FinancialObservationSupersession).all()
    return set(_valid_supersessions(observations, relationships))


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
    superseded_ids = _superseded_observation_ids(db, rows)
    candidates: dict[
        tuple[date, str, str], set[tuple[Decimal, str, str]]
    ] = {}
    for row in rows:
        if getattr(row, "observation_id", None) in superseded_ids:
            continue
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


def accepted_observation_periods(db, *, ticker: str) -> tuple[dict[str, Any], ...]:
    """Return deterministic sparse quarter/YTD profile rows when uncontested."""
    rows = (
        db.query(FinancialObservation)
        .filter(
            FinancialObservation.ticker == ticker,
            FinancialObservation.period_basis.in_(_QUARTER_PERIOD_ROLES),
            FinancialObservation.metric.in_(CANONICAL_METRIC_FIELDS),
            FinancialObservation.accounting_basis == "statutory",
            FinancialObservation.trust_state == "accepted",
        )
        .all()
    )
    superseded_ids = _superseded_observation_ids(db, rows)
    candidates: dict[
        tuple[date, str, str], set[tuple[Decimal, str, str]]
    ] = {}
    for row in rows:
        if getattr(row, "observation_id", None) in superseded_ids:
            continue
        key = (row.period_end, row.period_basis, row.metric)
        candidates.setdefault(key, set()).add(
            (Decimal(row.value), row.currency, row.scale)
        )

    periods: dict[tuple[date, str], dict[str, Any]] = {}
    for (period_end, period_basis, metric), truths in candidates.items():
        if len(truths) != 1:
            continue
        value, currency, scale = next(iter(truths))
        if scale != "units":
            continue
        item = periods.setdefault(
            (period_end, period_basis),
            {
                "ticker": ticker,
                "period_end": period_end,
                "period_type": period_basis,
                "period_basis": period_basis,
                "observation_only": True,
            },
        )
        item[metric] = str(value)
        item.setdefault("metric_units", {})[metric] = currency

    return tuple(
        periods[key]
        for key in sorted(
            periods, key=lambda item: (item[0], item[1]), reverse=True
        )
    )


def accepted_observation_history(
    db, *, ticker: str
) -> tuple[dict[str, Any], ...]:
    """Return accepted observations plus immutable supersession provenance."""
    observations = (
        db.query(FinancialObservation)
        .filter(
            FinancialObservation.ticker == ticker,
            FinancialObservation.metric.in_(CANONICAL_METRIC_FIELDS),
            FinancialObservation.accounting_basis == "statutory",
            FinancialObservation.trust_state == "accepted",
        )
        .all()
    )
    relationships = db.query(FinancialObservationSupersession).all()
    by_superseded = _valid_supersessions(observations, relationships)
    history = []
    for observation in observations:
        relationship = by_superseded.get(observation.observation_id)
        history.append(
            {
                "observation_id": str(observation.observation_id),
                "ticker": observation.ticker,
                "metric": observation.metric,
                "value": str(observation.value),
                "period_end": observation.period_end,
                "period_basis": observation.period_basis,
                "accounting_basis": observation.accounting_basis,
                "currency": observation.currency,
                "scale": observation.scale,
                "source_document_id": str(observation.source_document_id),
                "extraction_run_id": str(observation.extraction_run_id),
                "extractor_version": observation.extractor_version,
                "provenance": observation.provenance,
                "trust_state": observation.trust_state,
                "active": relationship is None,
                "superseded_by": (
                    str(relationship.superseding_observation_id)
                    if relationship is not None
                    else None
                ),
                "supersession_type": (
                    relationship.relationship_type
                    if relationship is not None
                    else None
                ),
                "supersession_evidence": (
                    relationship.evidence if relationship is not None else None
                ),
            }
        )
    return tuple(
        sorted(
            history,
            key=lambda item: (
                item["period_end"],
                item["period_basis"],
                item["metric"],
                item["observation_id"],
            ),
            reverse=True,
        )
    )
