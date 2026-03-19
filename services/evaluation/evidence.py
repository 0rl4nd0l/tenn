#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from services.evaluation.evidence_utils import numeric_match, verify_with_context


def verify_metrics(metrics: Mapping[str, Any] | None, raw_text: str | None) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    rejected: dict[str, dict[str, Any]] = {}

    for metric, value in dict(metrics or {}).items():
        metric_name = str(metric or "").strip()
        if not metric_name:
            continue
        numeric_ok = numeric_match(value, raw_text)
        context_ok = verify_with_context(value, metric_name, raw_text)
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
