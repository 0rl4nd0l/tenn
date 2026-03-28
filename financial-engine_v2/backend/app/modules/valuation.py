"""valuation.py — Valuation multiples and signals (D1 only, no LLM).

Computes market-relative valuation ratios from the latest period financials
and current price. Produces absolute valuation signals (cheap/fair/expensive)
and a composite signal via majority vote.

Implements the AnalysisModule Protocol from app.modules.base.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.base import (
    ArtifactSet,
    Completeness,
    EvidenceItem,
    ModuleHelpers,
)
from app.modules.math_utils import ratio, round_or_none, safe_mul
from app.modules.ticker_context import PeriodMetrics, TickerContext

logger = logging.getLogger(__name__)

# Signal thresholds (configurable defaults)
_DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "pe_ratio": {"cheap": 12.0, "expensive": 25.0},
    "ev_ebit": {"cheap": 8.0, "expensive": 16.0},
    "fcf_yield_pct": {"cheap": 8.0, "expensive": 4.0},  # inverted
    "ev_revenue": {"cheap": 2.0, "expensive": 6.0},
}


def _classify_signal(
    metric: str,
    value: float | None,
    thresholds: dict[str, dict[str, float]] | None = None,
) -> str | None:
    """Classify a valuation metric as cheap / fair / expensive.

    Returns None if value is None or metric has no threshold entry.
    fcf_yield_pct uses inverted logic (higher = cheaper).
    """
    if value is None:
        return None
    t = (thresholds or _DEFAULT_THRESHOLDS).get(metric)
    if t is None:
        return None
    if metric == "fcf_yield_pct":
        if value > t["cheap"]:
            return "cheap"
        return "fair" if value >= t["expensive"] else "expensive"
    if value < t["cheap"]:
        return "cheap"
    return "fair" if value <= t["expensive"] else "expensive"


def _composite_signal(signals: dict[str, str | None]) -> str:
    """Majority vote across available signals.

    Returns 'cheap', 'fair', or 'expensive'. Ties broken by order:
    cheap > fair > expensive. 'insufficient_data' if none available.
    """
    counts: dict[str, int] = {"cheap": 0, "fair": 0, "expensive": 0}
    for v in signals.values():
        if v is not None:
            counts[v] = counts.get(v, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return "insufficient_data"
    max_count = max(counts.values())
    for label in ("cheap", "fair", "expensive"):
        if counts[label] == max_count:
            return label
    return "fair"  # unreachable


def _compute_multiples(price: float, latest: PeriodMetrics) -> dict[str, Any]:
    """Compute valuation multiples from price and latest period metrics."""
    shares = latest.shares_outstanding
    np_attr = latest.np_attributable
    ebit = latest.ebit
    revenue = latest.revenue
    ocf = latest.operating_cf
    capex = latest.capex
    net_debt = latest.net_debt

    market_cap = safe_mul(price, shares)
    fcf = (ocf - abs(capex)) if (ocf is not None and capex is not None) else None
    ev = (market_cap + net_debt) if (market_cap is not None and net_debt is not None) else None

    pe_ratio = ratio(market_cap, np_attr) if (np_attr is not None and np_attr > 0) else None
    earnings_yield_pct = (
        safe_mul(ratio(np_attr, market_cap), 100.0)
        if (market_cap is not None and market_cap > 0) else None
    )
    ev_ebit = ratio(ev, ebit) if (ebit is not None and ebit > 0) else None
    ev_revenue = ratio(ev, revenue)
    ev_ocf = ratio(ev, ocf) if (ocf is not None and ocf > 0) else None
    p_fcf = ratio(market_cap, fcf) if (fcf is not None and fcf > 0) else None
    fcf_yield_pct = (
        safe_mul(ratio(fcf, market_cap), 100.0)
        if (market_cap is not None and market_cap > 0) else None
    )
    eps = ratio(np_attr, shares)
    fcf_per_share = ratio(fcf, shares)

    return {
        "market_cap": round_or_none(market_cap, 0),
        "enterprise_value": round_or_none(ev, 0),
        "fcf": round_or_none(fcf, 0),
        "pe_ratio": round_or_none(pe_ratio, 2),
        "earnings_yield_pct": round_or_none(earnings_yield_pct, 2),
        "ev_ebit": round_or_none(ev_ebit, 2),
        "ev_revenue": round_or_none(ev_revenue, 2),
        "ev_ocf": round_or_none(ev_ocf, 2),
        "p_fcf": round_or_none(p_fcf, 2),
        "fcf_yield_pct": round_or_none(fcf_yield_pct, 2),
        "eps": round_or_none(eps, 4),
        "fcf_per_share": round_or_none(fcf_per_share, 4),
    }


class ValuationModule(ModuleHelpers):
    """Valuation multiples and signals -- D1 only (no LLM)."""

    @property
    def name(self) -> str:
        return "valuation"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials", "price"})

    def _fail(self, ticker: str, reason: str) -> ArtifactSet:
        return self._build_artifact(
            ticker=ticker,
            module_name=self.name,
            completeness=Completeness.FAILED,
            structured={"reason": reason},
        )

    def run(
        self,
        context: TickerContext,
        *,
        thresholds: dict[str, dict[str, float]] | None = None,
    ) -> ArtifactSet:
        ticker = context.ticker

        # Gate: price required
        if not context.has_price or context.price is None:
            return self._fail(ticker, "no price data available")
        price = context.price.last_close
        if price <= 0:
            return self._fail(ticker, f"invalid price: {price}")

        # Gate: financials required
        if not context.has_financials or context.financials is None:
            return self._fail(ticker, "no financial data available")
        latest = context.financials.latest
        if latest is None:
            return self._fail(ticker, "no latest period in financials")

        # Compute multiples
        multiples = _compute_multiples(price, latest)

        # Signals
        signal_metrics = ("pe_ratio", "ev_ebit", "fcf_yield_pct", "ev_revenue")
        signals: dict[str, str | None] = {
            m: _classify_signal(m, multiples.get(m), thresholds)
            for m in signal_metrics
        }
        composite = _composite_signal(signals)

        # Completeness
        none_count = sum(1 for v in multiples.values() if v is None)
        warnings: tuple[str, ...] = ()
        if none_count > 0:
            warnings = (f"{none_count}/{len(multiples)} multiples unavailable",)
        completeness = Completeness.COMPLETE if none_count == 0 else Completeness.PARTIAL

        structured: dict[str, Any] = {
            "price": price,
            "price_currency": context.price.currency,
            "price_source": context.price.source,
            "period_end": str(latest.period_end),
            "period_type": latest.period_type,
            "multiples": multiples,
            "signals": signals,
            "composite_signal": composite,
        }
        evidence = (
            EvidenceItem(
                evidence_id=f"{ticker}_valuation_computed",
                source_type="computed",
                content=(
                    f"Valuation from price={price} ({context.price.source}) "
                    f"and {latest.period_type} period ending {latest.period_end}"
                ),
            ),
        )

        return self._build_artifact(
            ticker=ticker,
            module_name=self.name,
            completeness=completeness,
            structured=structured,
            evidence=evidence,
            warnings=warnings,
        )
