#!/usr/bin/env python3
"""Shared helpers for deterministic financial value normalization."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


EXPENSE_METRICS = {
    "depreciation_and_amortisation",
    "finance_costs",
    "income_tax_expense",
    "operating_expenses",
}


def _normalize_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_accounting_number(value: object) -> Optional[float]:
    """Parse a numeric token with accounting-style negatives."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None

    parsed_value = _normalize_space(value)
    if not parsed_value:
        return None

    negative_parentheses = parsed_value.startswith("(") and parsed_value.endswith(")")
    if negative_parentheses:
        parsed_value = parsed_value[1:-1].strip()

    parsed_value = parsed_value.replace(",", "")
    try:
        numeric_value = float(parsed_value)
    except ValueError:
        return None

    if negative_parentheses:
        return -abs(numeric_value)
    return numeric_value


def normalize_financial_value(metric: str, raw_value: object) -> object:
    """Normalize parsed numeric values and enforce expense polarity."""
    parsed = parse_accounting_number(raw_value)
    if parsed is None:
        return raw_value

    metric_name = (metric or "").strip().lower()
    if metric_name in EXPENSE_METRICS:
        return -abs(parsed)
    return parsed


def normalize_metric_rows(rows: List[Dict[str, object]]) -> None:
    """Normalize extracted numeric rows in place."""
    for row in rows:
        value_type = str(row.get("value_type", "")).strip().lower()
        if value_type not in {"amount", "percent"}:
            continue
        row["value"] = normalize_financial_value(str(row.get("metric", "")), row.get("value"))
