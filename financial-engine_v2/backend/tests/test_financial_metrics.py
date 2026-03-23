"""
test_financial_metrics.py — regression guards for financial_metrics.py.

These are pure unit tests: no LLM, no database, no network.
They enforce correct formula semantics and catch regressions in the
computed metrics layer that feeds downstream analysis and LLM context.

Critical regression being guarded:
  ebit_margin must equal ebit / revenue, NOT (ebit - revenue) / revenue.
  The latter produces inverted margins (negative for profitable companies).
"""
import math

import pytest

from app.services.analysis.financial_metrics import (
    _ratio,
    _pct_change,
    compute_period_metrics,
    compute_trends,
    score_financial_health,
    build_metrics_summary,
)


# ---------------------------------------------------------------------------
# _ratio helper
# ---------------------------------------------------------------------------

class TestRatio:
    def test_basic_division(self):
        assert _ratio(8.4e9, 22.6e9) == pytest.approx(8.4 / 22.6)

    def test_numerator_none(self):
        assert _ratio(None, 100.0) is None

    def test_denominator_none(self):
        assert _ratio(100.0, None) is None

    def test_denominator_zero(self):
        assert _ratio(100.0, 0.0) is None

    def test_both_none(self):
        assert _ratio(None, None) is None

    def test_negative_numerator(self):
        # Net loss scenario: NPAT negative, revenue positive → negative margin
        result = _ratio(-11.7e6, 485.6e6)
        assert result < 0
        assert result == pytest.approx(-11.7 / 485.6)

    def test_zero_numerator(self):
        assert _ratio(0.0, 100.0) == 0.0


# ---------------------------------------------------------------------------
# _pct_change helper (unchanged, ensure not broken by refactor)
# ---------------------------------------------------------------------------

class TestPctChange:
    def test_growth(self):
        result = _pct_change(110.0, 100.0)
        assert result == pytest.approx(0.10)

    def test_decline(self):
        result = _pct_change(90.0, 100.0)
        assert result == pytest.approx(-0.10)

    def test_old_zero(self):
        assert _pct_change(100.0, 0.0) is None

    def test_either_none(self):
        assert _pct_change(None, 100.0) is None
        assert _pct_change(100.0, None) is None


# ---------------------------------------------------------------------------
# compute_period_metrics — margin formula correctness (critical regression guard)
# ---------------------------------------------------------------------------

class TestComputePeriodMetrics:
    """
    Margin must be metric / revenue, not (metric - revenue) / revenue.

    Regression context: a previous bug used _pct_change(ebit, revenue) which
    computes (ebit - revenue) / revenue — producing large negative margins for
    profitable companies (e.g. NAB FY2024 ebit_margin was -0.628 instead of +0.372).
    """

    # NAB FY2024 ground-truth (from audit; manually confirmed test fixture)
    NAB_FY2024 = {
        "ticker": "NAB",
        "period_end": "2024-09-30",
        "period_type": "A",
        "revenue": 22_600_000_000.0,
        "ebit": 8_400_000_000.0,
        "np_attributable": 7_500_000_000.0,
        "operating_cf": 9_300_000_000.0,
        "capex": -800_000_000.0,
        "net_debt": 10_900_000_000.0,
        "cash_end": None,
        "confidence_metrics": 0.87,
    }

    # BHP FY2021 ground-truth (confirmed from ASX preliminary final report, page 44)
    BHP_FY2021 = {
        "ticker": "BHP",
        "period_end": "2021-06-30",
        "period_type": "A",
        "revenue": 60_817_000_000.0,
        "ebit": 25_906_000_000.0,
        "np_attributable": 11_304_000_000.0,
        "operating_cf": None,
        "capex": None,
        "net_debt": None,
        "cash_end": None,
        "confidence_metrics": 0.9,
    }

    # RMS H1 FY26 ground-truth (confirmed from ASX Appendix 4D, Dec 2025)
    RMS_H1FY26 = {
        "ticker": "RMS",
        "period_end": "2025-12-31",
        "period_type": "H",
        "revenue": 485_630_000.0,
        "ebit": 31_284_000.0,
        "np_attributable": -11_716_000.0,
        "operating_cf": 171_179_000.0,
        "investing_cf": -211_390_000.0,
        "financing_cf": -84_747_000.0,
        "cash_end": 658_721_000.0,
        "capex": -25_239_000.0,
        "net_debt": None,
        "shares_outstanding": 1_924_937_480,
        "confidence_metrics": 0.85,
    }

    def test_nab_ebit_margin_is_positive(self):
        """NAB is a profitable bank — EBIT margin must be positive."""
        result = compute_period_metrics(self.NAB_FY2024)
        assert result["ebit_margin"] is not None
        assert result["ebit_margin"] > 0, (
            f"NAB EBIT margin should be positive (~37%), got {result['ebit_margin']:.4f}. "
            "Likely cause: margin computed as _pct_change(ebit, revenue) instead of ebit / revenue."
        )

    def test_nab_ebit_margin_value(self):
        """NAB FY2024 EBIT margin ≈ 37.2% (8.4B / 22.6B)."""
        result = compute_period_metrics(self.NAB_FY2024)
        expected = 8_400_000_000.0 / 22_600_000_000.0
        assert result["ebit_margin"] == pytest.approx(expected, rel=1e-4)

    def test_nab_np_margin_is_positive(self):
        """NAB NP margin must be positive."""
        result = compute_period_metrics(self.NAB_FY2024)
        assert result["np_margin"] is not None
        assert result["np_margin"] > 0

    def test_nab_np_margin_value(self):
        """NAB FY2024 NP margin ≈ 33.2% (7.5B / 22.6B)."""
        result = compute_period_metrics(self.NAB_FY2024)
        expected = 7_500_000_000.0 / 22_600_000_000.0
        assert result["np_margin"] == pytest.approx(expected, rel=1e-4)

    def test_bhp_ebit_margin_value(self):
        """BHP FY2021 EBIT margin ≈ 42.6% (25,906M / 60,817M)."""
        result = compute_period_metrics(self.BHP_FY2021)
        expected = 25_906_000_000.0 / 60_817_000_000.0
        assert result["ebit_margin"] == pytest.approx(expected, rel=1e-3)

    def test_rms_np_margin_is_negative(self):
        """RMS H1 FY26 had a net loss — NP margin must be negative."""
        result = compute_period_metrics(self.RMS_H1FY26)
        assert result["np_margin"] is not None
        assert result["np_margin"] < 0, (
            f"RMS NP margin should be negative (net loss period), got {result['np_margin']:.4f}"
        )

    def test_rms_ebit_margin_is_positive(self):
        """RMS H1 FY26 had positive EBIT (31.3M) despite net loss — margin must be positive."""
        result = compute_period_metrics(self.RMS_H1FY26)
        assert result["ebit_margin"] is not None
        assert result["ebit_margin"] > 0

    def test_margin_none_when_revenue_none(self):
        row = {**self.NAB_FY2024, "revenue": None}
        result = compute_period_metrics(row)
        assert result["ebit_margin"] is None
        assert result["np_margin"] is None
        assert result["fcf_margin"] is None

    def test_margin_none_when_revenue_zero(self):
        row = {**self.NAB_FY2024, "revenue": 0.0}
        result = compute_period_metrics(row)
        assert result["ebit_margin"] is None

    def test_fcf_computed_correctly(self):
        """FCF = operating_cf - abs(capex)."""
        result = compute_period_metrics(self.NAB_FY2024)
        expected_fcf = 9_300_000_000.0 - abs(-800_000_000.0)
        assert result["fcf"] == pytest.approx(expected_fcf)

    def test_cash_conversion_computed_correctly(self):
        """Cash conversion = operating_cf / ebit."""
        result = compute_period_metrics(self.NAB_FY2024)
        expected = 9_300_000_000.0 / 8_400_000_000.0
        assert result["cash_conversion"] == pytest.approx(expected, rel=1e-4)

    def test_period_metadata_preserved(self):
        result = compute_period_metrics(self.NAB_FY2024)
        assert result["period_end"] == "2024-09-30"
        assert result["period_type"] == "A"

    def test_all_required_keys_present(self):
        result = compute_period_metrics(self.NAB_FY2024)
        required = {
            "period_end", "period_type", "revenue", "ebit", "np_attributable",
            "operating_cf", "capex", "fcf", "net_debt", "cash_end",
            "ebit_margin", "np_margin", "fcf_margin", "cash_conversion", "confidence",
        }
        assert required.issubset(result.keys())


# ---------------------------------------------------------------------------
# score_financial_health — health score not corrupted by inverted margins
# ---------------------------------------------------------------------------

class TestScoreFinancialHealth:
    def test_healthy_company_scores_above_25(self):
        """
        NAB-like company with 37% EBIT margin and good cash conversion must score >= 50.

        With CORRECT margins (ebit/revenue ≈ 0.372): profitability=25 + cash_quality=25 = 50.
        With INVERTED margins (_pct_change bug: ≈ -0.628): profitability=0 + cash_quality=25 = 25.

        This test distinguishes the two cases. If it fails with score=25, the margin
        formula regression has been reintroduced.
        """
        periods = [compute_period_metrics(TestComputePeriodMetrics.NAB_FY2024)]
        trends = compute_trends(periods)
        score = score_financial_health(periods, trends)
        assert score >= 50.0, (
            f"Healthy company (37% EBIT margin, positive OCF) should score >= 50, got {score}. "
            "If score is ~25, likely cause: ebit_margin is inverted "
            "(computed as _pct_change(ebit, revenue) instead of ebit / revenue)."
        )

    def test_high_margin_company_scores_maximum_profitability(self):
        """Company with ≥20% EBIT margin gets full 25 pts for profitability."""
        row = {
            "revenue": 100.0,
            "ebit": 30.0,   # 30% margin
            "np_attributable": 20.0,
            "operating_cf": 35.0,
            "capex": -5.0,
            "net_debt": -10.0,  # net cash
            "cash_end": None,
            "confidence_metrics": 0.9,
            "period_end": "2024-06-30",
            "period_type": "A",
        }
        periods = [compute_period_metrics(row)]
        trends = compute_trends(periods)
        score = score_financial_health(periods, trends)
        # 25 (margin ≥20%) + 25 (cc ≥1.0: 35/30=1.17) + 25 (net cash) = 75 minimum
        assert score >= 75.0


# ---------------------------------------------------------------------------
# build_metrics_summary — integration
# ---------------------------------------------------------------------------

class TestBuildMetricsSummary:
    def test_returns_required_keys(self):
        rows = [TestComputePeriodMetrics.NAB_FY2024]
        result = build_metrics_summary(rows, period_type="A")
        assert "periods" in result
        assert "trends" in result
        assert "financial_health_score" in result
        assert "period_count" in result

    def test_period_type_filter(self):
        annual = {**TestComputePeriodMetrics.NAB_FY2024, "period_type": "A"}
        half = {**TestComputePeriodMetrics.RMS_H1FY26, "period_type": "H"}
        result = build_metrics_summary([annual, half], period_type="A")
        assert result["period_count"] == 1
        assert result["periods"][0]["period_end"] == "2024-09-30"

    def test_empty_rows_returns_zero_periods(self):
        result = build_metrics_summary([], period_type="A")
        assert result["period_count"] == 0
        assert result["financial_health_score"] == 50.0  # default when no data
