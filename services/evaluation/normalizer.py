#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping, Sequence


CANONICAL_METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "net_income",
    "assets",
    "liabilities",
)

_ALIAS_TO_CANONICAL: dict[str, str] = {
    "revenue": "revenue",
    "total_revenue": "revenue",
    "revenue_total": "revenue",
    "sales": "revenue",
    "total_sales": "revenue",
    "operating_revenue": "revenue",
    "income": "revenue",
    "ebitda": "ebitda",
    "underlying_ebitda": "ebitda",
    "adjusted_ebitda": "ebitda",
    "earnings_before_interest_tax_depreciation_and_amortisation": "ebitda",
    "earnings_before_interest_tax_depreciation_and_amortization": "ebitda",
    "net_income": "net_income",
    "npat": "net_income",
    "np_attributable": "net_income",
    "net_profit": "net_income",
    "net_profit_after_tax": "net_income",
    "profit_after_tax": "net_income",
    "profit_for_the_period": "net_income",
    "assets": "assets",
    "total_assets": "assets",
    "assets_total": "assets",
    "liabilities": "liabilities",
    "total_liabilities": "liabilities",
    "liabilities_total": "liabilities",
}

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_NON_METRIC_CHARS_RE = re.compile(r"[^a-z0-9]+")
_NUMERIC_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_CURRENCY_TOKEN_RE = re.compile(r"(?i)(?:[A-Z]{1,3}\$)|[$€£¥]")
_MULTIPLIER_TOKEN_RE = re.compile(r"(?i)\b(billion|million|thousand|bn|mn|mm|k)\b")
_SUFFIX_RE = re.compile(r"(?i)^([-+]?\d[\d,]*(?:\.\d+)?)([kmb])$")


def canonical_metric_keys() -> tuple[str, ...]:
    return CANONICAL_METRICS


def normalize_metric_name(metric: Any) -> str | None:
    raw = str(metric or "").strip().lower()
    if not raw:
        return None
    canonicalized = _NON_METRIC_CHARS_RE.sub("_", raw).strip("_")
    if not canonicalized:
        return None
    return _ALIAS_TO_CANONICAL.get(canonicalized)


def _multiplier_for_text(text: str) -> float:
    suffix_match = _SUFFIX_RE.match(text.strip())
    if suffix_match:
        suffix = str(suffix_match.group(2)).lower()
        if suffix == "k":
            return 1_000.0
        if suffix == "m":
            return 1_000_000.0
        if suffix == "b":
            return 1_000_000_000.0

    unit_match = _MULTIPLIER_TOKEN_RE.search(text)
    if not unit_match:
        return 1.0
    token = str(unit_match.group(1)).lower()
    if token in {"bn", "billion"}:
        return 1_000_000_000.0
    if token in {"mn", "mm", "million"}:
        return 1_000_000.0
    if token in {"k", "thousand"}:
        return 1_000.0
    return 1.0


def normalize_numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    lowered = text.lower()
    multiplier = _multiplier_for_text(lowered)
    cleaned = _CURRENCY_TOKEN_RE.sub("", lowered)
    cleaned = cleaned.replace(" ", "")

    suffix_match = _SUFFIX_RE.match(cleaned)
    if suffix_match:
        numeric_text = str(suffix_match.group(1))
    else:
        numeric_match = _NUMERIC_RE.search(cleaned)
        if not numeric_match:
            return None
        numeric_text = str(numeric_match.group(0))

    try:
        parsed = float(numeric_text.replace(",", ""))
    except ValueError:
        return None

    parsed *= multiplier
    if negative:
        parsed = -abs(parsed)
    return parsed


def normalize_metric_payload(metrics: Mapping[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for raw_metric, raw_value in metrics.items():
        metric = normalize_metric_name(raw_metric)
        if metric is None:
            continue
        value = normalize_numeric(raw_value)
        if value is None:
            continue
        if metric not in normalized:
            normalized[metric] = value
    return normalized


def _scope_rank(scope: Any) -> int:
    normalized = str(scope or "").strip().lower()
    if normalized == "group":
        return 3
    if normalized == "any":
        return 2
    if normalized == "parent":
        return 1
    return 0


def _period_rank(period_end: Any) -> int:
    text = str(period_end or "").strip()
    if not text:
        return 0
    match = _DATE_RE.search(text)
    if not match:
        return 0
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    try:
        return date(year, month, day).toordinal()
    except ValueError:
        return 0


def rows_to_canonical_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    selected: dict[str, tuple[tuple[int, int, int], float]] = {}
    for index, row in enumerate(rows):
        metric = normalize_metric_name(row.get("metric"))
        if metric is None:
            continue
        raw_value = row.get("value")
        if raw_value is None:
            raw_value = row.get("raw_value")
        value = normalize_numeric(raw_value)
        if value is None:
            continue

        ranking = (
            _scope_rank(row.get("scope")),
            _period_rank(row.get("period_end")),
            -index,
        )
        current = selected.get(metric)
        if current is None or ranking > current[0]:
            selected[metric] = (ranking, value)

    return {metric: value for metric, (_, value) in selected.items()}


def metric_coverage_rate(metrics: Mapping[str, Any]) -> float:
    if not CANONICAL_METRICS:
        return 0.0
    present = 0
    for key in CANONICAL_METRICS:
        if key in metrics and normalize_numeric(metrics.get(key)) is not None:
            present += 1
    return float(present) / float(len(CANONICAL_METRICS))
