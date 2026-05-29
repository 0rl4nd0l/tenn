"""Tests for SubAgentSpawner — background asyncio agents with GPU concurrency control."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from cockpit.core.agent.subagents import SubAgentResult, SubAgentSpawner, SubAgentType


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_mock_llm(response: str = "analysis complete", delay: float = 0.0):
    """Return a mock LLM client whose chat() optionally sleeps."""
    client = MagicMock()
    client.model = "test-model"

    if delay > 0:
        def slow_chat(*args, **kwargs):
            time.sleep(delay)
            return response
        client.chat.side_effect = slow_chat
    else:
        client.chat.return_value = response

    return client


@pytest.fixture
def mock_llm():
    return make_mock_llm()


@pytest.fixture
def spawner(mock_llm):
    return SubAgentSpawner(llm_client=mock_llm)


# ---------------------------------------------------------------------------
# Data type tests
# ---------------------------------------------------------------------------


def test_subagent_result_is_dataclass():
    r = SubAgentResult(agent_type="researcher", success=True, result="found data", error=None)
    assert r.success
    assert r.agent_type == "researcher"
    assert r.result == "found data"
    assert r.error is None


def test_subagent_result_defaults():
    r = SubAgentResult(agent_type="auditor", success=False, result="")
    assert r.tool_calls_made == 0
    assert r.duration_ms == 0


def test_subagent_type_enum():
    assert SubAgentType.RESEARCHER == "researcher"
    assert SubAgentType.AUDITOR == "auditor"
    assert SubAgentType.COMPARATOR == "comparator"
    assert SubAgentType.PIPELINE_RUNNER == "pipeline_runner"


def test_subagent_type_is_str_enum():
    """SubAgentType values must be usable as plain strings."""
    assert str(SubAgentType.RESEARCHER) in ("researcher", "SubAgentType.RESEARCHER")
    assert SubAgentType.RESEARCHER.value == "researcher"


# ---------------------------------------------------------------------------
# Spawn: happy path
# ---------------------------------------------------------------------------


def test_spawn_researcher_runs(spawner):
    result = asyncio.run(
        spawner.spawn(agent_type=SubAgentType.RESEARCHER, task="Analyze BHP revenue trends", ticker="BHP")
    )
    assert result.success
    assert result.agent_type == "researcher"
    assert result.result  # non-empty


def test_spawn_auditor_runs(spawner):
    result = asyncio.run(
        spawner.spawn(agent_type=SubAgentType.AUDITOR, task="Audit MIN cashflow statement")
    )
    assert result.success
    assert result.agent_type == "auditor"


def test_spawn_comparator_runs(spawner):
    result = asyncio.run(
        spawner.spawn(agent_type=SubAgentType.COMPARATOR, task="Compare BHP vs RIO revenue")
    )
    assert result.success
    assert result.agent_type == "comparator"


def test_spawn_pipeline_runner_runs(spawner):
    result = asyncio.run(
        spawner.spawn(agent_type=SubAgentType.PIPELINE_RUNNER, task="Run extraction for CSL")
    )
    assert result.success
    assert result.agent_type == "pipeline_runner"


def test_spawn_records_duration(spawner):
    result = asyncio.run(
        spawner.spawn(agent_type=SubAgentType.RESEARCHER, task="quick task")
    )
    assert result.duration_ms >= 0


def test_spawn_with_string_agent_type(spawner):
    """Spawn must also accept a plain string for agent_type."""
    result = asyncio.run(
        spawner.spawn(agent_type="researcher", task="string type test")
    )
    assert result.success
    assert result.agent_type == "researcher"


# ---------------------------------------------------------------------------
# Depth guard
# ---------------------------------------------------------------------------


def test_max_spawn_depth_blocks_recursive(spawner):
    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "nested task", ticker="CSL", spawn_depth=2)
    )
    assert not result.success
    assert "depth" in result.error.lower()


def test_spawn_depth_1_is_blocked(spawner):
    """depth=1 is the first sub-level — must be blocked to prevent recursive spawning."""
    result = asyncio.run(
        spawner.spawn(SubAgentType.AUDITOR, "sub-task", spawn_depth=1)
    )
    assert not result.success
    assert "depth" in result.error.lower()


def test_spawn_depth_0_is_allowed(spawner):
    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "top-level task", spawn_depth=0)
    )
    assert result.success


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


def test_spawn_respects_timeout():
    slow_llm = make_mock_llm(delay=10.0)  # 10-second response
    slow_spawner = SubAgentSpawner(llm_client=slow_llm, timeout_seconds=0.1)
    result = asyncio.run(
        slow_spawner.spawn(SubAgentType.RESEARCHER, "slow task")
    )
    assert not result.success
    assert "timeout" in result.error.lower()


# ---------------------------------------------------------------------------
# Memory store integration
# ---------------------------------------------------------------------------


def test_spawn_writes_to_memory_when_provided(tmp_path):
    from cockpit.core.agent.memory.store import MemoryStore
    store = MemoryStore(root=tmp_path)
    llm = make_mock_llm(response="BHP revenue is $55B")
    spawner = SubAgentSpawner(llm_client=llm, memory_store=store)

    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "research BHP", ticker="BHP")
    )
    assert result.success
    content = store.read_research("BHP")
    assert content  # something was written


def test_spawn_without_memory_does_not_raise(spawner):
    """No memory_store — must succeed without writing anything."""
    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "no memory test", ticker="CBA")
    )
    assert result.success


def test_spawn_with_memory_no_ticker_does_not_write(tmp_path):
    """memory_store given but no ticker — must not write (no place to store it)."""
    from cockpit.core.agent.memory.store import MemoryStore
    store = MemoryStore(root=tmp_path)
    llm = make_mock_llm(response="some finding")
    spawner = SubAgentSpawner(llm_client=llm, memory_store=store)

    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "task without ticker")
    )
    assert result.success
    # No tickers should have been written
    assert store.list_research_tickers() == []


# ---------------------------------------------------------------------------
# Concurrency guard
# ---------------------------------------------------------------------------


def test_spawner_has_semaphore_attribute():
    llm = make_mock_llm()
    spawner = SubAgentSpawner(llm_client=llm, max_concurrent_local=1)
    assert spawner._semaphore is not None


def test_custom_concurrency_limit():
    llm = make_mock_llm()
    spawner = SubAgentSpawner(llm_client=llm, max_concurrent_local=2)
    # Semaphore with value 2 — just verify construction doesn't raise
    assert spawner._semaphore is not None


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------


def test_build_system_prompt_researcher():
    llm = make_mock_llm()
    spawner = SubAgentSpawner(llm_client=llm)
    prompt = spawner._build_system_prompt("researcher")
    assert "research" in prompt.lower() or "analyst" in prompt.lower() or "financ" in prompt.lower()


def test_build_system_prompt_auditor():
    llm = make_mock_llm()
    spawner = SubAgentSpawner(llm_client=llm)
    prompt = spawner._build_system_prompt("auditor")
    assert "audit" in prompt.lower() or "verify" in prompt.lower() or "check" in prompt.lower()


def test_build_system_prompt_unknown_falls_back():
    llm = make_mock_llm()
    spawner = SubAgentSpawner(llm_client=llm)
    prompt = spawner._build_system_prompt("unknown_type")
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# ---------------------------------------------------------------------------
# LLM failure handling
# ---------------------------------------------------------------------------


def test_spawn_returns_failure_on_llm_error():
    failing_llm = MagicMock()
    failing_llm.model = "test-model"
    failing_llm.chat.side_effect = RuntimeError("llama.cpp connection refused")

    spawner = SubAgentSpawner(llm_client=failing_llm)
    result = asyncio.run(
        spawner.spawn(SubAgentType.RESEARCHER, "task that will fail")
    )
    assert not result.success
    assert result.error is not None
    assert len(result.error) > 0
