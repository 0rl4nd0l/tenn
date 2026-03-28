"""balance_sheet.py — D1-only balance sheet analysis module.

Computes leverage, liquidity, FCF, and debt trajectory metrics from
PeriodMetrics. No LLM calls — pure deterministic computation.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.base import ArtifactSet, Completeness, EvidenceItem, ModuleHelpers
from app.modules.math_utils import (
    classify_direction,
    linear_slope,
    pct_change,
    ratio,
    round_or_none,
    safe_sub,
)
from app.modules.ticker_context import PeriodMetrics, TickerContext

logger = logging.getLogger(__name__)

_CORE_FIELDS = ("net_debt", "ebit", "operating_cf", "capex", "cash_end")


def _compute_fcf(p: PeriodMetrics) -> float | None:
    """operating_cf - abs(capex). None if either input missing."""
    if p.operating_cf is None or p.capex is None:
        return None
    return p.operating_cf - abs(p.capex)


def _period_metrics(p: PeriodMetrics) -> dict[str, Any]:
    """Compute balance-sheet metrics for a single period."""
    fcf = _compute_fcf(p)

    net_debt_to_ebit: float | None = None
    if p.ebit is not None and p.ebit > 0:
        net_debt_to_ebit = ratio(p.net_debt, p.ebit)

    debt_to_fcf: float | None = None
    if fcf is not None and fcf > 0:
        debt_to_fcf = ratio(p.net_debt, fcf)

    cash_runway_quarters: float | None = None
    if (
        p.operating_cf is not None
        and p.operating_cf < 0
        and p.cash_end is not None
        and p.cash_end > 0
    ):
        cash_runway_quarters = p.cash_end / abs(p.operating_cf)

    net_cash_position: bool | None = None
    if p.net_debt is not None:
        net_cash_position = p.net_debt < 0

    return {
        "period_end": str(p.period_end),
        "period_type": p.period_type,
        "net_debt": p.net_debt,
        "ebit": p.ebit,
        "operating_cf": p.operating_cf,
        "capex": p.capex,
        "cash_end": p.cash_end,
        "fcf": round_or_none(fcf),
        "net_debt_to_ebit": round_or_none(net_debt_to_ebit),
        "debt_to_fcf": round_or_none(debt_to_fcf),
        "cash_runway_quarters": round_or_none(cash_runway_quarters, 1),
        "net_cash_position": net_cash_position,
    }


def _compute_deltas(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute period-over-period deltas. First period has no delta."""
    deltas: list[dict[str, Any]] = [{}]
    for i in range(1, len(periods)):
        cur, prev = periods[i], periods[i - 1]
        deltas.append({
            "net_debt_change_abs": round_or_none(
                safe_sub(cur.get("net_debt"), prev.get("net_debt"))
            ),
            "net_debt_change_pct": round_or_none(
                pct_change(cur.get("net_debt"), prev.get("net_debt"))
            ),
            "fcf_change_pct": round_or_none(
                pct_change(cur.get("fcf"), prev.get("fcf"))
            ),
            "net_debt_to_ebit_change": round_or_none(
                safe_sub(cur.get("net_debt_to_ebit"), prev.get("net_debt_to_ebit"))
            ),
        })
    return deltas


def _compute_trajectory(periods: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute trajectory signals across the full period series."""
    net_debts = [p.get("net_debt") for p in periods]
    fcfs = [p.get("fcf") for p in periods]

    # For net_debt, decreasing is improving — invert classify_direction
    raw_nd = classify_direction(net_debts)
    nd_map = {
        "improving": "deteriorating",
        "deteriorating": "improving",
        "stable": "stable",
        "insufficient_data": "insufficient_data",
    }

    return {
        "net_debt_direction": nd_map[raw_nd],
        "net_debt_slope_per_period": round_or_none(linear_slope(net_debts)),
        "fcf_direction": classify_direction(fcfs),
        "fcf_positive_periods": sum(1 for f in fcfs if f is not None and f > 0),
        "fcf_negative_periods": sum(1 for f in fcfs if f is not None and f < 0),
    }


def _classify_leverage_risk(latest: dict[str, Any]) -> str:
    nd = latest.get("net_debt")
    ebit = latest.get("ebit")
    r = latest.get("net_debt_to_ebit")
    if nd is not None and nd < 0:
        return "low"
    if nd is not None and nd > 0 and (ebit is None or ebit <= 0):
        return "critical"
    if r is None:
        return "unknown"
    if r < 1.5:
        return "low"
    if r < 3.0:
        return "moderate"
    if r < 5.0:
        return "high"
    return "critical"


def _classify_liquidity_risk(latest: dict[str, Any]) -> str:
    ocf = latest.get("operating_cf")
    runway = latest.get("cash_runway_quarters")
    if ocf is not None and ocf >= 0:
        return "low"
    if runway is None:
        return "unknown"
    if runway > 8:
        return "low"
    if runway > 4:
        return "moderate"
    if runway > 2:
        return "high"
    return "critical"


def _classify_fcf_coverage(latest: dict[str, Any]) -> str:
    fcf = latest.get("fcf")
    if fcf is None or fcf <= 0:
        return "none"
    r = latest.get("debt_to_fcf")
    if r is None:
        return "unknown"
    if r < 3:
        return "strong"
    if r < 6:
        return "adequate"
    if r < 10:
        return "weak"
    return "none"


def _compute_signals(
    latest: dict[str, Any], trajectory: dict[str, Any],
) -> dict[str, Any]:
    return {
        "leverage_risk": _classify_leverage_risk(latest),
        "liquidity_risk": _classify_liquidity_risk(latest),
        "debt_trajectory_signal": trajectory.get(
            "net_debt_direction", "insufficient_data"
        ),
        "fcf_coverage_signal": _classify_fcf_coverage(latest),
    }


def _data_quality(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    if not periods:
        return {
            "fields_present": [],
            "fields_missing": list(_CORE_FIELDS),
            "min_confidence": None,
            "avg_confidence": None,
        }
    latest = periods[-1]
    present = [f for f in _CORE_FIELDS if getattr(latest, f, None) is not None]
    missing = [f for f in _CORE_FIELDS if getattr(latest, f, None) is None]
    confidences = [p.confidence for p in periods if p.confidence is not None]
    return {
        "fields_present": present,
        "fields_missing": missing,
        "min_confidence": min(confidences) if confidences else None,
        "avg_confidence": (
            round(sum(confidences) / len(confidences), 4) if confidences else None
        ),
    }


class BalanceSheetModule(ModuleHelpers):
    """D1-only balance sheet analysis — leverage, liquidity, FCF trajectory."""

    @property
    def name(self) -> str:
        return "balance_sheet"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []

        if not context.has_financials:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financial periods available"},
                warnings=("no_financials",),
            )

        assert context.financials is not None
        periods_raw = context.financials.periods
        if not periods_raw:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financial periods available"},
                warnings=("no_periods",),
            )

        computed = [_period_metrics(p) for p in periods_raw]

        deltas = _compute_deltas(computed)
        for i, d in enumerate(deltas):
            if d:
                computed[i]["deltas"] = d

        trajectory = _compute_trajectory(computed)
        latest = computed[-1]
        signals = _compute_signals(latest, trajectory)
        quality = _data_quality(periods_raw)

        has_none = any(
            latest.get(k) is None
            for k in ("net_debt_to_ebit", "debt_to_fcf", "fcf")
        )
        completeness = Completeness.PARTIAL if has_none else Completeness.COMPLETE

        if quality["fields_missing"]:
            warnings.append(
                f"missing_fields: {', '.join(quality['fields_missing'])}"
            )

        evidence = (
            EvidenceItem(
                evidence_id=f"bs_{ticker}_{latest['period_end']}",
                source_type="financial_statement",
                content=(
                    f"Balance sheet analysis from {len(computed)} periods "
                    f"ending {latest['period_end']}"
                ),
                confidence=quality.get("avg_confidence") or 1.0,
            ),
        )

        return self._build_artifact(
            ticker=ticker, module_name=self.name,
            completeness=completeness,
            structured={
                "periods": computed,
                "trajectory": trajectory,
                "signals": signals,
                "data_quality": quality,
            },
            evidence=evidence,
            warnings=tuple(warnings),
        )
