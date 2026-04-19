"""Regression tests for HybridRouter resilience features.

These cover two companion behaviours introduced alongside the wall-clock
deadline fix in ``LlamaCppClient``:

1. **API fallback on local timeout / runtime error** — if the local backend
   raises ``TimeoutError`` or ``RuntimeError`` and an API client is
   available, the router transparently retries on API instead of bubbling
   the failure to the caller. This keeps the cockpit UI responsive when
   the local model hangs on slow hardware.

2. **Periodic ``on_status`` ticks during local generation** — the agent
   loop's first reasoning pass intentionally does not surface chunks to
   the UI (it needs a clean JSON blob for parsing). Without an explicit
   progress tick, a multi-minute silent pass looks frozen. The router
   wraps ``on_chunk`` so each token chunk drives a throttled ``on_status``
   call, producing visible "generating: N chunks / Xs" updates.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cockpit.core.agent.hybrid_router import HybridRouter


@pytest.fixture
def mock_local_client() -> MagicMock:
    client = MagicMock(spec=["chat", "model"])
    client.model = "local-test"
    return client


@pytest.fixture
def mock_api_client() -> MagicMock:
    client = MagicMock(spec=["chat", "model"])
    client.model = "api-test"
    client.chat.return_value = "api-response"
    return client


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


class TestLocalFailureFallsBackToApi:
    """When local backend fails, router retries on API backend."""

    def test_timeout_error_triggers_api_fallback(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError(
            "llama.cpp wall-clock timeout (60s) exceeded"
        )
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )

        text = router.chat(prompt="hi", timeout=1.0)

        assert text == "api-response"
        mock_local_client.chat.assert_called_once()
        mock_api_client.chat.assert_called_once()

    def test_runtime_error_triggers_api_fallback(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = RuntimeError(
            "llama.cpp request error at http://127.0.0.1:8001: connection refused"
        )
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )

        text = router.chat(prompt="hi", timeout=1.0)

        assert text == "api-response"

    def test_fallback_records_routing_reason_in_cost_log(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError("slow")
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )
        router.chat(prompt="hi", timeout=1.0)

        log = router.cost_log()
        assert len(log) == 1
        assert log[0]["source"] == "api"
        assert "fallback_api_after_local_failure" in log[0]["routing_reason"]
        assert "TimeoutError" in log[0]["routing_reason"]

    def test_fallback_emits_status_update(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError("slow")
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )
        statuses: list[str] = []
        router.chat(prompt="hi", timeout=1.0, on_status=statuses.append)

        assert any(
            "retrying on API backend" in s.lower() or "retrying on api" in s.lower()
            for s in statuses
        ), f"Expected fallback status, got: {statuses}"


class TestLocalFailureDoesNotFallbackWhenGuardsApply:
    """Fallback is suppressed when it would be unsafe or contradict intent."""

    def test_force_local_never_falls_back(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError("slow")
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )
        with pytest.raises(TimeoutError):
            router.chat(prompt="hi", timeout=1.0, force_backend="local")
        mock_api_client.chat.assert_not_called()

    def test_no_api_client_raises_original_error(
        self, mock_local_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError("slow")
        router = HybridRouter(llm_client=mock_local_client, policy="local_preferred")
        with pytest.raises(TimeoutError):
            router.chat(prompt="hi", timeout=1.0)

    def test_local_only_policy_does_not_fall_back(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        mock_local_client.chat.side_effect = TimeoutError("slow")
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_only",
        )
        with pytest.raises(TimeoutError):
            router.chat(prompt="hi", timeout=1.0)
        mock_api_client.chat.assert_not_called()

    def test_value_error_is_not_caught(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        """Unexpected error types should propagate — only Timeout/Runtime fall back."""
        mock_local_client.chat.side_effect = ValueError("bad argument")
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )
        with pytest.raises(ValueError):
            router.chat(prompt="hi", timeout=1.0)
        mock_api_client.chat.assert_not_called()


# ---------------------------------------------------------------------------
# Progress-wrap behaviour
# ---------------------------------------------------------------------------


class TestWrapChunkProgress:
    """``_wrap_chunk_progress`` surfaces silent local generation as ticks."""

    def test_returns_original_for_api_backend(
        self, mock_local_client: MagicMock, mock_api_client: MagicMock
    ) -> None:
        """API backend must not get a wrapper — that would force chat() over complete()."""
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
        )
        sentinel = MagicMock()
        wrapped, _ = router._wrap_chunk_progress(
            on_chunk=sentinel, on_status=lambda _s: None, backend="api"
        )
        assert wrapped is sentinel

    def test_returns_none_when_both_callbacks_none_for_local(
        self, mock_local_client: MagicMock
    ) -> None:
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")
        wrapped, _ = router._wrap_chunk_progress(
            on_chunk=None, on_status=None, backend="local"
        )
        assert wrapped is None

    def test_forwards_chunks_to_original_callback(
        self, mock_local_client: MagicMock
    ) -> None:
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")
        received: list[str] = []
        wrapped, _ = router._wrap_chunk_progress(
            on_chunk=received.append, on_status=lambda _s: None, backend="local"
        )
        assert wrapped is not None
        wrapped("tok-a")
        wrapped("tok-b")
        assert received == ["tok-a", "tok-b"]

    def test_emits_periodic_status_ticks_only_after_threshold(
        self, mock_local_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Status emits at ~3s cadence, not on every chunk (otherwise UI floods)."""
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        fake_now = [1000.0]

        def _now() -> float:
            return fake_now[0]

        # Patch time.monotonic inside the hybrid_router module.
        monkeypatch.setattr(
            "cockpit.core.agent.hybrid_router.time.monotonic", _now
        )

        statuses: list[str] = []
        wrapped, _ = router._wrap_chunk_progress(
            on_chunk=None, on_status=statuses.append, backend="local"
        )
        assert wrapped is not None

        # First chunk arrives at t=1.5s — below 3s threshold, no status yet.
        fake_now[0] = 1001.5
        wrapped("tok")
        assert statuses == []

        # t=1004.0s — above threshold, emit.
        fake_now[0] = 1004.0
        wrapped("tok")
        assert len(statuses) == 1
        assert "2 token chunks" in statuses[0]
        assert "/ 4s" in statuses[0] or "/ 4.0s" in statuses[0]

        # t=1004.5s — too soon since last emit, skip.
        fake_now[0] = 1004.5
        wrapped("tok")
        assert len(statuses) == 1

        # t=1008.0s — another 3.5s since last emit, emit again.
        fake_now[0] = 1008.0
        wrapped("tok")
        assert len(statuses) == 2
        assert "4 token chunks" in statuses[1]


def test_wrap_chunk_progress_integration_with_real_sleep(
    mock_local_client: MagicMock,
) -> None:
    """End-to-end sanity check using real time.monotonic — no monkeypatch."""
    router = HybridRouter(llm_client=mock_local_client, policy="local_only")
    statuses: list[str] = []
    wrapped, _ = router._wrap_chunk_progress(
        on_chunk=None, on_status=statuses.append, backend="local"
    )
    assert wrapped is not None

    # First chunk shouldn't trigger status (< 3s since start).
    wrapped("x")
    assert statuses == []
    # Force a short sleep then another chunk — still under threshold.
    time.sleep(0.05)
    wrapped("x")
    assert statuses == []
