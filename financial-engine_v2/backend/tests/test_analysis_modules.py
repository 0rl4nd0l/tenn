"""test_analysis_modules.py — D1-only tests for all analysis modules.

No LLM calls. Covers protocol compliance, per-module behavior with
profitable/loss-making/empty/minimal contexts, math_utils, and artifacts.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.modules.artifacts import artifact_path, read_artifact, write_artifact
from app.modules.base import AnalysisModule, ArtifactSet, Completeness
from app.modules.balance_sheet import BalanceSheetModule
from app.modules.catalysts import CatalystsModule
from app.modules.math_utils import (
    classify_direction,
    count_consecutive_from_end,
    linear_slope,
    mean,
    pct_change,
    ratio,
    stdev,
)
from app.modules.moat import MoatModule
from app.modules.risk import RiskModule
from app.modules.roic import ROICModule
from app.modules.ticker_context import (
    FinancialSummary,
    PeriodMetrics,
    PriceSnapshot,
    RiskNote,
    TickerContext,
    TrendMetrics,
)
from app.modules.valuation import ValuationModule

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _period(
    year: int,
    *,
    revenue: float | None = None,
    ebit: float | None = None,
    np_attributable: float | None = None,
    operating_cf: float | None = None,
    capex: float | None = None,
    cash_end: float | None = None,
    net_debt: float | None = None,
    shares: float | None = None,
    ebit_margin: float | None = None,
    fcf: float | None = None,
    fcf_margin: float | None = None,
    cash_conversion: float | None = None,
) -> PeriodMetrics:
    return PeriodMetrics(
        period_end=date(year, 6, 30),
        period_type="A",
        revenue=revenue,
        ebit=ebit,
        np_attributable=np_attributable,
        operating_cf=operating_cf,
        capex=capex,
        cash_end=cash_end,
        net_debt=net_debt,
        shares_outstanding=shares,
        ebit_margin=ebit_margin,
        fcf=fcf,
        fcf_margin=fcf_margin,
        cash_conversion=cash_conversion,
        confidence=0.9,
    )


@pytest.fixture()
def profitable_context() -> TickerContext:
    """BHP-like: revenue 28B, ebit 9.5B, positive OCF, net debt 11B."""
    periods = (
        _period(2022, revenue=25e9, ebit=8e9, np_attributable=5.5e9,
                operating_cf=10e9, capex=-4e9, cash_end=8e9, net_debt=13e9,
                shares=5e9, ebit_margin=0.32, fcf=6e9, fcf_margin=0.24,
                cash_conversion=1.25),
        _period(2023, revenue=27e9, ebit=9e9, np_attributable=6e9,
                operating_cf=11e9, capex=-4.5e9, cash_end=9e9, net_debt=12e9,
                shares=5e9, ebit_margin=0.333, fcf=6.5e9, fcf_margin=0.241,
                cash_conversion=1.22),
        _period(2024, revenue=28e9, ebit=9.5e9, np_attributable=6.5e9,
                operating_cf=12e9, capex=-5e9, cash_end=10e9, net_debt=11e9,
                shares=5e9, ebit_margin=0.339, fcf=7e9, fcf_margin=0.25,
                cash_conversion=1.26),
    )
    trends = TrendMetrics(
        available=True, revenue_yoy=0.037, ebit_yoy=0.056,
        np_yoy=0.083, fcf_yoy=0.077, net_debt_yoy=-0.083,
    )
    return TickerContext(
        ticker="BHP",
        assembled_at=_NOW,
        financials=FinancialSummary(period_type="A", periods=periods, trends=trends),
        risk_notes=(
            RiskNote(
                document_id="doc1",
                risk_summary="Commodity price risk remains elevated",
                risk_bullets=("Iron ore oversupply", "China demand uncertainty"),
                guidance_summary="FY25 production guidance 250-260Mt",
                material_changes="New copper expansion approved",
            ),
        ),
        price=PriceSnapshot(last_close=42.50),
    )


@pytest.fixture()
def loss_making_context() -> TickerContext:
    """Cash-burning startup: negative OCF, no revenue, high cash."""
    periods = (
        _period(2023, revenue=0.0, ebit=-5e6, np_attributable=-6e6,
                operating_cf=-4e6, capex=-1e6, cash_end=20e6, net_debt=-18e6,
                shares=100e6),
        _period(2024, revenue=0.0, ebit=-7e6, np_attributable=-8e6,
                operating_cf=-6e6, capex=-1.5e6, cash_end=12e6, net_debt=-10e6,
                shares=100e6),
    )
    return TickerContext(
        ticker="STARTUP",
        assembled_at=_NOW,
        financials=FinancialSummary(period_type="A", periods=periods),
    )


@pytest.fixture()
def empty_context() -> TickerContext:
    return TickerContext(ticker="EMPTY", assembled_at=_NOW)


@pytest.fixture()
def minimal_context() -> TickerContext:
    """1 period, no price, no risk notes."""
    periods = (
        _period(2024, revenue=1e9, ebit=1e8, np_attributable=7e7,
                operating_cf=1.5e8, capex=-3e7, cash_end=2e8, net_debt=5e8,
                shares=1e9, ebit_margin=0.10),
    )
    return TickerContext(
        ticker="MIN",
        assembled_at=_NOW,
        financials=FinancialSummary(period_type="A", periods=periods),
    )


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

ALL_MODULES = [
    BalanceSheetModule(),
    ROICModule(),
    ValuationModule(),
    RiskModule(),
    CatalystsModule(),
    MoatModule(),
]


@pytest.mark.parametrize("module", ALL_MODULES, ids=lambda m: m.name)
def test_protocol_compliance(module: object) -> None:
    assert isinstance(module, AnalysisModule)


# ---------------------------------------------------------------------------
# balance_sheet
# ---------------------------------------------------------------------------


class TestBalanceSheet:
    def test_profitable_complete(self, profitable_context: TickerContext) -> None:
        result = BalanceSheetModule().run(profitable_context)
        assert result.completeness == Completeness.COMPLETE
        signals = result.structured["signals"]
        assert "leverage_risk" in signals

    def test_loss_making_signals(self, loss_making_context: TickerContext) -> None:
        result = BalanceSheetModule().run(loss_making_context)
        assert result.completeness in (Completeness.COMPLETE, Completeness.PARTIAL)
        signals = result.structured["signals"]
        # Net cash position means low leverage, but cash burn means liquidity risk
        assert signals["leverage_risk"] == "low"  # net debt is negative

    def test_empty_failed(self, empty_context: TickerContext) -> None:
        result = BalanceSheetModule().run(empty_context)
        assert result.completeness == Completeness.FAILED


# ---------------------------------------------------------------------------
# roic
# ---------------------------------------------------------------------------


class TestROIC:
    def test_with_price_complete(self, profitable_context: TickerContext) -> None:
        result = ROICModule().run(profitable_context)
        assert result.completeness == Completeness.COMPLETE
        latest = result.structured["periods"][-1]
        assert latest["ebit_on_ic"] is not None

    def test_without_price_partial(self, minimal_context: TickerContext) -> None:
        result = ROICModule().run(minimal_context)
        assert result.completeness == Completeness.PARTIAL
        latest = result.structured["periods"][-1]
        assert latest["invested_capital"] is None

    def test_empty_failed(self, empty_context: TickerContext) -> None:
        result = ROICModule().run(empty_context)
        assert result.completeness == Completeness.FAILED


# ---------------------------------------------------------------------------
# valuation
# ---------------------------------------------------------------------------


class TestValuation:
    def test_with_price_and_financials(self, profitable_context: TickerContext) -> None:
        result = ValuationModule().run(profitable_context)
        assert result.completeness in (Completeness.COMPLETE, Completeness.PARTIAL)
        multiples = result.structured["multiples"]
        assert multiples["pe_ratio"] is not None

    def test_without_price_failed(self, minimal_context: TickerContext) -> None:
        result = ValuationModule().run(minimal_context)
        assert result.completeness == Completeness.FAILED

    def test_negative_earnings_pe_none(self, loss_making_context: TickerContext) -> None:
        # Add a price to the loss-making context
        ctx = TickerContext(
            ticker=loss_making_context.ticker,
            assembled_at=loss_making_context.assembled_at,
            financials=loss_making_context.financials,
            price=PriceSnapshot(last_close=0.50),
        )
        result = ValuationModule().run(ctx)
        multiples = result.structured["multiples"]
        assert multiples["pe_ratio"] is None
        assert result.completeness == Completeness.PARTIAL


# ---------------------------------------------------------------------------
# risk
# ---------------------------------------------------------------------------


class TestRisk:
    def test_with_risk_notes(self, profitable_context: TickerContext) -> None:
        result = RiskModule().run(profitable_context)
        assert result.completeness == Completeness.COMPLETE
        assert len(result.structured["risk_items"]) > 0

    def test_high_leverage_stress(self) -> None:
        """Context with net_debt/ebit > 3x should produce high_leverage signal."""
        periods = (
            _period(2024, revenue=1e9, ebit=1e8, operating_cf=1.2e8,
                    capex=-2e7, cash_end=5e7, net_debt=5e8, shares=1e9),
        )
        ctx = TickerContext(
            ticker="LEVG", assembled_at=_NOW,
            financials=FinancialSummary(period_type="A", periods=periods),
            risk_notes=(RiskNote(document_id="d1", risk_summary="Debt concern"),),
        )
        result = RiskModule().run(ctx)
        signal_names = [s["signal"] for s in result.structured["stress_signals"]]
        assert "high_leverage" in signal_names

    def test_empty_failed(self, empty_context: TickerContext) -> None:
        result = RiskModule().run(empty_context)
        assert result.completeness == Completeness.FAILED


# ---------------------------------------------------------------------------
# catalysts
# ---------------------------------------------------------------------------


class TestCatalysts:
    def test_with_guidance(self, profitable_context: TickerContext) -> None:
        result = CatalystsModule().run(profitable_context)
        assert result.completeness == Completeness.COMPLETE
        assert len(result.structured["guidance"]) > 0

    def test_with_momentum(self, profitable_context: TickerContext) -> None:
        result = CatalystsModule().run(profitable_context)
        # Revenue growth is only ~3.7% so may not trigger, but guidance is present
        assert result.completeness == Completeness.COMPLETE

    def test_empty_failed(self, empty_context: TickerContext) -> None:
        result = CatalystsModule().run(empty_context)
        assert result.completeness == Completeness.FAILED


# ---------------------------------------------------------------------------
# moat
# ---------------------------------------------------------------------------


class TestMoat:
    def test_three_periods_margin_stability(
        self, profitable_context: TickerContext,
    ) -> None:
        result = MoatModule().run(profitable_context)
        # D1-only (no LLM) => PARTIAL (moat_classification is None)
        assert result.completeness == Completeness.PARTIAL
        d1 = result.structured["d1_signals"]
        ms = d1["margin_stability"]
        assert ms["stdev"] is not None
        assert ms["mean"] is not None

    def test_one_period_insufficient(self, minimal_context: TickerContext) -> None:
        result = MoatModule().run(minimal_context)
        assert result.completeness == Completeness.PARTIAL
        d1 = result.structured["d1_signals"]
        assert d1["revenue_persistence"]["assessment"] == "insufficient_data"

    def test_empty_failed(self, empty_context: TickerContext) -> None:
        result = MoatModule().run(empty_context)
        assert result.completeness == Completeness.FAILED


# ---------------------------------------------------------------------------
# math_utils
# ---------------------------------------------------------------------------


class TestMathUtils:
    def test_ratio_normal(self) -> None:
        assert ratio(10.0, 5.0) == 2.0

    def test_ratio_zero_denom(self) -> None:
        assert ratio(10.0, 0.0) is None

    def test_ratio_none_input(self) -> None:
        assert ratio(None, 5.0) is None
        assert ratio(10.0, None) is None

    def test_pct_change_normal(self) -> None:
        assert pct_change(110.0, 100.0) == pytest.approx(0.10)

    def test_pct_change_zero_old(self) -> None:
        assert pct_change(10.0, 0.0) is None

    def test_pct_change_none(self) -> None:
        assert pct_change(None, 100.0) is None

    def test_mean_normal(self) -> None:
        assert mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_mean_with_nones(self) -> None:
        assert mean([1.0, None, 3.0]) == pytest.approx(2.0)

    def test_mean_empty(self) -> None:
        assert mean([]) is None

    def test_stdev_normal(self) -> None:
        result = stdev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert result is not None
        assert result == pytest.approx(2.0, abs=0.01)

    def test_stdev_single_value(self) -> None:
        assert stdev([5.0]) is None

    def test_stdev_with_nones(self) -> None:
        result = stdev([2.0, None, 4.0, 6.0])
        assert result is not None

    def test_linear_slope_normal(self) -> None:
        result = linear_slope([1.0, 2.0, 3.0, 4.0])
        assert result == pytest.approx(1.0)

    def test_linear_slope_single(self) -> None:
        assert linear_slope([5.0]) is None

    def test_linear_slope_nones(self) -> None:
        result = linear_slope([1.0, None, 3.0])
        assert result is not None

    def test_classify_direction_improving(self) -> None:
        assert classify_direction([1.0, 1.5, 2.0]) == "improving"

    def test_classify_direction_stable(self) -> None:
        assert classify_direction([1.0, 1.01, 1.02]) == "stable"

    def test_classify_direction_insufficient(self) -> None:
        assert classify_direction([1.0]) == "insufficient_data"

    def test_count_consecutive_true(self) -> None:
        assert count_consecutive_from_end([True, False, True, True]) == 2

    def test_count_consecutive_false(self) -> None:
        assert count_consecutive_from_end(
            [True, True, False, False], target=False,
        ) == 2

    def test_count_consecutive_empty(self) -> None:
        assert count_consecutive_from_end([]) == 0


# ---------------------------------------------------------------------------
# artifacts
# ---------------------------------------------------------------------------


class TestArtifacts:
    def test_round_trip(self, tmp_path: object) -> None:
        root = str(tmp_path)
        art = ArtifactSet(
            ticker="TST",
            module_name="test_mod",
            completeness=Completeness.COMPLETE,
            structured={"key": "value", "num": 42},
        )
        path = write_artifact(art, reports_root=root)
        assert path.exists()

        loaded = read_artifact("TST", "test_mod", reports_root=root)
        assert loaded is not None
        assert loaded["ticker"] == "TST"
        assert loaded["key"] == "value"
        assert loaded["completeness"] == "complete"

    def test_artifact_path_structure(self) -> None:
        p = artifact_path("BHP", "balance_sheet", reports_root="/tmp/r")
        assert str(p) == "/tmp/r/analysis/BHP/balance_sheet.json"

    def test_read_missing_returns_none(self, tmp_path: object) -> None:
        result = read_artifact("MISSING", "mod", reports_root=str(tmp_path))
        assert result is None
