"""Tests for HybridRouter — local/API LLM routing."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from cockpit.core.agent.hybrid_router import HybridRouter, RouterResponse


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.chat.return_value = '{"type": "response", "content": "hello"}'
    return client


def test_router_response_is_dataclass():
    r = RouterResponse(text="hi", source="local", model="qwen", latency_ms=100, cost_usd=0.0, tool_calls=[])
    assert r.text == "hi"
    assert r.source == "local"
    assert r.cost_usd == 0.0


def test_local_route_uses_llm_client(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client)
    result = router.complete([{"role": "user", "content": "hello"}])
    assert result.source == "local"
    assert result.text == '{"type": "response", "content": "hello"}'
    mock_llm_client.chat.assert_called_once()


def test_force_local_ignores_policy(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client, policy="api_preferred")
    result = router.complete([{"role": "user", "content": "hi"}], force_backend="local")
    assert result.source == "local"


def test_api_not_called_without_client(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client, policy="local_only")
    result = router.complete([{"role": "user", "content": "hi"}])
    assert result.source == "local"


def test_cost_tracker_records_call(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client)
    router.complete([{"role": "user", "content": "test"}], role="orchestrator")
    log = router.cost_log()
    assert len(log) == 1
    assert log[0]["source"] == "local"
    assert log[0]["role"] == "orchestrator"


def test_latency_is_positive(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client)
    result = router.complete([{"role": "user", "content": "hi"}])
    assert result.latency_ms >= 0
