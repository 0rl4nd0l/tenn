"""sector_comparison.py — sector-relative metric comparison for ASX equities.

Computes how a ticker's fundamentals compare to its GICS sector peers.
No LLM, no network calls beyond DB reads. All outputs are numeric or None.

Usage:
    sector = get_sector_for_ticker("BHP")          # "Materials"
    peers  = SECTOR_TICKERS["Materials"]            # ["BHP", "RIO", ...]
    stats  = compute_sector_stats(db_reader, peers)
    result = compare_to_sector("BHP", ticker_metrics, stats)
"""
from __future__ import annotations

import logging
import time
from statistics import median
from typing import Any

logger = logging.getLogger(__name__)


def _get_financial_metrics():
    """Lazy import to avoid triggering the analysis __init__.py package import chain."""
    from backend.app.services.analysis.financial_metrics import (  # type: ignore[import-untyped]
        build_metrics_summary,
        compute_valuation_multiples,
    )
    return build_metrics_summary, compute_valuation_multiples


# ---------------------------------------------------------------------------
# ASX sector mappings (hardcoded — no live sector database available)
# ---------------------------------------------------------------------------

SECTOR_TICKERS: dict[str, list[str]] = {
    "Materials": [
        "BHP", "RIO", "FMG", "MIN", "S32", "IGO", "SFR", "PLS", "LYC",
        "ILU", "OZL", "NCM", "NST", "EVN", "GOR",
    ],
    "Financials": [
        "CBA", "NAB", "WBC", "ANZ", "MQG", "SUN", "IAG", "QBE", "ASX",
        "HUB", "NWL",
    ],
    "Healthcare": ["CSL", "RMD", "COH", "FPH", "PME", "PRN", "IMU", "NAN"],
    "Energy": ["WDS", "STO", "ORG", "WHC", "NHC", "BPT", "KAR"],
    "Consumer Discretionary": [
        "WES", "WOW", "COL", "JBH", "HVN", "SUL", "ALL", "TAH",
    ],
    "Consumer Staples": ["TWE", "A2M", "ING", "CGC", "GNC"],
    "Technology": [
        "WTC", "XRO", "CPU", "TNE", "ALU", "MP1", "REA", "CAR", "SEK",
    ],
    "Real Estate": ["GMG", "SGP", "GPT", "MGR", "SCG", "VCX", "CLW", "CHC"],
    "Industrials": ["BXB", "TCL", "QAN", "AZJ", "SYD", "DOW"],
    "Telecom/Utilities": ["TLS", "TPG", "AGL", "APA", "SKI"],
}

# Reverse index: ticker → sector name.
_TICKER_TO_SECTOR: dict[str, str] = {}
for _sector_name, _tickers in SECTOR_TICKERS.items():
    for _t in _tickers:
        _TICKER_TO_SECTOR[_t] = _sector_name


def get_sector_for_ticker(ticker: str) -> str | None:
    """Return the GICS sector name for *ticker*, or None if unmapped."""
    return _TICKER_TO_SECTOR.get(ticker.strip().upper())


def get_sector_peers(ticker: str, *, include_self: bool = False) -> list[str]:
    """Return the list of sector peers for *ticker*.

    By default the ticker itself is excluded from the peer list.
    """
    sector = get_sector_for_ticker(ticker)
    if sector is None:
        return []
    peers = SECTOR_TICKERS[sector]
    if include_self:
        return list(peers)
    t = ticker.strip().upper()
    return [p for p in peers if p != t]


# ---------------------------------------------------------------------------
# Sector statistics computation
# ---------------------------------------------------------------------------

_sector_stats_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_SECTOR_CACHE_TTL = 86400  # 24 hours


def _extract_ticker_metrics(
    rows: list[dict[str, Any]],
    price: float | None,
) -> dict[str, float | None]:
    """Distil raw DB rows + price into the four comparison metrics.

    Returns a dict with keys: pe_ratio, fcf_yield_pct, revenue_growth, ebit_margin.
    Any metric that cannot be computed is None.
    """
    build_metrics_summary, compute_valuation_multiples = _get_financial_metrics()
    summary = build_metrics_summary(rows, period_type="A", max_periods=5)
    periods = summary.get("periods", [])
    trends = summary.get("trends", {})

    ebit_margin: float | None = None
    if periods:
        ebit_margin = periods[-1].get("ebit_margin")

    revenue_growth: float | None = None
    if trends.get("available"):
        revenue_growth = trends.get("revenue_yoy")

    pe_ratio: float | None = None
    fcf_yield_pct: float | None = None

    if price is not None and price > 0 and rows:
        valuation = compute_valuation_multiples(price, rows[0])
        pe_ratio = valuation.get("pe_ratio")
        fcf_yield_pct = valuation.get("fcf_yield_pct")

    return {
        "pe_ratio": pe_ratio,
        "fcf_yield_pct": fcf_yield_pct,
        "revenue_growth": revenue_growth,
        "ebit_margin": ebit_margin,
    }


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a DB row (ORM object, namedtuple, or dict) to a plain dict."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "_asdict"):
        return row._asdict()
    if hasattr(row, "__dict__"):
        return {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return dict(row)


def _get_last_close(tool_router: Any, ticker: str) -> float | None:
    """Best-effort last close price via the tool router's price context."""
    try:
        ctx = tool_router.get_price_context_for_window(
            ticker=ticker, range_="1mo", interval="1d", max_history_rows=5,
        )
        ps = (ctx or {}).get("price_state", {})
        if ps.get("ok"):
            val = ps.get("last_close")
            return float(val) if val is not None else None
    except Exception:
        pass
    return None


def compute_sector_stats(
    db_reader: Any,
    sector_tickers: list[str],
    *,
    tool_router: Any | None = None,
) -> dict[str, Any]:
    """Compute median PE, FCF yield, revenue growth, EBIT margin for a sector.

    Queries financials for each ticker via *db_reader.get_financials(ticker, limit=N)*.
    Falls back gracefully when data is missing for individual tickers.

    If *tool_router* is provided, it is used to fetch last-close prices for
    valuation multiples (PE, FCF yield). Without it, only margin/growth stats
    are computed.

    Returns::

        {
            "ticker_count": 12,
            "tickers_with_data": 10,
            "pe_ratio_median": 15.8,
            "fcf_yield_pct_median": 4.1,
            "revenue_growth_median": 0.08,
            "ebit_margin_median": 0.18,
            "pe_values": [12.3, 14.1, ...],
            "fcf_yield_values": [...],
            "revenue_growth_values": [...],
            "ebit_margin_values": [...],
        }
    """
    pe_values: list[float] = []
    fcf_values: list[float] = []
    rev_growth_values: list[float] = []
    ebit_margin_values: list[float] = []
    tickers_with_data = 0

    for ticker in sector_tickers:
        try:
            raw_rows = db_reader.get_financials(ticker, limit=10)
            if not raw_rows:
                continue
            rows = [_row_to_dict(r) for r in raw_rows]
            tickers_with_data += 1

            price = _get_last_close(tool_router, ticker) if tool_router else None
            metrics = _extract_ticker_metrics(rows, price)

            if metrics["pe_ratio"] is not None and metrics["pe_ratio"] > 0:
                pe_values.append(metrics["pe_ratio"])
            if metrics["fcf_yield_pct"] is not None:
                fcf_values.append(metrics["fcf_yield_pct"])
            if metrics["revenue_growth"] is not None:
                rev_growth_values.append(metrics["revenue_growth"])
            if metrics["ebit_margin"] is not None:
                ebit_margin_values.append(metrics["ebit_margin"])

        except Exception as exc:
            logger.debug("sector_comparison: skipping %s: %s", ticker, exc)

    return {
        "ticker_count": len(sector_tickers),
        "tickers_with_data": tickers_with_data,
        "pe_ratio_median": _safe_median(pe_values),
        "fcf_yield_pct_median": _safe_median(fcf_values),
        "revenue_growth_median": _safe_median(rev_growth_values),
        "ebit_margin_median": _safe_median(ebit_margin_values),
        "pe_values": sorted(pe_values),
        "fcf_yield_values": sorted(fcf_values),
        "revenue_growth_values": sorted(rev_growth_values),
        "ebit_margin_values": sorted(ebit_margin_values),
    }


def get_sector_stats_cached(
    db_reader: Any,
    sector: str,
    *,
    tool_router: Any | None = None,
) -> dict[str, Any]:
    """Return sector stats, using a 24-hour in-memory cache.

    Avoids recomputing expensive cross-ticker aggregations on every call.
    """
    now = time.monotonic()
    cached = _sector_stats_cache.get(sector)
    if cached is not None:
        ts, stats = cached
        if now - ts < _SECTOR_CACHE_TTL:
            return stats

    tickers = SECTOR_TICKERS.get(sector)
    if tickers is None:
        return {
            "ticker_count": 0,
            "tickers_with_data": 0,
            "pe_ratio_median": None,
            "fcf_yield_pct_median": None,
            "revenue_growth_median": None,
            "ebit_margin_median": None,
            "pe_values": [],
            "fcf_yield_values": [],
            "revenue_growth_values": [],
            "ebit_margin_values": [],
        }

    stats = compute_sector_stats(db_reader, tickers, tool_router=tool_router)
    _sector_stats_cache[sector] = (now, stats)
    return stats


def invalidate_sector_cache(sector: str | None = None) -> None:
    """Clear cached sector stats. If *sector* is None, clear all."""
    if sector is None:
        _sector_stats_cache.clear()
    else:
        _sector_stats_cache.pop(sector, None)


# ---------------------------------------------------------------------------
# Ticker-vs-sector comparison
# ---------------------------------------------------------------------------

def compare_to_sector(
    ticker: str,
    ticker_metrics: dict[str, Any],
    sector_stats: dict[str, Any],
) -> dict[str, Any]:
    """Return relative positioning for each metric vs sector medians.

    *ticker_metrics* should contain keys from ``compute_valuation_multiples``
    and ``compute_period_metrics`` / ``build_metrics_summary``:
      - pe_ratio, fcf_yield_pct  (from valuation multiples)
      - revenue_growth, ebit_margin  (from period metrics / trends)

    Returns::

        {
            "sector": "Materials",
            "peers": ["RIO", "FMG", ...],
            "pe_vs_sector": {
                "value": 12.3,
                "sector_median": 15.8,
                "percentile": 35,
                "label": "cheap",
            },
            "fcf_yield_vs_sector": {...},
            "revenue_growth_vs_sector": {...},
            "ebit_margin_vs_sector": {...},
            "overall_relative_score": 65.0,
        }
    """
    t = ticker.strip().upper()
    sector = get_sector_for_ticker(t)
    peers = get_sector_peers(t)

    result: dict[str, Any] = {
        "sector": sector or "Unknown",
        "peers": peers,
    }

    sub_scores: list[float] = []

    # PE — lower is cheaper (inverted: being below median is good).
    pe_comp = _compare_metric(
        value=ticker_metrics.get("pe_ratio"),
        sector_median=sector_stats.get("pe_ratio_median"),
        sorted_values=sector_stats.get("pe_values", []),
        lower_is_better=True,
        label_fn=_pe_label,
    )
    result["pe_vs_sector"] = pe_comp
    if pe_comp.get("relative_score") is not None:
        sub_scores.append(pe_comp["relative_score"])

    # FCF yield — higher is better.
    fcf_comp = _compare_metric(
        value=ticker_metrics.get("fcf_yield_pct"),
        sector_median=sector_stats.get("fcf_yield_pct_median"),
        sorted_values=sector_stats.get("fcf_yield_values", []),
        lower_is_better=False,
        label_fn=_generic_label,
    )
    result["fcf_yield_vs_sector"] = fcf_comp
    if fcf_comp.get("relative_score") is not None:
        sub_scores.append(fcf_comp["relative_score"])

    # Revenue growth — higher is better.
    rev_comp = _compare_metric(
        value=ticker_metrics.get("revenue_growth"),
        sector_median=sector_stats.get("revenue_growth_median"),
        sorted_values=sector_stats.get("revenue_growth_values", []),
        lower_is_better=False,
        label_fn=_generic_label,
    )
    result["revenue_growth_vs_sector"] = rev_comp
    if rev_comp.get("relative_score") is not None:
        sub_scores.append(rev_comp["relative_score"])

    # EBIT margin — higher is better.
    margin_comp = _compare_metric(
        value=ticker_metrics.get("ebit_margin"),
        sector_median=sector_stats.get("ebit_margin_median"),
        sorted_values=sector_stats.get("ebit_margin_values", []),
        lower_is_better=False,
        label_fn=_generic_label,
    )
    result["ebit_margin_vs_sector"] = margin_comp
    if margin_comp.get("relative_score") is not None:
        sub_scores.append(margin_comp["relative_score"])

    # Overall relative score: average of available sub-scores (0-100, 50 = median).
    if sub_scores:
        result["overall_relative_score"] = round(sum(sub_scores) / len(sub_scores), 1)
    else:
        result["overall_relative_score"] = None

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_median(values: list[float]) -> float | None:
    """Return median of *values*, or None if empty."""
    if not values:
        return None
    return round(median(values), 4)


def _percentile_rank(value: float, sorted_values: list[float]) -> int:
    """Compute the percentile rank (0-100) of *value* within *sorted_values*.

    Uses the "percentage of values below" method. Returns 50 when the
    distribution is empty or contains only one value equal to *value*.
    """
    n = len(sorted_values)
    if n == 0:
        return 50
    count_below = sum(1 for v in sorted_values if v < value)
    count_equal = sum(1 for v in sorted_values if v == value)
    # Midpoint percentile: count_below + 0.5 * count_equal
    rank = (count_below + 0.5 * count_equal) / n * 100
    return int(round(rank))


def _compare_metric(
    *,
    value: float | None,
    sector_median: float | None,
    sorted_values: list[float],
    lower_is_better: bool,
    label_fn: Any,
) -> dict[str, Any]:
    """Build a comparison dict for a single metric."""
    if value is None:
        return {
            "value": None,
            "sector_median": sector_median,
            "percentile": None,
            "label": "no data",
            "relative_score": None,
        }

    percentile = _percentile_rank(value, sorted_values) if sorted_values else None

    # Relative score: 0-100 where 50 = at median.
    # For "lower is better" metrics (like PE), invert so that being below
    # median yields a score > 50.
    relative_score: float | None = None
    if percentile is not None:
        relative_score = float(100 - percentile) if lower_is_better else float(percentile)

    label = label_fn(value, sector_median, lower_is_better) if sector_median is not None else "no sector data"

    return {
        "value": round(value, 2) if value is not None else None,
        "sector_median": round(sector_median, 2) if sector_median is not None else None,
        "percentile": percentile,
        "label": label,
        "relative_score": relative_score,
    }


def _pe_label(value: float, sector_median: float, _lower_is_better: bool) -> str:
    """Human-readable label for PE ratio relative to sector."""
    if sector_median == 0:
        return "no sector data"
    ratio = value / sector_median
    if ratio < 0.70:
        return "very cheap"
    if ratio < 0.90:
        return "cheap"
    if ratio <= 1.10:
        return "in line"
    if ratio <= 1.30:
        return "expensive"
    return "very expensive"


def _generic_label(value: float, sector_median: float, lower_is_better: bool) -> str:
    """Human-readable label for a metric relative to sector median."""
    if sector_median == 0:
        return "no sector data"
    ratio = value / sector_median
    if lower_is_better:
        # Invert interpretation: below median is good.
        if ratio < 0.70:
            return "well below average"
        if ratio < 0.90:
            return "below average"
        if ratio <= 1.10:
            return "average"
        if ratio <= 1.30:
            return "above average"
        return "well above average"
    else:
        # Higher is better: above median is good.
        if ratio > 1.30:
            return "well above average"
        if ratio > 1.10:
            return "above average"
        if ratio >= 0.90:
            return "average"
        if ratio >= 0.70:
            return "below average"
        return "well below average"
