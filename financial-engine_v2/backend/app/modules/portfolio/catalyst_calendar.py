"""catalyst_calendar.py — Portfolio-level catalyst timeline.

Reads catalyst artifacts for all tickers, merges into a single timeline
sorted by timeframe, and counts by timeframe and impact direction.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.artifacts import read_artifact

logger = logging.getLogger(__name__)

_TIMEFRAME_ORDER = ("near_term", "medium_term", "long_term", "unknown")


def _timeframe_sort_key(item: dict[str, Any]) -> int:
    """Sort key for catalyst timeframe ordering."""
    tf = item.get("timeframe", "unknown")
    try:
        return _TIMEFRAME_ORDER.index(tf)
    except ValueError:
        return len(_TIMEFRAME_ORDER)


def compute_catalyst_calendar(
    tickers: tuple[str, ...],
    reports_root: str | None = None,
) -> dict[str, Any]:
    """Merge catalyst artifacts into a portfolio-level timeline.

    Returns:
        dict with timeline, by_timeframe counts, by_impact counts,
        and holdings_missing list.
    """
    timeline: list[dict[str, Any]] = []
    by_timeframe: dict[str, int] = {tf: 0 for tf in _TIMEFRAME_ORDER}
    by_impact: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}
    missing: list[str] = []

    for ticker in tickers:
        art = read_artifact(ticker, "catalysts", reports_root)
        if art is None:
            missing.append(ticker)
            continue

        catalysts = art.get("catalysts", [])
        for cat in catalysts:
            entry = {
                "ticker": ticker,
                "title": cat.get("title", ""),
                "category": cat.get("category", ""),
                "timeframe": cat.get("timeframe", "unknown"),
                "impact_direction": cat.get("impact_direction", "neutral"),
                "impact_magnitude": cat.get("impact_magnitude"),
            }
            timeline.append(entry)

            tf = entry["timeframe"]
            if tf in by_timeframe:
                by_timeframe[tf] += 1
            else:
                by_timeframe[tf] = by_timeframe.get(tf, 0) + 1

            impact = entry["impact_direction"]
            if impact in by_impact:
                by_impact[impact] += 1

    # Sort by timeframe priority
    timeline.sort(key=_timeframe_sort_key)

    return {
        "timeline": timeline,
        "by_timeframe": by_timeframe,
        "by_impact": by_impact,
        "total_catalysts": len(timeline),
        "holdings_missing": missing,
    }
