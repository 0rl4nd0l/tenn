"""weights.py — Portfolio weight computation.

Computes portfolio weights from one of three strategies (in priority order):
1. weight_override — explicit user-defined weight
2. shares x price — market-value weighting
3. equal-weight fallback — when neither is available
"""
from __future__ import annotations

from app.modules.portfolio.types import Holding


def compute_weights(
    holdings: tuple[Holding, ...] | list[Holding],
    prices: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute normalized weights for each holding.

    Priority:
      1. weight_override if set on the holding
      2. shares * price if both are available
      3. Equal weight across all holdings without override or value

    Returns dict of ticker -> weight (sums to 1.0).
    """
    if not holdings:
        return {}

    prices = prices or {}
    raw: dict[str, float] = {}

    for h in holdings:
        if h.weight_override is not None:
            raw[h.ticker] = h.weight_override
        elif h.shares is not None and h.ticker in prices:
            raw[h.ticker] = h.shares * prices[h.ticker]
        else:
            raw[h.ticker] = 0.0  # placeholder for equal-weight

    # Tickers needing equal-weight fallback
    zero_tickers = [t for t, w in raw.items() if w == 0.0]
    if zero_tickers:
        valued = {t: w for t, w in raw.items() if w > 0.0}
        if valued:
            # Give zero tickers the average of valued tickers
            avg = sum(valued.values()) / len(valued)
            for t in zero_tickers:
                raw[t] = avg
        else:
            # All are zero — pure equal weight
            for t in zero_tickers:
                raw[t] = 1.0

    # Normalize to sum to 1.0
    total = sum(raw.values())
    if total <= 0:
        n = len(raw)
        return {t: 1.0 / n for t in raw}
    return {t: w / total for t, w in raw.items()}
