from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService


def test_cockpit_chat_stream_done_event_carries_canonical_final_text(monkeypatch) -> None:
    class FakeService:
        def chat_stream(self, message: str, ticker: str | None = None, session_id: str | None = None, on_chunk=None):
            if on_chunk is not None:
                on_chunk('{"query":"BHP","ticker":"BHP","limit":5}')
            return SimpleNamespace(
                text="Recent BHP news is mixed, with coverage focused on operations and commodity outlook.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 1234,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(CockpitService, "get_instance", classmethod(lambda cls: FakeService()))

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "bhp news", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert (
        done_events[-1]["data"]["text"]
        == "Recent BHP news is mixed, with coverage focused on operations and commodity outlook."
    )
