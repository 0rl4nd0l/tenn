"""Regression tests for HybridRouter's wall-clock watchdog.

Background
----------
``LlamaCppClient`` already enforces a wall-clock deadline inside the streaming
loop, but that check only fires *after* ``iter_lines()`` yields a line. If
llama.cpp blocks before the first byte arrives (a realistic failure mode on
slow hardware like Tesla M40), or if tokens dribble in just fast enough to
keep resetting the per-read timeout, the caller can wait indefinitely.

``HybridRouter._run_with_wall_clock_watchdog`` closes that gap: it runs the
backend call in a daemon thread and hard-fails with ``TimeoutError`` after the
wall-clock budget expires, regardless of what the inner httpx client is doing.
The orphan thread is left to unwind on its own (its httpx session will hit its
own connect/read timeout eventually).
"""

from __future__ import annotations

import threading
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


class TestWallClockWatchdogRaisesOnHang:
    """When the inner call ignores its timeout, the watchdog still fires."""

    def test_pre_first_byte_hang_raises_timeout(
        self, mock_local_client: MagicMock
    ) -> None:
        """Simulate httpx blocking in ``read`` before any token arrives.

        The inner client sleeps well past the router's timeout. Without the
        watchdog, the caller would wait the full sleep duration. With it, we
        must get TimeoutError within ~timeout seconds.
        """
        stop = threading.Event()

        def _hang_pretending_no_bytes(*_args, **_kwargs) -> str:
            # The inner client would normally raise its own TimeoutError when
            # the per-read deadline expires. We simulate the *broken* case
            # where it never does — e.g. httpx blocked inside the TLS/connect
            # handshake, never yielding to the streaming loop's deadline check.
            stop.wait(timeout=5.0)
            return "never-returned"

        mock_local_client.chat.side_effect = _hang_pretending_no_bytes
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        t0 = time.monotonic()
        with pytest.raises(TimeoutError) as excinfo:
            router.chat(prompt="hi", timeout=0.2)
        elapsed = time.monotonic() - t0

        stop.set()  # release the worker so it doesn't linger across tests
        assert 0.2 <= elapsed < 1.5, f"watchdog fired too late: {elapsed:.2f}s"
        assert "watchdog expired" in str(excinfo.value).lower()

    def test_watchdog_timeout_triggers_api_fallback(
        self,
        mock_local_client: MagicMock,
        mock_api_client: MagicMock,
    ) -> None:
        """Watchdog-raised TimeoutError must be caught by the fallback path."""
        stop = threading.Event()

        def _hang(*_args, **_kwargs) -> str:
            stop.wait(timeout=5.0)
            return "never-returned"

        mock_local_client.chat.side_effect = _hang
        router = HybridRouter(
            llm_client=mock_local_client,
            api_client=mock_api_client,
            policy="local_preferred",
        )

        try:
            text = router.chat(prompt="hi", timeout=0.2)
        finally:
            stop.set()

        assert text == "api-response"
        mock_api_client.chat.assert_called_once()
        log = router.cost_log()
        assert log[-1]["source"] == "api"
        assert "fallback_api_after_local_failure" in log[-1]["routing_reason"]
        assert "TimeoutError" in log[-1]["routing_reason"]

    def test_watchdog_emits_status_before_raising(
        self, mock_local_client: MagicMock
    ) -> None:
        """Operators need visibility when the watchdog fires."""
        stop = threading.Event()

        def _hang(*_args, **_kwargs) -> str:
            stop.wait(timeout=5.0)
            return "never-returned"

        mock_local_client.chat.side_effect = _hang
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        statuses: list[str] = []
        try:
            with pytest.raises(TimeoutError):
                router.chat(prompt="hi", timeout=0.2, on_status=statuses.append)
        finally:
            stop.set()

        assert any("watchdog expired" in s.lower() for s in statuses), (
            f"expected watchdog status, got: {statuses}"
        )


class TestWallClockWatchdogPassThrough:
    """Fast calls and native exceptions must behave exactly as before."""

    def test_fast_call_returns_value(self, mock_local_client: MagicMock) -> None:
        """The watchdog must not penalise the happy path."""
        mock_local_client.chat.return_value = "ok"
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        t0 = time.monotonic()
        text = router.chat(prompt="hi", timeout=2.0)
        elapsed = time.monotonic() - t0

        assert text == "ok"
        assert elapsed < 0.5, f"watchdog added significant overhead: {elapsed:.2f}s"

    def test_inner_timeout_error_propagates_unchanged(
        self, mock_local_client: MagicMock
    ) -> None:
        """A genuine TimeoutError from the inner client still surfaces.

        The watchdog must not swallow or re-wrap inner exceptions — otherwise
        debuggability and existing fallback logic (which matches on the inner
        error's message) would break.
        """
        inner = TimeoutError("llama.cpp wall-clock timeout (60s) exceeded")
        mock_local_client.chat.side_effect = inner
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        with pytest.raises(TimeoutError) as excinfo:
            router.chat(prompt="hi", timeout=2.0)

        # The message must be the inner one, not the watchdog's "expired" string.
        assert "llama.cpp wall-clock timeout" in str(excinfo.value)
        assert "watchdog expired" not in str(excinfo.value).lower()

    def test_inner_runtime_error_propagates_unchanged(
        self, mock_local_client: MagicMock
    ) -> None:
        inner = RuntimeError("connection refused")
        mock_local_client.chat.side_effect = inner
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        with pytest.raises(RuntimeError) as excinfo:
            router.chat(prompt="hi", timeout=2.0)
        assert "connection refused" in str(excinfo.value)

    def test_inner_value_error_is_not_caught(
        self, mock_local_client: MagicMock
    ) -> None:
        """Only TimeoutError/RuntimeError get the fallback; others propagate."""
        mock_local_client.chat.side_effect = ValueError("bad arg")
        router = HybridRouter(llm_client=mock_local_client, policy="local_only")

        with pytest.raises(ValueError):
            router.chat(prompt="hi", timeout=2.0)


class TestWallClockWatchdogAppliesToApiBackend:
    """The watchdog also wraps API calls — a wedged API is just as bad."""

    def test_api_hang_raises_timeout(self, mock_api_client: MagicMock) -> None:
        stop = threading.Event()

        def _hang(*_args, **_kwargs) -> str:
            stop.wait(timeout=5.0)
            return "never"

        mock_api_client.chat.side_effect = _hang
        # local_only would never pick API; use api_only so the watchdog applies
        # to the API path directly.
        router = HybridRouter(api_client=mock_api_client, policy="api_only")

        try:
            with pytest.raises(TimeoutError):
                router.chat(prompt="hi", timeout=0.2)
        finally:
            stop.set()
