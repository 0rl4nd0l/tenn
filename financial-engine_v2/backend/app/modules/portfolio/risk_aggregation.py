"""risk_aggregation.py — Portfolio-level risk aggregation.

Computes weighted average risk score, risk distribution by bucket,
worst holdings list, and leverage concentration (weight in high-leverage
holdings).
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.artifacts import read_artifact
from app.modules.math_utils import round_or_none

logger = logging.getLogger(__name__)

_RISK_BUCKETS = ("low", "moderate", "elevated", "high")
_RISK_THRESHOLDS = {"low": 25.0, "moderate": 50.0, "elevated": 75.0}


def _classify_risk_bucket(score: float | None) -> str:
    """Classify a risk score into a bucket."""
    if score is None:
        return "moderate"  # conservative default
    if score < _RISK_THRESHOLDS["low"]:
        return "low"
    if score < _RISK_THRESHOLDS["moderate"]:
        return "moderate"
    if score < _RISK_THRESHOLDS["elevated"]:
        return "elevated"
    return "high"


def compute_risk_aggregation(
    tickers: tuple[str, ...],
    weights: dict[str, float],
    reports_root: str | None = None,
) -> dict[str, Any]:
    """Aggregate risk across portfolio holdings.

    Returns:
        dict with portfolio_risk_score, risk_distribution, worst_holdings,
        leverage_concentration, and holdings_missing.
    """
    distribution: dict[str, dict[str, Any]] = {
        b: {"count": 0, "weight": 0.0} for b in _RISK_BUCKETS
    }
    score_sum = 0.0
    weight_sum = 0.0
    details: list[dict[str, Any]] = []
    missing: list[str] = []

    for ticker in tickers:
        risk_art = read_artifact(ticker, "risk", reports_root)
        bs_art = read_artifact(ticker, "balance_sheet", reports_root)

        if risk_art is None:
            missing.append(ticker)
            continue

        w = weights.get(ticker, 0.0)
        risk_score = risk_art.get("risk_score")
        trajectory = risk_art.get("trajectory", "unknown")

        # Leverage from balance sheet
        leverage_risk = "unknown"
        if bs_art is not None:
            signals = bs_art.get("signals", {})
            leverage_risk = signals.get("leverage_risk", "unknown")

        bucket = _classify_risk_bucket(risk_score)
        distribution[bucket]["count"] += 1
        distribution[bucket]["weight"] += w

        if risk_score is not None:
            score_sum += risk_score * w
            weight_sum += w

        details.append({
            "ticker": ticker,
            "weight": round_or_none(w, 4),
            "risk_score": risk_score,
            "risk_bucket": bucket,
            "trajectory": trajectory,
            "leverage_risk": leverage_risk,
        })

    portfolio_risk_score = (
        round_or_none(score_sum / weight_sum, 2)
        if weight_sum > 0 else None
    )

    # Round distribution weights
    for bucket in distribution.values():
        bucket["weight"] = round_or_none(bucket["weight"], 4)

    # Worst holdings: sorted by risk score descending, top 5
    scored = [d for d in details if d["risk_score"] is not None]
    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    worst = scored[:5]

    # Leverage concentration: weight in high/critical leverage holdings
    high_leverage_weight = sum(
        d["weight"] or 0.0 for d in details
        if d["leverage_risk"] in ("high", "critical")
    )

    return {
        "portfolio_risk_score": portfolio_risk_score,
        "risk_distribution": distribution,
        "worst_holdings": worst,
        "leverage_concentration": round_or_none(high_leverage_weight, 4),
        "holdings_detail": details,
        "holdings_missing": missing,
    }
