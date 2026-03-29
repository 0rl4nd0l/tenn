"""valuation_summary.py — Portfolio-level valuation aggregation.

Reads valuation artifacts for all tickers, computes weighted harmonic
means for P/E and EV/EBIT, and tallies signal distribution.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.artifacts import read_artifact
from app.modules.math_utils import round_or_none

logger = logging.getLogger(__name__)


def _harmonic_mean_weighted(
    values: list[tuple[float, float]],
) -> float | None:
    """Weighted harmonic mean of (value, weight) pairs.

    Skips non-positive values. Returns None if no valid pairs.
    """
    denom = 0.0
    total_weight = 0.0
    for val, wt in values:
        if val > 0 and wt > 0:
            denom += wt / val
            total_weight += wt
    if denom <= 0 or total_weight <= 0:
        return None
    return total_weight / denom


def compute_valuation_summary(
    tickers: tuple[str, ...],
    weights: dict[str, float],
    reports_root: str | None = None,
) -> dict[str, Any]:
    """Aggregate valuation across portfolio holdings.

    Returns:
        dict with portfolio_pe, portfolio_ev_ebit, signal_distribution,
        and per-ticker details.
    """
    pe_pairs: list[tuple[float, float]] = []
    ev_ebit_pairs: list[tuple[float, float]] = []
    signals: dict[str, int] = {"cheap": 0, "fair": 0, "expensive": 0}
    details: list[dict[str, Any]] = []
    missing: list[str] = []

    for ticker in tickers:
        art = read_artifact(ticker, "valuation", reports_root)
        if art is None:
            missing.append(ticker)
            continue

        w = weights.get(ticker, 0.0)
        pe = art.get("pe_ratio")
        ev_ebit = art.get("ev_ebit")
        composite = art.get("composite_signal")

        if pe is not None and pe > 0:
            pe_pairs.append((pe, w))
        if ev_ebit is not None and ev_ebit > 0:
            ev_ebit_pairs.append((ev_ebit, w))
        if composite in signals:
            signals[composite] += 1

        details.append({
            "ticker": ticker,
            "weight": round_or_none(w, 4),
            "pe_ratio": pe,
            "ev_ebit": ev_ebit,
            "composite_signal": composite,
        })

    return {
        "portfolio_pe": round_or_none(_harmonic_mean_weighted(pe_pairs), 2),
        "portfolio_ev_ebit": round_or_none(
            _harmonic_mean_weighted(ev_ebit_pairs), 2,
        ),
        "signal_distribution": signals,
        "holdings_detail": details,
        "holdings_missing": missing,
    }
