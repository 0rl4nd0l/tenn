"""Tests for HybridRouter — local/API LLM routing."""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from cockpit.core.agent.hybrid_router import HybridRouter, RouterResponse


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.chat.return_value = '{"type": "response", "content": "hello"}'
    client.model = "test-model"
    return client


def test_router_response_is_dataclass():
    r = RouterResponse(
        text="hi",
        source="local",
        model="qwen",
        latency_ms=100,
        cost_usd=0.0,
        tool_calls=[],
    )
    assert r.text == "hi"
    assert r.source == "local"
    assert r.cost_usd == 0.0


def test_local_route_uses_llm_client(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client)
    result = router.complete([{"role": "user", "content": "hello"}])
    assert result.source == "local"
    assert result.text == '{"type": "response", "content": "hello"}'
    mock_llm_client.chat.assert_called_once()


def test_local_route_reports_resolved_client_model(mock_llm_client):
    def _chat(*args, **kwargs):
        mock_llm_client.model = "model:qwen3.5-35b-a3b-apex"
        return "resolved response"

    mock_llm_client.model = "local"
    mock_llm_client.chat.side_effect = _chat
    router = HybridRouter(llm_client=mock_llm_client, policy="local_only")

    result = router.complete([{"role": "user", "content": "hello"}])

    assert result.source == "local"
    assert result.model == "model:qwen3.5-35b-a3b-apex"
    assert router.cost_log()[-1]["model"] == "model:qwen3.5-35b-a3b-apex"


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
    assert log[0]["routing_reason"] == "policy:api_preferred_fallback_local"


def test_latency_is_positive(mock_llm_client):
    router = HybridRouter(llm_client=mock_llm_client)
    result = router.complete([{"role": "user", "content": "hi"}])
    assert result.latency_ms >= 0


# ---------------------------------------------------------------------------
# Extraction-aware routing tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api_client():
    client = MagicMock(spec=["chat", "model"])
    client.chat.return_value = "api response"
    client.model = "claude-sonnet"
    return client


class TestExtractionAwareRouting:
    """HybridRouter routes chat to API when GPU extraction is active."""

    def test_preview_route_reports_api_when_extraction_active(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=lambda: True,
        )

        assert router.preview_route() == {
            "source": "api",
            "model": "claude-sonnet",
            "routing_reason": "extraction_active",
        }

    def test_routes_to_api_when_extraction_active(
        self, mock_llm_client, mock_api_client
    ):
        statuses: list[str] = []
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=lambda: True,
        )
        result = router.complete(
            [{"role": "user", "content": "hi"}],
            on_status=statuses.append,
        )
        assert result.source == "api"
        assert router.cost_log()[-1]["routing_reason"] == "extraction_active"
        assert any("routing chat to API" in msg for msg in statuses)
        mock_api_client.chat.assert_called_once()
        mock_llm_client.chat.assert_not_called()

    def test_routes_to_local_when_extraction_inactive(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=lambda: False,
        )
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result.source == "local"
        assert router.cost_log()[-1]["routing_reason"] == "policy:local_preferred"

    def test_extraction_override_beats_local_only_policy(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_only",
            extraction_active_fn=lambda: True,
        )
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result.source == "api"
        mock_api_client.chat.assert_called_once()
        mock_llm_client.chat.assert_not_called()

    def test_no_api_client_blocks_local_chat_during_extraction(self, mock_llm_client):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=None,
            policy="local_preferred",
            extraction_active_fn=lambda: True,
        )
        with pytest.raises(
            RuntimeError,
            match="Extraction active on shared llama.cpp and no API client is configured",
        ):
            router.complete([{"role": "user", "content": "hi"}])

        mock_llm_client.chat.assert_not_called()

    def test_force_backend_overrides_extraction_check(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=lambda: True,
        )
        result = router.complete(
            [{"role": "user", "content": "hi"}], force_backend="local"
        )
        assert result.source == "local"
        assert router.cost_log()[-1]["routing_reason"] == "force:local"

    def test_extraction_fn_exception_falls_through(
        self, mock_llm_client, mock_api_client
    ):
        def broken_checker():
            raise ConnectionError("Redis down")

        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=broken_checker,
        )
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result.source == "local"

    def test_no_extraction_fn_uses_normal_policy(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=None,
        )
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result.source == "local"

    def test_chat_interface_respects_extraction_active(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            extraction_active_fn=lambda: True,
        )
        text = router.chat(prompt="hello", timeout=10.0)
        assert text == "api response"
        mock_api_client.chat.assert_called_once()


class TestGpuExclusiveRouting:
    def test_routes_to_api_when_gpu_exclusive_activity_active(
        self, mock_llm_client, mock_api_client
    ):
        statuses: list[str] = []
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            gpu_exclusive_active_fn=lambda: True,
        )

        result = router.complete(
            [{"role": "user", "content": "hi"}],
            on_status=statuses.append,
        )

        assert result.source == "api"
        assert router.cost_log()[-1]["routing_reason"] == "gpu_exclusive_active"
        assert any("routing chat to API" in msg for msg in statuses)
        mock_api_client.chat.assert_called_once()
        mock_llm_client.chat.assert_not_called()

    def test_no_api_client_blocks_local_chat_during_gpu_exclusive_activity(
        self, mock_llm_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=None,
            policy="local_preferred",
            gpu_exclusive_active_fn=lambda: True,
        )

        with pytest.raises(
            RuntimeError,
            match="GPU-exclusive activity active and no API client is configured",
        ):
            router.complete([{"role": "user", "content": "hi"}])

        mock_llm_client.chat.assert_not_called()

    def test_gpu_exclusive_activity_overrides_force_local(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            gpu_exclusive_active_fn=lambda: True,
        )

        result = router.complete(
            [{"role": "user", "content": "hi"}], force_backend="local"
        )

        assert result.source == "api"
        assert router.cost_log()[-1]["routing_reason"] == "gpu_exclusive_active"
        mock_api_client.chat.assert_called_once()
        mock_llm_client.chat.assert_not_called()


class TestGpuPreemptionRouting:
    def test_routes_to_api_when_gpu_preemption_detected(
        self, mock_llm_client, mock_api_client
    ):
        statuses: list[str] = []
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_preferred",
            gpu_preemption_fn=lambda: "higher_priority_gpu_process_present",
        )

        result = router.complete(
            [{"role": "user", "content": "hi"}],
            on_status=statuses.append,
        )

        assert result.source == "api"
        assert router.cost_log()[-1]["routing_reason"] == "gpu_preempted"
        assert any("routing chat to API" in msg for msg in statuses)
        mock_api_client.chat.assert_called_once()
        mock_llm_client.chat.assert_not_called()

    def test_local_only_still_respects_explicit_local_policy(
        self, mock_llm_client, mock_api_client
    ):
        router = HybridRouter(
            llm_client=mock_llm_client,
            api_client=mock_api_client,
            policy="local_only",
            gpu_preemption_fn=lambda: "higher_priority_gpu_process_present",
        )

        result = router.complete([{"role": "user", "content": "hi"}])

        assert result.source == "local"
        mock_llm_client.chat.assert_called_once()
        mock_api_client.chat.assert_not_called()


def test_last_attempt_metadata_is_preserved_on_failed_api_call(mock_llm_client):
    class _FailingApiClient:
        model = "claude-sonnet"

        def chat(self, prompt, timeout=120.0, prior_messages=None, on_chunk=None):
            raise RuntimeError("Error code: 529 - overloaded")

    router = HybridRouter(
        llm_client=mock_llm_client,
        api_client=_FailingApiClient(),
        policy="api_only",
    )

    with pytest.raises(RuntimeError, match="529"):
        router.complete([{"role": "user", "content": "hi"}])

    assert router.cost_log() == []
    assert router.last_attempt_metadata() == {
        "source": "api",
        "model": "claude-sonnet",
        "latency_ms": 0,
        "cost_usd": 0.0,
        "routing_reason": "policy:api_only",
    }
