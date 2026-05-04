"""Tests for slash command handling in ChatController."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from cockpit.core.chat import ChatController, ChatResponse, ResponseMode
from cockpit.core.types import ToolResult


class SlashCommandTestBase(unittest.TestCase):
    """Base class that sets up a ChatController in keyword mode with mocked deps."""

    def setUp(self) -> None:
        self._old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
        os.environ["COCKPIT_AGENT_MODE"] = "keyword"
        self.tool_router = MagicMock()
        self.action_registry = MagicMock()
        self.state_store = MagicMock()
        self.controller = ChatController(
            ollama_client=MagicMock(),
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            state_store=self.state_store,
        )

    def tearDown(self) -> None:
        if self._old_agent_mode is None:
            os.environ.pop("COCKPIT_AGENT_MODE", None)
        else:
            os.environ["COCKPIT_AGENT_MODE"] = self._old_agent_mode


class TestToggleCommands(SlashCommandTestBase):
    def test_web_on(self) -> None:
        resp = self.controller._handle_slash_command("/web on")
        assert resp is not None
        assert "enabled" in resp.text
        assert resp.mode == ResponseMode.FAST

    def test_web_off(self) -> None:
        resp = self.controller._handle_slash_command("/web off")
        assert resp is not None
        assert "disabled" in resp.text

    def test_web_invalid_arg(self) -> None:
        resp = self.controller._handle_slash_command("/web")
        assert resp is not None
        assert "Usage" in resp.text

    def test_rag_on(self) -> None:
        resp = self.controller._handle_slash_command("/rag on")
        assert resp is not None
        assert "enabled" in resp.text

    def test_rag_off(self) -> None:
        resp = self.controller._handle_slash_command("/rag off")
        assert resp is not None
        assert "disabled" in resp.text

    def test_dbdiag_on(self) -> None:
        resp = self.controller._handle_slash_command("/dbdiag on")
        assert resp is not None
        assert "enabled" in resp.text

    def test_dbdiag_off(self) -> None:
        resp = self.controller._handle_slash_command("/dbdiag off")
        assert resp is not None
        assert "disabled" in resp.text

    def test_sources_on(self) -> None:
        resp = self.controller._handle_slash_command("/sources on")
        assert resp is not None
        assert "enabled" in resp.text
        self.state_store.set_preference.assert_called_once_with("show_sources", "true")

    def test_sources_off(self) -> None:
        resp = self.controller._handle_slash_command("/sources off")
        assert resp is not None
        assert "disabled" in resp.text
        self.state_store.set_preference.assert_called_once_with("show_sources", "false")

    def test_sources_status(self) -> None:
        self.state_store.get_preference.return_value = "true"
        resp = self.controller._handle_slash_command("/sources")
        assert resp is not None
        assert "Sources display: ON" in resp.text

    def test_sources_invalid_arg(self) -> None:
        self.state_store.get_preference.return_value = "true"
        resp = self.controller._handle_slash_command("/sources maybe")
        assert resp is not None
        assert "Sources display: ON" in resp.text

    def test_sources_list_no_sources(self) -> None:
        self.controller._latest_sources_payloads = []
        resp = self.controller._handle_slash_command("/sources list")
        assert resp is not None
        assert "No sources available" in resp.text

    def test_sources_show_no_sources(self) -> None:
        self.controller._latest_sources_payloads = []
        resp = self.controller._handle_slash_command("/sources show 1")
        assert resp is not None
        assert "No sources available for inspection" in resp.text

    def test_sources_list_and_show(self) -> None:
        self.controller._latest_sources_payloads = [
            {
                "rag_hits": [
                    {
                        "title": "First document",
                        "score": 0.99,
                        "doc_type": "company",
                        "source_id": "s1",
                    },
                    {
                        "title": "Second source",
                        "score": 0.88,
                        "doc_type": "news",
                        "source_id": "s2",
                    },
                ]
            }
        ]
        list_resp = self.controller._handle_slash_command("/sources list")
        assert list_resp is not None
        assert "  1. First document" in list_resp.text
        assert "  2. Second source" in list_resp.text

        show_resp = self.controller._handle_slash_command("/sources show 2")
        assert show_resp is not None
        assert "Source 2: Second source" in show_resp.text
        assert "id: s2" in show_resp.text

        oob_resp = self.controller._handle_slash_command("/sources show 4")
        assert oob_resp is not None
        assert "Source index out of range. Use 1..2." in oob_resp.text


class TestInfoCommands(SlashCommandTestBase):
    def test_health_returns_status(self) -> None:
        self.controller.ollama_client.health.return_value = {"ok": True}
        self.tool_router.backend_api_client = MagicMock()
        self.tool_router.backend_api_client.health.return_value = {"ok": True}
        resp = self.controller._handle_slash_command("/health")
        assert resp is not None
        assert "Service health" in resp.text
        assert "ok" in resp.text

    def test_health_unreachable(self) -> None:
        self.controller.ollama_client.health.side_effect = ConnectionError("refused")
        self.tool_router.backend_api_client = None
        resp = self.controller._handle_slash_command("/health")
        assert resp is not None
        assert "unreachable" in resp.text

    def test_prompt_returns_system_instruction(self) -> None:
        resp = self.controller._handle_slash_command("/prompt")
        assert resp is not None
        assert "```" in resp.text
        assert "Tenn" in resp.text

    def test_access_shows_status(self) -> None:
        self.tool_router.web_default_enabled = True
        self.tool_router.qual_context_enabled = False
        self.tool_router.db_diagnostics_enabled = False
        self.tool_router.backend_api_client = MagicMock()
        self.tool_router.brave_search_client = None
        resp = self.controller._handle_slash_command("/access")
        assert resp is not None
        assert "web: on" in resp.text
        assert "rag: off" in resp.text
        assert "backend_api: connected" in resp.text

    def test_filestats_usage_when_missing_ticker(self) -> None:
        resp = self.controller._handle_slash_command("/filestats")
        assert resp is not None
        assert "Usage: /filestats <TICKER>" in resp.text

    def test_filestats_fetches_company_dump(self) -> None:
        backend = MagicMock()
        backend.get_company_dump.return_value = {
            "ticker": "BHP",
            "summary": {
                "doc_count": 1,
                "financial_period_count": 1,
                "announcement_context_count": 0,
                "risk_note_count": 0,
                "extraction_failure_count": 0,
                "low_confidence_financial_count": 0,
                "company_memory_entry_count": 0,
                "market_memory_item_count": 0,
                "price_points_1y": 1,
                "last_close": 10.5,
                "one_year_return_pct": 1.2,
            },
            "docs": [
                {
                    "document_id": "doc-1",
                    "published_at": "2026-04-01",
                    "doc_class": "results",
                    "title": "BHP Results",
                    "pdf_path": "/tmp/doc.pdf",
                }
            ],
            "financials": [
                {
                    "period_end": "2025-12-31",
                    "period_type": "FY",
                    "revenue": 100,
                    "ebit": 50,
                    "np_attributable": 40,
                    "operating_cf": 30,
                    "capex": -10,
                    "cash_end": 20,
                    "net_debt": 5,
                    "confidence_metrics": 0.9,
                    "source_document_id": "doc-1",
                }
            ],
            "announcement_context": [],
            "risk_notes": [],
            "price_history_1y": [
                {
                    "timestamp": "2026-04-01T00:00:00Z",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "volume": 1000,
                }
            ],
            "price": {"price": 10.5},
            "price_summary_1y": {
                "points": 1,
                "coverage_start": "2026-04-01",
                "coverage_end": "2026-04-01",
                "last_close": 10.5,
                "high_close": 10.5,
                "low_close": 10.5,
                "one_year_return_pct": 1.2,
            },
            "extraction_failures": [],
            "low_confidence_financials": [],
            "company_memory": {"entries": [], "change_log": []},
            "market_memory": {"items": []},
            "errors": [],
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/filestats bhp")

        assert resp is not None
        assert resp.mode == ResponseMode.FAST
        assert "Dashboard:" in resp.text
        assert "Company Data Dump: BHP" in resp.text
        assert "Financial Metrics" in resp.text
        backend.get_company_dump.assert_called_once_with(ticker="BHP")
        assert resp.evidence
        assert resp.evidence[0]["details"]["dashboard_path"]

    def test_filestats_raw_mode_hint_and_evidence_mode(self) -> None:
        backend = MagicMock()
        backend.get_company_dump.return_value = {
            "ticker": "BHP",
            "summary": {},
            "docs": [],
            "financials": [],
            "announcement_context": [],
            "risk_notes": [],
            "price_history_1y": [],
            "price": {},
            "price_summary_1y": {},
            "extraction_failures": [],
            "low_confidence_financials": [],
            "company_memory": {"entries": [], "change_log": []},
            "market_memory": {"items": []},
            "errors": [],
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/filestats raw bhp")

        assert resp is not None
        assert "Dashboard:" in resp.text
        assert "View: raw (full rows)." in resp.text
        assert resp.evidence
        assert resp.evidence[0]["details"]["view_mode"] == "raw"


class TestMemoryCommands(SlashCommandTestBase):
    def test_memory_usage_when_missing_args(self) -> None:
        resp = self.controller._handle_slash_command("/memory")
        assert resp is not None
        assert "Usage: /memory show <TICKER>" in resp.text

    def test_memory_show_fetches_memory_dump(self) -> None:
        backend = MagicMock()
        backend.get_memory_dump.return_value = {
            "ticker": "BHP",
            "company_memory": {
                "entries": [
                    {
                        "entry_id": 1,
                        "status": "active",
                        "type": "risk",
                        "statement": "Customer concentration remains elevated.",
                        "confidence": 0.8,
                        "materiality": 0.7,
                        "source": "manual",
                        "last_seen_at": "2026-04-18T00:00:00+00:00",
                    }
                ],
                "change_log": [],
                "entries_total": 1,
                "change_log_total": 0,
            },
            "market_memory": {
                "sector": "Materials",
                "items": [],
                "items_total": 0,
            },
            "errors": [],
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/memory show bhp")

        assert resp is not None
        assert resp.mode == ResponseMode.FAST
        assert "Memory View: BHP" in resp.text
        assert "Backend Company Memory" in resp.text
        backend.get_memory_dump.assert_called_once_with(ticker="BHP")
        assert resp.evidence[0]["type"] == "memory_dump"

    def test_memory_raw_mode_hint(self) -> None:
        backend = MagicMock()
        backend.get_memory_dump.return_value = {
            "ticker": "BHP",
            "company_memory": {"entries": [], "change_log": []},
            "market_memory": {"items": [], "sector": "Materials"},
            "errors": [],
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/memory raw bhp")

        assert resp is not None
        assert "View: raw (full rows)." in resp.text
        assert resp.evidence[0]["details"]["view_mode"] == "raw"

    def test_memory_add_company(self) -> None:
        backend = MagicMock()
        backend.add_company_memory_note.return_value = {
            "entry": {"entry_id": 7, "statement": "Manual note"}
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command(
            "/memory add company bhp Manual note"
        )

        assert resp is not None
        assert "Added company memory for BHP. Entry ID: 7." in resp.text
        backend.add_company_memory_note.assert_called_once_with("BHP", "Manual note")

    def test_memory_add_market(self) -> None:
        backend = MagicMock()
        backend.add_market_memory_note.return_value = {
            "entry": {"entry_id": 9, "statement": "Iron ore market tightening"}
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command(
            "/memory add market bhp Iron ore market tightening"
        )

        assert resp is not None
        assert "Added market memory for BHP. Entry ID: 9." in resp.text
        backend.add_market_memory_note.assert_called_once_with(
            "BHP", "Iron ore market tightening"
        )

    def test_memory_remove_company(self) -> None:
        backend = MagicMock()
        backend.expire_company_memory_entry.return_value = {"ok": True}
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/memory remove company bhp 11")

        assert resp is not None
        assert "Expired company memory entry 11 for BHP." in resp.text
        backend.expire_company_memory_entry.assert_called_once_with("BHP", 11)

    def test_memory_remove_market(self) -> None:
        backend = MagicMock()
        backend.expire_market_memory_entry.return_value = {"ok": True}
        self.tool_router.backend_api_client = backend

        resp = self.controller._handle_slash_command("/memory remove market macro 5")

        assert resp is not None
        assert "Expired market memory entry 5 (macro)." in resp.text
        backend.expire_market_memory_entry.assert_called_once_with(5, scope="macro")


class TestWatchlistCommands(SlashCommandTestBase):
    def test_watch_list_empty(self) -> None:
        self.state_store.list_watch_tickers.return_value = []
        resp = self.controller._handle_slash_command("/watch list")
        assert resp is not None
        assert "empty" in resp.text

    def test_watch_list_with_items(self) -> None:
        self.state_store.list_watch_tickers.return_value = [
            {"ticker": "CSL", "added_at": "2026-01-01T00:00:00Z"},
            {"ticker": "BHP", "added_at": "2026-01-02T00:00:00Z"},
        ]
        resp = self.controller._handle_slash_command("/watch list")
        assert resp is not None
        assert "CSL" in resp.text
        assert "BHP" in resp.text
        assert "(2)" in resp.text

    def test_watch_add(self) -> None:
        self.state_store.add_watch_ticker.return_value = True
        resp = self.controller._handle_slash_command("/watch add CSL")
        assert resp is not None
        assert "Added CSL" in resp.text

    def test_watch_add_duplicate(self) -> None:
        self.state_store.add_watch_ticker.return_value = False
        resp = self.controller._handle_slash_command("/watch add CSL")
        assert resp is not None
        assert "already on watchlist" in resp.text

    def test_watch_add_no_ticker(self) -> None:
        resp = self.controller._handle_slash_command("/watch add")
        assert resp is not None
        assert "Usage" in resp.text

    def test_watch_remove(self) -> None:
        self.state_store.remove_watch_ticker.return_value = True
        resp = self.controller._handle_slash_command("/watch remove BHP")
        assert resp is not None
        assert "Removed BHP" in resp.text

    def test_watch_remove_not_found(self) -> None:
        self.state_store.remove_watch_ticker.return_value = False
        resp = self.controller._handle_slash_command("/watch remove XYZ")
        assert resp is not None
        assert "not found" in resp.text

    def test_watch_clear(self) -> None:
        self.state_store.clear_watch_tickers.return_value = 3
        resp = self.controller._handle_slash_command("/watch clear")
        assert resp is not None
        assert "cleared" in resp.text
        assert "3" in resp.text

    def test_watch_invalid_subcommand(self) -> None:
        resp = self.controller._handle_slash_command("/watch foo")
        assert resp is not None
        assert "Usage" in resp.text

    def test_watch_no_state_store(self) -> None:
        self.controller._state_store = None
        resp = self.controller._handle_slash_command("/watch list")
        assert resp is not None
        assert "not available" in resp.text


class TestStrategyCommands(SlashCommandTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.strategy = MagicMock()
        self.controller._strategy_service = self.strategy

    def test_strategy_list_global(self) -> None:
        self.strategy.get_global.return_value = [
            {"id": 1, "criterion": "PE < 15", "priority": 3},
        ]
        resp = self.controller._handle_slash_command("/strategy list")
        assert resp is not None
        assert "PE < 15" in resp.text

    def test_strategy_list_ticker(self) -> None:
        self.strategy.get_global.return_value = []
        self.strategy.get_ticker.return_value = [
            {"id": 2, "criterion": "Revenue growing", "priority": 5, "decision": "buy"},
        ]
        resp = self.controller._handle_slash_command("/strategy list CSL")
        assert resp is not None
        assert "Revenue growing" in resp.text
        assert "buy" in resp.text

    def test_strategy_add_global(self) -> None:
        self.strategy.add_global.return_value = {
            "id": 10,
            "criterion": "dividend yield above 4%",
        }
        resp = self.controller._handle_slash_command(
            "/strategy add dividend yield above 4%"
        )
        assert resp is not None
        assert "global criterion" in resp.text.lower()

    def test_strategy_add_ticker(self) -> None:
        self.strategy.add_ticker.return_value = {
            "id": 11,
            "criterion": "Revenue growing",
        }
        resp = self.controller._handle_slash_command(
            "/strategy add CSL Revenue growing"
        )
        assert resp is not None
        assert "CSL" in resp.text

    def test_strategy_decide(self) -> None:
        self.strategy.record_decision.return_value = {"id": 12}
        resp = self.controller._handle_slash_command("/strategy decide CSL buy")
        assert resp is not None
        assert "buy" in resp.text

    def test_strategy_decide_invalid(self) -> None:
        resp = self.controller._handle_slash_command("/strategy decide CSL maybe")
        assert resp is not None
        assert "Invalid" in resp.text

    def test_strategy_delete(self) -> None:
        self.strategy.delete.return_value = True
        resp = self.controller._handle_slash_command("/strategy delete 5")
        assert resp is not None
        assert "Deleted" in resp.text

    def test_strategy_delete_not_found(self) -> None:
        self.strategy.delete.return_value = False
        resp = self.controller._handle_slash_command("/strategy delete 999")
        assert resp is not None
        assert "not found" in resp.text

    def test_strategy_not_available(self) -> None:
        self.controller._strategy_service = None
        resp = self.controller._handle_slash_command("/strategy list")
        assert resp is not None
        assert "not available" in resp.text


class TestActionCommands(SlashCommandTestBase):
    def test_run_with_preview(self) -> None:
        self.action_registry.preview.return_value = MagicMock(
            command=["python", "scripts/backfill.py", "--ticker=CSL"],
            estimated_impact="writes DB",
            timeout_seconds=300,
        )
        resp = self.controller._handle_slash_command(
            "/run single_ticker_announcement_backfill ticker=CSL"
        )
        assert resp is not None
        assert "Action ready" in resp.text
        assert resp.action_preview is not None
        assert resp.mode == ResponseMode.ACTION

    def test_run_no_action_id(self) -> None:
        resp = self.controller._handle_slash_command("/run")
        assert resp is not None
        assert "Usage" in resp.text

    def test_confirm_no_pending(self) -> None:
        resp = self.controller._handle_slash_command("/confirm")
        assert resp is not None
        assert "No pending" in resp.text

    def test_cancel(self) -> None:
        resp = self.controller._handle_slash_command("/cancel")
        assert resp is not None
        assert "Cancelled" in resp.text


class TestFileCommands(SlashCommandTestBase):
    def test_read_existing_file(self) -> None:
        resp = self.controller._handle_slash_command("/read /etc/hostname")
        assert resp is not None
        assert "```" in resp.text

    def test_read_nonexistent(self) -> None:
        resp = self.controller._handle_slash_command("/read /nonexistent/path/file.txt")
        assert resp is not None
        assert "not found" in resp.text.lower()

    def test_read_no_path(self) -> None:
        resp = self.controller._handle_slash_command("/read")
        assert resp is not None
        assert "Usage" in resp.text


class TestPreferenceCommands(SlashCommandTestBase):
    def test_prefer_set(self) -> None:
        resp = self.controller._handle_slash_command("/prefer theme=dark")
        assert resp is not None
        assert "theme=dark" in resp.text
        self.state_store.set_preference.assert_called_once_with("theme", "dark")

    def test_prefer_no_equals(self) -> None:
        resp = self.controller._handle_slash_command("/prefer invalid")
        assert resp is not None
        assert "Usage" in resp.text


class TestReconnectCommand(SlashCommandTestBase):
    def test_reconnect_probes_clients(self) -> None:
        self.controller.ollama_client.health.return_value = {"ok": True}
        self.tool_router.backend_api_client = MagicMock()
        self.tool_router.backend_api_client.health.return_value = {"ok": True}
        resp = self.controller._handle_slash_command("/reconnect")
        assert resp is not None
        assert "Reconnection" in resp.text
        assert "ok" in resp.text


class TestUnrecognisedCommand(SlashCommandTestBase):
    def test_unknown_command_returns_none(self) -> None:
        resp = self.controller._handle_slash_command("/unknown_command")
        assert resp is None


class TestBuildChatResponseSlashDispatch(SlashCommandTestBase):
    """Verify that build_chat_response dispatches slash commands before the LLM."""

    def test_slash_command_short_circuits_llm(self) -> None:
        """A recognised slash command should return without hitting the LLM."""
        self.state_store.list_watch_tickers.return_value = []
        resp = self.controller.build_chat_response("/watch list")
        assert resp is not None
        assert "empty" in resp.text
        # The ollama_client should NOT have been called (no LLM invocation).
        self.controller.ollama_client.chat.assert_not_called()

    def test_natural_language_holdings_short_circuits_llm(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": None,
                "thesis_bucket": None,
                "status": "active",
                "quantity": 100.0,
                "avg_cost": 45.5,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-21T00:00:00",
                "note": None,
            }
        ]
        resp = self.controller.build_chat_response("what stocks am i holding")
        assert resp is not None
        assert "Portfolio overview (1 holdings)" in resp.text
        assert "Live pricing coverage" in resp.text
        self.controller.ollama_client.chat.assert_not_called()

    def test_holdings_price_update_short_circuits_to_holdings(self) -> None:
        backend = MagicMock()
        backend.list_cockpit_holdings.return_value = {
            "items": [
                {
                    "holding_id": "h1",
                    "ticker": "BHP",
                    "account_label": None,
                    "quantity": 100.0,
                    "avg_cost": None,
                    "cost_currency": None,
                    "current_price": 50.0,
                    "price_currency": "AUD",
                    "market_value": 5000.0,
                    "unrealized_pnl": None,
                    "price_as_of": "2026-05-01T06:00:00Z",
                    "valuation_warning": None,
                }
            ]
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller.build_chat_response("holdings price update?")

        assert resp is not None
        assert "Portfolio overview (1 holdings)" in resp.text
        assert "Live pricing coverage: 1/1 positions." in resp.text
        assert "AUD 50.00" in resp.text
        backend.list_cockpit_holdings.assert_called_once_with(
            ticker=None,
            include_archived=False,
            timeout=15.0,
        )
        self.state_store.list_holdings.assert_not_called()
        self.controller.ollama_client.chat.assert_not_called()

    def test_typo_holdings_prompt_short_circuits_llm(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": None,
                "thesis_bucket": None,
                "status": "active",
                "quantity": 100.0,
                "avg_cost": 45.5,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-21T00:00:00",
                "note": None,
            }
        ]

        resp = self.controller.build_chat_response("what r my holdiongs")

        assert resp is not None
        assert "Portfolio overview (1 holdings)" in resp.text
        assert "BHP" in resp.text
        self.controller.ollama_client.chat.assert_not_called()

    def test_natural_language_watchlist_short_circuits_llm(self) -> None:
        self.state_store.list_watch_tickers.return_value = [
            {"ticker": "BHP", "added_at": "2026-04-21T00:00:00"}
        ]
        resp = self.controller.build_chat_response("what is in my watchlist")
        assert resp is not None
        assert "Watchlist (1)" in resp.text
        self.controller.ollama_client.chat.assert_not_called()

    def test_explicit_web_search_uses_web_tool(self) -> None:
        self.tool_router.web_enrich.return_value = ToolResult(
            ok=True,
            title="web_enrich",
            payload={
                "ok": True,
                "urls": [
                    "https://www.asx.com.au/",
                    "https://www.bhp.com/news",
                ],
                "facts_count": 2,
            },
        )
        resp = self.controller.build_chat_response(
            "search web for BHP latest announcement",
            enable_web=True,
        )
        assert resp is not None
        assert resp.mode == ResponseMode.WEB
        assert "Web search results for: BHP latest announcement" in resp.text
        self.tool_router.web_enrich.assert_called_once_with(
            "BHP latest announcement", enabled=True
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_explicit_web_search_requires_web_access_when_disabled(self) -> None:
        resp = self.controller.build_chat_response(
            "search web for BHP latest announcement",
            enable_web=False,
        )
        assert resp is not None
        assert "Web access is required for web search" in resp.text
        assert resp.action_preview is not None
        self.tool_router.web_enrich.assert_not_called()

    def test_ingest_shortcut_does_not_overlap_with_web_search(self) -> None:
        preview = MagicMock(
            command=["python", "scripts/run_full_pipeline.py", "--ticker", "BHP"],
            estimated_impact="Runs single-ticker ingest",
            timeout_seconds=3600,
        )
        self.action_registry.preview.return_value = preview

        resp = self.controller.build_chat_response(
            "ingest BHP",
            enable_web=True,
        )

        assert resp is not None
        assert resp.mode == ResponseMode.ACTION
        assert resp.action_preview is not None
        assert resp.action_preview["action_id"] == "single_ticker_announcement_backfill"
        self.tool_router.web_enrich.assert_not_called()

    def test_news_ingest_command_short_circuits_query_orchestration(self) -> None:
        query_orchestrator = MagicMock()
        self.controller._query_orchestrator = query_orchestrator

        resp = self.controller.build_chat_response("ingest VEA news")

        assert resp.mode == ResponseMode.ACTION
        assert resp.action_preview is not None
        assert resp.action_preview["action_id"] == "daily_news_ingest"
        assert resp.action_preview["args"]["tickers"] == "VEA"
        query_orchestrator.orchestrate_query_with_context.assert_not_called()
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_recent_video_followup_uses_prior_channel_context(self) -> None:
        backend = MagicMock()
        backend.get_youtube_channel_recent_videos.return_value = {
            "name": "Kneppy Invests",
            "channel_id": "UCabc123",
            "videos": [
                {
                    "title": "Latest ASX breakdown",
                    "published_at": "2026-04-29T00:00:00Z",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "duration_seconds": 600,
                    "scores": {"overall": 0.88},
                }
            ],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": "Recent videos from Kneppy Invests (UCabc123):",
            },
            {"role": "user", "content": "most recent video?"},
        ]

        resp = self.controller.build_chat_response("most recent video?")

        assert resp.mode == "command"
        assert "Recent videos from Kneppy Invests (UCabc123)" in resp.text
        assert "Latest ASX breakdown" in resp.text
        backend.get_youtube_channel_recent_videos.assert_called_once_with(
            "Kneppy Invests",
            limit=8,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_recent_video_followup_uses_watched_ack_context(self) -> None:
        backend = MagicMock()
        backend.get_youtube_channel_recent_videos.return_value = {
            "name": "Kneppy Invests",
            "channel_id": "UCabc123",
            "videos": [
                {
                    "title": "Latest ASX breakdown",
                    "published_at": "2026-04-29T00:00:00Z",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "duration_seconds": 600,
                    "scores": {"overall": 0.88},
                }
            ],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    '"Kneppy Invests" is already being watched. The YouTube '
                    "channel (UCabc123) has active monitoring enabled."
                ),
            },
            {"role": "user", "content": "most recent video?"},
        ]

        resp = self.controller.build_chat_response("most recent video?")

        assert resp.mode == "command"
        assert "Recent videos from Kneppy Invests (UCabc123)" in resp.text
        assert "Latest ASX breakdown" in resp.text
        backend.get_youtube_channel_recent_videos.assert_called_once_with(
            "Kneppy Invests",
            limit=8,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_bare_channel_youtube_query_lists_recent_videos_directly(self) -> None:
        backend = MagicMock()
        backend.get_youtube_channel_recent_videos.return_value = {
            "name": "Kneppy Invests",
            "channel_id": "UCabc123",
            "videos": [
                {
                    "title": "Latest ASX breakdown",
                    "published_at": "2026-04-29T00:00:00Z",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "duration_seconds": 600,
                    "scores": {"overall": 0.88},
                }
            ],
        }
        self.tool_router.backend_api_client = backend

        resp = self.controller.build_chat_response("kneppy invests youtube")

        assert resp.mode == "command"
        assert "Recent videos from Kneppy Invests (UCabc123)" in resp.text
        assert "Latest ASX breakdown" in resp.text
        assert "ingest most recent video" in resp.text
        backend.get_youtube_channel_recent_videos.assert_called_once_with(
            "kneppy invests",
            limit=8,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_recent_video_followup_without_channel_asks_clearly(self) -> None:
        self.state_store.get_chat_messages.return_value = [
            {"role": "user", "content": "most recent video?"}
        ]

        resp = self.controller.build_chat_response("most recent video?")

        assert resp.mode == ResponseMode.FAST
        assert "Which YouTube channel" in resp.text
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_number_selection_ingests_selected_video(self) -> None:
        backend = MagicMock()
        backend.ingest_youtube_urls.return_value = {
            "ok": True,
            "count": 1,
            "error_count": 0,
            "results": [
                {
                    "source_id": "youtube_transcript:test:abc123",
                    "video_title": "Latest ASX breakdown",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "staged": True,
                    "chunks_staged": 4,
                    "takeaways": [{"text": "Important ASX takeaway"}],
                }
            ],
            "errors": [],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    "Recent videos from Kneppy Invests (UCabc123):\n"
                    "1. Latest ASX breakdown | date unknown | 10 min | score 0.88\n"
                    "   https://www.youtube.com/watch?v=abc123def45\n"
                    "2. Older ASX breakdown | date unknown | 9 min | score 0.50\n"
                    "   https://www.youtube.com/watch?v=older123456"
                ),
            }
        ]

        resp = self.controller.build_chat_response("ingest 1")

        assert resp.mode == "command"
        assert "Staged selected YouTube transcript" in resp.text
        assert "Important ASX takeaway" in resp.text
        assert "/review approve youtube_transcript:test:abc123" in resp.text
        backend.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc123def45"],
            credibility_weight=None,
            takeaway_limit=5,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_number_selection_accepts_latest_videos_history(self) -> None:
        backend = MagicMock()
        backend.ingest_youtube_urls.return_value = {
            "ok": True,
            "count": 1,
            "error_count": 0,
            "results": [
                {
                    "source_id": "youtube_transcript:status-trades:abc123",
                    "video_title": "Status of My Trades",
                    "webpage_url": "https://www.youtube.com/watch?v=ULVlVUSSSkI",
                    "staged": True,
                    "chunks_staged": 4,
                    "takeaways": [{"text": "Trade status takeaway"}],
                }
            ],
            "errors": [],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    "Here are Kneppy Invests' latest videos:\n\n"
                    "**Most Recent:**\n"
                    "1. **\"Status of My Trades\"** (16 mins)\n"
                    "   - https://www.youtube.com/watch?v=ULVlVUSSSkI\n\n"
                    "2. **\"Technical Update\"** (26 mins)\n"
                    "   - https://www.youtube.com/watch?v=0GW4EMwsrzY"
                ),
            }
        ]

        resp = self.controller.build_chat_response("ingest 1")

        assert resp.mode == "command"
        assert "Staged selected YouTube transcript" in resp.text
        assert "Trade status takeaway" in resp.text
        backend.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=ULVlVUSSSkI"],
            credibility_weight=None,
            takeaway_limit=5,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_most_recent_selection_ingests_first_video(self) -> None:
        backend = MagicMock()
        backend.ingest_youtube_urls.return_value = {
            "ok": True,
            "count": 1,
            "error_count": 0,
            "results": [
                {
                    "source_id": "youtube_transcript:test:abc123",
                    "video_title": "Latest ASX breakdown",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "staged": True,
                    "chunks_staged": 4,
                    "takeaways": [{"text": "Important ASX takeaway"}],
                }
            ],
            "errors": [],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    "Recent videos from Kneppy Invests (UCabc123):\n"
                    "1. Latest ASX breakdown | date unknown | 10 min | score 0.88\n"
                    "   https://www.youtube.com/watch?v=abc123def45\n"
                    "2. Older ASX breakdown | date unknown | 9 min | score 0.50\n"
                    "   https://www.youtube.com/watch?v=older123456"
                ),
            }
        ]

        resp = self.controller.build_chat_response("ingest most recent video")

        assert resp.mode == "command"
        assert "Staged selected YouTube transcript" in resp.text
        assert "/review approve youtube_transcript:test:abc123" in resp.text
        backend.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc123def45"],
            credibility_weight=None,
            takeaway_limit=5,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_transcript_confirmation_ingests_first_video(self) -> None:
        backend = MagicMock()
        backend.ingest_youtube_urls.return_value = {
            "ok": True,
            "count": 1,
            "error_count": 0,
            "results": [
                {
                    "source_id": "youtube_transcript:test:abc123",
                    "video_title": "Latest ASX breakdown",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "staged": True,
                    "chunks_staged": 4,
                    "takeaways": [{"text": "Important ASX takeaway"}],
                }
            ],
            "errors": [],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    "Recent videos from Kneppy Invests (UCabc123):\n"
                    "1. Latest ASX breakdown | date unknown | 10 min | score 0.88\n"
                    "   https://www.youtube.com/watch?v=abc123def45"
                ),
            }
        ]

        resp = self.controller.build_chat_response("yes access the transcript")

        assert resp.mode == "command"
        assert "Staged selected YouTube transcript" in resp.text
        backend.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc123def45"],
            credibility_weight=None,
            takeaway_limit=5,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_youtube_number_selection_can_set_weight(self) -> None:
        backend = MagicMock()
        backend.ingest_youtube_urls.return_value = {
            "ok": True,
            "count": 1,
            "error_count": 0,
            "results": [
                {
                    "source_id": "youtube_transcript:test:abc123",
                    "video_title": "Latest ASX breakdown",
                    "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    "staged": True,
                    "chunks_staged": 4,
                    "credibility_weight": 0.7,
                    "takeaways": [{"text": "Important ASX takeaway"}],
                }
            ],
            "errors": [],
        }
        self.tool_router.backend_api_client = backend
        self.state_store.get_chat_messages.return_value = [
            {
                "role": "assistant",
                "content": (
                    "Recent videos from Kneppy Invests (UCabc123):\n"
                    "1. Latest ASX breakdown | date unknown | 10 min | score 0.88\n"
                    "   https://www.youtube.com/watch?v=abc123def45"
                ),
            }
        ]

        resp = self.controller.build_chat_response("ingest 1 weight 0.7")

        assert resp.mode == "command"
        assert "review weight: 0.70" in resp.text
        backend.ingest_youtube_urls.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc123def45"],
            credibility_weight=0.7,
            takeaway_limit=5,
        )
        self.controller.ollama_client.chat.assert_not_called()

    def test_review_commands_use_backend_when_configured(self) -> None:
        backend = MagicMock()
        backend.get_pending_transcripts.return_value = {
            "pending": [
                {
                    "source_id": "youtube_transcript:test:abc123",
                    "source_type": "youtube_transcript",
                    "title": "Latest ASX breakdown",
                    "chunk_count": 4,
                    "staged_at": "2026-04-30T00:00:00Z",
                    "credibility_weight": 0.55,
                    "review_takeaways": [{"text": "Edited takeaway"}],
                }
            ]
        }
        backend.get_commentary_takeaways.return_value = {
            "takeaways": [
                {"text": "Generated takeaway"},
                {"text": "Second takeaway"},
            ],
            "credibility_weight": 0.55,
        }
        backend.update_transcript_review.return_value = {
            "ok": True,
            "source_id": "youtube_transcript:test:abc123",
        }
        backend.approve_transcript.return_value = {"points_upserted": 4}
        self.tool_router.backend_api_client = backend

        list_resp = self.controller.build_chat_response("/review list")
        takeaways_resp = self.controller.build_chat_response(
            "/review takeaways youtube_transcript:test:abc123"
        )
        weight_resp = self.controller.build_chat_response(
            "/review weight youtube_transcript:test:abc123 0.7"
        )
        edit_resp = self.controller.build_chat_response(
            "/review edit youtube_transcript:test:abc123 1 Edited operator takeaway"
        )
        approve_resp = self.controller.build_chat_response(
            "/review approve youtube_transcript:test:abc123"
        )

        assert "Pending transcript review" in list_resp.text
        assert "weight 0.55" in list_resp.text
        assert "Generated takeaway" in takeaways_resp.text
        assert "Updated youtube_transcript:test:abc123 review weight to 0.70" in weight_resp.text
        assert "Updated takeaway 1" in edit_resp.text
        assert "Approved and indexed 4 chunks" in approve_resp.text
        backend.get_pending_transcripts.assert_called_once()
        backend.update_transcript_review.assert_any_call(
            "youtube_transcript:test:abc123",
            credibility_weight=0.7,
        )
        backend.update_transcript_review.assert_any_call(
            "youtube_transcript:test:abc123",
            takeaways=["Edited operator takeaway", "Second takeaway"],
        )
        backend.approve_transcript.assert_called_once_with(
            "youtube_transcript:test:abc123"
        )


class TestIngestCommand(unittest.TestCase):
    """Tests for /ingest <url> command dispatch."""

    def _make_app(self, backend_result=None, backend_raises=None):
        from cockpit.ui.app import CockpitApp

        app = object.__new__(CockpitApp)

        class StubClient:
            def ingest_url(self, url):
                if backend_raises:
                    raise backend_raises
                return backend_result or {
                    "ok": True,
                    "source_id": "youtube_transcript:test:abc123",
                    "staged": True,
                    "chunks_staged": 5,
                    "video_title": "Test Video",
                    "channel": "Test Channel",
                }

        app._backend_client = StubClient()
        return app

    def test_ingest_url_success_returns_staged_message(self):
        app = self._make_app()
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "Test Video" in result
        assert "5 chunks staged" in result
        assert "/review approve" in result

    def test_ingest_url_empty_returns_usage(self):
        app = self._make_app()
        result = app._handle_ingest_command("", log=None)
        assert "Usage" in result

    def test_ingest_url_backend_error_returns_error_message(self):
        app = self._make_app(backend_raises=Exception("502 upstream"))
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "failed" in result.lower()

    def test_ingest_no_backend_returns_not_available(self):
        from cockpit.ui.app import CockpitApp

        app = object.__new__(CockpitApp)
        app._backend_client = None
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "backend" in result.lower()


class TestHoldingsSlashCommand(SlashCommandTestBase):
    """P4: /holdings list|add|remove|archive handler.

    Cockpit-local portfolio state, persisted via ``StateStore`` (P1).
    Holdings are NOT a financial truth source (SYSTEM_CONTRACT §1.2) and
    must NOT auto-mutate the watchlist.
    """

    # --- list -------------------------------------------------------------
    def test_holdings_list_empty_returns_friendly_message(self) -> None:
        self.state_store.list_holdings.return_value = []
        resp = self.controller._handle_slash_command("/holdings list")
        assert resp is not None
        assert "no holdings" in resp.text.lower()
        self.state_store.list_holdings.assert_called_once_with()

    def test_holdings_default_subcommand_is_list(self) -> None:
        self.state_store.list_holdings.return_value = []
        resp = self.controller._handle_slash_command("/holdings")
        assert resp is not None
        assert "no holdings" in resp.text.lower()

    def test_holdings_list_renders_active_rows(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": "main",
                "thesis_bucket": None,
                "status": "active",
                "quantity": 100.0,
                "avg_cost": 45.5,
                "cost_currency": "AUD",
                "opened_at": "2026-04-01T00:00:00",
                "updated_at": "2026-04-01T00:00:00",
                "note": None,
            },
            {
                "holding_id": "h2",
                "ticker": "CBA",
                "account_label": None,
                "thesis_bucket": None,
                "status": "active",
                "quantity": None,
                "avg_cost": None,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-02T00:00:00",
                "note": None,
            },
        ]
        resp = self.controller._handle_slash_command("/holdings list")
        assert resp is not None
        assert "Portfolio overview (2 holdings)" in resp.text
        assert "Live pricing coverage" in resp.text
        assert "BHP" in resp.text
        assert "CBA" in resp.text
        # Quantity and avg cost surfaced when present
        assert "100" in resp.text
        assert "45.50" in resp.text
        assert "Tip: use `/holdings remove <ID>`" in resp.text

    def test_holdings_list_prefers_backend_enriched_rows_when_available(self) -> None:
        backend = MagicMock()
        backend.list_cockpit_holdings.return_value = {
            "items": [
                {
                    "holding_id": "h1",
                    "ticker": "BHP",
                    "account_label": "main",
                    "quantity": 100.0,
                    "avg_cost": 40.0,
                    "cost_currency": "AUD",
                    "current_price": 50.0,
                    "price_currency": "AUD",
                    "market_value": 5000.0,
                    "unrealized_pnl": 1000.0,
                    "price_as_of": "2026-04-22T08:30:00Z",
                    "valuation_warning": None,
                }
            ]
        }
        self.tool_router.backend_api_client = backend
        self.state_store.list_holdings.return_value = []

        resp = self.controller._handle_slash_command("/holdings list")

        assert resp is not None
        assert "Portfolio overview (1 holdings)" in resp.text
        assert "Market value:" in resp.text
        assert "AUD 5,000.00" in resp.text
        assert "+AUD 1,000.00" in resp.text
        backend.list_cockpit_holdings.assert_called_once_with(
            ticker=None,
            include_archived=False,
            timeout=15.0,
        )
        self.state_store.list_holdings.assert_not_called()

    def test_holdings_list_filters_by_ticker(self) -> None:
        self.state_store.list_holdings.return_value = []
        self.controller._handle_slash_command("/holdings list bhp")
        self.state_store.list_holdings.assert_called_once_with(ticker="BHP")

    # --- add --------------------------------------------------------------
    def test_holdings_add_ticker_only(self) -> None:
        self.state_store.add_holding.return_value = "new-id-123"
        resp = self.controller._handle_slash_command("/holdings add bhp")
        assert resp is not None
        assert "Added BHP" in resp.text
        self.state_store.add_holding.assert_called_once_with(
            "BHP", quantity=None, avg_cost=None
        )

    def test_holdings_add_ticker_with_quantity(self) -> None:
        self.state_store.add_holding.return_value = "new-id-123"
        resp = self.controller._handle_slash_command("/holdings add BHP 100")
        assert resp is not None
        assert "BHP" in resp.text
        self.state_store.add_holding.assert_called_once_with(
            "BHP", quantity=100.0, avg_cost=None
        )

    def test_holdings_add_ticker_with_quantity_and_cost(self) -> None:
        self.state_store.add_holding.return_value = "new-id-123"
        resp = self.controller._handle_slash_command("/holdings add BHP 100 45.5")
        assert resp is not None
        assert "BHP" in resp.text
        self.state_store.add_holding.assert_called_once_with(
            "BHP", quantity=100.0, avg_cost=45.5
        )

    def test_holdings_add_missing_ticker_returns_usage(self) -> None:
        resp = self.controller._handle_slash_command("/holdings add")
        assert resp is not None
        assert "Usage" in resp.text
        self.state_store.add_holding.assert_not_called()

    def test_holdings_add_invalid_quantity_returns_error(self) -> None:
        resp = self.controller._handle_slash_command("/holdings add BHP not-a-number")
        assert resp is not None
        assert "quantity" in resp.text.lower()
        self.state_store.add_holding.assert_not_called()

    # --- remove -----------------------------------------------------------
    def test_holdings_remove_single_match_by_ticker(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": None,
                "thesis_bucket": None,
                "status": "active",
                "quantity": None,
                "avg_cost": None,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-01T00:00:00",
                "note": None,
            }
        ]
        self.state_store.remove_holding.return_value = True
        resp = self.controller._handle_slash_command("/holdings remove BHP")
        assert resp is not None
        assert "Removed" in resp.text
        assert "BHP" in resp.text
        self.state_store.remove_holding.assert_called_once_with("h1")

    def test_holdings_remove_multi_match_asks_for_holding_id(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": "main",
                "thesis_bucket": None,
                "status": "active",
                "quantity": 100.0,
                "avg_cost": None,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-01T00:00:00",
                "note": None,
            },
            {
                "holding_id": "h2",
                "ticker": "BHP",
                "account_label": "smsf",
                "thesis_bucket": None,
                "status": "active",
                "quantity": 50.0,
                "avg_cost": None,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-01T00:00:00",
                "note": None,
            },
        ]
        resp = self.controller._handle_slash_command("/holdings remove BHP")
        assert resp is not None
        assert "Multiple holdings" in resp.text or "multiple" in resp.text.lower()
        assert "h1" in resp.text
        assert "h2" in resp.text
        self.state_store.remove_holding.assert_not_called()

    def test_holdings_remove_no_match_by_ticker(self) -> None:
        self.state_store.list_holdings.return_value = []
        resp = self.controller._handle_slash_command("/holdings remove XYZ")
        assert resp is not None
        assert "No active holding" in resp.text or "not found" in resp.text.lower()
        self.state_store.remove_holding.assert_not_called()

    def test_holdings_remove_by_holding_id(self) -> None:
        # UUID-shaped argument — treated as holding_id, no list lookup needed
        holding_id = "12345678-1234-1234-1234-123456789abc"
        self.state_store.remove_holding.return_value = True
        resp = self.controller._handle_slash_command(f"/holdings remove {holding_id}")
        assert resp is not None
        assert "Removed" in resp.text
        self.state_store.remove_holding.assert_called_once_with(holding_id)
        self.state_store.list_holdings.assert_not_called()

    def test_holdings_remove_missing_arg_returns_usage(self) -> None:
        resp = self.controller._handle_slash_command("/holdings remove")
        assert resp is not None
        assert "Usage" in resp.text
        self.state_store.remove_holding.assert_not_called()

    # --- archive ----------------------------------------------------------
    def test_holdings_archive_single_match_by_ticker(self) -> None:
        self.state_store.list_holdings.return_value = [
            {
                "holding_id": "h1",
                "ticker": "BHP",
                "account_label": None,
                "thesis_bucket": None,
                "status": "active",
                "quantity": None,
                "avg_cost": None,
                "cost_currency": None,
                "opened_at": None,
                "updated_at": "2026-04-01T00:00:00",
                "note": None,
            }
        ]
        self.state_store.archive_holding.return_value = True
        resp = self.controller._handle_slash_command("/holdings archive BHP")
        assert resp is not None
        assert "Archived" in resp.text
        assert "BHP" in resp.text
        self.state_store.archive_holding.assert_called_once_with("h1")

    def test_holdings_archive_by_holding_id(self) -> None:
        holding_id = "12345678-1234-1234-1234-123456789abc"
        self.state_store.archive_holding.return_value = True
        resp = self.controller._handle_slash_command(f"/holdings archive {holding_id}")
        assert resp is not None
        assert "Archived" in resp.text
        self.state_store.archive_holding.assert_called_once_with(holding_id)

    # --- usage / unknown subcommand --------------------------------------
    def test_holdings_unknown_subcommand_returns_usage(self) -> None:
        resp = self.controller._handle_slash_command("/holdings frobnicate")
        assert resp is not None
        assert "Usage" in resp.text

    # --- no state store --------------------------------------------------
    def test_holdings_without_state_store_returns_friendly_message(self) -> None:
        self.controller._state_store = None
        resp = self.controller._handle_slash_command("/holdings list")
        assert resp is not None
        assert "not available" in resp.text.lower()


class TestMarketUpdateSlashCommand(SlashCommandTestBase):
    """P4 + P5b: /market-update list|show|<run_type>|latest handler.

    For ``list``, ``show``, and ``latest`` the handler reads from the
    cockpit-local market-update tables (P2). For a run_type
    (``noon|final|manual``) the handler delegates to a
    ``MarketUpdateOrchestrator`` constructed via
    ``_build_market_update_orchestrator``; tests inject a stub
    orchestrator so no live yfinance calls are made.
    """

    _SAMPLE_REPORT = {
        "report_id": "r1",
        "run_type": "noon",
        "report_date": "2026-04-20",
        "status": "complete",
        "created_at": "2026-04-20T12:05:00",
        "summary": {
            "headline": "ASX 200 +0.6% at noon",
            "tickers": [
                {
                    "ticker": "BHP",
                    "pct_change": 1.2,
                    "significance": 0.82,
                    "reasons": ["price move", "fresh news"],
                }
            ],
        },
        "markdown_path": None,
        "json_path": None,
    }

    # --- default / latest ------------------------------------------------
    def test_market_update_default_shows_latest(self) -> None:
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update")
        assert resp is not None
        assert "noon" in resp.text.lower()
        assert "2026-04-20" in resp.text
        assert "ASX 200" in resp.text
        assert "Ranked movers:" in resp.text
        assert "BHP: +1.20% (sig 0.82)" in resp.text
        assert "price move" in resp.text
        self.state_store.get_latest_market_update_report.assert_called_once_with(None)

    def test_market_update_latest_explicit(self) -> None:
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update latest")
        assert resp is not None
        assert "ASX 200" in resp.text

    def test_market_update_latest_when_none_present(self) -> None:
        self.state_store.get_latest_market_update_report.return_value = None
        resp = self.controller._handle_slash_command("/market-update")
        assert resp is not None
        assert "no market-update" in resp.text.lower() or (
            "no" in resp.text.lower() and "report" in resp.text.lower()
        )

    def test_market_update_pronoun_followup_uses_latest_report(self) -> None:
        self.state_store.get_chat_messages.return_value = [
            {"role": "user", "content": "market update today?"},
            {
                "role": "assistant",
                "content": "Latest market update:\n[noon] 2026-04-20  ASX 200 +0.6% at noon",
            },
        ]
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )

        resp = self.controller.build_chat_response("tell me about it\\")

        assert resp is not None
        assert "Latest market update detail" in resp.text
        assert "ASX 200 +0.6% at noon" in resp.text
        assert resp.evidence == [
            {"type": "market_update_report", "details": self._SAMPLE_REPORT}
        ]
        self.controller.ollama_client.chat.assert_not_called()
        self.state_store.get_latest_market_update_report.assert_called_once_with(None)

    def test_market_update_pronoun_followup_requires_recent_market_context(self) -> None:
        self.state_store.get_chat_messages.return_value = [
            {"role": "assistant", "content": "BHP company overview"}
        ]

        resp = self.controller._try_market_update_followup("tell me about it")

        assert resp is None
        self.state_store.get_latest_market_update_report.assert_not_called()

    # --- list ------------------------------------------------------------
    def test_market_update_list_empty(self) -> None:
        self.state_store.list_market_update_reports.return_value = []
        resp = self.controller._handle_slash_command("/market-update list")
        assert resp is not None
        assert "no market-update" in resp.text.lower() or (
            "no" in resp.text.lower() and "report" in resp.text.lower()
        )

    def test_market_update_list_renders_rows(self) -> None:
        self.state_store.list_market_update_reports.return_value = [
            self._SAMPLE_REPORT,
            {**self._SAMPLE_REPORT, "report_id": "r2", "run_type": "final"},
        ]
        resp = self.controller._handle_slash_command("/market-update list")
        assert resp is not None
        assert "noon" in resp.text.lower()
        assert "final" in resp.text.lower()
        assert "2026-04-20" in resp.text

    def test_market_update_list_filters_by_run_type(self) -> None:
        self.state_store.list_market_update_reports.return_value = []
        self.controller._handle_slash_command("/market-update list noon")
        self.state_store.list_market_update_reports.assert_called_once_with(
            run_type="noon"
        )

    # --- show ------------------------------------------------------------
    def test_market_update_show_default(self) -> None:
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update show")
        assert resp is not None
        assert "ASX 200" in resp.text

    def test_market_update_show_filters_by_run_type(self) -> None:
        self.state_store.get_latest_market_update_report.return_value = None
        self.controller._handle_slash_command("/market-update show final")
        self.state_store.get_latest_market_update_report.assert_called_once_with(
            "final"
        )

    # --- run_type orchestrator integration (P5b) ------------------------
    def _stub_orchestrator(
        self,
        *,
        status: str = "complete",
        gathered: int = 1,
        followups: int = 0,
        errors: tuple[str, ...] = (),
        report_id: str | None = "report-stub-1",
    ) -> MagicMock:
        from cockpit.core.market_update_orchestrator import RunResult

        orc = MagicMock()
        orc.run.return_value = RunResult(
            report_id=report_id,
            run_type="noon",
            status=status,
            gathered_tickers=gathered,
            queued_followups=followups,
            errors=errors,
            started_at="2026-04-20T12:00:00+00:00",
            finished_at="2026-04-20T12:00:01+00:00",
        )
        return orc

    def test_market_update_noon_invokes_orchestrator(self) -> None:
        orc = self._stub_orchestrator()
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update noon")
        assert resp is not None
        orc.run.assert_called_once_with("noon", tickers=None)
        assert "complete" in resp.text.lower()
        assert "ASX 200" in resp.text  # rendered persisted report

    def test_market_update_noon_passes_explicit_tickers(self) -> None:
        orc = self._stub_orchestrator()
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        self.state_store.get_latest_market_update_report.return_value = None
        self.controller._handle_slash_command("/market-update noon BHP RIO")
        orc.run.assert_called_once_with("noon", tickers=["BHP", "RIO"])

    def test_market_update_final_renders_status_summary(self) -> None:
        orc = self._stub_orchestrator(
            status="partial", gathered=2, followups=1, errors=("RIO: snapshot failed",)
        )
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update final")
        assert resp is not None
        assert "partial" in resp.text.lower()
        assert "tickers=2" in resp.text
        assert "followups=1" in resp.text
        assert "RIO" in resp.text  # error surfaced
        assert resp.routing_metadata is not None
        assert resp.routing_metadata["source"] == "cockpit"
        assert resp.routing_metadata["model"] == "deterministic:market-update"

    def test_market_update_snapshot_gaps_are_not_labeled_top_level_errors(self) -> None:
        orc = self._stub_orchestrator(
            status="partial",
            gathered=354,
            followups=52,
            errors=(
                "ADR: no snapshot available",
                "ADT: no snapshot available",
                "AMPPB: no snapshot available",
            ),
        )
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        self.state_store.get_latest_market_update_report.return_value = (
            self._SAMPLE_REPORT
        )
        resp = self.controller._handle_slash_command("/market-update final")
        assert resp is not None
        assert "Snapshot gaps (3 ticker(s)): ADR, ADT, AMPPB" in resp.text
        assert "Errors (3)" not in resp.text

    def test_market_update_manual_handles_skipped_run(self) -> None:
        orc = self._stub_orchestrator(
            status="skipped", gathered=0, followups=0, report_id=None
        )
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        resp = self.controller._handle_slash_command("/market-update manual")
        assert resp is not None
        assert "skipped" in resp.text.lower()
        # No report fetched when report_id is None
        self.state_store.get_latest_market_update_report.assert_not_called()

    def test_market_update_orchestrator_init_failure_is_friendly(self) -> None:
        self.controller._build_market_update_orchestrator = MagicMock(
            side_effect=RuntimeError("yfinance import failed")
        )
        resp = self.controller._handle_slash_command("/market-update noon")
        assert resp is not None
        assert "unavailable" in resp.text.lower()
        assert "yfinance" in resp.text.lower()

    def test_market_update_run_failure_is_friendly(self) -> None:
        orc = MagicMock()
        orc.run.side_effect = RuntimeError("network down")
        self.controller._build_market_update_orchestrator = MagicMock(
            return_value=orc
        )
        resp = self.controller._handle_slash_command("/market-update noon")
        assert resp is not None
        assert "failed" in resp.text.lower()
        assert "network down" in resp.text.lower()

    # --- unknown subcommand ---------------------------------------------
    def test_market_update_unknown_subcommand_returns_usage(self) -> None:
        resp = self.controller._handle_slash_command("/market-update frobnicate")
        assert resp is not None
        assert "Usage" in resp.text

    # --- no state store --------------------------------------------------
    def test_market_update_without_state_store_returns_friendly_message(self) -> None:
        self.controller._state_store = None
        resp = self.controller._handle_slash_command("/market-update")
        assert resp is not None
        assert "not available" in resp.text.lower()


if __name__ == "__main__":
    unittest.main()
