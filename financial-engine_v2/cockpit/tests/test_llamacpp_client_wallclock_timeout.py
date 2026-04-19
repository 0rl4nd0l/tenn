"""Regression tests for wall-clock deadline enforcement in LlamaCppClient.

The httpx `read` timeout is a per-read timeout, so a slow-but-streaming backend
can keep a call alive indefinitely by dribbling one chunk per (read_timeout - ε)
seconds. The client must enforce a total wall-clock deadline on top of that so
the agent loop can surface "local model too slow" errors and fall back to the
API backend.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

import pytest

from cockpit.integrations.llamacpp_client import LlamaCppClient


class _FakeStreamResponse:
    """Minimal stand-in for httpx.Response inside a `with client.stream(...)` block."""

    def __init__(self, lines: list[str], *, per_line_sleep: float) -> None:
        self._lines = lines
        self._per_line_sleep = per_line_sleep

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        for line in self._lines:
            time.sleep(self._per_line_sleep)
            yield line


class _FakeHttpClient:
    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    @contextmanager
    def stream(self, *_args, **_kwargs):
        yield self._response


def _chunk_line(text: str) -> str:
    return (
        'data: {"choices":[{"delta":{"content":"' + text + '"},"index":0}]}'
    )


def test_chat_raises_timeout_when_wallclock_deadline_exceeded_during_stream(
    monkeypatch,
) -> None:
    """A slow stream that dribbles tokens within per-read timeout still aborts."""
    client = LlamaCppClient("http://127.0.0.1:8001", "model:test")
    monkeypatch.setattr(client, "_resolve_model_id", lambda name: name)
    monkeypatch.setattr(client, "_log_model_resolution", lambda *a, **k: None)

    # Each chunk takes 0.25s; ten chunks → 2.5s total; deadline is 0.5s.
    lines = [_chunk_line(f"tok{i}") for i in range(10)] + ["data: [DONE]"]
    response = _FakeStreamResponse(lines, per_line_sleep=0.25)
    fake_http = _FakeHttpClient(response)
    monkeypatch.setattr(client, "_http_client", lambda: fake_http)

    with pytest.raises(TimeoutError) as exc_info:
        client.chat(prompt="hello", timeout=0.5)

    assert "wall-clock timeout" in str(exc_info.value)
    assert "0s" in str(exc_info.value) or "1s" in str(exc_info.value)


def test_chat_returns_when_stream_completes_before_deadline(monkeypatch) -> None:
    """Happy path: a fast stream returns concatenated text without tripping the deadline."""
    client = LlamaCppClient("http://127.0.0.1:8001", "model:test")
    monkeypatch.setattr(client, "_resolve_model_id", lambda name: name)
    monkeypatch.setattr(client, "_log_model_resolution", lambda *a, **k: None)

    lines = [_chunk_line("hello "), _chunk_line("world"), "data: [DONE]"]
    response = _FakeStreamResponse(lines, per_line_sleep=0.0)
    fake_http = _FakeHttpClient(response)
    monkeypatch.setattr(client, "_http_client", lambda: fake_http)

    text = client.chat(prompt="hi", timeout=5.0)
    assert text == "hello world"
