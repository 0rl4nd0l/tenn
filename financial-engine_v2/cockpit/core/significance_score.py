"""significance_score.py — Pure scoring for market-update prioritisation.

Used by the bounded v1 verbal market-update orchestrator (P5) to decide which
tickers warrant inclusion in the headline summary and which deserve a queued
follow-up action.

This module is deliberately pure: no I/O, no LLM, no model loading, no GPU
work. It runs synchronously alongside live extraction without contention.

Scoring rubric (additive, capped at 1.0):
    * |pct_change| >= 5.0  -> +0.5  ("major move")
    * |pct_change| >= 2.0  -> +0.3  ("notable move")
    * has_alerts           -> +0.3  ("active alerts")
    * news_count_24h >= 5  -> +0.2  ("news volume")

Stale-news flag is informational only — recorded in `reasons` but not scored.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "TickerSnapshot",
    "TickerScore",
    "compute_significance",
]


@dataclass(frozen=True)
class TickerSnapshot:
    """Lightweight market snapshot for a single ticker.

    All fields are optional except `ticker`. Producers should populate what
    they have; the scorer treats missing fields as "no signal".
    """

    ticker: str
    price: float | None
    pct_change: float | None
    volume: int | None
    news_count_24h: int = 0
    has_alerts: bool = False
    stale_news: bool = False


@dataclass(frozen=True)
class TickerScore:
    """Significance score plus human-readable reasons.

    `significance` is in [0.0, 1.0]. `reasons` is an ordered tuple suitable
    for surfacing to the operator (e.g., "major move +6.50%, active alerts").
    """

    ticker: str
    significance: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


_MAJOR_MOVE_PCT = 5.0
_NOTABLE_MOVE_PCT = 2.0
_NEWS_VOLUME_THRESHOLD = 5

_MAJOR_MOVE_WEIGHT = 0.5
_NOTABLE_MOVE_WEIGHT = 0.3
_ALERTS_WEIGHT = 0.3
_NEWS_VOLUME_WEIGHT = 0.2


def compute_significance(snap: TickerSnapshot) -> TickerScore:
    """Score `snap` and return a frozen TickerScore.

    Pure function: identical input always yields identical output.
    """
    score = 0.0
    reasons: list[str] = []

    pc = snap.pct_change
    if pc is not None:
        magnitude = abs(pc)
        if magnitude >= _MAJOR_MOVE_PCT:
            score += _MAJOR_MOVE_WEIGHT
            reasons.append(f"major move {pc:+.2f}%")
        elif magnitude >= _NOTABLE_MOVE_PCT:
            score += _NOTABLE_MOVE_WEIGHT
            reasons.append(f"notable move {pc:+.2f}%")

    if snap.has_alerts:
        score += _ALERTS_WEIGHT
        reasons.append("active alerts")

    if snap.news_count_24h >= _NEWS_VOLUME_THRESHOLD:
        score += _NEWS_VOLUME_WEIGHT
        reasons.append(f"news volume ({snap.news_count_24h} items)")

    if snap.stale_news:
        reasons.append("stale news data")

    capped = min(score, 1.0)
    return TickerScore(
        ticker=snap.ticker.upper(),
        significance=capped,
        reasons=tuple(reasons),
    )
