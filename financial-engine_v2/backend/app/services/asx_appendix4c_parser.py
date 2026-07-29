"""Deterministic ASX Appendix 4C candidate extraction.

This module operates on already-extracted table rows. It deliberately does not
write canonical financial truth, route production extraction, or call LLM/runtime
services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Protocol


PARSER_METHOD = "appendix4c_deterministic_v1"
FALLBACK_METHOD = "appendix4c_explicit_fallback_v1"
DATA_MISSING = "DATA_MISSING"


class Appendix4CTableLike(Protocol):
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]


@dataclass(frozen=True)
class Appendix4CEvidence:
    page: int
    table_index: int
    row_index: int
    column_index: int
    row_label: str
    column_label: str
    line_item: str
    source_span: str


@dataclass(frozen=True)
class Appendix4CCandidate:
    metric_name: str
    value: Decimal
    raw_value: str
    unit: str
    currency: str | None
    scale: str | None
    period_label: str
    column_role: str
    document_type: str
    parser_method: str
    confidence: float
    trust_status: str
    status: str
    canonical_write: bool
    evidence: Appendix4CEvidence
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": float(self.value),
            "raw_value": self.raw_value,
            "unit": self.unit,
            "currency": self.currency,
            "scale": self.scale,
            "period_label": self.period_label,
            "column_role": self.column_role,
            "document_type": self.document_type,
            "parser_method": self.parser_method,
            "confidence": self.confidence,
            "trust_status": self.trust_status,
            "status": self.status,
            "canonical_write": self.canonical_write,
            "evidence": self.evidence.__dict__,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Appendix4CMissing:
    metric_name: str
    column_role: str
    status: str
    failure_reason: str
    expected_line_items: list[str]
    parser_method: str = PARSER_METHOD

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Appendix4CParseResult:
    document_type: str
    status: str
    parser_method: str
    canonical_write: bool
    candidates: list[Appendix4CCandidate]
    missing: list[Appendix4CMissing]
    tables_seen: int
    warnings: list[str] = field(default_factory=list)

    def metric_map(self, column_role: str = "current_quarter") -> dict[str, Appendix4CCandidate]:
        mapped: dict[str, Appendix4CCandidate] = {}
        for candidate in self.candidates:
            if candidate.column_role != column_role:
                continue
            mapped.setdefault(candidate.metric_name, candidate)
        return mapped

    def missing_map(self, column_role: str = "current_quarter") -> dict[str, Appendix4CMissing]:
        mapped: dict[str, Appendix4CMissing] = {}
        for missing in self.missing:
            if missing.column_role != column_role:
                continue
            mapped.setdefault(missing.metric_name, missing)
        return mapped

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "status": self.status,
            "parser_method": self.parser_method,
            "canonical_write": self.canonical_write,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "missing": [missing.to_dict() for missing in self.missing],
            "tables_seen": self.tables_seen,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Appendix4CFallbackValue:
    """Explicit, caller-supplied fallback value.

    This is a validation seam, not a model invocation seam. The parser never
    obtains fallback values itself.
    """

    profile_field: str
    value: Decimal
    raw_value: str
    unit: str
    currency: str | None
    scale: str
    period_basis: str
    column_role: str
    period_evidence: str
    currency_evidence: str
    scale_evidence: str
    page: int
    table_index: int
    row_index: int
    column_index: int
    row_label: str
    column_label: str
    line_item: str
    source_span: str


@dataclass(frozen=True)
class Appendix4CCashObservation:
    profile_field: str
    value: Decimal
    raw_value: str
    unit: str
    currency: str | None
    scale: str
    period_basis: str
    period_evidence: str
    currency_evidence: str
    scale_evidence: str
    source_method: str
    evidence: Appendix4CEvidence

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["value"] = float(self.value)
        payload["evidence"] = self.evidence.__dict__.copy()
        return payload


@dataclass(frozen=True)
class Appendix4CCashProfile:
    document_type: str
    status: str
    canonical_write: bool
    observations: list[Appendix4CCashObservation]
    missing: list[Appendix4CMissing]
    fallback_considered: bool
    warnings: list[str] = field(default_factory=list)

    def observation_map(
        self,
        period_basis: str = "period_only",
    ) -> dict[str, Appendix4CCashObservation]:
        mapped: dict[str, Appendix4CCashObservation] = {}
        for observation in self.observations:
            if observation.period_basis != period_basis:
                continue
            mapped.setdefault(observation.profile_field, observation)
        return mapped

    def missing_map(
        self,
        period_basis: str = "period_only",
    ) -> dict[str, Appendix4CMissing]:
        role = _BASIS_TO_ROLE.get(period_basis)
        if role is None:
            return {}
        mapped: dict[str, Appendix4CMissing] = {}
        for missing in self.missing:
            if missing.column_role != role:
                continue
            mapped.setdefault(missing.metric_name, missing)
        return mapped

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "status": self.status,
            "canonical_write": self.canonical_write,
            "observations": [observation.to_dict() for observation in self.observations],
            "missing": [missing.to_dict() for missing in self.missing],
            "fallback_considered": self.fallback_considered,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class _CellMatch:
    value: Decimal
    raw_value: str
    column_index: int
    column_label: str
    column_role: str


@dataclass(frozen=True)
class _RowMatch:
    line_item: str
    row_label: str
    cells: list[_CellMatch]
    evidence_by_column: dict[int, Appendix4CEvidence]
    currency: str | None
    scale: str | None


@dataclass(frozen=True)
class _TableContext:
    headers: list[str]
    roles: dict[int, str]
    currency: str | None
    scale: str | None


_LINE_ITEM_RE = re.compile(r"\b([1-8])\.(\d+)(?:\(([a-z])\))?(?=\W|$)", re.IGNORECASE)
_NUMERIC_RE = re.compile(r"^\(?-?\$?\s*[0-9][0-9,\s]*(?:\.[0-9]+)?\)?$")
_MISSING_VALUE_TOKENS = {"", "-", "--", "n/a", "na", "nil"}

_LINE_TO_METRIC: dict[str, tuple[str, str, str]] = {
    "1.1": ("cash_receipts", "review_only", "cash receipts are not revenue"),
    "1.9": ("operating_cf", "candidate", ""),
    "2.1(c)": ("capex", "candidate", ""),
    "2.6": ("investing_cf", "candidate", ""),
    "3.10": ("financing_cf", "candidate", ""),
    "4.6": ("cash_end", "candidate", ""),
    "5.5": ("cash_end", "candidate", ""),
    "7.5": ("unused_financing", "candidate", ""),
    "8.8": ("estimated_funding_quarters", "candidate", ""),
}

_EXPECTED_METRIC_LINES: dict[str, list[str]] = {
    "operating_cf": ["1.9"],
    "investing_cf": ["2.6"],
    "financing_cf": ["3.10"],
    "cash_end": ["4.6", "5.5"],
}

_VALUE_COLUMN_ROLES = {"current_quarter", "year_to_date", "value"}
_ROLE_TO_BASIS = {
    "current_quarter": "period_only",
    "year_to_date": "year_to_date",
    "value": "period_only",
}
_BASIS_TO_ROLE = {
    "period_only": "current_quarter",
    "year_to_date": "year_to_date",
}
_PROFILE_FIELD_BY_METRIC = {
    "cash_receipts": "customer_receipts",
    "operating_cf": "operating_cf",
    "investing_cf": "investing_cf",
    "financing_cf": "financing_cf",
    "capex": "capex",
    "cash_end": "cash_end",
    "unused_financing": "unused_financing",
    "estimated_funding_quarters": "estimated_funding_quarters",
}
_PROFILE_FIELDS = frozenset(_PROFILE_FIELD_BY_METRIC.values())
_FORBIDDEN_APPENDIX4C_FIELDS = frozenset(
    {"revenue", "profit", "np_attributable", "npat", "net_debt"}
)
_FALLBACK_LINE_ITEMS = {
    "customer_receipts": frozenset({"1.1"}),
    "operating_cf": frozenset({"1.9"}),
    "investing_cf": frozenset({"2.6"}),
    "financing_cf": frozenset({"3.10"}),
    "capex": frozenset({"2.1(c)"}),
    "cash_end": frozenset({"4.6", "5.5"}),
    "unused_financing": frozenset({"7.5"}),
    "estimated_funding_quarters": frozenset({"8.8"}),
}


def parse_appendix4c_tables(tables: list[Appendix4CTableLike]) -> Appendix4CParseResult:
    """Parse Appendix 4C candidate metrics from structured tables.

    The result is intentionally candidate-only and report-local. Callers must
    run evidence, validation, and promotion gates before any canonical write.
    """

    if not _looks_like_appendix4c(tables):
        return Appendix4CParseResult(
            document_type="unknown",
            status="not_applicable",
            parser_method=PARSER_METHOD,
            canonical_write=False,
            candidates=[],
            missing=[],
            tables_seen=len(tables),
        )

    candidates: list[Appendix4CCandidate] = []
    previous_context: _TableContext | None = None

    for table_index, table in enumerate(tables):
        raw_headers = _headers_for(table)
        raw_roles = _column_roles(raw_headers)
        context = _resolve_table_context(
            table=table,
            raw_headers=raw_headers,
            raw_roles=raw_roles,
            previous_context=previous_context,
        )
        if raw_roles and _headers_are_informative(raw_headers):
            previous_context = context
        for row_index, row in enumerate(table.rows):
            row_match = _match_row(
                table=table,
                table_index=table_index,
                row_index=row_index,
                row=row,
                headers=context.headers,
                roles=context.roles,
                currency=context.currency,
                scale=context.scale,
            )
            if row_match is None:
                continue

            metric_config = _LINE_TO_METRIC.get(row_match.line_item)
            if metric_config is None:
                continue
            metric_name, status, warning = metric_config
            for cell in row_match.cells:
                warnings = [warning] if warning else []
                candidates.append(
                    Appendix4CCandidate(
                        metric_name=metric_name,
                        value=cell.value,
                        raw_value=cell.raw_value,
                        unit="currency",
                        currency=row_match.currency,
                        scale=row_match.scale,
                        period_label=cell.column_label,
                        column_role=cell.column_role,
                        document_type="appendix_4c",
                        parser_method=PARSER_METHOD,
                        confidence=0.94 if status == "candidate" else 0.82,
                        trust_status=status,
                        status=status,
                        canonical_write=False,
                        evidence=row_match.evidence_by_column[cell.column_index],
                        warnings=warnings,
                    )
                )

    missing = _missing_for(candidates)
    return Appendix4CParseResult(
        document_type="appendix_4c",
        status="parsed" if candidates else "no_metrics",
        parser_method=PARSER_METHOD,
        canonical_write=False,
        candidates=candidates,
        missing=missing,
        tables_seen=len(tables),
    )


def build_appendix4c_cash_profile(
    tables: list[Appendix4CTableLike],
    *,
    fallback_values: list[Appendix4CFallbackValue] | None = None,
) -> Appendix4CCashProfile:
    """Build an evidence-gated Appendix 4C cash profile.

    Deterministic table parsing always runs first. Explicit fallback values are
    considered only for profile-field/period pairs that deterministic parsing
    did not accept.
    """

    parsed = parse_appendix4c_tables(tables)
    if parsed.document_type != "appendix_4c":
        return Appendix4CCashProfile(
            document_type=parsed.document_type,
            status="not_applicable",
            canonical_write=False,
            observations=[],
            missing=[],
            fallback_considered=False,
        )

    observations: list[Appendix4CCashObservation] = []
    occupied: set[tuple[str, str]] = set()
    warnings: list[str] = []

    for candidate in parsed.candidates:
        observation = _observation_from_candidate(candidate)
        if observation is None:
            continue
        key = (observation.profile_field, observation.period_basis)
        if key in occupied:
            continue
        occupied.add(key)
        observations.append(observation)

    supplied_fallback = fallback_values or []
    for fallback in supplied_fallback:
        if fallback.profile_field in _FORBIDDEN_APPENDIX4C_FIELDS:
            warnings.append(f"forbidden fallback field rejected: {fallback.profile_field}")
            continue
        key = (fallback.profile_field, fallback.period_basis)
        if key in occupied:
            continue
        observation = _observation_from_fallback(fallback)
        if observation is None:
            warnings.append(f"invalid fallback value rejected: {fallback.profile_field}")
            continue
        occupied.add(key)
        observations.append(observation)

    observations.sort(
        key=lambda item: (
            item.period_basis,
            item.profile_field,
            item.evidence.page,
            item.evidence.table_index,
            item.evidence.row_index,
            item.evidence.column_index,
        )
    )
    bases = {observation.period_basis for observation in observations}
    if "period_only" not in bases:
        bases.add("period_only")
    missing = _profile_missing(occupied, bases)
    period_only_fields = {
        observation.profile_field
        for observation in observations
        if observation.period_basis == "period_only"
    }
    status = "complete" if period_only_fields == _PROFILE_FIELDS else "partial"
    if not observations:
        status = "no_values"
    return Appendix4CCashProfile(
        document_type="appendix_4c",
        status=status,
        canonical_write=False,
        observations=observations,
        missing=missing,
        fallback_considered=bool(supplied_fallback),
        warnings=warnings,
    )


def _observation_from_candidate(
    candidate: Appendix4CCandidate,
) -> Appendix4CCashObservation | None:
    profile_field = _PROFILE_FIELD_BY_METRIC.get(candidate.metric_name)
    period_basis = _ROLE_TO_BASIS.get(candidate.column_role)
    if profile_field is None or period_basis is None:
        return None
    if not candidate.period_label.strip():
        return None
    if profile_field == "estimated_funding_quarters":
        return Appendix4CCashObservation(
            profile_field=profile_field,
            value=candidate.value,
            raw_value=candidate.raw_value,
            unit="quarters",
            currency=None,
            scale="units",
            period_basis=period_basis,
            period_evidence=candidate.period_label,
            currency_evidence="not_applicable: unit is quarters",
            scale_evidence="units: explicit Appendix 4C item 8.8 value",
            source_method=PARSER_METHOD,
            evidence=candidate.evidence,
        )
    if candidate.currency is None or candidate.scale is None:
        return None
    return Appendix4CCashObservation(
        profile_field=profile_field,
        value=candidate.value,
        raw_value=candidate.raw_value,
        unit="currency",
        currency=candidate.currency,
        scale=candidate.scale,
        period_basis=period_basis,
        period_evidence=candidate.period_label,
        currency_evidence=(
            f"resolved table/header context: {candidate.currency}; "
            f"source column: {candidate.period_label}"
        ),
        scale_evidence=(
            f"resolved table/header context: {candidate.scale}; "
            f"source column: {candidate.period_label}"
        ),
        source_method=PARSER_METHOD,
        evidence=candidate.evidence,
    )


def _observation_from_fallback(
    fallback: Appendix4CFallbackValue,
) -> Appendix4CCashObservation | None:
    if fallback.profile_field not in _PROFILE_FIELDS:
        return None
    if fallback.line_item not in _FALLBACK_LINE_ITEMS[fallback.profile_field]:
        return None
    if _ROLE_TO_BASIS.get(fallback.column_role) != fallback.period_basis:
        return None
    if fallback.period_basis not in _BASIS_TO_ROLE:
        return None
    if min(
        fallback.page,
        fallback.table_index,
        fallback.row_index,
        fallback.column_index,
    ) < 0:
        return None
    required_text = (
        fallback.raw_value,
        fallback.period_evidence,
        fallback.currency_evidence,
        fallback.scale_evidence,
        fallback.row_label,
        fallback.column_label,
        fallback.source_span,
    )
    if any(not str(value).strip() for value in required_text):
        return None
    if (
        not fallback.value.is_finite()
        or _parse_decimal(fallback.raw_value) != fallback.value
        or _line_item(fallback.row_label) != fallback.line_item
    ):
        return None

    if fallback.profile_field == "estimated_funding_quarters":
        if (
            fallback.unit != "quarters"
            or fallback.currency is not None
            or fallback.scale != "units"
        ):
            return None
    elif (
        fallback.unit != "currency"
        or not fallback.currency
        or fallback.scale not in {"units", "thousands", "millions", "billions"}
    ):
        return None

    evidence = Appendix4CEvidence(
        page=fallback.page,
        table_index=fallback.table_index,
        row_index=fallback.row_index,
        column_index=fallback.column_index,
        row_label=fallback.row_label,
        column_label=fallback.column_label,
        line_item=fallback.line_item,
        source_span=fallback.source_span,
    )
    return Appendix4CCashObservation(
        profile_field=fallback.profile_field,
        value=fallback.value,
        raw_value=fallback.raw_value,
        unit=fallback.unit,
        currency=fallback.currency,
        scale=fallback.scale,
        period_basis=fallback.period_basis,
        period_evidence=fallback.period_evidence,
        currency_evidence=fallback.currency_evidence,
        scale_evidence=fallback.scale_evidence,
        source_method=FALLBACK_METHOD,
        evidence=evidence,
    )


def _profile_missing(
    occupied: set[tuple[str, str]],
    bases: set[str],
) -> list[Appendix4CMissing]:
    missing: list[Appendix4CMissing] = []
    for period_basis in sorted(bases):
        role = _BASIS_TO_ROLE.get(period_basis)
        if role is None:
            continue
        for profile_field in sorted(_PROFILE_FIELDS):
            if (profile_field, period_basis) in occupied:
                continue
            missing.append(
                Appendix4CMissing(
                    metric_name=profile_field,
                    column_role=role,
                    status=DATA_MISSING,
                    failure_reason=(
                        f"{DATA_MISSING}: {period_basis} Appendix 4C evidence-gated "
                        "profile value not found"
                    ),
                    expected_line_items=sorted(_FALLBACK_LINE_ITEMS[profile_field]),
                )
            )
    return missing


def _looks_like_appendix4c(tables: list[Appendix4CTableLike]) -> bool:
    text = "\n".join(
        [
            " ".join(str(getattr(table, "caption", "")) for table in tables),
            " ".join(str(cell) for table in tables for row in table.rows[:12] for cell in row),
            " ".join(str(cell) for table in tables for cell in getattr(table, "headers", [])),
        ]
    ).lower()
    if "appendix 5b" in text:
        return False
    if "appendix 4c" in text:
        return True
    if "quarterly cash flow report" in text and "rule 4.7b" in text:
        return True

    line_items = set(_LINE_ITEM_RE.findall(text))
    flattened = {".".join((major, minor)) for major, minor, _subitem in line_items}
    return len({"1.1", "1.9", "2.6", "3.10", "4.6", "5.5"} & flattened) >= 4


def _headers_for(table: Appendix4CTableLike) -> list[str]:
    headers = [str(cell or "").strip() for cell in getattr(table, "headers", [])]
    if headers:
        return headers
    if table.rows:
        return [str(cell or "").strip() for cell in table.rows[0]]
    return []


def _detect_currency(table: Appendix4CTableLike, headers: list[str]) -> str | None:
    text = " ".join([getattr(table, "caption", ""), *headers, *_flatten_rows(table.rows[:3])])
    if re.search(r"\bUSD\b|US\$|\$US", text, re.IGNORECASE):
        return "USD"
    if re.search(r"\bNZD\b|NZ\$|\$NZ", text, re.IGNORECASE):
        return "NZD"
    if re.search(r"\bAUD\b|A\$|\$A", text, re.IGNORECASE):
        return "AUD"
    return None


def _detect_scale(table: Appendix4CTableLike, headers: list[str]) -> str | None:
    text = " ".join([getattr(table, "caption", ""), *headers, *_flatten_rows(table.rows[:3])])
    if re.search(r"(?:\$A?|US\$|\$US|NZ\$|\$NZ)?'?000,000\b|millions?|\b(?:A|US|NZ)?\$m\b", text, re.IGNORECASE):
        return "millions"
    if re.search(r"(?:\$A?|US\$|\$US|NZ\$|\$NZ)?'?000\b|thousands?", text, re.IGNORECASE):
        return "thousands"
    return None


def _column_roles(headers: list[str]) -> dict[int, str]:
    roles: dict[int, str] = {}
    for idx, header in enumerate(headers):
        normalized = _normalize(header)
        if "current quarter" in normalized or "current qtr" in normalized:
            roles[idx] = "current_quarter"
        elif "year to date" in normalized or "ytd" in normalized:
            roles[idx] = "year_to_date"
        elif re.search(r"(?:\$A?|US\$|\$US|NZ\$|\$NZ)?'?000", header, re.IGNORECASE):
            roles[idx] = "value"
    return roles


def _resolve_table_context(
    *,
    table: Appendix4CTableLike,
    raw_headers: list[str],
    raw_roles: dict[int, str],
    previous_context: _TableContext | None,
) -> _TableContext:
    currency = _detect_currency(table, raw_headers)
    scale = _detect_scale(table, raw_headers)
    if raw_roles and _headers_are_informative(raw_headers):
        return _TableContext(
            headers=raw_headers,
            roles=raw_roles,
            currency=currency,
            scale=scale,
        )
    if previous_context is not None and _can_inherit_context(raw_headers, previous_context):
        return _TableContext(
            headers=previous_context.headers,
            roles=previous_context.roles,
            currency=currency or previous_context.currency,
            scale=scale or previous_context.scale,
        )
    return _TableContext(headers=raw_headers, roles=raw_roles, currency=currency, scale=scale)


def _headers_are_informative(headers: list[str]) -> bool:
    return any(not _is_uninformative_header(header) for header in headers)


def _can_inherit_context(raw_headers: list[str], previous_context: _TableContext) -> bool:
    if not previous_context.roles:
        return False
    if not raw_headers:
        return False
    if not all(_is_uninformative_header(header) for header in raw_headers):
        return False
    return max(previous_context.roles) < len(raw_headers)


def _is_uninformative_header(header: str) -> bool:
    text = str(header or "").strip()
    return not text or bool(re.fullmatch(r"\d+", text))


def _match_row(
    *,
    table: Appendix4CTableLike,
    table_index: int,
    row_index: int,
    row: list[str],
    headers: list[str],
    roles: dict[int, str],
    currency: str | None,
    scale: str | None,
) -> _RowMatch | None:
    row_text = " ".join(str(cell or "") for cell in row).strip()
    line_item = _line_item(row_text)
    if line_item is None:
        return None

    numeric_cells: list[_CellMatch] = []
    for column_index, cell in enumerate(row):
        raw_value = str(cell or "").strip()
        if _line_item(raw_value) == line_item:
            continue
        parsed = _parse_decimal(raw_value)
        if parsed is None:
            continue
        column_role = roles.get(column_index)
        if column_role is None and not roles:
            column_role = "current_quarter" if not numeric_cells else "value"
        if column_role not in _VALUE_COLUMN_ROLES:
            continue
        column_label = _column_label(headers, column_index, column_role)
        numeric_cells.append(
            _CellMatch(
                value=parsed,
                raw_value=raw_value,
                column_index=column_index,
                column_label=column_label,
                column_role=column_role,
            )
        )

    if not numeric_cells:
        return None

    row_label = _row_label(row)
    evidence_by_column = {
        cell.column_index: Appendix4CEvidence(
            page=int(getattr(table, "page_number", 0) or 0),
            table_index=table_index,
            row_index=row_index,
            column_index=cell.column_index,
            row_label=row_label,
            column_label=cell.column_label,
            line_item=line_item,
            source_span=f"page_{getattr(table, 'page_number', 0)}:table_{table_index}:row_{row_index}:col_{cell.column_index}",
        )
        for cell in numeric_cells
    }
    return _RowMatch(
        line_item=line_item,
        row_label=row_label,
        cells=numeric_cells,
        evidence_by_column=evidence_by_column,
        currency=currency,
        scale=scale,
    )


def _missing_for(candidates: list[Appendix4CCandidate]) -> list[Appendix4CMissing]:
    present = {
        (candidate.metric_name, candidate.column_role)
        for candidate in candidates
        if candidate.status == "candidate"
    }
    column_roles = {"current_quarter"}
    if any(candidate.column_role == "year_to_date" for candidate in candidates):
        column_roles.add("year_to_date")

    missing: list[Appendix4CMissing] = []
    for metric_name, expected_lines in _EXPECTED_METRIC_LINES.items():
        for column_role in sorted(column_roles):
            if (metric_name, column_role) in present:
                continue
            missing.append(
                Appendix4CMissing(
                    metric_name=metric_name,
                    column_role=column_role,
                    status=DATA_MISSING,
                    failure_reason=f"{DATA_MISSING}: {column_role} Appendix 4C line value not found",
                    expected_line_items=expected_lines,
                )
            )
    return missing


def _line_item(row_text: str) -> str | None:
    match = _LINE_ITEM_RE.search(row_text)
    if match is None:
        return None
    major, minor, subitem = match.groups()
    line = f"{major}.{minor}"
    if subitem:
        line = f"{line}({subitem.lower()})"
    return line


def _parse_decimal(raw_value: str) -> Decimal | None:
    normalized = raw_value.strip().lower()
    if normalized in _MISSING_VALUE_TOKENS:
        return None
    if not _NUMERIC_RE.match(raw_value.strip()):
        return None

    negative = normalized.startswith("(") and normalized.endswith(")")
    cleaned = (
        raw_value.replace("$", "")
        .replace(",", "")
        .replace(" ", "")
        .replace("(", "")
        .replace(")", "")
    )
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if negative and value > 0:
        value = -value
    return value


def _row_label(row: list[str]) -> str:
    label_cells = []
    for cell in row:
        text = str(cell or "").strip()
        if not text:
            continue
        if _line_item(text) is None and _parse_decimal(text) is not None:
            continue
        label_cells.append(text)
    return " | ".join(label_cells)


def _column_label(headers: list[str], column_index: int, column_role: str) -> str:
    if 0 <= column_index < len(headers) and headers[column_index].strip():
        return headers[column_index].strip()
    return column_role


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _flatten_rows(rows: list[list[str]]) -> list[str]:
    return [str(cell or "") for row in rows for cell in row]
