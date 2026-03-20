#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from services.evaluation.normalizer import normalize_metric_name, normalize_numeric


def build_verification_candidates(
    payload: Mapping[str, Any],
    *,
    strict_period_filter: bool,
    strict_scope_filter: bool,
    strict_evidence: bool,
) -> dict[str, Any]:
    canonical_metrics = dict(payload.get("canonical_metrics") or {})
    if strict_period_filter and strict_scope_filter and strict_evidence:
        return canonical_metrics

    candidates: dict[str, Any] = dict(canonical_metrics)
    rows = list(payload.get("primary_rows") or payload.get("canonical_rows") or payload.get("normalized_metrics") or [])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        raw_metric = row.get("metric_base") or row.get("metric")
        if raw_metric is None:
            continue
        raw_metric_s = str(raw_metric).strip().lower()
        if not raw_metric_s:
            continue

        period = str(row.get("period") or row.get("statement_period_end") or "").strip()
        scope = str(row.get("statement_scope") or row.get("statement_type") or "").strip().lower()
        if strict_period_filter and not period:
            continue
        if strict_scope_filter and scope in {"", "narrative", "other", "unknown"}:
            continue

        value = row.get("value")
        if normalize_numeric(value) is None:
            continue

        canonical_name = normalize_metric_name(raw_metric_s)
        key = canonical_name or raw_metric_s
        if key not in candidates:
            candidates[key] = value
    return candidates
