"""Regression test for SSE keepalive in the cockpit chat stream.

Background
----------
When the local LLM generates silently for minutes (no on_chunk / on_status
ticks reach the queue), intermediate proxies can drop an idle SSE
connection, and the UI cannot distinguish a live-but-quiet stream from a
dead one. The generator emits ``: keepalive\\n\\n`` comments every
``SSE_KEEPALIVE_INTERVAL_SECONDS`` so the connection remains visibly alive
and proxies keep it open.

The interval is exposed as a module-level constant so this test can shrink
it to a sub-second value and observe the behaviour quickly.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService


def test_chat_stream_emits_sse_keepalive_during_silent_worker(
    monkeypatch,
) -> None:
    """A worker that stalls past the keepalive interval must produce ``: keepalive``."""

    # Shrink keepalive to 0.1s so we observe at least one comment in the
    # ~0.6s window the slow service takes to complete.
    monkeypatch.setattr(cockpit_api, "SSE_KEEPALIVE_INTERVAL_SECONDS", 0.1)
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)

    worker_started = threading.Event()

    class SlowService:
        def chat_stream(self, *args, **kwargs) -> SimpleNamespace:
            worker_started.set()
            # Real sleep — this runs inside ``asyncio.to_thread`` so the
            # event-generator loop keeps polling the empty queue and trips
            # the keepalive branch.
            time.sleep(0.6)
            return SimpleNamespace(
                text="done",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "test",
                    "latency_ms": 1,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: SlowService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        headers={"X-API-Key": "local-secret"},
        json={"message": "stall please", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert worker_started.is_set(), "Worker never ran — test setup broken"
    assert ": keepalive" in body, (
        "Expected at least one SSE keepalive comment, but the response body was:\n"
        f"{body!r}"
    )
    # Happy-path sanity: stream still terminates cleanly with a done event
    # and the ``event: end`` marker.
    assert "event: end" in body
    assert '"type": "done"' in body


def test_chat_stream_keepalive_not_emitted_when_worker_is_fast(
    monkeypatch,
) -> None:
    """A fast worker never trips the keepalive branch (no noise in normal flow)."""

    # Keep the default large interval; the fast worker finishes well inside it.
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)

    class FastService:
        def chat_stream(self, *args, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                text="done",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "test",
                    "latency_ms": 1,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FastService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        headers={"X-API-Key": "local-secret"},
        json={"message": "quick", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert ": keepalive" not in body
    assert "event: end" in body
