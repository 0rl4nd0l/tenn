"""Tests for signal_engine.py (TickerScorer, ScreenRunner) and sector_comparison.py.

Covers composite scoring, sub-score computations, screening with filters,
sector mappings, and sector-relative comparisons.
"""
from __future__ import annotations

import importlib
from collections import namedtuple
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cockpit.core.research.signal_engine import (
    ScreenRunner,
    TickerScorer,
    _compute_momentum_from_returns,
    _compute_momentum_from_trends,
    _compute_technical_score,
    _compute_valuation_score,
    _passes_filters,
    _row_to_dict,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_tool_router(
    *,
    financials: list[dict[str, Any]] | None = None,
    price_ok: bool = True,
    last_close: float = 10.0,
) -> MagicMock:
    """Build a mock tool_router with backend_api_client and price context."""
    router = MagicMock()

    # backend_api_client.get_ticker_context
    ctx = {"financials": financials or []}
    router.backend_api_client.get_ticker_context.return_value = ctx

    # get_price_context_for_window
    if price_ok:
        price_state = {
            "ok": True,
            "rsi_14": 45.0,
            "sma20": 9.5,
            "sma50": 9.0,
            "trend_regime": "bull",
            "vol_20d_ann": 0.25,
            "drawdown_from_63d_high": -0.05,
            "ret_5d": 0.03,
            "ret_20d": 0.06,
            "ret_63d": 0.12,
            "last_close": last_close,
        }
    else:
        price_state = {"ok": False}
    router.get_price_context_for_window.return_value = {"price_state": price_state}
    return router


def _sample_financial_row() -> dict[str, Any]:
    """A minimal financial row that build_metrics_summary can consume."""
    return {
        "ticker": "TST",
        "period_type": "A",
        "period_end": "2025-06-30",
        "revenue": 1_000_000,
        "ebit": 200_000,
        "net_income": 150_000,
        "total_assets": 5_000_000,
        "total_liabilities": 2_000_000,
        "free_cash_flow": 180_000,
        "shares_outstanding": 100_000,
        "eps": 1.50,
    }


def _load_sector_comparison():
    """Lazily import sector_comparison to avoid __init__.py chain issues."""
    return importlib.import_module("backend.app.services.analysis.sector_comparison")


# ===================================================================
# TickerScorer.score() tests
# ===================================================================

class TestTickerScorerHappyPath:
    """TickerScorer.score() with all data present."""

    def test_score_happy_path(self):
        """Composite score is computed and all sub-scores are in [0, 100]."""
        rows = [_sample_financial_row()]
        router = _make_tool_router(financials=rows, price_ok=True, last_close=10.0)

        # Patch the lazy imports inside score()
        mock_build = MagicMock(return_value={
            "financial_health_score": 72.0,
            "period_count": 3,
            "trends": {
                "available": True,
                "revenue_yoy": 0.15,
                "ebit_yoy": 0.10,
                "fcf_yoy": 0.08,
            },
            "periods": [{"ebit_margin": 0.20}],
        })
        mock_valuation = MagicMock(return_value={
            "pe_ratio": 12.5,
            "fcf_yield_pct": 6.0,
        })

        with patch.dict(
            "sys.modules",
            {
                "backend": MagicMock(),
                "backend.app": MagicMock(),
                "backend.app.services": MagicMock(),
                "backend.app.services.analysis": MagicMock(),
            },
        ):
            with patch(
                "cockpit.core.research.signal_engine._compute_momentum_from_trends",
            ) as mock_mom_trends, patch(
                "cockpit.core.research.signal_engine._compute_momentum_from_returns",
            ) as mock_mom_ret, patch(
                "cockpit.core.research.signal_engine._compute_technical_score",
            ) as mock_tech, patch(
                "cockpit.core.research.signal_engine._compute_valuation_score",
            ) as mock_val_score:
                mock_mom_trends.return_value = 65.0
                mock_mom_ret.return_value = 60.0
                mock_tech.return_value = 70.0
                mock_val_score.return_value = 75.0

                # Patch the lazy import of build_metrics_summary and compute_valuation_multiples
                fm_module = MagicMock()
                fm_module.build_metrics_summary = mock_build
                fm_module.compute_valuation_multiples = mock_valuation

                sc_module = MagicMock()
                sc_module.get_sector_for_ticker.return_value = None  # skip sector comparison

                with patch.dict("sys.modules", {
                    "backend.app.services.analysis.financial_metrics": fm_module,
                    "backend.app.services.analysis.sector_comparison": sc_module,
                }):
                    scorer = TickerScorer(router)
                    result = scorer.score("TST")

        assert result["ok"] is True
        assert result["ticker"] == "TST"
        assert 0 <= result["composite_score"] <= 100
        assert 0 <= result["financial_health"] <= 100
        assert 0 <= result["momentum_score"] <= 100
        assert 0 <= result["valuation_score"] <= 100
        assert 0 <= result["technical_score"] <= 100
        assert result["data_quality"] == "good"
        assert result["data_gaps"] == []


class TestTickerScorerMissingData:
    """TickerScorer.score() with missing financials or price data."""

    def test_empty_ticker(self):
        """Empty ticker returns error without crashing."""
        router = _make_tool_router()
        scorer = TickerScorer(router)
        result = scorer.score("")
        assert result["ok"] is False
        assert "ticker is required" in result["error"]

    def test_whitespace_ticker(self):
        """Whitespace-only ticker returns error."""
        router = _make_tool_router()
        scorer = TickerScorer(router)
        result = scorer.score("   ")
        assert result["ok"] is False

    def test_missing_financials(self):
        """No financials marks data gap but still returns a result."""
        router = _make_tool_router(financials=[], price_ok=True)

        fm_module = MagicMock()
        fm_module.build_metrics_summary = MagicMock(return_value={})
        sc_module = MagicMock()
        sc_module.get_sector_for_ticker.return_value = None

        with patch.dict("sys.modules", {
            "backend.app.services.analysis.financial_metrics": fm_module,
            "backend.app.services.analysis.sector_comparison": sc_module,
        }):
            scorer = TickerScorer(router)
            result = scorer.score("XYZ")

        assert result["ok"] is True
        assert "no_financials" in result["data_gaps"]
        assert result["data_quality"] in ("partial", "poor")
        assert 0 <= result["composite_score"] <= 100

    def test_missing_price_data(self):
        """No price data marks data gap."""
        router = _make_tool_router(financials=[_sample_financial_row()], price_ok=False)

        fm_module = MagicMock()
        fm_module.build_metrics_summary = MagicMock(return_value={
            "financial_health_score": 60.0,
            "period_count": 1,
            "trends": {"available": False},
            "periods": [],
        })
        sc_module = MagicMock()
        sc_module.get_sector_for_ticker.return_value = None

        with patch.dict("sys.modules", {
            "backend.app.services.analysis.financial_metrics": fm_module,
            "backend.app.services.analysis.sector_comparison": sc_module,
        }):
            scorer = TickerScorer(router)
            result = scorer.score("ABC")

        assert result["ok"] is True
        assert "no_price_data" in result["data_gaps"]

    def test_ticker_normalized_to_upper(self):
        """Ticker is stripped and uppercased."""
        router = _make_tool_router(financials=[])

        fm_module = MagicMock()
        fm_module.build_metrics_summary = MagicMock(return_value={})
        sc_module = MagicMock()
        sc_module.get_sector_for_ticker.return_value = None

        with patch.dict("sys.modules", {
            "backend.app.services.analysis.financial_metrics": fm_module,
            "backend.app.services.analysis.sector_comparison": sc_module,
        }):
            scorer = TickerScorer(router)
            result = scorer.score("  bhp  ")

        assert result["ticker"] == "BHP"


class TestTickerScorerWeights:
    """TickerScorer._resolve_weights() with custom strategy service."""

    def test_default_weights(self):
        """Default weights are used when no strategy service."""
        router = _make_tool_router()
        scorer = TickerScorer(router)
        w = scorer._resolve_weights()
        assert w == {"health": 0.40, "momentum": 0.25, "valuation": 0.20, "technical": 0.15}
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_custom_weights_from_strategy(self):
        """Strategy service weights are used when available."""
        router = _make_tool_router()
        strategy = MagicMock()
        custom = {"health": 0.30, "momentum": 0.30, "valuation": 0.20, "technical": 0.20}
        strategy.get_signal_weights.return_value = custom

        scorer = TickerScorer(router, strategy_service=strategy)
        w = scorer._resolve_weights()
        assert w == custom

    def test_fallback_on_strategy_error(self):
        """Falls back to defaults if strategy raises."""
        router = _make_tool_router()
        strategy = MagicMock()
        strategy.get_signal_weights.side_effect = RuntimeError("broken")

        scorer = TickerScorer(router, strategy_service=strategy)
        w = scorer._resolve_weights()
        assert w["health"] == 0.40


# ===================================================================
# Sub-score computation functions
# ===================================================================

class TestComputeMomentumFromTrends:
    """_compute_momentum_from_trends()"""

    def test_strong_positive_growth(self):
        trends = {"revenue_yoy": 0.25, "ebit_yoy": 0.30, "fcf_yoy": 0.22}
        score = _compute_momentum_from_trends(trends)
        assert 0 <= score <= 100
        # 50 + 16*3 = 98
        assert score == 98.0

    def test_moderate_positive_growth(self):
        trends = {"revenue_yoy": 0.08, "ebit_yoy": 0.06, "fcf_yoy": 0.07}
        score = _compute_momentum_from_trends(trends)
        # 50 + 10*3 = 80
        assert score == 80.0

    def test_slight_positive_growth(self):
        trends = {"revenue_yoy": 0.02, "ebit_yoy": 0.03, "fcf_yoy": 0.01}
        score = _compute_momentum_from_trends(trends)
        # 50 + 4*3 = 62
        assert score == 62.0

    def test_negative_growth(self):
        trends = {"revenue_yoy": -0.15, "ebit_yoy": -0.20, "fcf_yoy": -0.30}
        score = _compute_momentum_from_trends(trends)
        # 50 - 12*3 = 14
        assert score == 14.0

    def test_mild_negative_growth(self):
        trends = {"revenue_yoy": -0.05, "ebit_yoy": -0.08, "fcf_yoy": -0.03}
        score = _compute_momentum_from_trends(trends)
        # 50 - 5*3 = 35
        assert score == 35.0

    def test_mixed_growth(self):
        trends = {"revenue_yoy": 0.25, "ebit_yoy": -0.15, "fcf_yoy": None}
        score = _compute_momentum_from_trends(trends)
        # 50 + 16 - 12 = 54
        assert score == 54.0

    def test_all_none(self):
        trends = {"revenue_yoy": None, "ebit_yoy": None, "fcf_yoy": None}
        score = _compute_momentum_from_trends(trends)
        # Baseline stays at 50
        assert score == 50.0

    def test_empty_trends(self):
        score = _compute_momentum_from_trends({})
        assert score == 50.0

    def test_clamped_to_100(self):
        # Even with extreme values, should not exceed 100
        trends = {"revenue_yoy": 0.25, "ebit_yoy": 0.25, "fcf_yoy": 0.25}
        score = _compute_momentum_from_trends(trends)
        assert score <= 100.0

    def test_clamped_to_0(self):
        trends = {"revenue_yoy": -0.50, "ebit_yoy": -0.50, "fcf_yoy": -0.50}
        score = _compute_momentum_from_trends(trends)
        assert score >= 0.0


class TestComputeMomentumFromReturns:
    """_compute_momentum_from_returns()"""

    def test_strong_positive_returns(self):
        ps = {"ret_5d": 0.15, "ret_20d": 0.12, "ret_63d": 0.20}
        score = _compute_momentum_from_returns(ps)
        # 50 + 10*1.0 + 10*1.5 + 10*2.0 = 95
        assert score == 95.0

    def test_strong_negative_returns(self):
        ps = {"ret_5d": -0.15, "ret_20d": -0.12, "ret_63d": -0.20}
        score = _compute_momentum_from_returns(ps)
        # 50 - 10*1.0 - 10*1.5 - 10*2.0 = 5
        assert score == 5.0

    def test_moderate_positive(self):
        ps = {"ret_5d": 0.05, "ret_20d": 0.04, "ret_63d": 0.03}
        score = _compute_momentum_from_returns(ps)
        # 50 + 5*1.0 + 5*1.5 + 5*2.0 = 72.5
        assert score == 72.5

    def test_flat_returns(self):
        ps = {"ret_5d": 0.00, "ret_20d": 0.01, "ret_63d": -0.01}
        score = _compute_momentum_from_returns(ps)
        # All within [-0.02, 0.02]: no change → 50
        assert score == 50.0

    def test_missing_keys(self):
        ps = {"ret_5d": 0.15}
        score = _compute_momentum_from_returns(ps)
        # 50 + 10*1.0 = 60
        assert score == 60.0

    def test_empty_state(self):
        score = _compute_momentum_from_returns({})
        assert score == 50.0


class TestComputeTechnicalScore:
    """_compute_technical_score()"""

    def test_bull_regime_normal_rsi(self):
        ps = {"trend_regime": "bull", "rsi_14": 50, "drawdown_from_63d_high": -0.03}
        score = _compute_technical_score(ps)
        # 50 + 20 = 70
        assert score == 70.0

    def test_bear_regime(self):
        ps = {"trend_regime": "bear", "rsi_14": 50, "drawdown_from_63d_high": -0.03}
        score = _compute_technical_score(ps)
        # 50 - 15 = 35
        assert score == 35.0

    def test_neutral_regime(self):
        ps = {"trend_regime": "neutral", "rsi_14": 50, "drawdown_from_63d_high": -0.03}
        score = _compute_technical_score(ps)
        # 50 (no change for neutral)
        assert score == 50.0

    def test_oversold_rsi(self):
        ps = {"trend_regime": "neutral", "rsi_14": 25, "drawdown_from_63d_high": 0.0}
        score = _compute_technical_score(ps)
        # 50 + 15 = 65
        assert score == 65.0

    def test_slightly_oversold_rsi(self):
        ps = {"trend_regime": "neutral", "rsi_14": 35, "drawdown_from_63d_high": 0.0}
        score = _compute_technical_score(ps)
        # 50 + 8 = 58
        assert score == 58.0

    def test_overbought_rsi(self):
        ps = {"trend_regime": "neutral", "rsi_14": 75, "drawdown_from_63d_high": 0.0}
        score = _compute_technical_score(ps)
        # 50 - 10 = 40
        assert score == 40.0

    def test_slightly_overbought_rsi(self):
        ps = {"trend_regime": "neutral", "rsi_14": 65, "drawdown_from_63d_high": 0.0}
        score = _compute_technical_score(ps)
        # 50 - 3 = 47
        assert score == 47.0

    def test_deep_drawdown(self):
        ps = {"trend_regime": "neutral", "rsi_14": 50, "drawdown_from_63d_high": -0.20}
        score = _compute_technical_score(ps)
        # 50 - 5 = 45
        assert score == 45.0

    def test_bull_oversold_combined(self):
        ps = {"trend_regime": "bull", "rsi_14": 28, "drawdown_from_63d_high": 0.0}
        score = _compute_technical_score(ps)
        # 50 + 20 + 15 = 85
        assert score == 85.0

    def test_bear_overbought_deep_dd(self):
        ps = {"trend_regime": "bear", "rsi_14": 72, "drawdown_from_63d_high": -0.25}
        score = _compute_technical_score(ps)
        # 50 - 15 - 10 - 5 = 20
        assert score == 20.0

    def test_no_rsi(self):
        ps = {"trend_regime": "bull", "rsi_14": None}
        score = _compute_technical_score(ps)
        # 50 + 20 = 70
        assert score == 70.0

    def test_empty(self):
        score = _compute_technical_score({})
        assert score == 50.0


class TestComputeValuationScore:
    """_compute_valuation_score()"""

    def test_very_cheap(self):
        v = {"pe_ratio": 8, "fcf_yield_pct": 10}
        score = _compute_valuation_score(v)
        # 50 + 25 + 25 = 100
        assert score == 100.0

    def test_cheap(self):
        v = {"pe_ratio": 12, "fcf_yield_pct": 6}
        score = _compute_valuation_score(v)
        # 50 + 15 + 15 = 80
        assert score == 80.0

    def test_moderate(self):
        v = {"pe_ratio": 20, "fcf_yield_pct": 3}
        score = _compute_valuation_score(v)
        # 50 + 5 + 5 = 60
        assert score == 60.0

    def test_expensive(self):
        v = {"pe_ratio": 35, "fcf_yield_pct": 1}
        score = _compute_valuation_score(v)
        # 50 - 8 + 0 = 42
        assert score == 42.0

    def test_very_expensive(self):
        v = {"pe_ratio": 50, "fcf_yield_pct": -5}
        score = _compute_valuation_score(v)
        # 50 - 15 - 10 = 25
        assert score == 25.0

    def test_no_pe(self):
        v = {"pe_ratio": None, "fcf_yield_pct": 6}
        score = _compute_valuation_score(v)
        # 50 + 15 = 65
        assert score == 65.0

    def test_no_fcf(self):
        v = {"pe_ratio": 12, "fcf_yield_pct": None}
        score = _compute_valuation_score(v)
        # 50 + 15 = 65
        assert score == 65.0

    def test_empty_valuation(self):
        score = _compute_valuation_score({})
        assert score == 50.0


class TestPassesFilters:
    """_passes_filters() filter logic."""

    def _scored(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "financial_health": 70,
            "composite_score": 65,
            "technicals": {"trend_regime": "bull"},
            "valuation": {"fcf_yield_pct": 5.0, "pe_ratio": 15},
        }
        base.update(overrides)
        return base

    def test_no_filters(self):
        assert _passes_filters(self._scored(), {}) is True

    def test_min_health_pass(self):
        assert _passes_filters(self._scored(financial_health=80), {"min_health_score": 70}) is True

    def test_min_health_fail(self):
        assert _passes_filters(self._scored(financial_health=50), {"min_health_score": 70}) is False

    def test_min_composite_pass(self):
        assert _passes_filters(self._scored(composite_score=80), {"min_composite_score": 60}) is True

    def test_min_composite_fail(self):
        assert _passes_filters(self._scored(composite_score=40), {"min_composite_score": 60}) is False

    def test_trend_regime_match(self):
        assert _passes_filters(self._scored(), {"trend_regime": "bull"}) is True

    def test_trend_regime_mismatch(self):
        assert _passes_filters(self._scored(), {"trend_regime": "bear"}) is False

    def test_min_fcf_yield_pass(self):
        assert _passes_filters(self._scored(), {"min_fcf_yield": 4.0}) is True

    def test_min_fcf_yield_fail(self):
        assert _passes_filters(self._scored(), {"min_fcf_yield": 6.0}) is False

    def test_min_fcf_yield_none(self):
        s = self._scored()
        s["valuation"]["fcf_yield_pct"] = None
        assert _passes_filters(s, {"min_fcf_yield": 4.0}) is False

    def test_max_pe_pass(self):
        assert _passes_filters(self._scored(), {"max_pe": 20}) is True

    def test_max_pe_fail(self):
        assert _passes_filters(self._scored(), {"max_pe": 10}) is False

    def test_max_pe_none_passes(self):
        """When PE is None, max_pe filter should pass (no data to compare)."""
        s = self._scored()
        s["valuation"]["pe_ratio"] = None
        assert _passes_filters(s, {"max_pe": 10}) is True

    def test_combined_filters(self):
        s = self._scored(financial_health=80, composite_score=75)
        filters = {"min_health_score": 70, "min_composite_score": 60, "trend_regime": "bull"}
        assert _passes_filters(s, filters) is True

    def test_combined_filters_one_fails(self):
        s = self._scored(financial_health=50, composite_score=75)
        filters = {"min_health_score": 70, "min_composite_score": 60}
        assert _passes_filters(s, filters) is False


# ===================================================================
# _row_to_dict tests
# ===================================================================

class TestRowToDict:
    """_row_to_dict() conversion for various row types."""

    def test_dict_passthrough(self):
        d = {"a": 1, "b": 2}
        assert _row_to_dict(d) == d

    def test_namedtuple(self):
        Row = namedtuple("Row", ["ticker", "revenue"])
        r = Row(ticker="BHP", revenue=1000)
        result = _row_to_dict(r)
        assert result == {"ticker": "BHP", "revenue": 1000}

    def test_object_with_dict(self):
        class FakeRow:
            def __init__(self):
                self.ticker = "CSL"
                self.revenue = 2000
                self._hidden = "skip"

        result = _row_to_dict(FakeRow())
        assert result == {"ticker": "CSL", "revenue": 2000}
        assert "_hidden" not in result

    def test_mapping_like(self):
        """Fallback: dict() on an iterable of pairs."""
        pairs = [("x", 10), ("y", 20)]
        result = _row_to_dict(pairs)
        assert result == {"x": 10, "y": 20}


# ===================================================================
# ScreenRunner tests
# ===================================================================

class TestScreenRunnerHappyPath:
    """ScreenRunner.run() with mocked scorer."""

    def _make_scorer(self, results: dict[str, dict[str, Any]]) -> MagicMock:
        scorer = MagicMock(spec=TickerScorer)

        def score_fn(ticker):
            return results.get(ticker, {"ok": False, "error": "not found"})

        scorer.score.side_effect = score_fn
        return scorer

    def test_ranked_by_composite_descending(self):
        results = {
            "AAA": {"ok": True, "ticker": "AAA", "composite_score": 80, "financial_health": 70,
                     "technicals": {}, "valuation": {}},
            "BBB": {"ok": True, "ticker": "BBB", "composite_score": 60, "financial_health": 50,
                     "technicals": {}, "valuation": {}},
            "CCC": {"ok": True, "ticker": "CCC", "composite_score": 90, "financial_health": 85,
                     "technicals": {}, "valuation": {}},
        }
        scorer = self._make_scorer(results)
        runner = ScreenRunner(scorer)
        out = runner.run(["AAA", "BBB", "CCC"])

        assert out["ok"] is True
        assert out["total_screened"] == 3
        assert out["filtered_out"] == 0
        ranked = out["ranked"]
        assert len(ranked) == 3
        assert ranked[0]["ticker"] == "CCC"
        assert ranked[1]["ticker"] == "AAA"
        assert ranked[2]["ticker"] == "BBB"

    def test_with_filters(self):
        results = {}
        for i, t in enumerate(["A", "B", "C", "D", "E"]):
            health = 40 + i * 15  # 40, 55, 70, 85, 100
            results[t] = {
                "ok": True, "ticker": t,
                "composite_score": 50 + i * 10,
                "financial_health": health,
                "technicals": {"trend_regime": "bull"},
                "valuation": {"fcf_yield_pct": 5.0, "pe_ratio": 15},
            }
        scorer = self._make_scorer(results)
        runner = ScreenRunner(scorer)
        out = runner.run(["A", "B", "C", "D", "E"], filters={"min_health_score": 60})

        assert out["ok"] is True
        assert out["total_screened"] == 5
        assert out["filtered_out"] == 2  # A (40) and B (55)
        assert len(out["ranked"]) == 3

    def test_error_ticker(self):
        results = {
            "OK1": {"ok": True, "ticker": "OK1", "composite_score": 70, "financial_health": 60,
                     "technicals": {}, "valuation": {}},
        }
        scorer = self._make_scorer(results)
        runner = ScreenRunner(scorer)
        out = runner.run(["OK1", "FAIL1"])

        assert out["ok"] is True
        assert out["total_screened"] == 1
        assert len(out["errors"]) == 1
        assert "FAIL1" in out["errors"][0]

    def test_scorer_exception(self):
        scorer = MagicMock(spec=TickerScorer)
        scorer.score.side_effect = RuntimeError("kaboom")
        runner = ScreenRunner(scorer)
        out = runner.run(["X"])
        assert out["ok"] is True
        assert out["total_screened"] == 0
        assert len(out["errors"]) == 1


class TestScreenRunnerWatchlist:
    """ScreenRunner.run() with watchlist fallback."""

    def test_uses_watchlist_when_no_tickers(self):
        scorer = MagicMock(spec=TickerScorer)
        scorer.score.return_value = {
            "ok": True, "ticker": "WL1", "composite_score": 50,
            "financial_health": 50, "technicals": {}, "valuation": {},
        }
        state_store = MagicMock()
        state_store.conn.execute.return_value.fetchall.return_value = [
            {"ticker": "WL1"},
            {"ticker": "WL2"},
        ]

        runner = ScreenRunner(scorer, state_store=state_store)
        out = runner.run(None)

        assert out["ok"] is True
        assert out["total_screened"] == 2
        assert scorer.score.call_count == 2

    def test_no_tickers_no_watchlist(self):
        scorer = MagicMock(spec=TickerScorer)
        runner = ScreenRunner(scorer, state_store=None)
        out = runner.run(None)
        assert out["ok"] is False
        assert "No tickers" in out["error"]

    def test_empty_list_no_watchlist(self):
        scorer = MagicMock(spec=TickerScorer)
        runner = ScreenRunner(scorer, state_store=None)
        out = runner.run([])
        assert out["ok"] is False

    def test_watchlist_exception_falls_through(self):
        scorer = MagicMock(spec=TickerScorer)
        state_store = MagicMock()
        state_store.conn.execute.side_effect = RuntimeError("db error")

        runner = ScreenRunner(scorer, state_store=state_store)
        out = runner.run(None)
        assert out["ok"] is False


# ===================================================================
# sector_comparison.py tests (lazy-imported)
# ===================================================================

class TestSectorMappings:
    """get_sector_for_ticker() and sector mappings."""

    def test_bhp_is_materials(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("BHP") == "Materials"

    def test_csl_is_healthcare(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("CSL") == "Healthcare"

    def test_cba_is_financials(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("CBA") == "Financials"

    def test_wds_is_energy(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("WDS") == "Energy"

    def test_unknown_ticker_returns_none(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("ZZZZZ") is None

    def test_case_insensitive(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_for_ticker("bhp") == "Materials"
        assert sc.get_sector_for_ticker("  Bhp  ") == "Materials"


class TestGetSectorPeers:
    """get_sector_peers() excluding and including self."""

    def test_excludes_self_by_default(self):
        sc = _load_sector_comparison()
        peers = sc.get_sector_peers("BHP")
        assert "BHP" not in peers
        assert "RIO" in peers

    def test_include_self(self):
        sc = _load_sector_comparison()
        peers = sc.get_sector_peers("BHP", include_self=True)
        assert "BHP" in peers

    def test_unknown_ticker_empty(self):
        sc = _load_sector_comparison()
        assert sc.get_sector_peers("ZZZZZ") == []


class TestCompareToSector:
    """compare_to_sector() with pre-built sector stats."""

    def _sector_stats(self) -> dict[str, Any]:
        return {
            "ticker_count": 10,
            "tickers_with_data": 8,
            "pe_ratio_median": 15.0,
            "fcf_yield_pct_median": 4.0,
            "revenue_growth_median": 0.08,
            "ebit_margin_median": 0.18,
            "pe_values": [8.0, 10.0, 12.0, 14.0, 15.0, 16.0, 18.0, 22.0],
            "fcf_yield_values": [1.0, 2.5, 3.5, 4.0, 4.5, 5.5, 6.0, 8.0],
            "revenue_growth_values": [-0.05, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20],
            "ebit_margin_values": [0.05, 0.10, 0.12, 0.18, 0.20, 0.22, 0.25, 0.30],
        }

    def test_cheap_pe(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": 10.0, "fcf_yield_pct": 4.0, "revenue_growth": 0.08, "ebit_margin": 0.18}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())

        pe_comp = result["pe_vs_sector"]
        assert pe_comp["value"] == 10.0
        assert pe_comp["sector_median"] == 15.0
        # 10/15 = 0.667 < 0.70 → "very cheap"
        assert pe_comp["label"] == "very cheap"
        # PE 10 is below median of 15 → low percentile.
        # For lower_is_better, relative_score = 100 - percentile → should be > 50.
        assert pe_comp["relative_score"] is not None
        assert pe_comp["relative_score"] > 50

    def test_expensive_pe(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": 22.0, "fcf_yield_pct": None, "revenue_growth": None, "ebit_margin": None}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())

        pe_comp = result["pe_vs_sector"]
        assert pe_comp["label"] in ("expensive", "very expensive")
        # High PE → high percentile → low relative_score (lower is better inverted)
        assert pe_comp["relative_score"] < 50

    def test_missing_pe(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": None, "fcf_yield_pct": 4.0, "revenue_growth": None, "ebit_margin": None}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())

        pe_comp = result["pe_vs_sector"]
        assert pe_comp["value"] is None
        assert pe_comp["label"] == "no data"
        assert pe_comp["relative_score"] is None

    def test_overall_relative_score_computed(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": 10.0, "fcf_yield_pct": 6.0, "revenue_growth": 0.15, "ebit_margin": 0.25}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())

        assert result["overall_relative_score"] is not None
        # All metrics are above-median quality → overall should be > 50
        assert result["overall_relative_score"] > 50

    def test_overall_none_when_all_missing(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": None, "fcf_yield_pct": None, "revenue_growth": None, "ebit_margin": None}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())
        assert result["overall_relative_score"] is None

    def test_sector_and_peers_populated(self):
        sc = _load_sector_comparison()
        ticker_metrics = {"pe_ratio": 10.0, "fcf_yield_pct": 4.0}
        result = sc.compare_to_sector("BHP", ticker_metrics, self._sector_stats())
        assert result["sector"] == "Materials"
        assert "RIO" in result["peers"]
        assert "BHP" not in result["peers"]

    def test_missing_sector_median(self):
        """When sector stats have None medians, labels show 'no sector data'."""
        sc = _load_sector_comparison()
        empty_stats = {
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
        ticker_metrics = {"pe_ratio": 10.0, "fcf_yield_pct": 4.0}
        result = sc.compare_to_sector("BHP", ticker_metrics, empty_stats)
        assert result["pe_vs_sector"]["label"] == "no sector data"


class TestSectorHelpers:
    """_percentile_rank, _safe_median, _pe_label, _generic_label."""

    def test_percentile_rank_middle(self):
        sc = _load_sector_comparison()
        # Value 5.0 in [1,2,3,4,5,6,7,8,9,10]
        rank = sc._percentile_rank(5.0, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert 40 <= rank <= 50

    def test_percentile_rank_lowest(self):
        sc = _load_sector_comparison()
        rank = sc._percentile_rank(1.0, [1, 2, 3, 4, 5])
        assert rank < 20

    def test_percentile_rank_highest(self):
        sc = _load_sector_comparison()
        rank = sc._percentile_rank(5.0, [1, 2, 3, 4, 5])
        assert rank > 80

    def test_percentile_rank_empty(self):
        sc = _load_sector_comparison()
        assert sc._percentile_rank(10.0, []) == 50

    def test_safe_median_normal(self):
        sc = _load_sector_comparison()
        assert sc._safe_median([1.0, 2.0, 3.0]) == 2.0

    def test_safe_median_empty(self):
        sc = _load_sector_comparison()
        assert sc._safe_median([]) is None

    def test_pe_label_cheap(self):
        sc = _load_sector_comparison()
        assert sc._pe_label(12.0, 15.0, True) == "cheap"

    def test_pe_label_very_cheap(self):
        sc = _load_sector_comparison()
        assert sc._pe_label(8.0, 15.0, True) == "very cheap"

    def test_pe_label_in_line(self):
        sc = _load_sector_comparison()
        assert sc._pe_label(15.0, 15.0, True) == "in line"

    def test_pe_label_expensive(self):
        sc = _load_sector_comparison()
        assert sc._pe_label(19.0, 15.0, True) == "expensive"

    def test_pe_label_very_expensive(self):
        sc = _load_sector_comparison()
        assert sc._pe_label(25.0, 15.0, True) == "very expensive"

    def test_generic_label_above_average(self):
        sc = _load_sector_comparison()
        # Higher is better: ratio 1.2 → above average
        assert sc._generic_label(1.2, 1.0, False) == "above average"

    def test_generic_label_below_average(self):
        sc = _load_sector_comparison()
        assert sc._generic_label(0.8, 1.0, False) == "below average"

    def test_generic_label_well_above(self):
        sc = _load_sector_comparison()
        assert sc._generic_label(1.5, 1.0, False) == "well above average"

    def test_generic_label_lower_is_better_below(self):
        sc = _load_sector_comparison()
        # Lower is better: ratio 0.8 → below average (good)
        assert sc._generic_label(0.8, 1.0, True) == "below average"


class TestSectorRowToDict:
    """_row_to_dict in sector_comparison module."""

    def test_dict_passthrough(self):
        sc = _load_sector_comparison()
        d = {"a": 1}
        assert sc._row_to_dict(d) == d

    def test_namedtuple_conversion(self):
        sc = _load_sector_comparison()
        Row = namedtuple("Row", ["x", "y"])
        assert sc._row_to_dict(Row(x=1, y=2)) == {"x": 1, "y": 2}

    def test_object_skips_private(self):
        sc = _load_sector_comparison()

        class Obj:
            def __init__(self):
                self.pub = "yes"
                self._priv = "no"

        result = sc._row_to_dict(Obj())
        assert result == {"pub": "yes"}


class TestSectorStatsCache:
    """get_sector_stats_cached and invalidate_sector_cache."""

    def test_unknown_sector_returns_empty(self):
        sc = _load_sector_comparison()
        stats = sc.get_sector_stats_cached(MagicMock(), "NonExistentSector99")
        assert stats["ticker_count"] == 0
        assert stats["pe_ratio_median"] is None

    def test_invalidate_clears_cache(self):
        sc = _load_sector_comparison()
        # Seed cache manually
        sc._sector_stats_cache["TestSector"] = (0.0, {"fake": True})
        sc.invalidate_sector_cache("TestSector")
        assert "TestSector" not in sc._sector_stats_cache

    def test_invalidate_all(self):
        sc = _load_sector_comparison()
        sc._sector_stats_cache["A"] = (0.0, {})
        sc._sector_stats_cache["B"] = (0.0, {})
        sc.invalidate_sector_cache(None)
        assert len(sc._sector_stats_cache) == 0


class TestSectorStatsBackendProjection:
    """Production sector flow consumes BackendApiClient context projections."""

    def test_compute_sector_stats_uses_projected_financials(self, monkeypatch):
        sc = _load_sector_comparison()
        backend = MagicMock()
        backend.get_ticker_context.side_effect = [
            {"financials": [{"ticker": "BHP", "period_type": "A"}]},
            {"financials": []},
        ]
        extracted = {
            "pe_ratio": None,
            "fcf_yield_pct": None,
            "revenue_growth": 0.12,
            "ebit_margin": 0.25,
        }
        extract = MagicMock(return_value=extracted)
        monkeypatch.setattr(sc, "_extract_ticker_metrics", extract)

        stats = sc.compute_sector_stats(backend, ["BHP", "RIO"])

        assert stats["tickers_with_data"] == 1
        assert stats["revenue_growth_median"] == 0.12
        assert stats["ebit_margin_median"] == 0.25
        assert backend.get_ticker_context.call_args_list == [
            (("BHP",), {"financials_limit": 10}),
            (("RIO",), {"financials_limit": 10}),
        ]
        extract.assert_called_once_with(
            [{"ticker": "BHP", "period_type": "A"}],
            None,
        )
