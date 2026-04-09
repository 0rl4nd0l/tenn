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


def test_cockpit_chat_stream_done_event_carries_canonical_final_text(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
        ):
            if on_chunk is not None:
                on_chunk('{"query":"BHP","ticker":"BHP","limit":5}')
            if on_status is not None:
                on_status("Resolving request context")
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

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

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


def test_cockpit_feedback_flag_route_returns_saved_artifact_info(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["session_id"] == "session-123"
            assert kwargs["ticker"] == "BHP"
            assert kwargs["flagged_message"]["content"] == "Bad answer"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "analysis_summary": "The answer appears to have ignored the retrieved evidence.",
            }

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flag",
        json={
            "session_id": "session-123",
            "ticker": "BHP",
            "flagged_message": {
                "id": "assistant-1",
                "role": "assistant",
                "content": "Bad answer",
            },
            "transcript": [
                {"id": "user-1", "role": "user", "content": "Tell me about BHP"},
                {"id": "assistant-1", "role": "assistant", "content": "Bad answer"},
            ],
            "frontend_context": {"source": "cockpit-ui-chat"},
        },
    )

    assert response.status_code == 200
    assert response.json()["report_id"] == "flag_20260409_abc123"
