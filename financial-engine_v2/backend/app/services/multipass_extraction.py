from __future__ import annotations

import re
from datetime import date
from typing import Any

from dateutil import parser as dtparser


EXTRACTOR_VERSION = "multipass_v1"
PROMPT_HASH = "multipass_v1"

METRIC_FIELDS = (
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
)

SCALE_MULTIPLIERS = {
    "unknown": 1.0,
    "units": 1.0,
    "thousands": 1_000.0,
    "millions": 1_000_000.0,
}

_NPAT_OWNER_MARKERS = (
    "owners of the parent",
    "owners of parent",
    "owner of the parent",
    "pemilik entitas induk",
    "ordinary equity holders",
    "shareholders of",
    "security holders",
    "members of",
)

_NPAT_TOTAL_COMPREHENSIVE_MARKERS = (
    "total comprehensive",
    "penghasilan komprehensif",
)

_NPAT_ATTRIBUTABLE_CONTEXT_MARKERS = (
    "attributable",
    "diatribusikan",
)

_NPAT_PROFIT_CONTEXT_MARKERS = (
    "profit",
    "loss",
    "laba",
    "rugi",
)

_NPAT_TOTAL_PROFIT_ROW_MARKERS = (
    "profit after income tax expense",
    "profit/(loss) after income tax expense",
    "profit for the year",
    "profit attributable to owners of the parent",
)

_NPAT_PROFIT_AFTER_TAX_ROW_MARKERS = (
    "profit/(loss) after income tax expense for the year",
    "profit/(loss) after income tax expense for the period",
    "profit/(loss) after income tax expense for the half-year",
    "profit after income tax expense for the year",
    "loss after income tax expense for the year",
    "profit after income tax expense from ordinary activities",
    "profit/(loss) after income tax expense from ordinary activities",
)

_WRAPPER_DOCUMENT_MARKERS = ("appendix 4d", "appendix 4e")

_WRAPPER_DISCLOSURE_MARKER_GROUPS = (
    ("nta per security", "net tangible assets per security"),
    ("dividends / distributions", "dividends/distributions", "dividends", "distribution"),
    ("record date", "record-date"),
    ("details of associates and joint ventures", "associates and joint ventures", "joint ventures"),
)


def parse_period_end(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return dtparser.parse(str(s)).date()
    except Exception:
        return None


def _derive_period_start(period_end: date | None, period_type: str | None) -> date | None:
    if period_end is None:
        return None
    if period_type == "A":
        return date(period_end.year, 1, 1)
    if period_type == "H":
        return date(period_end.year, 7, 1) if period_end.month >= 7 else date(period_end.year, 1, 1)
    if period_type == "Q":
        quarter = ((period_end.month - 1) // 3) * 3 + 1
        return date(period_end.year, quarter, 1)
    return None


def _normalize_filter_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _parse_statement_numeric_cell(cell: Any) -> float | None:
    if cell is None:
        return None
    if isinstance(cell, bool):
        return None
    if isinstance(cell, (int, float)):
        return float(cell)
    text = str(cell).strip()
    if not text or text in {"-", "—", "–"}:
        return None
    text = text.replace(",", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace("$", "").replace("A", "").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def _statement_row_label(row: list[Any]) -> str:
    parts: list[str] = []
    for cell in row:
        text = str(cell or "").strip()
        if not text:
            continue
        if _parse_statement_numeric_cell(text) is not None:
            continue
        if _normalize_filter_text(text) in {"note", "notes", "catatannotes"}:
            continue
        parts.append(text)
    return (" ".join(parts).strip()[:220]) or (str(row[0]).strip() if row else "")


def _statement_note_columns(rows: list[list[Any]]) -> set[int]:
    note_columns: set[int] = set()
    for row in rows[:5]:
        for idx, cell in enumerate(row):
            if _normalize_filter_text(cell) in {"note", "notes", "catatannotes"}:
                note_columns.add(idx)
    return note_columns


def _first_current_period_value(row: list[Any], note_columns: set[int] | None) -> float | None:
    parsed: list[tuple[str, float]] = []
    note_columns = note_columns or set()
    for idx, cell in enumerate(row[1:], start=1):
        if idx in note_columns:
            continue
        value = _parse_statement_numeric_cell(cell)
        if value is not None:
            parsed.append((str(cell or "").strip(), value))
    if not parsed:
        return None
    return parsed[0][1]


def _markdown_table_rows(markdown: str | None) -> list[list[str]]:
    if not markdown:
        return []
    rows: list[list[str]] = []
    for raw_line in str(markdown).splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.count("|") < 2:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        rows.append(cells)
    return rows


def _row_matches_keywords(row: list[Any] | None, keywords: tuple[str, ...]) -> bool:
    label = str(row[0]).strip().lower() if row else ""
    if any(kw in label for kw in keywords):
        return True
    compact_label = _normalize_filter_text(label)
    return any(_normalize_filter_text(kw) in compact_label for kw in keywords)


def _combined_source_text(row_ref: Any, provenance: Any) -> str:
    bits = [str(row_ref or "").strip(), str(provenance or "").strip()]
    return " ".join(part for part in bits if part).strip().lower()


def _flatten_text_fragments(value: Any) -> list[str]:
    fragments: list[str] = []
    if value is None:
        return fragments
    if isinstance(value, dict):
        for key, item in value.items():
            fragments.extend(_flatten_text_fragments(key))
            fragments.extend(_flatten_text_fragments(item))
        return fragments
    if isinstance(value, (list, tuple, set)):
        for item in value:
            fragments.extend(_flatten_text_fragments(item))
        return fragments
    text = str(value).strip()
    if text:
        fragments.append(text.lower())
    return fragments


def _combined_payload_text(payload: dict[str, Any], *keys: str) -> str:
    fragments: list[str] = []
    for key in keys:
        fragments.extend(_flatten_text_fragments(payload.get(key)))
    return " ".join(fragment for fragment in fragments if fragment).strip()


def _is_appendix_wrapper_document(payload: dict[str, Any]) -> bool:
    doc_subtype = _normalize_filter_text(
        payload.get("document_subtype")
        or payload.get("doc_subtype")
        or payload.get("source_doc_subtype")
        or payload.get("wrapper_doc_subtype")
    )
    if doc_subtype in {"4d", "4e"}:
        return True
    title_text = _normalize_filter_text(
        payload.get("document_title")
        or payload.get("title")
        or payload.get("source_title")
        or payload.get("announcement_title")
    )
    return any(marker in title_text for marker in _WRAPPER_DOCUMENT_MARKERS)


def _wrapper_disclosure_evidence_present(payload: dict[str, Any]) -> bool:
    combined = _combined_payload_text(
        payload,
        "wrapper_disclosures",
        "disclosure_evidence",
        "source_evidence",
        "row_refs",
        "provenance",
        "source_notes",
    )
    if not combined:
        return False
    return all(any(marker in combined for marker in group) for group in _WRAPPER_DISCLOSURE_MARKER_GROUPS)


def _wrapper_source_bound_context(payload: dict[str, Any]) -> dict[str, Any]:
    source_bound = payload.get("source_bound")
    return source_bound if isinstance(source_bound, dict) else {}


def _wrapper_source_bound_ready(payload: dict[str, Any]) -> bool:
    source_bound = _wrapper_source_bound_context(payload)
    required_fields = ("period_end", "period_type", "scale", "currency")
    return all(source_bound.get(field) not in (None, "") for field in required_fields)


def _wrapper_required_canonical_metrics_present(metrics: dict[str, Any]) -> bool:
    return metrics.get("revenue") is not None and metrics.get("np_attributable") is not None


def _wrapper_only_canonical_metrics(metrics: dict[str, Any]) -> bool:
    non_null_names = {name for name, value in metrics.items() if value is not None}
    return non_null_names.issubset({"revenue", "np_attributable"})


def _wrapper_gate_error(payload: dict[str, Any], metrics: dict[str, Any]) -> str | None:
    if not _is_appendix_wrapper_document(payload):
        return None
    if not _wrapper_required_canonical_metrics_present(metrics):
        return "validation_gate:wrapper_missing_required_canonical_metrics"
    if not _wrapper_only_canonical_metrics(metrics):
        return "validation_gate:wrapper_has_noncanonical_metrics"
    if not _wrapper_source_bound_ready(payload):
        return "validation_gate:wrapper_missing_source_bound_context"
    if not _wrapper_disclosure_evidence_present(payload):
        return "validation_gate:wrapper_missing_disclosure_evidence"
    return None


def _np_attributable_selection_needs_repair(row_ref: Any, provenance: Any) -> bool:
    evidence = _combined_source_text(row_ref, provenance)
    if not evidence:
        return False
    if any(marker in evidence for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS):
        return True
    owner_selected = any(marker in evidence for marker in _NPAT_OWNER_MARKERS)
    owner_context_is_profit = any(marker in evidence for marker in _NPAT_PROFIT_CONTEXT_MARKERS) and any(
        marker in evidence for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS
    )
    if owner_selected and not owner_context_is_profit:
        return True
    if not (any(marker in evidence for marker in _NPAT_TOTAL_PROFIT_ROW_MARKERS) and any(marker in evidence for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS)):
        return True
    return False


def _find_owner_attributable_profit_row(rows: list[list[Any]]) -> tuple[float, str] | None:
    note_columns = _statement_note_columns(rows)
    for idx, row in enumerate(rows):
        label = _statement_row_label(row).lower()
        if not any(marker in label for marker in _NPAT_OWNER_MARKERS):
            continue
        context_rows = rows[max(0, idx - 6) : idx + 1]
        context = " ".join(_statement_row_label(context_rows_row) for context_rows_row in context_rows).lower()
        evidence_context = f"{context} {label}".strip()
        if any(marker in evidence_context for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS):
            continue
        if not any(marker in evidence_context for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS):
            continue
        if not any(marker in evidence_context for marker in _NPAT_PROFIT_CONTEXT_MARKERS):
            continue
        value = _first_current_period_value(row, note_columns)
        if value is None:
            continue
        return value, _statement_row_label(row)
    return None


def _find_profit_after_tax_row(rows: list[list[Any]]) -> tuple[float, str] | None:
    note_columns = _statement_note_columns(rows)
    for row in rows:
        label = _statement_row_label(row).lower()
        if any(marker in label for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS):
            continue
        if not any(marker in label for marker in _NPAT_PROFIT_AFTER_TAX_ROW_MARKERS):
            continue
        value = _first_current_period_value(row, note_columns)
        if value is None:
            continue
        return value, _statement_row_label(row)
    return None


def _repair_np_attributable_from_income_statement(
    merged_metrics: dict[str, Any],
    row_refs: dict[str, Any],
    provenance: dict[str, Any],
    markdown_map: dict[str, Any],
    pass1_result: dict[str, Any],
) -> None:
    if merged_metrics.get("np_attributable") is not None:
        return None
    if not _np_attributable_selection_needs_repair(row_refs.get("np_attributable"), provenance.get("np_attributable")):
        return None

    rows = _markdown_table_rows(markdown_map.get("np_attributable"))
    if not rows:
        return None

    candidate = _find_owner_attributable_profit_row(rows)
    if candidate is None:
        candidate = _find_profit_after_tax_row(rows)
    if candidate is None:
        return None

    raw_value, source_row_ref = candidate
    multiplier = SCALE_MULTIPLIERS.get(str(pass1_result.get("scale", "unknown")).lower(), 1.0)
    merged_metrics["np_attributable"] = raw_value * multiplier
    row_refs["np_attributable"] = source_row_ref
    provenance["np_attributable"] = f"income_statement:deterministic:{source_row_ref}"
    return None


def _metric_label_mismatch(payload: dict[str, Any]) -> tuple[str, str] | None:
    return None


def _source_unit_value_mismatch(payload: dict[str, Any]) -> tuple[str, float, float] | None:
    return None


def _period_source_mismatch(payload: dict[str, Any]) -> tuple[str, str, str] | None:
    return None


def _period_end_source_mismatch(payload: dict[str, Any]) -> tuple[str, str, str] | None:
    return None


def _normalize_currency_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text or text == "NULL":
        return "AUD"
    return text


def _native_currency_sanity_cap(currency: Any) -> float:
    return 1_000_000_000_000.0 if _normalize_currency_code(currency) == "AUD" else 10_000_000_000_000.0


def _validate_gate(payload: dict[str, Any]) -> tuple[str, str | None]:
    scale_validation = payload.get("scale_validation", "pass")
    if scale_validation != "pass":
        return "failed", f"validation_gate:scale_validation:{scale_validation}"

    if not payload.get("period_end"):
        return "failed", "validation_gate:missing_period_end"
    try:
        dtparser.parse(str(payload["period_end"]))
    except Exception:
        return "failed", "validation_gate:invalid_period_end"

    if payload.get("period_type") not in ("A", "H", "Q"):
        return "failed", f"validation_gate:invalid_period_type:{payload.get('period_type')}"

    if payload.get("scale") == "unknown":
        return "failed", "validation_gate:scale_unknown"

    metrics = dict(payload.get("metrics") or {})
    wrapper_error = _wrapper_gate_error(payload, metrics)
    if wrapper_error is not None:
        return "failed", wrapper_error

    mismatch = _metric_label_mismatch(payload)
    if mismatch is not None:
        metric_name, source_label = mismatch
        return "failed", f"validation_gate:metric_label_mismatch:{metric_name}:{source_label}"

    source_unit_mismatch = _source_unit_value_mismatch(payload)
    if source_unit_mismatch is not None:
        metric_name, actual, expected = source_unit_mismatch
        return "failed", f"validation_gate:source_unit_value_mismatch:{metric_name}:actual={actual:g}:source_unit={expected:g}"

    period_mismatch = _period_source_mismatch(payload)
    if period_mismatch is not None:
        period_type, source_period_type, reason = period_mismatch
        return "failed", f"validation_gate:period_source_mismatch:payload={period_type}:source={source_period_type}:{reason}"

    period_end_mismatch = _period_end_source_mismatch(payload)
    if period_end_mismatch is not None:
        period_end, source_period_end, reason = period_end_mismatch
        return "failed", f"validation_gate:period_end_source_mismatch:payload={period_end}:source={source_period_end}:{reason}"

    non_null = [v for v in metrics.values() if v is not None]
    min_metrics = 2 if _is_appendix_wrapper_document(payload) else (1 if payload.get("period_type") == "Q" else 3)
    if len(non_null) < min_metrics:
        return "failed", f"validation_gate:insufficient_metrics:{len(non_null)}"

    sanity_cap = _native_currency_sanity_cap(payload.get("currency"))
    for metric_name, value in metrics.items():
        if value is not None and abs(value) > sanity_cap:
            return "failed", f"validation_gate:sanity_cap_exceeded:{metric_name}={value}"

    confidence = float(payload.get("confidence_metrics", 0.0) or 0.0)
    if confidence < 0.6:
        return "failed", f"validation_gate:low_confidence:{confidence}"

    currency = _normalize_currency_code(payload.get("currency"))
    if currency != "AUD":
        return "ok_low_confidence", None
    if confidence < 0.7:
        return "ok_low_confidence", None
    return "ok", None


def _run_pass4_reconciler(
    pass3a_results: list[dict[str, Any]],
    pass3b_result: dict[str, Any] | None,
    pass1_result: dict[str, Any] | None,
    *,
    sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    merged_metrics = {field: None for field in METRIC_FIELDS}
    row_refs: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    markdown_map: dict[str, Any] = {}

    for result in pass3a_results or []:
        result_row_refs = dict(result.get("row_refs") or {})
        for field in METRIC_FIELDS:
            if field in result_row_refs and field not in row_refs:
                row_refs[field] = result_row_refs.get(field)
                provenance[field] = (
                    f"income_statement:pass3a:{row_refs[field]}" if row_refs.get(field) is not None else None
                )
            if result.get(field) is not None and merged_metrics[field] is None:
                merged_metrics[field] = result[field]
        if result.get("_markdown"):
            markdown_map.setdefault("np_attributable", result["_markdown"])

    pass1_result = dict(pass1_result or {})
    _repair_np_attributable_from_income_statement(merged_metrics, row_refs, provenance, markdown_map, pass1_result)

    source_bound = {
        "period_type": pass1_result.get("period_type"),
        "period_end": pass1_result.get("period_end"),
        "scale": pass1_result.get("scale"),
        "currency": pass1_result.get("currency", "AUD"),
    }
    if pass1_result.get("doc_subtype") is not None:
        source_bound["document_subtype"] = pass1_result.get("doc_subtype")
    if pass1_result.get("doc_class") is not None:
        source_bound["document_class"] = pass1_result.get("doc_class")
    if pass1_result.get("title") is not None:
        source_bound["document_title"] = pass1_result.get("title")

    payload = {
        "period_type": pass1_result.get("period_type"),
        "period_end": pass1_result.get("period_end"),
        "scale": pass1_result.get("scale", "unknown"),
        "currency": pass1_result.get("currency", "AUD"),
        "confidence_metrics": pass3a_results[0].get("pass3_confidence", 0.0) if pass3a_results else 0.0,
        "metrics": merged_metrics,
        "row_refs": row_refs,
        "provenance": provenance,
        "source_bound": source_bound,
        "_structured_extraction": {"warnings": []},
    }
    if pass3b_result:
        payload.update(pass3b_result)
    for key in ("doc_subtype", "doc_class", "title", "document_subtype", "document_class", "document_title", "wrapper_disclosures"):
        if pass1_result.get(key) is not None:
            payload[key] = pass1_result.get(key)
    return payload


def run_multipass_extraction(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "status": "skipped",
        "payload": {},
        "sections": kwargs.get("sections") or [],
        "error": None,
    }
