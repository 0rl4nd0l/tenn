#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from services.evaluation.evidence_utils import numeric_match, verify_with_context


_METRIC_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "total revenue", "sales", "turnover", "total income"),
    "ebitda": ("ebitda",),
    "net_income": ("net income", "net profit", "profit after tax", "profit attributable", "npat"),
    "assets": ("total assets", "assets"),
    "liabilities": ("total liabilities", "liabilities"),
    "equity": ("total equity", "equity", "net assets"),
    "current_assets": ("current assets",),
    "current_liabilities": ("current liabilities",),
    "cash_and_equivalents": ("cash and equivalents", "cash equivalents", "cash and cash equivalents"),
    "ebit": ("ebit", "operating profit", "profit from operations"),
    "gross_profit": ("gross profit", "gross income"),
    "capital_expenditure": ("capital expenditure", "capex"),
    "operating_cash_flow": ("operating cash flow", "cash from operations", "net cash from operating activities"),
    "free_cash_flow": ("free cash flow", "fcf"),
    "total_debt": ("total debt", "total borrowings", "borrowings"),
    "net_debt": ("net debt",),
    "impairment_expense": ("impairment expense", "impairment", "impairment loss", "one-off impairment"),
}


def _label_candidates(metric_name: str) -> tuple[str, ...]:
    normalized = str(metric_name or "").strip().lower()
    if not normalized:
        return ()
    candidates = [normalized]
    if "_" in normalized:
        candidates.append(normalized.replace("_", " "))
    candidates.extend(_METRIC_LABEL_ALIASES.get(normalized, ()))
    # de-dup while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for cand in candidates:
        c = str(cand or "").strip().lower()
        if c and c not in seen:
            ordered.append(c)
            seen.add(c)
    return tuple(ordered)


def verify_metrics(metrics: Mapping[str, Any] | None, raw_text: str | None) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    rejected: dict[str, dict[str, Any]] = {}

    for metric, value in dict(metrics or {}).items():
        metric_name = str(metric or "").strip()
        if not metric_name:
            continue
        numeric_ok = numeric_match(value, raw_text)
        context_ok = any(
            verify_with_context(value, label, raw_text)
            for label in _label_candidates(metric_name)
        )
        if numeric_ok and context_ok:
            verified[metric_name] = value
        else:
            rejected[metric_name] = {
                "value": value,
                "numeric_match": bool(numeric_ok),
                "context_match": bool(context_ok),
            }

    total = len(dict(metrics or {}))
    verified_count = len(verified)
    return {
        "verified": verified,
        "rejected": rejected,
        "verified_count": verified_count,
        "rejected_count": total - verified_count,
        "verification_ratio": float(verified_count) / float(max(1, total)),
    }
