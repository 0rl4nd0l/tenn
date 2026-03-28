"""roic.py — Return on Invested Capital analysis module.

D1-only (no LLM). Computes pre-tax and post-tax ROIC per period,
capital turnover, and trend direction.

Invested capital = market_cap + net_debt (proxy; total_equity not in schema).
Statutory tax rate defaults to 30% (Australian corporate rate).
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
from app.modules.math_utils import ratio, round_or_none, safe_add, safe_mul, safe_sub
from app.modules.ticker_context import PeriodMetrics, TickerContext

logger = logging.getLogger(__name__)

_DEFAULT_TAX_RATE: float = 0.30
_ROIC_THRESHOLD: float = 0.10
_TREND_THRESHOLD: float = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invested_capital(
    period: PeriodMetrics, market_cap: float | None
) -> float | None:
    """IC = market_cap_proxy + net_debt. None when either is missing."""
    if market_cap is not None and period.net_debt is not None:
        return safe_add(market_cap, period.net_debt)
    return None


def _period_metrics(
    period: PeriodMetrics, market_cap: float | None, tax_rate: float
) -> dict[str, Any]:
    ic = _invested_capital(period, market_cap)
    nopat = safe_mul(period.ebit, 1.0 - tax_rate) if period.ebit is not None else None
    return {
        "period_end": str(period.period_end),
        "period_type": period.period_type,
        "ebit": round_or_none(period.ebit, 2),
        "nopat": round_or_none(nopat, 2),
        "invested_capital": round_or_none(ic, 2),
        "ebit_on_ic": round_or_none(ratio(period.ebit, ic)),
        "nopat_on_ic": round_or_none(ratio(nopat, ic)),
        "capital_turnover": round_or_none(ratio(period.revenue, ic)),
    }


def _classify_direction(values: list[float | None]) -> str:
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return "insufficient_data"
    first, last = clean[0], clean[-1]
    if first == 0:
        return "insufficient_data"
    change = (last - first) / abs(first)
    if change > _TREND_THRESHOLD:
        return "improving"
    if change < -_TREND_THRESHOLD:
        return "declining"
    return "stable"


def _trend(periods: list[dict[str, Any]]) -> dict[str, Any]:
    if len(periods) < 2:
        return {
            "available": False,
            "ebit_on_ic_delta": None,
            "nopat_on_ic_delta": None,
            "direction": "insufficient_data",
        }
    latest, prior = periods[-1], periods[-2]
    return {
        "available": True,
        "ebit_on_ic_delta": round_or_none(
            safe_sub(latest["ebit_on_ic"], prior["ebit_on_ic"])
        ),
        "nopat_on_ic_delta": round_or_none(
            safe_sub(latest["nopat_on_ic"], prior["nopat_on_ic"])
        ),
        "direction": _classify_direction([p["ebit_on_ic"] for p in periods]),
    }


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class ROICModule(ModuleHelpers):
    """Return on Invested Capital — D1 computation module."""

    @property
    def name(self) -> str:
        return "roic"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []

        # Minimum viability
        if not context.has_financials:
            return self._fail(ticker, "no_financial_data")

        assert context.financials is not None
        annual = [p for p in context.financials.periods if p.period_type == "A"]
        if not annual:
            return self._fail(ticker, "no_annual_periods")

        # Market cap proxy
        market_cap: float | None = None
        latest_period = annual[-1]
        if context.has_price and latest_period.shares_outstanding is not None:
            assert context.price is not None
            market_cap = context.price.last_close * latest_period.shares_outstanding
            logger.info("ROIC %s: market_cap proxy %.2f", ticker, market_cap)
        else:
            warnings.append("No price/shares for market_cap proxy; IC may be None.")

        # Per-period computation
        tax_rate = _DEFAULT_TAX_RATE
        computed = [_period_metrics(p, market_cap, tax_rate) for p in annual]

        # Data quality flags
        ic_available = any(p["invested_capital"] is not None for p in computed)
        has_net_debt = any(p.net_debt is not None for p in annual)
        if not ic_available:
            warnings.append("Invested capital could not be computed for any period.")

        # Completeness
        lc = computed[-1]
        all_core = all(
            lc.get(k) is not None
            for k in ("ebit_on_ic", "nopat_on_ic", "capital_turnover")
        )
        completeness = Completeness.COMPLETE if all_core else Completeness.PARTIAL

        # Summary
        latest_nopat_on_ic = lc.get("nopat_on_ic")
        summary = {
            "latest_ebit_on_ic": lc.get("ebit_on_ic"),
            "latest_nopat_on_ic": latest_nopat_on_ic,
            "roic_above_10pct": (
                latest_nopat_on_ic > _ROIC_THRESHOLD
                if latest_nopat_on_ic is not None
                else None
            ),
            "period_count": len(computed),
            "coverage_years": sorted(
                p["period_end"][:4] for p in computed if p["ebit_on_ic"] is not None
            ),
        }

        # Evidence
        evidence: list[EvidenceItem] = [
            EvidenceItem(
                evidence_id="roic_tax_rate",
                source_type="computed",
                content=f"Statutory tax rate assumed: {tax_rate:.0%}",
            ),
        ]
        if market_cap is not None:
            evidence.insert(
                0,
                EvidenceItem(
                    evidence_id="roic_market_cap_proxy",
                    source_type="computed",
                    content=f"Market cap proxy: {market_cap:,.0f} (price * shares)",
                ),
            )

        return self._build_artifact(
            ticker=ticker,
            module_name=self.name,
            completeness=completeness,
            structured={
                "config": {"statutory_tax_rate": tax_rate, "period_type": "A"},
                "periods": computed,
                "trend": _trend(computed),
                "summary": summary,
                "data_quality": {
                    "has_equity_data": False,
                    "has_net_debt": has_net_debt,
                    "ic_available": ic_available,
                    "tax_rate_assumed": True,
                    "statutory_tax_rate": tax_rate,
                    "market_cap_proxy_used": market_cap is not None,
                },
            },
            evidence=tuple(evidence),
            warnings=tuple(warnings),
        )

    def _fail(self, ticker: str, error: str) -> ArtifactSet:
        msg = error.replace("_", " ").capitalize() + "."
        return self._build_artifact(
            ticker=ticker,
            module_name=self.name,
            completeness=Completeness.FAILED,
            structured={"error": error},
            warnings=(msg,),
        )
