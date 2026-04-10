"""Tests for /api/context/ticker and /api/context/verification endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.context import (
    get_company_dump,
    get_ticker_context,
    get_verification_context,
    _validate_ticker,
)


# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------


class TestValidateTicker:
    def test_valid_ticker(self):
        assert _validate_ticker("bhp") == "BHP"
        assert _validate_ticker("  cba ") == "CBA"
        assert _validate_ticker("4DS") == "4DS"

    def test_empty_ticker_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_ticker("")
        assert exc_info.value.status_code == 400

    def test_none_ticker_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_ticker(None)
        assert exc_info.value.status_code == 400

    def test_too_long_ticker_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_ticker("ABCDEFGHIJK")
        assert exc_info.value.status_code == 400

    def test_special_chars_ticker_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_ticker("BH.P")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_db_session(query_results: dict[str, list[dict[str, Any]]] | None = None):
    """Create a mock DB session that returns results based on SQL table name."""
    results = query_results or {}
    db = MagicMock()

    def fake_execute(sql_text, params=None):
        sql_str = str(sql_text)
        result_mock = MagicMock()
        # Determine which table is being queried
        rows = []
        for table_key, table_rows in results.items():
            if table_key.lower() in sql_str.lower():
                rows = table_rows
                break

        row_mocks = []
        for row in rows:
            row_mock = MagicMock()
            row_mock._mapping = row
            row_mocks.append(row_mock)
        result_mock.__iter__ = lambda self: iter(row_mocks)
        return result_mock

    db.execute = fake_execute
    return db


def _mock_db_session_with_error(failing_table: str):
    """Create a mock DB session where one specific table query raises OperationalError."""
    from sqlalchemy.exc import OperationalError

    db = MagicMock()
    call_count = {"n": 0}

    def fake_execute(sql_text, params=None):
        sql_str = str(sql_text)
        if failing_table.lower() in sql_str.lower():
            raise OperationalError("mock", {}, Exception("table locked"))

        result_mock = MagicMock()
        result_mock.__iter__ = lambda self: iter([])
        return result_mock

    db.execute = fake_execute
    return db


# ---------------------------------------------------------------------------
# GET /api/context/ticker
# ---------------------------------------------------------------------------


class TestGetTickerContext:
    def test_valid_ticker_with_data(self):
        db = _mock_db_session(
            {
                "documents": [
                    {
                        "document_id": "abc-123",
                        "ticker": "BHP",
                        "doc_class": "results",
                        "doc_subtype": None,
                        "published_at": "2026-01-15",
                        "title": "Q1 Results",
                        "source_url": "https://example.com",
                        "pdf_path": "/path/to/pdf",
                        "pdf_sha256": "abc123",
                    },
                ],
                "asx_periodic_financials": [
                    {
                        "ticker": "BHP",
                        "period_end": "2025-12-31",
                        "period_type": "annual",
                        "revenue": "50000",
                        "ebit": "20000",
                        "np_attributable": "15000",
                        "operating_cf": "25000",
                        "investing_cf": "-10000",
                        "financing_cf": "-5000",
                        "capex": "-8000",
                        "cash_end": "12000",
                        "net_debt": "3000",
                        "shares_outstanding": "5000000",
                        "confidence_metrics": 0.95,
                        "source_document_id": "doc-1",
                    },
                ],
            }
        )
        result = get_ticker_context(ticker="BHP", db=db)
        assert result["ticker"] == "BHP"
        assert len(result["docs"]) == 1
        assert result["docs"][0]["pdf_sha256"] == "abc123"
        assert result["backend_version"] == "1.0"
        assert result["errors"] == []

    def test_valid_ticker_no_data(self):
        db = _mock_db_session({})
        result = get_ticker_context(ticker="XYZ", db=db)
        assert result["ticker"] == "XYZ"
        assert result["docs"] == []
        assert result["financials"] == []
        assert result["latest_financial_snapshot"] is None
        assert result["announcement_context"] == []
        assert result["extraction_failures"] == []
        assert result["low_confidence_financials"] == []
        assert result["errors"] == []

    def test_missing_ticker_raises_400(self):
        db = _mock_db_session({})
        with pytest.raises(HTTPException) as exc_info:
            get_ticker_context(ticker="", db=db)
        assert exc_info.value.status_code == 400

    def test_one_subquery_failure_populates_errors(self):
        db = _mock_db_session_with_error("extraction_runs")
        result = get_ticker_context(ticker="BHP", db=db)
        assert result["ticker"] == "BHP"
        assert result["docs"] == []
        assert any("extraction_failures" in e for e in result["errors"])
        # Other fields should still be present (empty but no error)
        assert isinstance(result["financials"], list)

    def test_announcement_context_missing_table(self):
        """When cockpit_announcement_context table doesn't exist, return empty list, no error."""
        from sqlalchemy.exc import OperationalError

        db = MagicMock()

        def fake_execute(sql_text, params=None):
            sql_str = str(sql_text)
            if "cockpit_announcement_context" in sql_str:
                raise OperationalError(
                    "mock", {}, Exception("no such table: cockpit_announcement_context")
                )
            result_mock = MagicMock()
            result_mock.__iter__ = lambda self: iter([])
            return result_mock

        db.execute = fake_execute
        result = get_ticker_context(ticker="BHP", db=db)
        assert result["announcement_context"] == []
        # "no such table" should NOT appear in errors — it's handled gracefully
        assert not any("announcement_context" in e for e in result["errors"])

    def test_docs_limit_clamped(self):
        """Verify limit param is passed through (FastAPI Query handles clamping)."""
        db = _mock_db_session({})
        result = get_ticker_context(ticker="BHP", docs_limit=5, db=db)
        assert result["ticker"] == "BHP"

    def test_low_confidence_threshold_default_is_04(self):
        """Verify the default threshold matches DbReader's 0.4, not 0.7."""
        import inspect

        sig = inspect.signature(get_ticker_context)
        default = sig.parameters["low_confidence_threshold"].default
        assert default.default == 0.4


# ---------------------------------------------------------------------------
# GET /api/context/company_dump
# ---------------------------------------------------------------------------


class TestGetCompanyDump:
    def test_company_dump_success(self):
        db = _mock_db_session({})
        base_context = {
            "ticker": "BHP",
            "docs": [
                {
                    "document_id": "doc-1",
                    "title": "Interim",
                    "published_at": "2026-01-01",
                }
            ],
            "financials": [{"period_end": "2025-12-31", "revenue": "100.0"}],
            "latest_financial_snapshot": {"period_end": "2025-12-31"},
            "announcement_context": [{"title": "Announcement"}],
            "extraction_failures": [],
            "low_confidence_financials": [],
            "errors": [],
        }
        with (
            patch("app.api.context.get_ticker_context", return_value=base_context),
            patch(
                "app.api.context._run_query",
                return_value=(
                    [
                        {
                            "document_id": "doc-1",
                            "ticker": "BHP",
                            "published_at": "2026-01-01",
                            "title": "Interim",
                            "risk_summary": "Demand softening",
                            "risk_bullets": ["cost inflation"],
                            "guidance_summary": "Maintained guidance",
                            "material_changes": "None",
                            "confidence_narrative": 0.8,
                            "updated_at": "2026-01-02",
                        }
                    ],
                    None,
                ),
            ),
            patch(
                "app.api.context._load_price_context_1y",
                return_value=(
                    {"price": 45.2},
                    [{"timestamp": "2026-01-01T00:00:00Z", "close": 45.2}],
                    {
                        "points": 1,
                        "coverage_start": "2026-01-01",
                        "coverage_end": "2026-01-01",
                        "last_close": 45.2,
                        "first_close": 45.2,
                        "one_year_return_pct": 0.0,
                        "high_close": 45.2,
                        "low_close": 45.2,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_company_memory",
                return_value=({"entries": [{"entry_id": 1}], "change_log": []}, None),
            ),
            patch(
                "app.api.context._load_market_memory",
                return_value=({"items": [{"entry_id": 2}]}, None),
            ),
        ):
            result = get_company_dump(ticker="BHP", db=db)

        assert result["ticker"] == "BHP"
        assert result["summary"]["doc_count"] == 1
        assert result["summary"]["financial_period_count"] == 1
        assert result["summary"]["price_points_1y"] == 1
        assert result["summary"]["company_memory_entry_count"] == 1
        assert result["summary"]["market_memory_item_count"] == 1
        assert result["errors"] == []
        assert result["backend_version"] == "1.1"

    def test_company_dump_captures_partial_failures(self):
        db = _mock_db_session({})
        base_context = {
            "ticker": "BHP",
            "docs": [],
            "financials": [],
            "latest_financial_snapshot": None,
            "announcement_context": [],
            "extraction_failures": [],
            "low_confidence_financials": [],
            "errors": ["docs: table locked"],
        }
        with (
            patch("app.api.context.get_ticker_context", return_value=base_context),
            patch("app.api.context._run_query", return_value=([], None)),
            patch(
                "app.api.context._load_price_context_1y",
                return_value=({}, [], {"points": 0}, "provider unavailable"),
            ),
            patch(
                "app.api.context._load_company_memory",
                return_value=({"entries": [], "change_log": []}, "sqlite busy"),
            ),
            patch(
                "app.api.context._load_market_memory",
                return_value=({"items": []}, None),
            ),
        ):
            result = get_company_dump(ticker="BHP", db=db)

        assert any("docs:" in err for err in result["errors"])
        assert any("price_history_1y:" in err for err in result["errors"])
        assert any("company_memory:" in err for err in result["errors"])
        assert result["summary"]["price_points_1y"] == 0


# ---------------------------------------------------------------------------
# GET /api/context/verification
# ---------------------------------------------------------------------------


class TestGetVerificationContext:
    def test_with_ticker(self):
        db = _mock_db_session({})
        result = get_verification_context(ticker="BHP", db=db)
        assert result["extraction_failures"] == []
        assert result["low_confidence_financials"] == []
        assert result["errors"] == []

    def test_without_ticker(self):
        db = _mock_db_session({})
        result = get_verification_context(ticker=None, db=db)
        assert result["extraction_failures"] == []
        assert result["low_confidence_financials"] == []

    def test_threshold_param(self):
        db = _mock_db_session({})
        result = get_verification_context(
            ticker="BHP",
            low_confidence_threshold=0.8,
            db=db,
        )
        assert result["errors"] == []

    def test_default_threshold_is_04(self):
        import inspect

        sig = inspect.signature(get_verification_context)
        default = sig.parameters["low_confidence_threshold"].default
        assert default.default == 0.4
