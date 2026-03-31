"""End-to-end integration tests for the cockpit agent system.

Exercises: HybridRouter → AgentLoop → ToolExecutor → tools → MemoryStore.

These tests make real LLM calls and are skipped when backends are unavailable.
Run explicitly with: pytest cockpit/tests/test_agent_e2e.py -v -m slow
"""
from __future__ import annotations

import os
import socket
from unittest.mock import MagicMock

import pytest

# ---------- Skip conditions ----------


def _anthropic_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _llama_available() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=2):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


skip_no_anthropic = pytest.mark.skipif(
    not _anthropic_available(), reason="ANTHROPIC_API_KEY not set"
)
skip_no_llama = pytest.mark.skipif(
    not _llama_available(), reason="llama.cpp not reachable on :8001"
)

# ---------- Fixtures ----------


@pytest.fixture
def tmp_memory(tmp_path):
    from cockpit.core.agent.memory.store import MemoryStore

    return MemoryStore(root=tmp_path)


@pytest.fixture
def mock_tool_router():
    """Mock ToolRouter that returns canned data for get_financials.

    Uses a plain MagicMock (no spec) so instance attributes like db_reader
    and file_indexer can be set freely without triggering AttributeError.
    """
    router = MagicMock()
    mock_backend_api = MagicMock()
    mock_backend_api.get_ticker_context.return_value = {
        "financials": [
            {"metric": "revenue", "value": 55000, "currency": "AUD", "period": "FY2025"}
        ],
        "docs": [],
        "announcement_context": [],
    }
    router.backend_api_client = mock_backend_api
    router._build_financials_narrative.return_value = "BHP FY2025 Revenue: $55B AUD"
    router.file_indexer.search_text.return_value = []
    router.file_indexer.list_recent_reports.return_value = []
    router.web_default_enabled = False
    return router


@pytest.fixture
def mock_action_registry():
    from cockpit.core.actions import ActionRegistry

    return MagicMock(spec=ActionRegistry)


# ---------- Anthropic E2E ----------


@skip_no_anthropic
@pytest.mark.slow
def test_anthropic_agent_loop_responds(tmp_memory, mock_tool_router, mock_action_registry):
    """Full loop: Anthropic API → AgentLoop → ToolExecutor → response."""
    from cockpit.core.agent.anthropic_client import AnthropicClient
    from cockpit.core.agent.hybrid_router import HybridRouter
    from cockpit.core.agent_loop import AgentLoop
    from cockpit.core.tool_executor import ToolExecutor

    api_client = AnthropicClient(model="claude-haiku-4-5-20251001", max_tokens=512)
    router = HybridRouter(api_client=api_client, policy="api_only")

    class _RouterClient:
        model = "claude-haiku-4-5-20251001"

        def chat(self, prompt, timeout=120, prior_messages=None):
            msgs = (prior_messages or []) + [{"role": "user", "content": prompt}]
            return router.complete(msgs, role="orchestrator").text

    executor = ToolExecutor(mock_tool_router, mock_action_registry)
    loop = AgentLoop(
        llm_client=_RouterClient(),
        tool_executor=executor.execute,
        llm_timeout=30.0,
    )

    result = loop.run("What is 2 + 2? Answer briefly.", ticker=None)
    assert result.text, "Expected a non-empty response from the agent"
    assert result.iterations_used >= 1

    # Verify cost was tracked (API calls should have non-zero cost)
    assert router.total_cost_usd() > 0

    # Verify memory can persist session turns
    tmp_memory.append_session_turn("user", "What is 2+2?")
    tmp_memory.append_session_turn("assistant", result.text)
    turns = tmp_memory.read_session_turns()
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


# ---------- Local llama.cpp E2E ----------


@skip_no_llama
@pytest.mark.slow
def test_local_agent_loop_responds(tmp_memory, mock_tool_router, mock_action_registry):
    """Full loop: local llama.cpp → AgentLoop → ToolExecutor → response."""
    from cockpit.core.agent.hybrid_router import HybridRouter
    from cockpit.core.agent_loop import AgentLoop
    from cockpit.core.tool_executor import ToolExecutor
    from cockpit.integrations.llamacpp_client import LlamaCppClient

    local_client = LlamaCppClient(
        base_url="http://127.0.0.1:8001",
        model="local",
        api_key="local-openai-key",
    )
    router = HybridRouter(llm_client=local_client, policy="local_only")

    class _RouterClient:
        model = "local"

        def chat(self, prompt, timeout=120, prior_messages=None):
            msgs = (prior_messages or []) + [{"role": "user", "content": prompt}]
            return router.complete(msgs, role="orchestrator").text

    executor = ToolExecutor(mock_tool_router, mock_action_registry)
    loop = AgentLoop(
        llm_client=_RouterClient(),
        tool_executor=executor.execute,
        llm_timeout=60.0,
    )

    result = loop.run("Say hello in exactly 3 words.", ticker=None)
    assert result.text, "Expected a non-empty response from the local agent"
    assert result.iterations_used >= 1
    # Local inference is free
    assert router.total_cost_usd() == 0.0


# ---------- Memory round-trip (no LLM required) ----------


def test_memory_round_trip_no_llm(tmp_memory):
    """Verify MemoryStore integration without needing any LLM."""
    tmp_memory.write_research("BHP", "Revenue: $55B, EBIT: $19B")
    tmp_memory.append_session_turn("user", "Tell me about BHP")
    tmp_memory.append_session_turn("assistant", "BHP had $55B revenue in FY2025")

    assert "55B" in tmp_memory.read_research("BHP")

    turns = tmp_memory.read_session_turns()
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"
    assert "BHP" in turns[0]["content"]

    archived = tmp_memory.rotate_session()
    assert archived.exists()
    assert tmp_memory.read_session_turns() == []
