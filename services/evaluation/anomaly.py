#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.evaluation.normalizer import normalize_metric_name, normalize_numeric


_HIGH_FLAGS = {
    "negative_revenue",
    "negative_assets",
    "negative_liabilities",
    "assets_less_than_liabilities",
    "ebitda_exceeds_revenue",
}
_MEDIUM_FLAGS = {
    "scale_outlier",
    "extreme_ebitda_margin",
    "net_income_to_revenue_outlier",
}
_LOW_FLAGS = {
    "assets_liabilities_equity_inconsistency",
    "missing_revenue",
    "missing_net_income",
}


def _safe_float(value: Any) -> float | None:
    parsed = normalize_numeric(value)
    if parsed is None:
        return None
    return float(parsed)


def _canonical_metrics(method_payload: Mapping[str, Any]) -> dict[str, float]:
    canonical_metrics = method_payload.get("canonical_metrics")
    if isinstance(canonical_metrics, Mapping):
        resolved: dict[str, float] = {}
        for key, value in canonical_metrics.items():
            metric = normalize_metric_name(key)
            if metric is None:
                metric = str(key or "").strip().lower()
            parsed = _safe_float(value)
            if metric and parsed is not None:
                resolved[metric] = parsed
        if resolved:
            return resolved

    normalized_metrics = method_payload.get("normalized_metrics")
    resolved: dict[str, float] = {}
    if isinstance(normalized_metrics, Sequence):
        for row in normalized_metrics:
            if not isinstance(row, Mapping):
                continue
            metric = normalize_metric_name(row.get("metric"))
            if metric is None:
                metric = normalize_metric_name(row.get("metric_base"))
            if metric is None:
                continue
            parsed = _safe_float(row.get("value"))
            if parsed is None:
                parsed = _safe_float(row.get("raw_value"))
            if parsed is None:
                continue
            if metric not in resolved:
                resolved[metric] = parsed
    return resolved


def _severity(flags: list[str]) -> str:
    flag_set = set(flags)
    if flag_set & _HIGH_FLAGS:
        return "high"
    if flag_set & _MEDIUM_FLAGS:
        return "medium"
    if flag_set & _LOW_FLAGS:
        return "low"
    return "low"


def detect_anomalies(method_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(method_payload or {})
    metrics = _canonical_metrics(payload)
    flags: list[str] = []

    revenue = metrics.get("revenue")
    ebitda = metrics.get("ebitda")
    net_income = metrics.get("net_income")
    assets = metrics.get("assets")
    liabilities = metrics.get("liabilities")
    equity = metrics.get("equity")

    if revenue is None:
        flags.append("missing_revenue")
    elif revenue < 0:
        flags.append("negative_revenue")

    if net_income is None:
        flags.append("missing_net_income")

    if assets is not None and assets < 0:
        flags.append("negative_assets")
    if liabilities is not None and liabilities < 0:
        flags.append("negative_liabilities")

    if assets is not None and liabilities is not None and assets < liabilities:
        flags.append("assets_less_than_liabilities")

    if ebitda is not None and revenue is not None:
        if ebitda > revenue:
            flags.append("ebitda_exceeds_revenue")
        if revenue != 0.0:
            ebitda_margin = ebitda / revenue
            if ebitda_margin > 1.5:
                flags.append("extreme_ebitda_margin")

    if net_income is not None and revenue is not None and revenue != 0.0:
        if abs(net_income) > (3.0 * abs(revenue)):
            flags.append("net_income_to_revenue_outlier")

    if revenue is not None and revenue != 0.0:
        if abs(revenue) > 1_000_000_000_000.0 or abs(revenue) < 1_000.0:
            flags.append("scale_outlier")

    if equity is not None and assets is not None and liabilities is not None:
        tolerance = max(1_000.0, 0.05 * abs(assets))
        if abs(assets - (liabilities + equity)) > tolerance:
            flags.append("assets_liabilities_equity_inconsistency")

    deduped_flags = sorted(set(flags))
    has_anomaly = bool(deduped_flags)
    severity = _severity(deduped_flags) if has_anomaly else "low"

    return {
        "has_anomaly": has_anomaly,
        "severity": severity,
        "flags": deduped_flags,
    }
