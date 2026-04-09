"""Tests for slash command handling in ChatController."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from cockpit.core.chat import ChatController, ChatResponse, ResponseMode


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


if __name__ == "__main__":
    unittest.main()
