"""financial_metrics.py — deterministic financial metric computation.

Operates on rows from asx_periodic_financials. No LLM, no network calls.
All inputs are numeric or None; all outputs are float or None.

Available schema fields per row:
    revenue, ebit, np_attributable, operating_cf, investing_cf,
    financing_cf, capex, cash_end, net_debt, shares_outstanding,
    period_end, period_type ('Q'|'H'|'A'), confidence_metrics
"""
from __future__ import annotations

from typing import Any


def _f(value: Any) -> float | None:
    """Coerce a DB Decimal / int / str to float, return None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return (new - old) / abs(old)


def compute_period_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Compute derived metrics for a single period row."""
    revenue = _f(row.get("revenue"))
    ebit = _f(row.get("ebit"))
    np_attr = _f(row.get("np_attributable"))
    ocf = _f(row.get("operating_cf"))
    capex = _f(row.get("capex"))
    net_debt = _f(row.get("net_debt"))
    cash_end = _f(row.get("cash_end"))

    # Free cash flow = operating CF − capex (capex stored as negative in some extractions)
    fcf: float | None = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    ebit_margin = _pct_change(ebit, revenue) if revenue else None
    np_margin = _pct_change(np_attr, revenue) if revenue else None
    fcf_margin = _pct_change(fcf, revenue) if revenue else None

    # Cash conversion: how much of EBIT becomes operating cash
    cash_conversion: float | None = None
    if ocf is not None and ebit is not None and ebit != 0:
        cash_conversion = ocf / ebit

    return {
        "period_end": str(row.get("period_end") or ""),
        "period_type": str(row.get("period_type") or ""),
        "revenue": revenue,
        "ebit": ebit,
        "np_attributable": np_attr,
        "operating_cf": ocf,
        "capex": capex,
        "fcf": fcf,
        "net_debt": net_debt,
        "cash_end": cash_end,
        "ebit_margin": ebit_margin,
        "np_margin": np_margin,
        "fcf_margin": fcf_margin,
        "cash_conversion": cash_conversion,
        "confidence": _f(row.get("confidence_metrics")),
    }


def compute_trends(periods: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Given a time-ordered list of period metric dicts (oldest → newest),
    return YoY deltas and directional signals for the most recent period.
    """
    if len(periods) < 2:
        return {"available": False, "reason": "fewer than 2 periods"}

    latest = periods[-1]
    prior = periods[-2]

    def _delta(key: str) -> float | None:
        return _pct_change(_f(latest.get(key)), _f(prior.get(key)))

    return {
        "available": True,
        "revenue_yoy": _delta("revenue"),
        "ebit_yoy": _delta("ebit"),
        "np_yoy": _delta("np_attributable"),
        "fcf_yoy": _delta("fcf"),
        "net_debt_yoy": _delta("net_debt"),
        "ebit_margin_delta": (
            (latest.get("ebit_margin") or 0) - (prior.get("ebit_margin") or 0)
            if latest.get("ebit_margin") is not None and prior.get("ebit_margin") is not None
            else None
        ),
    }


def score_financial_health(periods: list[dict[str, Any]], trends: dict[str, Any]) -> float:
    """
    Heuristic financial health score in [0, 100].

    Scoring dimensions (each contributes up to 25 pts):
      1. Profitability  — EBIT margin of the latest period
      2. Cash quality   — cash conversion (OCF / EBIT)
      3. Balance sheet  — net debt sign (negative = net cash)
      4. Momentum       — revenue and EBIT trending positively
    """
    if not periods:
        return 50.0

    latest = periods[-1]
    score = 0.0

    # 1. Profitability (25 pts)
    ebit_margin = latest.get("ebit_margin")
    if ebit_margin is not None:
        if ebit_margin >= 0.20:
            score += 25
        elif ebit_margin >= 0.10:
            score += 18
        elif ebit_margin >= 0.05:
            score += 12
        elif ebit_margin >= 0:
            score += 6

    # 2. Cash quality (25 pts)
    cc = latest.get("cash_conversion")
    if cc is not None:
        if cc >= 1.0:
            score += 25
        elif cc >= 0.75:
            score += 18
        elif cc >= 0.5:
            score += 10
        elif cc >= 0:
            score += 5

    # 3. Balance sheet (25 pts)
    net_debt = latest.get("net_debt")
    cash_end = latest.get("cash_end")
    if net_debt is not None:
        if net_debt <= 0:          # net cash position
            score += 25
        elif net_debt < 0.5e9:     # low debt (< $500M)
            score += 15
        elif net_debt < 2e9:
            score += 8
    elif cash_end is not None and cash_end > 0:
        score += 12                # cash held, no debt info

    # 4. Momentum (25 pts)
    if trends.get("available"):
        rev_yoy = trends.get("revenue_yoy")
        ebit_yoy = trends.get("ebit_yoy")
        positive = sum(
            1 for v in (rev_yoy, ebit_yoy) if v is not None and v > 0
        )
        score += positive * 12.5

    return min(100.0, round(score, 1))


def build_metrics_summary(
    rows: list[dict[str, Any]],
    *,
    period_type: str = "A",
    max_periods: int = 5,
) -> dict[str, Any]:
    """
    Main entry point. Accepts raw DB rows for a ticker, filters to the
    requested period_type, computes metrics and trends.

    Returns a dict ready for use in context assembly and report generation.
    """
    filtered = [
        r for r in rows
        if str(r.get("period_type") or "").upper() == period_type.upper()
    ]
    # Sort oldest → newest
    filtered.sort(key=lambda r: str(r.get("period_end") or ""))
    filtered = filtered[-max_periods:]

    computed = [compute_period_metrics(r) for r in filtered]
    trends = compute_trends(computed)
    health_score = score_financial_health(computed, trends)

    return {
        "period_type": period_type,
        "periods": computed,
        "trends": trends,
        "financial_health_score": health_score,
        "period_count": len(computed),
    }
