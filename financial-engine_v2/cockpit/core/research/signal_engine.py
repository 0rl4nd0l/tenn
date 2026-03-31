"""Signal engine — composite scoring and multi-ticker screening.

TickerScorer produces a 0-100 composite score combining financial health,
valuation, momentum, and technical indicators.  When sector data is
available, valuation is scored relative to sector medians rather than
using absolute thresholds.

ScreenRunner scans multiple tickers (or the watchlist) and returns a
ranked list — a meta-tool that bypasses the agent loop iteration limit.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Composite score weights (must sum to 1.0).
_W_HEALTH = 0.40
_W_MOMENTUM = 0.25
_W_VALUATION = 0.20
_W_TECHNICAL = 0.15


class TickerScorer:
    """Scores a single ASX ticker by combining fundamentals + technicals."""

    def __init__(
        self,
        tool_router: Any,
        *,
        state_store: Any | None = None,
        strategy_service: Any | None = None,
    ) -> None:
        self._router = tool_router
        self._state_store = state_store
        self._strategy_service = strategy_service

    def score(self, ticker: str) -> dict[str, Any]:
        """Compute a composite investment score for *ticker*.

        Returns a dict with composite_score (0-100) and sub-score breakdowns.
        Never raises — returns partial results with data_quality flags.
        """
        ticker = ticker.strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}

        health_score = 0.0
        momentum_score = 0.0
        valuation_score = 0.0
        technical_score = 0.0
        valuation_data: dict[str, Any] = {}
        technicals: dict[str, Any] = {}
        metrics_summary: dict[str, Any] = {}
        data_gaps: list[str] = []
        rows: list[Any] = []

        # --- Financial health ---
        try:
            from backend.app.services.analysis.financial_metrics import (  # type: ignore[import-untyped]
                build_metrics_summary,
            )

            if self._router.backend_api_client:
                try:
                    ctx = self._router.backend_api_client.get_ticker_context(ticker, financials_limit=10)
                    rows = ctx.get("financials", [])
                except Exception as exc:
                    logger.warning("signal_engine: backend financials failed for %s: %s", ticker, exc)
            if rows:
                metrics_summary = build_metrics_summary(
                    [_row_to_dict(r) for r in rows], period_type="A", max_periods=5,
                )
                health_score = float(metrics_summary.get("financial_health_score", 0))

                # Momentum from financial trends.
                trends = metrics_summary.get("trends", {})
                if trends.get("available"):
                    momentum_score = _compute_momentum_from_trends(trends)
            else:
                data_gaps.append("no_financials")
        except Exception as exc:
            logger.warning("signal_engine: financials failed for %s: %s", ticker, exc)
            data_gaps.append("financials_error")

        # --- Price & technicals ---
        try:
            price_ctx = self._router.get_price_context_for_window(
                ticker=ticker, range_="6mo", interval="1d", max_history_rows=130,
            )
            price_state = price_ctx.get("price_state", {}) if price_ctx else {}
            if price_state.get("ok"):
                technicals = {
                    "rsi_14": price_state.get("rsi_14"),
                    "sma20": price_state.get("sma20"),
                    "sma50": price_state.get("sma50"),
                    "trend_regime": price_state.get("trend_regime"),
                    "vol_20d_ann": price_state.get("vol_20d_ann"),
                    "drawdown_from_63d_high": price_state.get("drawdown_from_63d_high"),
                    "ret_5d": price_state.get("ret_5d"),
                    "ret_20d": price_state.get("ret_20d"),
                    "ret_63d": price_state.get("ret_63d"),
                    "last_close": price_state.get("last_close"),
                }
                technical_score = _compute_technical_score(price_state)

                # Add price-based momentum to financial momentum.
                price_momentum = _compute_momentum_from_returns(price_state)
                momentum_score = (momentum_score + price_momentum) / 2 if momentum_score > 0 else price_momentum

                # Valuation (needs price + financials).
                if rows and price_state.get("last_close"):
                    try:
                        from backend.app.services.analysis.financial_metrics import (  # type: ignore[import-untyped]
                            compute_valuation_multiples,
                        )
                        latest_row = _row_to_dict(rows[0])
                        valuation_data = compute_valuation_multiples(
                            float(price_state["last_close"]), latest_row,
                        )
                        valuation_score = _compute_valuation_score(valuation_data)
                    except Exception as exc:
                        logger.debug("signal_engine: valuation failed for %s: %s", ticker, exc)
                        data_gaps.append("valuation_error")
            else:
                data_gaps.append("no_price_data")
        except Exception as exc:
            logger.warning("signal_engine: price failed for %s: %s", ticker, exc)
            data_gaps.append("price_error")

        # --- Sector comparison ---
        sector_comparison: dict[str, Any] = {}
        try:
            from backend.app.services.analysis.sector_comparison import (  # type: ignore[import-untyped]
                compare_to_sector,
                get_sector_for_ticker,
                get_sector_stats_cached,
            )

            sector = get_sector_for_ticker(ticker)
            if sector is not None and self._router.backend_api_client:
                sector_stats = get_sector_stats_cached(
                    self._router.backend_api_client,
                    sector,
                    tool_router=self._router,
                )
                # Build the ticker_metrics dict expected by compare_to_sector.
                ticker_metrics_for_sector: dict[str, Any] = {}
                ticker_metrics_for_sector["pe_ratio"] = valuation_data.get("pe_ratio")
                ticker_metrics_for_sector["fcf_yield_pct"] = valuation_data.get("fcf_yield_pct")
                if metrics_summary.get("trends", {}).get("available"):
                    ticker_metrics_for_sector["revenue_growth"] = metrics_summary["trends"].get("revenue_yoy")
                if metrics_summary.get("periods"):
                    ticker_metrics_for_sector["ebit_margin"] = metrics_summary["periods"][-1].get("ebit_margin")

                sector_comparison = compare_to_sector(ticker, ticker_metrics_for_sector, sector_stats)

                # Adjust valuation sub-score to be sector-relative when available.
                relative_score = sector_comparison.get("overall_relative_score")
                if relative_score is not None and valuation_score > 0:
                    # Blend: 40% absolute valuation + 60% sector-relative.
                    valuation_score = 0.4 * valuation_score + 0.6 * relative_score
        except Exception as exc:
            logger.debug("signal_engine: sector comparison failed for %s: %s", ticker, exc)

        # --- Composite ---
        # Use user-configured weights if available, otherwise module defaults.
        w = self._resolve_weights()
        composite = (
            w["health"] * health_score
            + w["momentum"] * momentum_score
            + w["valuation"] * valuation_score
            + w["technical"] * technical_score
        )
        composite = round(min(100.0, max(0.0, composite)), 1)

        data_quality = "good" if not data_gaps else ("partial" if len(data_gaps) <= 2 else "poor")

        return {
            "ok": True,
            "ticker": ticker,
            "composite_score": composite,
            "financial_health": round(health_score, 1),
            "momentum_score": round(momentum_score, 1),
            "valuation_score": round(valuation_score, 1),
            "technical_score": round(technical_score, 1),
            "valuation": valuation_data,
            "technicals": technicals,
            "metrics_summary": {
                "period_count": metrics_summary.get("period_count", 0),
                "health_score": metrics_summary.get("financial_health_score", 0),
            },
            "sector_comparison": sector_comparison,
            "data_quality": data_quality,
            "data_gaps": data_gaps,
        }

    def _resolve_weights(self) -> dict[str, float]:
        """Return composite weights, preferring user-configured values."""
        if self._strategy_service is not None:
            try:
                return self._strategy_service.get_signal_weights()
            except Exception:
                pass
        return {
            "health": _W_HEALTH,
            "momentum": _W_MOMENTUM,
            "valuation": _W_VALUATION,
            "technical": _W_TECHNICAL,
        }


class ScreenRunner:
    """Screens multiple tickers and returns ranked results."""

    def __init__(self, scorer: TickerScorer, *, state_store: Any | None = None) -> None:
        self._scorer = scorer
        self._state_store = state_store

    def run(
        self,
        tickers: list[str] | None = None,
        *,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Screen and rank tickers by composite score.

        If *tickers* is empty/None, uses watchlist from StateStore.
        """
        if not tickers and self._state_store is not None:
            try:
                rows = self._state_store.conn.execute(
                    "SELECT ticker FROM watchlist ORDER BY added_at"
                ).fetchall()
                tickers = [r["ticker"] for r in rows]
            except Exception:
                pass
        if not tickers:
            return {"ok": False, "error": "No tickers to screen. Provide a list or add tickers to watchlist."}

        filters = filters or {}
        scored: list[dict[str, Any]] = []
        errors: list[str] = []

        for t in tickers:
            try:
                result = self._scorer.score(t)
                if result.get("ok"):
                    scored.append(result)
                else:
                    errors.append(f"{t}: {result.get('error', 'unknown')}")
            except Exception as exc:
                errors.append(f"{t}: {exc}")

        # Apply filters.
        filtered_out = 0
        passed: list[dict[str, Any]] = []
        for s in scored:
            if not _passes_filters(s, filters):
                filtered_out += 1
            else:
                passed.append(s)

        # Rank by composite score descending.
        passed.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

        return {
            "ok": True,
            "ranked": passed,
            "filtered_out": filtered_out,
            "total_screened": len(scored),
            "errors": errors if errors else None,
        }


# ------------------------------------------------------------------
# Sub-score computations
# ------------------------------------------------------------------

def _compute_momentum_from_trends(trends: dict[str, Any]) -> float:
    """Financial momentum from YoY growth rates. Returns 0-100."""
    score = 50.0  # neutral baseline
    for growth in (trends.get("revenue_yoy"), trends.get("ebit_yoy"), trends.get("fcf_yoy")):
        if growth is None:
            continue
        if growth > 0.20:
            score += 16
        elif growth > 0.05:
            score += 10
        elif growth > 0:
            score += 4
        elif growth > -0.10:
            score -= 5
        else:
            score -= 12
    return max(0, min(100, score))


def _compute_momentum_from_returns(price_state: dict[str, Any]) -> float:
    """Price momentum from recent returns. Returns 0-100."""
    score = 50.0
    for key, weight in [("ret_5d", 1.0), ("ret_20d", 1.5), ("ret_63d", 2.0)]:
        ret = price_state.get(key)
        if ret is None:
            continue
        if ret > 0.10:
            score += 10 * weight
        elif ret > 0.02:
            score += 5 * weight
        elif ret > -0.02:
            pass
        elif ret > -0.10:
            score -= 5 * weight
        else:
            score -= 10 * weight
    return max(0, min(100, score))


def _compute_technical_score(price_state: dict[str, Any]) -> float:
    """Technical strength from indicators. Returns 0-100."""
    score = 50.0

    regime = price_state.get("trend_regime", "")
    if regime == "bull":
        score += 20
    elif regime == "bear":
        score -= 15

    rsi = price_state.get("rsi_14")
    if rsi is not None:
        if rsi < 30:
            score += 15  # oversold — potential entry
        elif rsi < 40:
            score += 8
        elif rsi > 70:
            score -= 10  # overbought — caution
        elif rsi > 60:
            score -= 3

    dd = price_state.get("drawdown_from_63d_high")
    if dd is not None and dd < -0.15:
        score -= 5

    return max(0, min(100, score))


def _compute_valuation_score(valuation: dict[str, Any]) -> float:
    """Valuation attractiveness score. Returns 0-100."""
    score = 50.0

    pe = valuation.get("pe_ratio")
    if pe is not None:
        if pe < 10:
            score += 25
        elif pe < 15:
            score += 15
        elif pe < 25:
            score += 5
        elif pe > 40:
            score -= 15
        elif pe > 30:
            score -= 8

    fcf_yield = valuation.get("fcf_yield_pct")
    if fcf_yield is not None:
        if fcf_yield > 8:
            score += 25
        elif fcf_yield > 5:
            score += 15
        elif fcf_yield > 2:
            score += 5
        elif fcf_yield < 0:
            score -= 10

    return max(0, min(100, score))


def _passes_filters(scored: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if a scored ticker passes all filters."""
    if not filters:
        return True

    min_health = filters.get("min_health_score")
    if min_health is not None and scored.get("financial_health", 0) < min_health:
        return False

    min_composite = filters.get("min_composite_score")
    if min_composite is not None and scored.get("composite_score", 0) < min_composite:
        return False

    regime = filters.get("trend_regime")
    if regime and scored.get("technicals", {}).get("trend_regime") != regime:
        return False

    min_fcf = filters.get("min_fcf_yield")
    if min_fcf is not None:
        fcf = scored.get("valuation", {}).get("fcf_yield_pct")
        if fcf is None or fcf < min_fcf:
            return False

    max_pe = filters.get("max_pe")
    if max_pe is not None:
        pe = scored.get("valuation", {}).get("pe_ratio")
        if pe is not None and pe > max_pe:
            return False

    return True


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a DB row (could be ORM object or dict) to a plain dict."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "_asdict"):
        return row._asdict()
    if hasattr(row, "__dict__"):
        return {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
    return dict(row)
