#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable


MARKETINDEX_HEADED_RECOVERY_MARKERS = (
    "blocked_marketindex_headed_required",
    "blocked_marketindex_403",
    "blocked_marketindex_no_candidate",
    "blocked_marketindex_headed_error",
)
MARKETINDEX_HEADED_RECOVERY_COMMAND = "python3 scripts/recover_marketindex_headed.py"


def _normalize_tickers(tickers: Iterable[Any] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in tickers or []:
        ticker = str(raw or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        ordered.append(ticker)
    return ordered


def build_marketindex_recovery_command(tickers: Iterable[Any] | None = None) -> str:
    ordered = _normalize_tickers(tickers)
    if not ordered:
        return MARKETINDEX_HEADED_RECOVERY_COMMAND
    return f"{MARKETINDEX_HEADED_RECOVERY_COMMAND} --ticker {','.join(ordered)}"


def build_marketindex_recovery_summary(tickers: Iterable[Any] | None = None) -> dict[str, Any]:
    return {
        "status": "none",
        "requires_headed_recovery_count": 0,
        "recommended_action": "Run headed MarketIndex recovery for blocked or pending MarketIndex documents.",
        "recommended_command": build_marketindex_recovery_command(tickers),
        "status_markers": list(MARKETINDEX_HEADED_RECOVERY_MARKERS),
        "counts_by_marker": {},
        "counts_by_ticker": {},
        "samples": [],
    }


def add_marketindex_recovery_blocker(
    summary: dict[str, Any],
    *,
    ticker: Any,
    marker: Any,
    document_id: Any = "",
    source_url: Any = "",
    stage: str = "download",
) -> None:
    marker_text = str(marker or "").strip()
    if marker_text not in MARKETINDEX_HEADED_RECOVERY_MARKERS:
        return

    ticker_text = str(ticker or "").strip().upper() or "DATA_MISSING"
    summary["status"] = "requires_headed_recovery"
    summary["requires_headed_recovery_count"] = int(summary.get("requires_headed_recovery_count") or 0) + 1

    counts_by_marker = summary.setdefault("counts_by_marker", {})
    counts_by_marker[marker_text] = int(counts_by_marker.get(marker_text) or 0) + 1

    counts_by_ticker = summary.setdefault("counts_by_ticker", {})
    counts_by_ticker[ticker_text] = int(counts_by_ticker.get(ticker_text) or 0) + 1

    samples = summary.setdefault("samples", [])
    if len(samples) < 10:
        samples.append(
            {
                "ticker": ticker_text,
                "marker": marker_text,
                "document_id": str(document_id or ""),
                "source_url": str(source_url or ""),
                "stage": str(stage or "download"),
            }
        )
