"""Tests for /api/context/ticker and /api/context/verification endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.core.config as config

from app.api.context import (
    _load_market_memory,
    CompanyMemoryAddRequest,
    CompanyMemoryExpireRequest,
    MarketMemoryAddRequest,
    MarketMemoryExpireRequest,
    UserThesisConfirmRequest,
    UserThesisProposalRequest,
    UserThesisRejectRequest,
    add_company_memory_note,
    add_market_memory_note,
    apply_user_thesis_proposal,
    confirm_user_thesis_proposal,
    create_user_thesis_proposal,
    expire_company_memory_note,
    expire_market_memory_note,
    get_memory_index_context,
    get_memory_context,
    get_user_thesis_context,
    reject_user_thesis_proposal,
    get_company_dump,
    get_ticker_context,
    get_verification_context,
    router as context_router,
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


def _context_client() -> TestClient:
    app = FastAPI()
    app.include_router(context_router, prefix="/api/context")
    return TestClient(app)


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
        """When cockpit_announcement_context is missing, return fallback status in errors."""
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
        assert any(
            "announcement_context" in e and "documents_pdf_excerpt" in e
            for e in result["errors"]
        )

    def test_announcement_context_missing_table_uses_document_excerpt_fallback(self):
        """Missing materialized context uses non-admin document PDF excerpts."""
        from sqlalchemy.exc import OperationalError

        db = MagicMock()
        docs = [
            {
                "document_id": "admin-doc",
                "ticker": "PPT",
                "doc_class": "quarterly",
                "doc_subtype": "other",
                "published_at": "2026-04-09",
                "title": "Appendix 3Y - G Cooper",
                "source_url": "https://example.com/admin.pdf",
                "pdf_path": "/tmp/admin.pdf",
                "pdf_sha256": "abc",
            },
            {
                "document_id": "sale-doc",
                "ticker": "PPT",
                "doc_class": "quarterly",
                "doc_subtype": "other",
                "published_at": "2026-03-16",
                "title": "Sale of Wealth Management business",
                "source_url": "https://example.com/sale.pdf",
                "pdf_path": "/tmp/sale.pdf",
                "pdf_sha256": "def",
            },
        ]

        def fake_execute(sql_text, params=None):
            sql_str = str(sql_text)
            if "cockpit_announcement_context" in sql_str:
                raise OperationalError(
                    "mock", {}, Exception("no such table: cockpit_announcement_context")
                )
            rows = docs if "FROM documents" in sql_str and "pdf_sha256" in sql_str else []
            row_mocks = []
            for row in rows:
                row_mock = MagicMock()
                row_mock._mapping = row
                row_mocks.append(row_mock)
            result_mock = MagicMock()
            result_mock.__iter__ = lambda self: iter(row_mocks)
            return result_mock

        db.execute = fake_execute
        with patch(
            "app.services.announcement_importance._extract_pdf_excerpt",
            return_value="confirmed sale excerpt",
        ):
            result = get_ticker_context(ticker="PPT", db=db)

        assert any(
            "announcement_context" in e and "documents_pdf_excerpt" in e
            for e in result["errors"]
        )
        assert result["announcement_context"] == [
            {
                "document_id": "sale-doc",
                "ticker": "PPT",
                "published_at": "2026-03-16",
                "title": "Sale of Wealth Management business",
                "pdf_path": "/tmp/sale.pdf",
                "source_url": "https://example.com/sale.pdf",
                "excerpt": "confirmed sale excerpt",
                "updated_at": None,
                "context_source": "documents_pdf_excerpt",
            }
        ]

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
            patch(
                "app.api.context._load_user_thesis_memory",
                return_value=({"entries": [], "proposals": []}, None),
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

    def test_company_dump_summary_prefers_memory_totals_over_sliced_lengths(self):
        db = _mock_db_session({})
        base_context = {
            "ticker": "BHP",
            "docs": [],
            "financials": [],
            "latest_financial_snapshot": None,
            "announcement_context": [],
            "extraction_failures": [],
            "low_confidence_financials": [],
            "errors": [],
        }
        with (
            patch("app.api.context.get_ticker_context", return_value=base_context),
            patch("app.api.context._run_query", return_value=([], None)),
            patch(
                "app.api.context._load_price_context_1y",
                return_value=({}, [], {"points": 0}, None),
            ),
            patch(
                "app.api.context._load_company_memory",
                return_value=(
                    {
                        "entries": [{"entry_id": 1}],
                        "change_log": [{"change_id": 1}],
                        "entries_total": 7,
                        "change_log_total": 9,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_market_memory",
                return_value=(
                    {
                        "items": [{"entry_id": 2}],
                        "items_total": 11,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_user_thesis_memory",
                return_value=(
                    {
                        "entries": [{"entry_id": 3}],
                        "proposals": [{"proposal_id": "thp_1"}],
                        "entries_total": 13,
                        "proposals_total": 17,
                    },
                    None,
                ),
            ),
        ):
            result = get_company_dump(ticker="BHP", db=db)

        assert result["summary"]["company_memory_entry_count"] == 7
        assert result["summary"]["company_memory_change_count"] == 9
        assert result["summary"]["market_memory_item_count"] == 11
        assert result["summary"]["user_thesis_entry_count"] == 13
        assert result["summary"]["user_thesis_proposal_count"] == 17

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
            patch(
                "app.api.context._load_user_thesis_memory",
                return_value=({"entries": [], "proposals": []}, "sqlite busy"),
            ),
        ):
            result = get_company_dump(ticker="BHP", db=db)

        assert any("docs:" in err for err in result["errors"])
        assert any("price_history_1y:" in err for err in result["errors"])
        assert any("company_memory:" in err for err in result["errors"])
        assert any("user_thesis_memory:" in err for err in result["errors"])
        assert result["summary"]["price_points_1y"] == 0


class TestGetMemoryContext:
    def test_memory_context_loads_company_and_market_memory(self):
        with (
            patch(
                "app.api.context._load_company_memory",
                return_value=(
                    {
                        "entries": [{"entry_id": 1}],
                        "change_log": [{"change_id": 2}],
                        "entries_total": 3,
                        "change_log_total": 4,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_market_memory",
                return_value=(
                    {
                        "sector": "Materials",
                        "items": [{"entry_id": 7}],
                        "items_total": 5,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_user_thesis_memory",
                return_value=(
                    {
                        "entries": [{"entry_id": 12}],
                        "proposals": [{"proposal_id": "thp_1"}],
                        "entries_total": 2,
                        "proposals_total": 3,
                    },
                    None,
                ),
            ),
        ):
            result = get_memory_context(ticker="BHP")

        assert result["ticker"] == "BHP"
        assert result["summary"]["company_memory_entry_count"] == 3
        assert result["summary"]["company_memory_change_count"] == 4
        assert result["summary"]["market_memory_item_count"] == 5
        assert result["summary"]["market_memory_sector"] == "Materials"
        assert result["summary"]["user_thesis_entry_count"] == 2
        assert result["summary"]["user_thesis_proposal_count"] == 3
        assert [level["level"] for level in result["memory_levels"]] == [
            "financial_truth",
            "company",
            "sector",
            "macro",
            "strategy",
            "session",
            "operational",
        ]
        assert result["memory_levels"][0]["status"] == "ticker_scoped"
        assert result["errors"] == []


class TestGetMemoryIndexContext:
    def test_memory_index_loads_all_persistent_memory(self):
        with (
            patch(
                "app.api.context._load_company_memory_index",
                return_value=(
                    {
                        "entries": [{"entry_id": 1, "company_id": "BHP"}],
                        "change_log": [{"change_id": 2}],
                        "entries_total": 10,
                        "change_log_total": 4,
                        "ticker_count": 3,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_market_memory_index",
                return_value=(
                    {
                        "items": [{"entry_id": 5}],
                        "items_total": 7,
                        "sector_count": 2,
                        "macro_topic_count": 4,
                    },
                    None,
                ),
            ),
            patch(
                "app.api.context._load_user_thesis_memory_index",
                return_value=(
                    {
                        "entries": [{"entry_id": 9, "ticker": "BHP"}],
                        "proposals": [{"proposal_id": "thp_1"}],
                        "entries_total": 6,
                        "proposals_total": 8,
                        "ticker_count": 2,
                    },
                    None,
                ),
            ),
        ):
            result = get_memory_index_context()

        assert result["ticker"] is None
        assert result["summary"]["company_memory_entry_count"] == 10
        assert result["summary"]["company_memory_change_count"] == 4
        assert result["summary"]["company_memory_ticker_count"] == 3
        assert result["summary"]["market_memory_item_count"] == 7
        assert result["summary"]["market_memory_sector_count"] == 2
        assert result["summary"]["market_memory_macro_topic_count"] == 4
        assert result["summary"]["user_thesis_entry_count"] == 6
        assert result["summary"]["user_thesis_proposal_count"] == 8
        assert result["summary"]["user_thesis_ticker_count"] == 2
        assert [level["level"] for level in result["memory_levels"]] == [
            "financial_truth",
            "company",
            "sector",
            "macro",
            "strategy",
            "session",
            "operational",
        ]
        assert result["memory_levels"][0]["status"] == "load_ticker"
        assert result["memory_levels"][4]["row_count"] == 14
        assert result["errors"] == []


class TestMemoryMutations:
    def test_add_company_memory_note_delegates_to_store_helper(self):
        with patch(
            "app.services.company_memory.add_manual_company_memory_entry",
            return_value={"rule": "insert", "entry": {"entry_id": 9}},
        ) as mocked:
            result = add_company_memory_note(
                CompanyMemoryAddRequest(
                    ticker="BHP",
                    type="risk",
                    statement="Operations are stabilising.",
                    note="operator note",
                    metadata={"operator": "alex"},
                    supersedes=[3],
                )
            )

        assert result["ok"] is True
        assert result["entry"]["entry_id"] == 9
        mocked.assert_called_once()
        assert mocked.call_args.kwargs["signal_type"] == "risk"
        assert mocked.call_args.kwargs["metadata"]["manual"] is True
        assert mocked.call_args.kwargs["metadata"]["manual_note"] == "operator note"
        assert mocked.call_args.kwargs["metadata"]["operator"] == "alex"
        assert mocked.call_args.kwargs["supersedes"] == [3]

    def test_expire_company_memory_note_delegates_to_store_helper(self):
        with patch(
            "app.services.company_memory.expire_company_memory_entry",
            return_value={"rule": "expire", "entry": {"entry_id": 5}},
        ) as mocked:
            result = expire_company_memory_note(
                CompanyMemoryExpireRequest(
                    ticker="BHP",
                    entry_id=5,
                    note="cleanup",
                )
            )

        assert result["ok"] is True
        mocked.assert_called_once_with("BHP", 5, reason="cleanup")

    def test_add_market_memory_note_uses_sector_mapping_for_ticker(self):
        with (
            patch(
                "app.services.analysis.sector_comparison.get_sector_for_ticker",
                return_value="Materials",
            ),
            patch(
                "app.services.market_memory.add_manual_market_memory_entry",
                return_value={"rule": "insert", "entry": {"entry_id": 11}},
            ) as mocked,
        ):
            result = add_market_memory_note(
                MarketMemoryAddRequest(
                    scope="sector",
                    type="sector_trend",
                    ticker="BHP",
                    statement="Iron ore sentiment is improving.",
                    note="market note",
                )
            )

        assert result["ok"] is True
        assert result["entry"]["entry_id"] == 11
        assert mocked.call_args.kwargs["scope"] == "sector"
        assert mocked.call_args.kwargs["sector"] == "Materials"
        assert mocked.call_args.kwargs["linked_tickers"] == ["BHP"]
        assert mocked.call_args.kwargs["metadata"]["manual_note"] == "market note"

    def test_expire_market_memory_note_delegates_to_store_helper(self):
        with patch(
            "app.services.market_memory.expire_market_memory_entry",
            return_value={"rule": "expire", "entry": {"entry_id": 6}},
        ) as mocked:
            result = expire_market_memory_note(
                MarketMemoryExpireRequest(entry_id=6, scope="macro", note="cleanup")
            )

        assert result["ok"] is True
        mocked.assert_called_once_with(scope="macro", entry_id=6, reason="cleanup")

    def test_mutation_routes_require_api_key_when_configured(self, monkeypatch):
        monkeypatch.setattr(
            config.settings,
            "local_api_key",
            "local-secret",
            raising=False,
        )
        client = _context_client()

        response = client.post(
            "/api/context/memory/company/add",
            json={
                "ticker": "BHP",
                "type": "risk",
                "statement": "Manual note",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"

    def test_company_mutation_routes_write_to_backend_store(
        self,
        monkeypatch,
        tmp_path,
    ):
        from app.services.company_memory import CompanyMemoryStore

        store_path = tmp_path / "company_memory.sqlite"
        monkeypatch.setattr(
            config.settings,
            "local_api_key",
            "local-secret",
            raising=False,
        )
        monkeypatch.setattr(
            "app.services.company_memory.DEFAULT_COMPANY_MEMORY_PATH",
            store_path,
        )
        client = _context_client()
        headers = {"X-API-Key": "local-secret"}

        add_response = client.post(
            "/api/context/memory/company/add",
            headers=headers,
            json={
                "ticker": "BHP",
                "type": "risk",
                "statement": "Costs remain elevated.",
                "note": "operator note",
            },
        )

        assert add_response.status_code == 200
        entry_id = add_response.json()["entry"]["entry_id"]

        expire_response = client.post(
            "/api/context/memory/company/expire",
            headers=headers,
            json={"ticker": "BHP", "entry_id": entry_id, "note": "resolved"},
        )

        assert expire_response.status_code == 200
        store = CompanyMemoryStore(store_path)
        entries = store.list_entries("BHP")
        assert entries[0]["status"] == "expired"

    def test_market_mutation_routes_write_to_backend_store(
        self,
        monkeypatch,
        tmp_path,
    ):
        from app.services.market_memory import MarketMemoryStore

        store_path = tmp_path / "market_memory.sqlite"
        monkeypatch.setattr(
            config.settings,
            "local_api_key",
            "local-secret",
            raising=False,
        )
        monkeypatch.setattr(
            "app.services.market_memory.DEFAULT_MARKET_MEMORY_PATH",
            store_path,
        )
        client = _context_client()
        headers = {"X-API-Key": "local-secret"}

        add_response = client.post(
            "/api/context/memory/market/add",
            headers=headers,
            json={
                "scope": "sector",
                "type": "sector_trend",
                "statement": "Iron ore supply discipline is improving.",
                "sector": "Materials",
                "linked_tickers": ["BHP"],
            },
        )

        assert add_response.status_code == 200
        entry_id = add_response.json()["entry"]["entry_id"]

        expire_response = client.post(
            "/api/context/memory/market/expire",
            headers=headers,
            json={"scope": "sector", "entry_id": entry_id, "note": "stale"},
        )

        assert expire_response.status_code == 200
        store = MarketMemoryStore(store_path)
        entries = store.list_sector_entries("Materials")
        assert entries[0]["status"] == "expired"

    def test_company_add_route_preserves_financial_guardrail(self, monkeypatch):
        monkeypatch.setattr(
            config.settings,
            "local_api_key",
            "local-secret",
            raising=False,
        )
        client = _context_client()

        response = client.post(
            "/api/context/memory/company/add",
            headers={"X-API-Key": "local-secret"},
            json={
                "ticker": "BHP",
                "type": "revenue",
                "statement": "Revenue reached AUD 55 billion.",
            },
        )

        assert response.status_code == 400
        assert "financial" in response.json()["detail"].lower()


class TestUserThesisMutations:
    def test_get_user_thesis_context(self):
        with patch(
            "app.api.context._load_user_thesis_memory",
            return_value=(
                {
                    "entries": [{"entry_id": 1}],
                    "proposals": [{"proposal_id": "thp_1"}],
                    "entries_total": 3,
                    "proposals_total": 4,
                },
                None,
            ),
        ):
            result = get_user_thesis_context(ticker="BHP")

        assert result["ticker"] == "BHP"
        assert result["summary"]["entry_count"] == 3
        assert result["summary"]["proposal_count"] == 4
        assert result["errors"] == []

    def test_create_confirm_reject_apply_delegates_to_store(self):
        with patch(
            "app.services.user_thesis_memory.UserThesisMemoryStore.create_proposal",
            return_value={"proposal_id": "thp_1", "status": "pending"},
        ) as create_mock:
            result = create_user_thesis_proposal(
                UserThesisProposalRequest(
                    ticker="BHP",
                    proposal_type="create_thesis",
                    statement="Copper growth supports rerating.",
                    signal="BUY",
                    note="manual note",
                )
            )
        assert result["ok"] is True
        assert result["proposal"]["proposal_id"] == "thp_1"
        assert create_mock.call_args.kwargs["ticker"] == "BHP"

        with patch(
            "app.services.user_thesis_memory.UserThesisMemoryStore.confirm_proposal",
            return_value={"proposal_id": "thp_1", "status": "confirmed"},
        ):
            confirm = confirm_user_thesis_proposal(
                "thp_1",
                UserThesisConfirmRequest(note="yes"),
            )
        assert confirm["ok"] is True
        assert confirm["proposal"]["status"] == "confirmed"

        with patch(
            "app.services.user_thesis_memory.UserThesisMemoryStore.reject_proposal",
            return_value={"proposal_id": "thp_2", "status": "rejected"},
        ):
            reject = reject_user_thesis_proposal(
                "thp_2",
                UserThesisRejectRequest(note="no"),
            )
        assert reject["ok"] is True
        assert reject["proposal"]["status"] == "rejected"

        with patch(
            "app.services.user_thesis_memory.UserThesisMemoryStore.apply_confirmed_proposal",
            return_value={"proposal": {"proposal_id": "thp_1"}, "entry": {"entry_id": 9}},
        ):
            apply_result = apply_user_thesis_proposal("thp_1")
        assert apply_result["ok"] is True
        assert apply_result["entry"]["entry_id"] == 9

    def test_user_thesis_routes_require_api_key_when_configured(self, monkeypatch):
        monkeypatch.setattr(
            config.settings,
            "local_api_key",
            "local-secret",
            raising=False,
        )
        client = _context_client()

        response = client.post(
            "/api/context/thesis/proposals",
            json={
                "ticker": "BHP",
                "proposal_type": "create_thesis",
                "statement": "Thesis statement",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API key"


class TestLoadMarketMemory:
    def test_load_market_memory_uses_raw_active_rows(self, tmp_path):
        store_path = tmp_path / "market_memory.sqlite"
        store_path.touch()

        fake_store = MagicMock()
        fake_store.list_sector_entries.return_value = [
            {"entry_id": 1, "statement": "Sector state"}
        ]
        fake_store.list_all_macro_entries.return_value = [
            {"entry_id": 2, "statement": "Macro state"}
        ]
        fake_store.retrieve.side_effect = AssertionError("retrieve should not be used")

        with (
            patch(
                "app.services.market_memory.DEFAULT_MARKET_MEMORY_PATH",
                store_path,
            ),
            patch(
                "app.services.market_memory.MarketMemoryStore",
                return_value=fake_store,
            ),
            patch(
                "app.services.analysis.sector_comparison.get_sector_for_ticker",
                return_value="Materials",
            ),
        ):
            payload, err = _load_market_memory("BHP", limit=10)

        assert err is None
        assert payload["status"] == "ok"
        assert payload["sector"] == "Materials"
        assert payload["sector_items"] == [{"entry_id": 1, "statement": "Sector state"}]
        assert payload["macro_items"] == [{"entry_id": 2, "statement": "Macro state"}]
        assert payload["items"] == [
            {"entry_id": 1, "statement": "Sector state"},
            {"entry_id": 2, "statement": "Macro state"},
        ]
        assert payload["sector_items_total"] == 1
        assert payload["macro_items_total"] == 1
        assert payload["items_total"] == 2


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
