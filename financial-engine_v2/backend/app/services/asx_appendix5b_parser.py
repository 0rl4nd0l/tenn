"""Deterministic ASX Appendix 5B candidate extraction.

This module operates on already-extracted table rows. It deliberately does not
write canonical financial truth or call LLM/runtime services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Protocol


PARSER_METHOD = "appendix5b_deterministic_v1"
DATA_MISSING = "DATA_MISSING"


class Appendix5BTableLike(Protocol):
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]


@dataclass(frozen=True)
class Appendix5BEvidence:
    page: int
    table_index: int
    row_index: int
    column_index: int
    row_label: str
    column_label: str
    line_item: str
    source_span: str


@dataclass(frozen=True)
class Appendix5BCandidate:
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
    evidence: Appendix5BEvidence
    component_evidence: list[Appendix5BEvidence] = field(default_factory=list)

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
            "evidence": self.evidence.__dict__,
            "component_evidence": [ev.__dict__ for ev in self.component_evidence],
        }


@dataclass(frozen=True)
class Appendix5BMissing:
    metric_name: str
    column_role: str
    status: str
    failure_reason: str
    expected_line_items: list[str]
    parser_method: str = PARSER_METHOD

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Appendix5BParseResult:
    document_type: str
    status: str
    parser_method: str
    candidates: list[Appendix5BCandidate]
    missing: list[Appendix5BMissing]
    tables_seen: int

    def metric_map(self, column_role: str = "current_quarter") -> dict[str, Appendix5BCandidate]:
        mapped: dict[str, Appendix5BCandidate] = {}
        for candidate in self.candidates:
            if candidate.column_role != column_role:
                continue
            mapped.setdefault(candidate.metric_name, candidate)
        return mapped

    def missing_map(self, column_role: str = "current_quarter") -> dict[str, Appendix5BMissing]:
        mapped: dict[str, Appendix5BMissing] = {}
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
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "missing": [missing.to_dict() for missing in self.missing],
            "tables_seen": self.tables_seen,
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
    evidence_by_column: dict[int, Appendix5BEvidence]
    currency: str | None
    scale: str | None


@dataclass(frozen=True)
class _TableContext:
    headers: list[str]
    roles: dict[int, str]
    currency: str | None
    scale: str | None


_LINE_ITEM_RE = re.compile(r"\b([1-5])\.(\d+)(?:\(([a-z])\))?(?=\W|$)", re.IGNORECASE)
_NUMERIC_RE = re.compile(r"^\(?-?\$?\s*[0-9][0-9,\s]*(?:\.[0-9]+)?\)?$")
_MISSING_VALUE_TOKENS = {"", "-", "--", "n/a", "na", "nil"}

_LINE_TO_METRIC: dict[str, str] = {
    "1.9": "operating_cf",
    "2.6": "investing_cf",
    "3.10": "financing_cf",
    "4.6": "cash_end",
    "5.5": "cash_end",
}

_EXPECTED_METRIC_LINES: dict[str, list[str]] = {
    "operating_cf": ["1.9"],
    "investing_cf": ["2.6"],
    "financing_cf": ["3.10"],
    "cash_end": ["4.6", "5.5"],
    "capex": ["2.1(c)", "2.1(d)"],
}

_CAPEX_LINE_ITEMS = {"2.1(c)", "2.1(d)"}
_RECONCILIATION_LINE_TO_METRIC: dict[str, str] = {
    "4.2": "operating_cf",
    "4.3": "investing_cf",
    "4.4": "financing_cf",
}
_VALUE_COLUMN_ROLES = {"current_quarter", "year_to_date", "value"}


def parse_appendix5b_tables(tables: list[Appendix5BTableLike]) -> Appendix5BParseResult:
    """Parse Appendix 5B candidate metrics from structured tables.

    The result is intentionally candidate-only. Callers must run evidence,
    validation, and promotion gates before any canonical write.
    """

    if not _looks_like_appendix5b(tables):
        return Appendix5BParseResult(
            document_type="unknown",
            status="not_applicable",
            parser_method=PARSER_METHOD,
            candidates=[],
            missing=[],
            tables_seen=len(tables),
        )

    candidates: list[Appendix5BCandidate] = []
    row_matches: list[_RowMatch] = []
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
        headers = context.headers
        currency = context.currency
        scale = context.scale
        roles = context.roles
        if raw_roles and _headers_are_informative(raw_headers):
            previous_context = context
        for row_index, row in enumerate(table.rows):
            row_match = _match_row(
                table=table,
                table_index=table_index,
                row_index=row_index,
                row=row,
                headers=headers,
                roles=roles,
                currency=currency,
                scale=scale,
            )
            if row_match is None:
                continue
            row_matches.append(row_match)

            metric_name = _LINE_TO_METRIC.get(row_match.line_item)
            if metric_name:
                for cell in row_match.cells:
                    candidates.append(
                        Appendix5BCandidate(
                            metric_name=metric_name,
                            value=cell.value,
                            raw_value=cell.raw_value,
                            unit="currency",
                            currency=row_match.currency,
                            scale=row_match.scale,
                            period_label=cell.column_label,
                            column_role=cell.column_role,
                            document_type="appendix_5b",
                            parser_method=PARSER_METHOD,
                            confidence=0.96,
                            trust_status="candidate",
                            evidence=row_match.evidence_by_column[cell.column_index],
                        )
                    )

    candidates.extend(_capex_candidates(row_matches))
    candidates.extend(_reconciliation_fallback_candidates(row_matches, candidates))
    missing = _missing_for(candidates)

    return Appendix5BParseResult(
        document_type="appendix_5b",
        status="parsed" if candidates else "no_metrics",
        parser_method=PARSER_METHOD,
        candidates=candidates,
        missing=missing,
        tables_seen=len(tables),
    )


def _looks_like_appendix5b(tables: list[Appendix5BTableLike]) -> bool:
    text = "\n".join(
        [
            " ".join(str(getattr(table, "caption", "")) for table in tables),
            " ".join(str(cell) for table in tables for row in table.rows[:12] for cell in row),
            " ".join(str(cell) for table in tables for cell in getattr(table, "headers", [])),
        ]
    ).lower()
    if "appendix 5b" in text:
        return True
    if "mining exploration entity" in text or "oil and gas exploration entity" in text:
        return True

    line_items = set(_LINE_ITEM_RE.findall(text))
    flattened = {".".join((major, minor)) for major, minor, _subitem in line_items}
    return len({"1.9", "2.6", "3.10", "4.6", "5.5"} & flattened) >= 3


def _headers_for(table: Appendix5BTableLike) -> list[str]:
    headers = [str(cell or "").strip() for cell in getattr(table, "headers", [])]
    if headers:
        return headers
    if table.rows:
        return [str(cell or "").strip() for cell in table.rows[0]]
    return []


def _detect_currency(table: Appendix5BTableLike, headers: list[str]) -> str | None:
    text = " ".join([getattr(table, "caption", ""), *headers, *_flatten_rows(table.rows[:3])])
    if re.search(r"\bAUD\b|A\$|\$A", text, re.IGNORECASE):
        return "AUD"
    return None


def _detect_scale(table: Appendix5BTableLike, headers: list[str]) -> str | None:
    text = " ".join([getattr(table, "caption", ""), *headers, *_flatten_rows(table.rows[:3])])
    if re.search(r"\$A?'?000,000\b|millions?|\bA?\$m\b", text, re.IGNORECASE):
        return "millions"
    if re.search(r"\$A?'?000\b|\$'?000\b|thousands?", text, re.IGNORECASE):
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
        elif re.search(r"\$A?'?000|\$'?000", header, re.IGNORECASE):
            roles[idx] = "value"
    return roles


def _resolve_table_context(
    *,
    table: Appendix5BTableLike,
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
    return _TableContext(
        headers=raw_headers,
        roles=raw_roles,
        currency=currency,
        scale=scale,
    )


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
    table: Appendix5BTableLike,
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

    resolved_roles = dict(roles)
    numeric_cells: list[_CellMatch] = []
    for column_index, cell in enumerate(row):
        raw_value = str(cell or "").strip()
        if _line_item(raw_value) == line_item:
            continue
        parsed = _parse_decimal(raw_value)
        if parsed is None:
            continue
        column_role = resolved_roles.get(column_index)
        if column_role is None and not resolved_roles:
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
        cell.column_index: Appendix5BEvidence(
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


def _capex_candidates(
    row_matches: list[_RowMatch],
) -> list[Appendix5BCandidate]:
    by_role: dict[str, list[tuple[_CellMatch, Appendix5BEvidence, _RowMatch]]] = {}
    for match in row_matches:
        if match.line_item not in _CAPEX_LINE_ITEMS:
            continue
        for cell in match.cells:
            if cell.column_role not in _VALUE_COLUMN_ROLES:
                continue
            by_role.setdefault(cell.column_role, []).append(
                (cell, match.evidence_by_column[cell.column_index], match)
            )

    candidates: list[Appendix5BCandidate] = []
    for column_role, components in by_role.items():
        if not components:
            continue
        value = sum((cell.value for cell, _evidence, _match in components), Decimal("0"))
        raw_value = " + ".join(cell.raw_value for cell, _evidence, _match in components)
        first_cell, first_evidence, first_match = components[0]
        candidates.append(
            Appendix5BCandidate(
                metric_name="capex",
                value=value,
                raw_value=raw_value,
                unit="currency",
                currency=first_match.currency,
                scale=first_match.scale,
                period_label=first_cell.column_label,
                column_role=column_role,
                document_type="appendix_5b",
                parser_method=PARSER_METHOD,
                confidence=0.90,
                trust_status="candidate",
                evidence=first_evidence,
                component_evidence=[evidence for _cell, evidence, _match in components],
            )
        )
    return candidates


def _reconciliation_fallback_candidates(
    row_matches: list[_RowMatch],
    existing_candidates: list[Appendix5BCandidate],
) -> list[Appendix5BCandidate]:
    present = {
        (candidate.metric_name, candidate.column_role)
        for candidate in existing_candidates
    }
    candidates: list[Appendix5BCandidate] = []
    for match in row_matches:
        metric_name = _RECONCILIATION_LINE_TO_METRIC.get(match.line_item)
        if metric_name is None:
            continue
        for cell in match.cells:
            if cell.column_role not in _VALUE_COLUMN_ROLES:
                continue
            key = (metric_name, cell.column_role)
            if key in present:
                continue
            present.add(key)
            candidates.append(
                Appendix5BCandidate(
                    metric_name=metric_name,
                    value=cell.value,
                    raw_value=cell.raw_value,
                    unit="currency",
                    currency=match.currency,
                    scale=match.scale,
                    period_label=cell.column_label,
                    column_role=cell.column_role,
                    document_type="appendix_5b",
                    parser_method=PARSER_METHOD,
                    confidence=0.90,
                    trust_status="candidate",
                    evidence=match.evidence_by_column[cell.column_index],
                )
            )
    return candidates


def _missing_for(candidates: list[Appendix5BCandidate]) -> list[Appendix5BMissing]:
    present = {(candidate.metric_name, candidate.column_role) for candidate in candidates}
    column_roles = {"current_quarter"}
    if any(candidate.column_role == "year_to_date" for candidate in candidates):
        column_roles.add("year_to_date")

    missing: list[Appendix5BMissing] = []
    for metric_name, expected_lines in _EXPECTED_METRIC_LINES.items():
        for column_role in sorted(column_roles):
            if (metric_name, column_role) in present:
                continue
            missing.append(
                Appendix5BMissing(
                    metric_name=metric_name,
                    column_role=column_role,
                    status=DATA_MISSING,
                    failure_reason=f"{DATA_MISSING}: {column_role} Appendix 5B line value not found",
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
