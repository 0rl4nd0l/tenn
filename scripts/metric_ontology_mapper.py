#!/usr/bin/env python3
"""Canonical metric alias mapping helpers for financial extraction."""

from __future__ import annotations

import re
from typing import Dict, List, MutableMapping


_CANONICAL_METRICS = {
    "capital_expenditure",
    "depreciation_and_amortisation",
    "ebit",
    "ebitda",
    "free_cash_flow",
    "net_income",
    "operating_cash_flow",
    "revenue",
    "total_assets",
    "total_equity",
    "total_liabilities",
}

_METRIC_ALIAS_TO_CANONICAL: Dict[str, str] = {
    "cash from operations": "operating_cash_flow",
    "cash from operating activities": "operating_cash_flow",
    "capex": "capital_expenditure",
    "d&a": "depreciation_and_amortisation",
    "depreciation and amortization": "depreciation_and_amortisation",
    "depreciation and amortisation": "depreciation_and_amortisation",
    "ebit": "ebit",
    "ebitda": "ebitda",
    "fcf": "free_cash_flow",
    "free cash flow": "free_cash_flow",
    "net cash from operating activities": "operating_cash_flow",
    "operating profit": "ebit",
    "pat": "net_income",
    "profit after tax": "net_income",
    "sales": "revenue",
    "shareholders equity": "total_equity",
    "total assets": "total_assets",
    "total equity": "total_equity",
    "total liabilities": "total_liabilities",
    "turnover": "revenue",
}


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonicalize_metric_name(metric_name: object) -> str:
    """Map common aliases onto extractor canonical metric names."""
    normalized = _normalize_text(metric_name)
    if not normalized:
        return ""
    mapped = _METRIC_ALIAS_TO_CANONICAL.get(normalized)
    if mapped:
        return mapped
    snake_case = normalized.replace(" ", "_")
    if snake_case in _CANONICAL_METRICS:
        return snake_case
    return snake_case


def canonicalize_metric_row(row: MutableMapping[str, object]) -> MutableMapping[str, object]:
    """Normalize explicit metric fields in place when an alias is recognized."""
    source_metric = row.get("metric_base") or row.get("metric") or row.get("metric_alias")
    normalized = _normalize_text(source_metric)
    if not normalized:
        return row

    mapped = _METRIC_ALIAS_TO_CANONICAL.get(normalized)
    if mapped:
        canonical = mapped
    else:
        canonical = normalized.replace(" ", "_")
        if canonical not in _CANONICAL_METRICS:
            return row

    if not canonical:
        return row

    existing_metric = str(row.get("metric", "")).strip()
    existing_base = str(row.get("metric_base", "")).strip()
    if existing_metric and canonical != existing_metric:
        row["metric_alias"] = str(row.get("metric_alias", "")).strip() or existing_metric
    elif existing_base and canonical != existing_base:
        row["metric_alias"] = str(row.get("metric_alias", "")).strip() or existing_base

    row["metric"] = canonical
    row["metric_base"] = canonical
    return row


def canonicalize_metric_rows(rows: List[MutableMapping[str, object]]) -> None:
    """Normalize metric aliases for a batch of extracted rows."""
    for row in rows:
        canonicalize_metric_row(row)
