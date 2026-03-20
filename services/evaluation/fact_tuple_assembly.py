#!/usr/bin/env python3
"""Table-first enrichment: map extractor rows to structured fact tuples (instrumentation only)."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

from services.evaluation.evidence import verify_single_metric
from services.evaluation.normalizer import normalize_metric_name, normalize_numeric

_SCALE_HINT_RE = re.compile(
    r"(?i)\b(thousand|million|billion|trillion|k\b|m\b|b\b|t\b|000s|000\'s)\b"
)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    s = str(value or "").strip()
    return s if s else None


def _period_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    end = row.get("statement_period_end")
    if end is None or str(end).strip() == "":
        end = row.get("period_end")
    ptype = row.get("statement_period")
    if ptype is None or str(ptype).strip() == "":
        ptype = row.get("period_type")
    return {
        "period_end": _str_or_none(end),
        "period_type": _str_or_none(ptype),
        "period_label": _str_or_none(row.get("period")),
    }


def _unit_scale_hint(row: Mapping[str, Any]) -> str | None:
    parts: list[str] = []
    cur = _str_or_none(row.get("currency"))
    if cur and cur.upper() != "UNKNOWN":
        parts.append(cur.upper())
    for blob in (
        str(row.get("table_header_text") or ""),
        str(row.get("line") or ""),
        str(row.get("raw_value") or ""),
    ):
        m = _SCALE_HINT_RE.search(blob)
        if m:
            parts.append(m.group(1).lower())
            break
    if not parts:
        return None
    return "|".join(parts)


def _sign_for_value(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 0:
        return "negative"
    if value > 0:
        return "positive"
    return "zero"


def enrich_row_to_fact_tuple(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    Enrich one extractor row into a JSON-serializable fact tuple (normalization path).

    Uses canonical metric names when ``normalize_metric_name`` recognizes the label.
    """
    raw_metric = row.get("metric_base")
    if raw_metric is None or str(raw_metric).strip() == "":
        raw_metric = row.get("metric")
    raw_metric_s = str(raw_metric or "").strip()
    canonical = normalize_metric_name(raw_metric_s)

    raw_val = row.get("value")
    if raw_val is None:
        raw_val = row.get("raw_value")
    parsed = normalize_numeric(raw_val)

    stype = _str_or_none(row.get("statement_family"))
    if stype is None:
        stype = _str_or_none(row.get("statement_type"))
    scope = _str_or_none(row.get("statement_scope"))
    if scope is None:
        scope = _str_or_none(row.get("scope"))

    period = _period_fields(row)

    page = _safe_int(row.get("page_number"))
    if page is None:
        page = _safe_int(row.get("table_page"))

    return {
        "statement_type": stype,
        "concept": {
            "canonical": canonical,
            "raw_metric": raw_metric_s or None,
        },
        "period": period,
        "scope": scope,
        "unit_scale_hint": _unit_scale_hint(row),
        "sign": _sign_for_value(parsed),
        "value": parsed,
        "source": {
            "page": page,
            "line_no": _safe_int(row.get("line_no")),
            "line_preview": (str(row.get("line") or "")[:240] or None),
            "source_mode": _str_or_none(row.get("source_mode")),
            "table_id": _str_or_none(row.get("table_id")),
            "table_page": _safe_int(row.get("table_page")),
            "block_id": _str_or_none(row.get("block_id")),
        },
    }


def _table_first_candidate_rows(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    p = dict(payload or {})
    canonical = p.get("canonical_rows")
    if isinstance(canonical, list) and canonical:
        return [dict(r) if isinstance(r, Mapping) else {} for r in canonical]
    primary = p.get("primary_rows")
    if isinstance(primary, list) and primary:
        return [dict(r) if isinstance(r, Mapping) else {} for r in primary]
    return []


def build_fact_assembly_summary(
    selected_payload: Mapping[str, Any] | None,
    raw_text: str | None,
) -> dict[str, Any]:
    """
    Counts for table-first fact assembly (per routed document).

    Rows are taken from ``canonical_rows``, else ``primary_rows``.
    """
    rows = _table_first_candidate_rows(selected_payload)
    total_candidate_rows = len(rows)
    numeric_candidate_rows = 0
    canonical_fact_candidates = 0
    verified_facts = 0

    for row in rows:
        raw_val = row.get("value")
        if raw_val is None:
            raw_val = row.get("raw_value")
        parsed = normalize_numeric(raw_val)
        if parsed is not None:
            numeric_candidate_rows += 1

        raw_metric = row.get("metric_base") or row.get("metric")
        canonical = normalize_metric_name(str(raw_metric or "").strip())
        if canonical is None or parsed is None:
            continue
        canonical_fact_candidates += 1
        if verify_single_metric(canonical, parsed, raw_text):
            verified_facts += 1

    dropped_pre_verification = total_candidate_rows - canonical_fact_candidates
    dropped_in_verification = canonical_fact_candidates - verified_facts

    return {
        "total_candidate_rows": total_candidate_rows,
        "numeric_candidate_rows": numeric_candidate_rows,
        "canonical_fact_candidates": canonical_fact_candidates,
        "verified_facts": verified_facts,
        "dropped_pre_verification": dropped_pre_verification,
        "dropped_in_verification": dropped_in_verification,
    }


def enrich_rows_to_fact_tuples(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Batch helper for tests and optional callers."""
    return [enrich_row_to_fact_tuple(r) for r in rows]
