"""Integration tests for chat.py with HybridRouter and MemoryStore wired in."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from cockpit.core.agent.hybrid_router import HybridRouter
from cockpit.core.agent.memory.store import MemoryStore


@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.chat.return_value = '{"type": "response", "content": "router integration ok"}'
    client.model = "test-model"
    return client


@pytest.fixture
def tmp_memory(tmp_path):
    return MemoryStore(root=tmp_path)


@pytest.fixture
def router(mock_llm):
    return HybridRouter(llm_client=mock_llm, policy="local_only")


def test_hybrid_router_integrates_with_agent_loop(router, tmp_memory):
    from cockpit.core.agent_loop import AgentLoop

    class _RouterAsClient:
        def __init__(self, r):
            self._r = r

        def chat(self, prompt, timeout=120, prior_messages=None):
            msgs = (prior_messages or []) + [{"role": "user", "content": prompt}]
            return self._r.complete(msgs).text

    loop = AgentLoop(llm_client=_RouterAsClient(router))
    result = loop.run("Reply with the router integration phrase.")
    assert "router integration ok" in result.text
    assert result.iterations_used >= 1


def test_memory_context_injected_into_session(tmp_memory):
    tmp_memory.write_research("BHP", "BHP FY2025 revenue: $55.2B, EBIT margin: 35%")
    content = tmp_memory.read_research("BHP")
    assert "55.2B" in content


def test_session_turns_persist_and_load(tmp_memory):
    tmp_memory.append_session_turn("user", "What is BHP's revenue?")
    tmp_memory.append_session_turn("assistant", "BHP revenue is $55B.")
    turns = tmp_memory.read_session_turns()
    assert len(turns) == 2
    archived = tmp_memory.rotate_session()
    assert archived.exists()
    assert tmp_memory.read_session_turns() == []


def test_router_cost_log_grows_per_call(router):
    router.complete([{"role": "user", "content": "q1"}], role="orchestrator")
    router.complete([{"role": "user", "content": "q2"}], role="analyst")
    log = router.cost_log()
    assert len(log) == 2
    assert log[0]["role"] == "orchestrator"
    assert log[1]["role"] == "analyst"


def test_chat_controller_accepts_memory_store_param(tmp_memory):
    """Verify ChatController accepts memory_store without breaking existing init."""
    from unittest.mock import MagicMock
    from cockpit.core.chat import ChatController

    mock_ollama = MagicMock()
    mock_tool_router = MagicMock()
    mock_action_registry = MagicMock()

    ctrl = ChatController(
        ollama_client=mock_ollama,
        tool_router=mock_tool_router,
        action_registry=mock_action_registry,
        memory_store=tmp_memory,
    )
    assert ctrl._memory is tmp_memory


def test_chat_controller_memory_store_defaults_to_none():
    """Existing code paths work when no memory_store is passed."""
    from unittest.mock import MagicMock
    from cockpit.core.chat import ChatController

    mock_ollama = MagicMock()
    mock_tool_router = MagicMock()
    mock_action_registry = MagicMock()

    ctrl = ChatController(
        ollama_client=mock_ollama,
        tool_router=mock_tool_router,
        action_registry=mock_action_registry,
    )
    assert ctrl._memory is None


def test_memory_store_conditional_import():
    """MemoryStore is importable from cockpit.core.chat module namespace."""
    import cockpit.core.chat as chat_module
    # Either the real MemoryStore or the None fallback — both are valid
    assert hasattr(chat_module, "MemoryStore")
