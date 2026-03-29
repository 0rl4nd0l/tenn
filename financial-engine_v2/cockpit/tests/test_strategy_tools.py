"""Tests for strategy tool integration — get_strategy handler and deep_research strategy injection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cockpit.core.strategy import StrategyService
from cockpit.storage.state import StateStore


@pytest.fixture()
def strategy_svc(tmp_path):
    """Fresh StrategyService backed by temporary SQLite."""
    db_path = str(tmp_path / "state.db")
    store = StateStore(db_path)
    return StrategyService(store)


# ------------------------------------------------------------------
# ToolExecutor: _exec_get_strategy
# ------------------------------------------------------------------


class TestGetStrategyHandler:
    """Test the _exec_get_strategy handler in ToolExecutor."""

    def _make_executor(self, strategy_service):
        """Create a minimal ToolExecutor with only strategy_service wired."""
        from cockpit.core.tool_executor import ToolExecutor

        router = MagicMock()
        registry = MagicMock()
        return ToolExecutor(
            router,
            registry,
            strategy_service=strategy_service,
        )

    def test_no_strategy_service_returns_error(self):
        from cockpit.core.tool_executor import ToolExecutor

        executor = ToolExecutor(MagicMock(), MagicMock())
        result = executor._exec_get_strategy({})
        assert result["ok"] is False
        assert "not available" in result["error"]

    def test_empty_strategy_returns_empty(self, strategy_svc):
        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({})
        assert result["ok"] is True
        assert result["global_criteria"] == []
        assert result["ticker_criteria"] == []
        assert result["decision"] is None

    def test_global_criteria_returned(self, strategy_svc):
        strategy_svc.add_global("Positive FCF", category="quality", priority=2)
        strategy_svc.add_global("Low debt", category="risk", priority=4)

        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({})
        assert result["ok"] is True
        assert len(result["global_criteria"]) == 2
        assert result["global_criteria"][0]["criterion"] == "Positive FCF"

    def test_ticker_criteria_returned(self, strategy_svc):
        strategy_svc.add_global("Low PE", category="valuation")
        strategy_svc.add_ticker("BHP", "Iron ore cycle position", category="momentum")

        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({"ticker": "BHP"})
        assert result["ok"] is True
        assert len(result["global_criteria"]) == 1
        assert len(result["ticker_criteria"]) == 1
        assert result["ticker_criteria"][0]["criterion"] == "Iron ore cycle position"

    def test_decision_returned(self, strategy_svc):
        strategy_svc.record_decision("CSL", "buy", "Strong pipeline and FCF")

        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({"ticker": "CSL"})
        assert result["ok"] is True
        assert result["decision"] is not None
        assert result["decision"]["decision"] == "buy"
        assert "Strong pipeline" in result["decision"]["decision_rationale"]

    def test_context_block_included(self, strategy_svc):
        strategy_svc.add_global("Must have positive EBIT margin", category="quality")

        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({"ticker": "BHP"})
        assert "context_block" in result
        assert "positive EBIT margin" in result["context_block"]

    def test_ticker_case_insensitive(self, strategy_svc):
        strategy_svc.add_ticker("BHP", "Test criterion")

        executor = self._make_executor(strategy_svc)
        result = executor._exec_get_strategy({"ticker": "bhp"})
        assert len(result["ticker_criteria"]) == 1


# ------------------------------------------------------------------
# Tool definitions: get_strategy registered correctly
# ------------------------------------------------------------------


def test_get_strategy_in_tool_definitions():
    from cockpit.core.tool_definitions import TOOL_DEFINITIONS, MUTATING_TOOL_NAMES

    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert "get_strategy" in names
    assert "get_strategy" not in MUTATING_TOOL_NAMES


def test_get_strategy_in_dispatch_table():
    from cockpit.core.tool_executor import ToolExecutor

    assert "get_strategy" in ToolExecutor._READ_ONLY_DISPATCH


# ------------------------------------------------------------------
# DeepResearchRunner: strategy injection into _gather
# ------------------------------------------------------------------


class TestDeepResearchStrategyInjection:
    """Test that DeepResearchRunner injects strategy criteria into gathered data."""

    def test_strategy_injected_when_available(self, strategy_svc):
        strategy_svc.add_global("Must have positive FCF", category="quality")
        strategy_svc.add_ticker("BHP", "Iron ore outlook", category="momentum")

        from cockpit.core.research.deep_research import DeepResearchRunner

        router = MagicMock()
        router.db_reader.get_financials.return_value = []
        router.db_reader.get_docs.return_value = []
        router.db_reader.get_announcement_context.return_value = []

        runner = DeepResearchRunner(
            tool_router=router,
            backend_client=MagicMock(),
            strategy_service=strategy_svc,
        )
        gathered = runner._gather("BHP")
        assert "strategy_criteria" in gathered
        assert "positive FCF" in gathered["strategy_criteria"]
        assert "Iron ore outlook" in gathered["strategy_criteria"]

    def test_no_strategy_when_service_absent(self):
        from cockpit.core.research.deep_research import DeepResearchRunner

        router = MagicMock()
        router.db_reader.get_financials.return_value = []
        router.db_reader.get_docs.return_value = []
        router.db_reader.get_announcement_context.return_value = []

        runner = DeepResearchRunner(
            tool_router=router,
            backend_client=MagicMock(),
        )
        gathered = runner._gather("BHP")
        assert "strategy_criteria" not in gathered

    def test_no_strategy_when_criteria_empty(self, strategy_svc):
        from cockpit.core.research.deep_research import DeepResearchRunner

        router = MagicMock()
        router.db_reader.get_financials.return_value = []
        router.db_reader.get_docs.return_value = []
        router.db_reader.get_announcement_context.return_value = []

        runner = DeepResearchRunner(
            tool_router=router,
            backend_client=MagicMock(),
            strategy_service=strategy_svc,
        )
        gathered = runner._gather("BHP")
        assert "strategy_criteria" not in gathered


# ------------------------------------------------------------------
# Research synthesis prompt: strategy_evaluation field present
# ------------------------------------------------------------------


def test_synthesis_prompt_includes_strategy_evaluation():
    from backend.app.services.research_synthesis import _RESEARCH_SYSTEM_PROMPT

    assert "strategy_evaluation" in _RESEARCH_SYSTEM_PROMPT
    assert "strategy_criteria" in _RESEARCH_SYSTEM_PROMPT
    assert "met|not_met|insufficient_data" in _RESEARCH_SYSTEM_PROMPT
