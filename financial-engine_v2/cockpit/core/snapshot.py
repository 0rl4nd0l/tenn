from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


NUMERIC_FIELDS = [
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
]


@dataclass
class SnapshotBundle:
    ticker: str
    run_context: dict[str, Any]
    source_documents: list[dict[str, Any]]
    metrics_before: dict[str, Any] | None
    metrics_after: dict[str, Any] | None
    metrics_diff: list[dict[str, Any]]
    confidence_summary: dict[str, Any]
    verification_summary: dict[str, Any]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def build_snapshot_payload(
    ticker: str,
    run_context: dict[str, Any],
    docs: list[dict[str, Any]],
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    verification_summary: dict[str, Any],
) -> dict[str, Any]:
    diff: list[dict[str, Any]] = []
    for field in NUMERIC_FIELDS:
        before_value = _to_float((before or {}).get(field))
        after_value = _to_float((after or {}).get(field))
        if before_value != after_value:
            delta = None if before_value is None or after_value is None else after_value - before_value
            diff.append(
                {
                    "field": field,
                    "before": before_value,
                    "after": after_value,
                    "delta": delta,
                }
            )

    payload = {
        "ticker": ticker.upper(),
        "run_context": run_context,
        "source_documents": docs[:20],
        "metrics_before": before,
        "metrics_after": after,
        "metrics_diff": diff,
        "confidence_summary": {
            "before": (before or {}).get("confidence_metrics"),
            "after": (after or {}).get("confidence_metrics"),
        },
        "verification_summary": verification_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return payload
