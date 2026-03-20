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


def _strip_unicode_numeric_spaces(s: str) -> str:
    for ch in ("\u00a0", "\u2009", "\u202f", "\u2007", "\u2060"):
        s = s.replace(ch, "")
    return s


def _maybe_european_decimal_to_us(s: str) -> str:
    """If s looks like EU-style grouping (1.234,56), convert to US decimal form."""
    if "," not in s or "." not in s:
        return s
    last_comma = s.rfind(",")
    dec = s[last_comma + 1 :]
    if not re.fullmatch(r"\d{1,4}", dec):
        return s
    int_part = s[:last_comma]
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", int_part):
        return s
    return int_part.replace(".", "") + "." + dec


def parse_accounting_number(value: object) -> Optional[float]:
    """Parse a numeric token with accounting-style negatives."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None

    parsed_value = str(value or "").strip()
    parsed_value = _strip_unicode_numeric_spaces(parsed_value)
    parsed_value = _normalize_space(parsed_value)
    if not parsed_value:
        return None

    # Strip a single leading currency / ISO prefix (OCR often glues symbols to amounts).
    parsed_value = re.sub(
        r"^(?:(?:USD|AUD|NZD|EUR|GBP)\s+|(?:A|US|C|NZ)?[$€£]\s*)",
        "",
        parsed_value,
        count=1,
        flags=re.IGNORECASE,
    )
    parsed_value = parsed_value.strip()
    parsed_value = _maybe_european_decimal_to_us(parsed_value)

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
