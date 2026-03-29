"""position_sizing.py — Risk-parity position sizing with quality overlay.

Algorithm:
  1. Inverse-risk weights: 1 / max(risk_score, 10)
  2. Quality factor: moat_score * 0.4 + valuation_signal * 0.3 + roic_flag * 0.3
  3. Adjusted weight = raw * (0.7 + 0.3 * quality)
  4. Normalize, apply 20% single-stock cap
  5. Returns suggested_weights with delta from current
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.artifacts import read_artifact
from app.modules.math_utils import round_or_none

logger = logging.getLogger(__name__)

_SINGLE_STOCK_CAP = 0.20
_RISK_FLOOR = 10.0

# Valuation signal -> numeric score for quality factor
_VALUATION_SCORES: dict[str, float] = {
    "cheap": 1.0,
    "fair": 0.5,
    "expensive": 0.0,
}


def _normalize_moat_score(raw: int | float | None) -> float:
    """Normalize moat_score (0-100) to 0.0-1.0 range."""
    if raw is None:
        return 0.5  # neutral default
    return max(0.0, min(1.0, float(raw) / 100.0))


def _get_roic_flag(ticker: str, reports_root: str | None) -> float:
    """Return 1.0 if ROIC exceeds WACC (positive spread), else 0.0."""
    art = read_artifact(ticker, "roic", reports_root)
    if art is None:
        return 0.5  # neutral default
    roic = art.get("roic_pct")
    wacc = art.get("wacc_pct")
    if roic is not None and wacc is not None:
        return 1.0 if roic > wacc else 0.0
    # Fallback: check if ROIC is positive
    if roic is not None:
        return 1.0 if roic > 0 else 0.0
    return 0.5


def compute_position_sizing(
    tickers: tuple[str, ...],
    current_weights: dict[str, float],
    reports_root: str | None = None,
) -> dict[str, Any]:
    """Compute risk-parity position sizes with quality overlay.

    Returns:
        dict with suggested_weights, deltas, and per-ticker breakdown.
    """
    if not tickers:
        return {
            "suggested_weights": {},
            "deltas": {},
            "holdings_detail": [],
            "holdings_missing": [],
        }

    missing: list[str] = []
    raw_weights: dict[str, float] = {}
    quality_factors: dict[str, float] = {}
    details: list[dict[str, Any]] = []

    for ticker in tickers:
        risk_art = read_artifact(ticker, "risk", reports_root)
        moat_art = read_artifact(ticker, "moat", reports_root)
        val_art = read_artifact(ticker, "valuation", reports_root)

        if risk_art is None:
            missing.append(ticker)
            continue

        # Step 1: Inverse-risk weight
        risk_score = risk_art.get("risk_score")
        if risk_score is None:
            risk_score = 50.0  # moderate default
        inv_risk = 1.0 / max(risk_score, _RISK_FLOOR)
        raw_weights[ticker] = inv_risk

        # Step 2: Quality factor
        moat_score = moat_art.get("moat_score") if moat_art else None
        moat_norm = _normalize_moat_score(moat_score)

        val_signal = val_art.get("composite_signal") if val_art else None
        val_score = _VALUATION_SCORES.get(val_signal or "", 0.5)

        roic_flag = _get_roic_flag(ticker, reports_root)

        quality = moat_norm * 0.4 + val_score * 0.3 + roic_flag * 0.3
        quality_factors[ticker] = quality

        details.append({
            "ticker": ticker,
            "risk_score": risk_score,
            "inverse_risk_weight": round_or_none(inv_risk, 6),
            "moat_score_norm": round_or_none(moat_norm, 4),
            "valuation_score": round_or_none(val_score, 4),
            "roic_flag": round_or_none(roic_flag, 4),
            "quality_factor": round_or_none(quality, 4),
        })

    if not raw_weights:
        return {
            "suggested_weights": {},
            "deltas": {},
            "holdings_detail": details,
            "holdings_missing": missing,
        }

    # Step 3: Apply quality overlay
    adjusted: dict[str, float] = {}
    for ticker, raw in raw_weights.items():
        q = quality_factors.get(ticker, 0.5)
        adjusted[ticker] = raw * (0.7 + 0.3 * q)

    # Step 4: Normalize and apply cap (iterative)
    suggested = _normalize_with_cap(adjusted, _SINGLE_STOCK_CAP)

    # Compute deltas from current weights
    deltas: dict[str, float] = {}
    for ticker in suggested:
        current = current_weights.get(ticker, 0.0)
        deltas[ticker] = round_or_none(suggested[ticker] - current, 4) or 0.0

    # Augment details with final weights
    for d in details:
        t = d["ticker"]
        d["suggested_weight"] = round_or_none(suggested.get(t, 0.0), 4)
        d["current_weight"] = round_or_none(current_weights.get(t, 0.0), 4)
        d["delta"] = deltas.get(t, 0.0)

    return {
        "suggested_weights": {
            t: round_or_none(w, 4) for t, w in suggested.items()
        },
        "deltas": deltas,
        "holdings_detail": details,
        "holdings_missing": missing,
    }


def _normalize_with_cap(
    weights: dict[str, float],
    cap: float,
    max_iterations: int = 10,
) -> dict[str, float]:
    """Normalize weights to sum to 1.0, applying a single-stock cap.

    Iteratively caps and redistributes until stable or max iterations.
    """
    result = dict(weights)

    for _ in range(max_iterations):
        total = sum(result.values())
        if total <= 0:
            n = len(result)
            return {t: 1.0 / n for t in result} if n > 0 else {}

        # Normalize
        result = {t: w / total for t, w in result.items()}

        # Check for cap violations
        capped = {t: w for t, w in result.items() if w > cap}
        if not capped:
            break

        # Cap and redistribute excess
        excess = sum(w - cap for w in capped.values())
        uncapped = {t: w for t, w in result.items() if w <= cap}
        uncapped_total = sum(uncapped.values())

        for t in capped:
            result[t] = cap

        if uncapped_total > 0:
            for t in uncapped:
                result[t] += excess * (result[t] / uncapped_total)

    return result
