"""Tests for _build_financials_narrative string-to-float coercion.

Validates that financial values arriving as strings from the DB (e.g.,
"27902000000") are safely coerced to float before formatting — the fix
for the ValueError that blocked ALL chat for tickers with financial data.
"""

from __future__ import annotations

from cockpit.core.tools import ToolRouter


class TestBuildFinancialsNarrativeCoercion:
    """_build_financials_narrative handles string, int, float, and None values."""

    def test_string_values_produce_narrative(self) -> None:
        financials = [
            {
                "revenue": "27902000000",
                "ebit": "8500000000",
                "operating_cf": "12000000000",
                "capex": "5000000000",
                "net_debt": "3000000000",
            },
            {
                "revenue": "25000000000",
            },
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "Revenue" in result
        assert "$" in result
        # Should not raise ValueError

    def test_float_values_produce_narrative(self) -> None:
        financials = [
            {
                "revenue": 27902000000.0,
                "ebit": 8500000000.0,
            }
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "revenue" in result.lower()

    def test_int_values_produce_narrative(self) -> None:
        financials = [
            {
                "revenue": 27902000000,
                "ebit": 8500000000,
            }
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "revenue" in result.lower()

    def test_none_values_skipped_gracefully(self) -> None:
        financials = [
            {
                "revenue": None,
                "ebit": None,
                "operating_cf": None,
                "capex": None,
                "net_debt": None,
            }
        ]
        result = ToolRouter._build_financials_narrative(financials)
        # All values None → empty narrative
        assert result == ""

    def test_empty_financials_returns_empty(self) -> None:
        result = ToolRouter._build_financials_narrative([])
        assert result == ""

    def test_unparseable_string_skipped(self) -> None:
        financials = [
            {
                "revenue": "not-a-number",
                "ebit": "N/A",
            }
        ]
        result = ToolRouter._build_financials_narrative(financials)
        # Unparseable values should be skipped, not crash
        assert isinstance(result, str)

    def test_mixed_types_produce_narrative(self) -> None:
        financials = [
            {
                "revenue": "27902000000",
                "ebit": 8500000000,
                "operating_cf": 12000000000.0,
                "capex": None,
                "net_debt": "3000000000",
            },
            {
                "revenue": 25000000000,
            },
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "Revenue" in result
        assert "EBIT" in result
        # capex is None so FCF line should be absent
        assert "Free cash flow" not in result

    def test_yoy_calculation_with_string_values(self) -> None:
        financials = [
            {"revenue": "30000000000"},
            {"revenue": "25000000000"},
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "grew" in result
        assert "20.0%" in result

    def test_net_cash_position_with_negative_string(self) -> None:
        financials = [
            {"net_debt": "-5000000000"},
        ]
        result = ToolRouter._build_financials_narrative(financials)
        assert "net cash" in result
