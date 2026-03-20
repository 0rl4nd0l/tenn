#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from services.evaluation.normalizer import normalize_metric_name, normalize_numeric


def _is_plausible_financial_row(row: Mapping[str, Any]) -> bool:
    scope = str(row.get("statement_scope") or row.get("statement_type") or "").strip().lower()
    if scope and scope not in {"narrative", "other", "unknown"}:
        return True
    text = " ".join(
        str(row.get(key) or "")
        for key in ("row_label", "line", "statement_title", "table_header_text")
    ).lower()
    financial_tokens = (
        "revenue",
        "profit",
        "income",
        "assets",
        "liabilities",
        "equity",
        "cash flow",
        "debt",
        "capex",
        "impairment",
        "ebit",
        "ebitda",
    )
    return any(tok in text for tok in financial_tokens)


def _is_explicit_noise_row(row: Mapping[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("row_label", "line", "statement_title", "table_header_text")
    ).lower()
    noise_tokens = (
        "for personal use only",
        "drill",
        "assay",
        "ore",
        "g/t",
        "au",
        "ag",
        "hole",
        "resource update",
    )
    return any(tok in text for tok in noise_tokens)


def build_verification_candidates(
    payload: Mapping[str, Any],
    *,
    strict_period_filter: bool,
    strict_scope_filter: bool,
    strict_evidence: bool,
) -> dict[str, Any]:
    candidates, _ = build_verification_candidates_with_stats(
        payload,
        strict_period_filter=strict_period_filter,
        strict_scope_filter=strict_scope_filter,
        strict_evidence=strict_evidence,
    )
    return candidates


def build_verification_candidates_with_stats(
    payload: Mapping[str, Any],
    *,
    strict_period_filter: bool,
    strict_scope_filter: bool,
    strict_evidence: bool,
) -> tuple[dict[str, Any], dict[str, int]]:
    canonical_metrics = dict(payload.get("canonical_metrics") or {})
    candidates: dict[str, Any] = dict(canonical_metrics)
    stats = {
        "candidate_rows": 0,
        "dropped_period": 0,
        "dropped_scope": 0,
        "dropped_noncanonical": 0,
    }
    rows = list(payload.get("primary_rows") or payload.get("canonical_rows") or payload.get("normalized_metrics") or [])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        stats["candidate_rows"] += 1
        raw_metric = row.get("metric_base") or row.get("metric")
        if raw_metric is None:
            continue
        raw_metric_s = str(raw_metric).strip().lower()
        if not raw_metric_s:
            continue

        period = str(row.get("period") or row.get("statement_period_end") or "").strip()
        scope = str(row.get("statement_scope") or row.get("statement_type") or "").strip().lower()
        if strict_period_filter and not period:
            stats["dropped_period"] += 1
        if strict_scope_filter and scope in {"", "narrative", "other", "unknown"}:
            stats["dropped_scope"] += 1

        value = row.get("value")
        if normalize_numeric(value) is None:
            continue

        canonical_name = normalize_metric_name(raw_metric_s)
        if strict_evidence and canonical_name is None and _is_explicit_noise_row(row):
            stats["dropped_noncanonical"] += 1
            continue
        key = canonical_name or raw_metric_s
        if key not in candidates:
            candidates[key] = value
    return candidates, stats
