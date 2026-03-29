"""moat_quality.py — Portfolio-level moat quality aggregation.

Reads moat artifacts for all tickers, produces distribution of moat
classifications (wide/narrow/none/unassessed) with counts and weights,
and computes a weighted average moat score.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.artifacts import read_artifact
from app.modules.math_utils import round_or_none

logger = logging.getLogger(__name__)

_MOAT_BUCKETS = ("wide", "narrow", "none", "unassessed")


def compute_moat_quality(
    tickers: tuple[str, ...],
    weights: dict[str, float],
    reports_root: str | None = None,
) -> dict[str, Any]:
    """Aggregate moat quality across portfolio holdings.

    Returns:
        dict with portfolio_moat_score, moat_distribution, and per-ticker details.
    """
    distribution: dict[str, dict[str, Any]] = {
        b: {"count": 0, "weight": 0.0} for b in _MOAT_BUCKETS
    }
    score_sum = 0.0
    weight_sum = 0.0
    details: list[dict[str, Any]] = []
    missing: list[str] = []

    for ticker in tickers:
        art = read_artifact(ticker, "moat", reports_root)
        if art is None:
            missing.append(ticker)
            distribution["unassessed"]["count"] += 1
            distribution["unassessed"]["weight"] += weights.get(ticker, 0.0)
            continue

        w = weights.get(ticker, 0.0)
        classification = art.get("moat_classification") or "unassessed"
        moat_score = art.get("moat_score")

        bucket = classification if classification in _MOAT_BUCKETS else "unassessed"
        distribution[bucket]["count"] += 1
        distribution[bucket]["weight"] += w

        if moat_score is not None:
            score_sum += moat_score * w
            weight_sum += w

        details.append({
            "ticker": ticker,
            "weight": round_or_none(w, 4),
            "moat_classification": classification,
            "moat_score": moat_score,
        })

    portfolio_moat_score = (
        round_or_none(score_sum / weight_sum, 2)
        if weight_sum > 0 else None
    )

    # Round distribution weights
    for bucket in distribution.values():
        bucket["weight"] = round_or_none(bucket["weight"], 4)

    return {
        "portfolio_moat_score": portfolio_moat_score,
        "moat_distribution": distribution,
        "holdings_detail": details,
        "holdings_missing": missing,
    }
