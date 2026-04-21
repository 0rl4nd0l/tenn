from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService


def test_cockpit_chat_stream_emits_only_status_plain_text_chunks_and_done(
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
            on_thinking=None,
            **kwargs,
        ):
            if on_chunk is not None:
                on_chunk("Hello ")
                on_chunk("there.")
            if on_status is not None:
                on_status("Resolving request context")
            if on_thinking is not None:
                on_thinking("internal assessment", "internal plan")
            return SimpleNamespace(
                text="Hello there.",
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
        json={"message": "hello", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chunk_events = [event for event in data_events if event.get("type") == "chunk"]
    assert [event["data"]["text"] for event in chunk_events] == [
        "Hello ",
        "there.",
    ]
    assert all('{"type"' not in event["data"]["text"] for event in chunk_events)
    assert not [event for event in data_events if event.get("type") == "thinking"]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"]["text"] == "Hello there."


def test_cockpit_chat_stream_blocks_substantive_answer_without_sources(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="BHP revenue grew sharply and broker sentiment improved.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
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
        json={"message": "tell me about BHP", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"]["text"].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_allows_good_morning_without_sources(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Good morning. How can I help?",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
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
        json={"message": "good morning", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == "Good morning. How can I help?"


def test_cockpit_chat_stream_allows_market_update_command_phrase_without_sources(
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
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No market-update reports found.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 111,
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
        json={"message": "market update today?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == "No market-update reports found."
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_emits_sources_when_evidence_is_renderable(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="BHP news is mixed.",
                evidence=[
                    {
                        "tool": "search_news",
                        "result": {
                            "hits": [
                                {
                                    "title": "BHP update",
                                    "url": "https://example.com/bhp-update",
                                    "published_at": "2026-04-16T07:00:00Z",
                                    "snippet": "BHP released an update.",
                                }
                            ]
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
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
    source_events = [event for event in data_events if event.get("type") == "sources"]
    assert source_events
    items = source_events[-1]["data"]["items"]
    assert items[0]["url"] == "https://example.com/bhp-update"


def test_cockpit_chat_stream_tv_screener_evidence_satisfies_source_contract(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Top movers include BHP and RIO today.",
                evidence=[
                    {
                        "tool": "tv_screener",
                        "result": {
                            "market": "australia",
                            "results": [
                                {
                                    "symbol": "ASX:BHP",
                                    "change_percent": 2.4,
                                    "close": 45.2,
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 121,
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
        json={"message": "what are some market movers today", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events
    assert done_events[-1]["data"]["text"] == "Top movers include BHP and RIO today."
    assert source_events
    assert source_events[-1]["data"]["items"][0]["source_id"] == "tv_screener:AUSTRALIA:ASX:BHP"


def test_cockpit_chat_stream_done_event_preserves_model_metadata(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No evidence available.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:qwen3.5-35b-a3b",
                    "latency_ms": 0,
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
        json={"message": "tell me about BHP", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]

    assert done_events[-1]["data"]["model"] == "model:qwen3.5-35b-a3b"


def test_cockpit_chat_non_stream_uses_to_thread(monkeypatch) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:gpt-oss-20b",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                },
                tool_traces=[],
            )

    called: dict[str, object] = {"used": False, "kwargs": None}

    async def _fake_to_thread(func, /, *args, **kwargs):
        called["used"] = True
        called["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "hello", "stream": False},
    )

    assert response.status_code == 200
    assert called["used"] is True
    assert response.json()["data"]["text"] == "Hello there."


def test_cockpit_chat_forwards_attached_sources(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def chat_stream(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:gpt-oss-20b",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "hello",
            "stream": False,
            "attached_sources": [{"source_id": "src-1", "source_kind": "concat"}],
        },
    )

    assert response.status_code == 200
    assert captured["attached_sources"] == [
        {"source_id": "src-1", "source_kind": "concat"}
    ]


def test_cockpit_chat_stream_emits_filestats_chart_event(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Company Data Dump: BHP\nSummary\n- Docs: 1",
                evidence=[
                    {
                        "type": "company_dump",
                        "details": {
                            "ticker": "BHP",
                            "backend": {
                                "ticker": "BHP",
                                "summary": {"doc_count": 1, "price_points_1y": 1},
                                "docs": [
                                    {
                                        "document_id": "doc-1",
                                        "published_at": "2026-04-09",
                                        "doc_class": "quarterly",
                                        "title": "Quarterly",
                                    }
                                ],
                                "financials": [],
                                "risk_notes": [],
                                "price_history_1y": [
                                    {
                                        "timestamp": "2026-04-09T00:00:00Z",
                                        "close": 55.2,
                                    }
                                ],
                                "extraction_failures": [],
                                "low_confidence_financials": [],
                                "company_memory": {"entries": []},
                                "market_memory": {"items": []},
                            },
                            "cockpit_local_memory": {},
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
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
        json={"message": "bhp filestats", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chart_events = [event for event in data_events if event.get("type") == "chart"]
    assert chart_events, body
    assert chart_events[-1]["data"]["title"].startswith("BHP filestats")
    assert "Filestats Dashboard" in chart_events[-1]["data"]["html"]

    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"].get("chart") is not None


def test_cockpit_feedback_flag_route_returns_saved_artifact_info(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["session_id"] == "session-123"
            assert kwargs["ticker"] == "BHP"
            assert kwargs["feedback_type"] == "poor"
            assert kwargs["capture_kind"] == "chat_feedback"
            assert kwargs["flagged_message"]["content"] == "Bad answer"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "codex_prompt": "Investigate this flagged cockpit response and fix the underlying bug.\n\nFlag ID: flag_20260409_abc123\nRead API: /api/cockpit/feedback/flags/flag_20260409_abc123",
                "analysis_summary": "The answer appears to have ignored the retrieved evidence.",
            }

        def list_flagged_reports(self, limit):
            assert limit == 5
            return [
                {
                    "report_id": "flag_20260409_abc123",
                    "feedback_type": "poor",
                    "session_id": "session-123",
                    "ticker": "BHP",
                    "saved_at": "2026-04-09T07:31:00Z",
                    "note": "Missed cited evidence",
                    "flagged_response_excerpt": "Bad answer",
                    "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                }
            ]

        def get_flagged_report(self, report_id):
            assert report_id == "flag_20260409_abc123"
            return {
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "bundle": {"report_id": "flag_20260409_abc123"},
                "summary_markdown": "# Flagged Cockpit Chat",
                "analysis": {"summary": "Ignored evidence"},
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
    payload = response.json()
    assert payload["ok"] is True
    assert payload["report_id"] == "flag_20260409_abc123"
    assert payload["feedback_type"] == "poor"
    assert payload["capture_kind"] == "chat_feedback"
    assert (
        payload["read_api_path"] == "/api/cockpit/feedback/flags/flag_20260409_abc123"
    )
    assert "Flag ID: flag_20260409_abc123" in payload["codex_prompt"]
    assert "/api/cockpit/feedback/flags/flag_20260409_abc123" in payload["codex_prompt"]
    assert (
        payload["analysis_summary"]
        == "The answer appears to have ignored the retrieved evidence."
    )


def test_cockpit_feedback_flag_list_route_returns_recent_flags(monkeypatch) -> None:
    class FakeService:
        def list_flagged_reports(self, limit):
            assert limit == 5
            return [
                {
                    "report_id": "flag_20260409_abc123",
                    "feedback_type": "poor",
                    "capture_kind": "chat_feedback",
                    "session_id": "session-123",
                    "ticker": "BHP",
                    "saved_at": "2026-04-09T07:31:00Z",
                    "note": "Missed cited evidence",
                    "flagged_response_excerpt": "Bad answer",
                    "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                }
            ]

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/feedback/flags?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["report_id"] == "flag_20260409_abc123"
    assert payload["items"][0]["feedback_type"] == "poor"
    assert payload["items"][0]["capture_kind"] == "chat_feedback"


def test_cockpit_feedback_flag_read_route_returns_flag_payload(monkeypatch) -> None:
    class FakeService:
        def get_flagged_report(self, report_id):
            assert report_id == "flag_20260409_abc123"
            return {
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "bundle": {"report_id": "flag_20260409_abc123", "ticker": "BHP"},
                "summary_markdown": "# Flagged Cockpit Chat",
                "analysis": {"summary": "Ignored evidence"},
            }

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/feedback/flags/flag_20260409_abc123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "flag_20260409_abc123"
    assert payload["feedback_type"] == "poor"
    assert payload["capture_kind"] == "chat_feedback"
    assert payload["bundle"]["ticker"] == "BHP"


def test_cockpit_feedback_flag_route_supports_good_feedback(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["feedback_type"] == "good"
            assert kwargs["capture_kind"] == "chat_feedback"
            return {
                "ok": True,
                "report_id": "good_20260410_abc123",
                "feedback_type": "good",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/good_20260410_abc123",
                "codex_prompt": "Review this positively rated cockpit response and capture what worked well.",
                "analysis_summary": None,
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
            "feedback_type": "good",
            "flagged_message": {
                "id": "assistant-1",
                "role": "assistant",
                "content": "Strong answer",
            },
            "transcript": [
                {"id": "user-1", "role": "user", "content": "Tell me about BHP"},
                {"id": "assistant-1", "role": "assistant", "content": "Strong answer"},
            ],
            "frontend_context": {"source": "cockpit-ui-chat"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "good_20260410_abc123"
    assert payload["feedback_type"] == "good"
    assert payload["capture_kind"] == "chat_feedback"


def test_cockpit_feedback_flag_route_supports_ui_issue_capture(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["feedback_type"] == "poor"
            assert kwargs["capture_kind"] == "ui_issue"
            assert kwargs["flagged_message"]["content"] == "Toolbar button overlaps status bar"
            assert kwargs["screenshot"]["filename"] == "ui-screenshot.png"
            return {
                "ok": True,
                "report_id": "ui_issue_20260415_deadbeef",
                "feedback_type": "poor",
                "capture_kind": "ui_issue",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/ui_issue_20260415_deadbeef",
                "codex_prompt": "Investigate this cockpit UI issue and implement the minimal safe fix.",
                "analysis_summary": None,
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
            "capture_kind": "ui_issue",
            "note": "Happens after resizing the window",
            "flagged_message": {
                "id": "ui-issue-1",
                "role": "system",
                "content": "Toolbar button overlaps status bar",
            },
            "frontend_context": {"source": "cockpit-ui-issue-capture", "pathname": "/verification"},
            "screenshot": {
                "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p0NvwAAAABJRU5ErkJggg==",
                "mime_type": "image/png",
                "filename": "ui-screenshot.png",
                "width": 1,
                "height": 1,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "ui_issue_20260415_deadbeef"
    assert payload["capture_kind"] == "ui_issue"


def test_flag_chat_feedback_persists_before_background_analysis(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )

    def _resolve_thread_id(session_id):
        return session_id or "global-main"

    service._resolve_thread_id = _resolve_thread_id
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {
        "request": {"message": "bhp 7 day price summary"},
        "routing_metadata": {"model": "model:test"},
        "response_mode": "deep_analysis",
        "prompt": "system prompt excerpt",
        "evidence": [
            {
                "tool": "query_ticker_data",
                "arguments": {"ticker": "BHP"},
                "result": {"ok": True},
            }
        ],
        "tool_traces": [
            {
                "iteration": 2,
                "ok": True,
                "duration_ms": 42.5,
            }
        ],
    }

    scheduled: dict[str, object] = {}

    def _schedule_flagged_report_analysis(**kwargs):
        scheduled.update(kwargs)

    service._schedule_flagged_report_analysis = _schedule_flagged_report_analysis

    result = service.flag_chat_feedback(
        session_id="session-1",
        ticker="BHP",
        feedback_type="poor",
        note="Unsupported claim",
        flagged_message={
            "id": "assistant-1",
            "role": "assistant",
            "content": "Bad answer",
        },
        transcript=[
            {"id": "user-1", "role": "user", "content": "bhp 7 day price summary"}
        ],
        frontend_context={"source": "cockpit-ui-chat"},
    )

    assert result["analysis_summary"] is None
    assert result["analysis_path"].endswith("analysis.json")
    bundle_path = Path(result["bundle_path"])
    summary_path = Path(result["summary_path"])
    analysis_path = Path(result["analysis_path"])
    assert bundle_path.exists()
    assert summary_path.exists()
    assert not analysis_path.exists()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["feedback_type"] == "poor"
    assert bundle["note"] == "Unsupported claim"
    assert bundle["backend_turn"]["response_mode"] == "deep_analysis"
    assert bundle["backend_turn"]["response_prompt"] == "system prompt excerpt"
    assert bundle["backend_turn"]["tool_calls"][0]["tool"] == "query_ticker_data"
    assert bundle["backend_turn"]["tool_calls"][0]["iteration"] == 2
    assert bundle["backend_turn"]["tool_calls"][0]["duration_ms"] == 42.5
    assert scheduled["report_id"] == result["report_id"]
    assert scheduled["analysis_path"] == analysis_path


def test_cockpit_workspace_root_env_overrides_flagged_reports_root(
    tmp_path, monkeypatch
) -> None:
    """COCKPIT_WORKSPACE_ROOT env var must route flagged reports to the workspace volume."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("COCKPIT_WORKSPACE_ROOT", str(workspace))

    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path / "app"  # simulates /app inside Docker
    (service.repo_root).mkdir()
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._resolve_thread_id = lambda sid: sid or "global-main"
    service._resolve_turn_diagnostics = lambda tid, fm: {}
    service._schedule_flagged_report_analysis = lambda **kw: None

    result = service.flag_chat_feedback(
        session_id="env-test",
        ticker="TST",
        feedback_type="poor",
        flagged_message={"id": "a1", "role": "assistant", "content": "bad"},
    )

    bundle_path = Path(result["bundle_path"])
    assert bundle_path.exists()
    # Must be under workspace, not under repo_root (/app)
    assert str(workspace) in str(bundle_path)
    assert str(service.repo_root) not in str(bundle_path)
    flagged_root = workspace / "reports" / "cockpit" / "flagged_sessions"
    assert flagged_root.exists()


def test_good_chat_feedback_persists_without_background_analysis(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )

    def _resolve_thread_id(session_id):
        return session_id or "global-main"

    service._resolve_thread_id = _resolve_thread_id
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {
        "request": {"message": "tell me about bhp"},
        "routing_metadata": {"model": "model:test"},
        "response_mode": "fast",
        "prompt": "good prompt excerpt",
        "evidence": [],
    }

    scheduled: dict[str, object] = {}

    def _schedule_flagged_report_analysis(**kwargs):
        scheduled.update(kwargs)

    service._schedule_flagged_report_analysis = _schedule_flagged_report_analysis

    result = service.flag_chat_feedback(
        session_id="session-1",
        ticker="BHP",
        feedback_type="good",
        note="Well grounded and concise",
        flagged_message={
            "id": "assistant-1",
            "role": "assistant",
            "content": "Strong answer",
        },
        transcript=[{"id": "user-1", "role": "user", "content": "tell me about bhp"}],
        frontend_context={"source": "cockpit-ui-chat"},
    )

    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert result["feedback_type"] == "good"
    assert bundle["feedback_type"] == "good"
    assert bundle["backend_turn"]["response_mode"] == "fast"
    assert bundle["backend_turn"]["response_prompt"] == "good prompt excerpt"
    assert result["report_id"].startswith("good_")
    assert scheduled == {}


def test_ui_issue_capture_persists_screenshot_artifact(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._resolve_thread_id = lambda session_id: session_id or "global-main"
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {}
    scheduled: dict[str, object] = {}
    service._schedule_flagged_report_analysis = lambda **kwargs: scheduled.update(kwargs)

    result = service.flag_chat_feedback(
        session_id="session-ui",
        ticker="BHP",
        feedback_type="poor",
        capture_kind="ui_issue",
        note="Toolbar overlap after resize",
        flagged_message={
            "id": "ui-issue-1",
            "role": "system",
            "content": "Toolbar button overlaps status bar",
        },
        frontend_context={
            "source": "cockpit-ui-issue-capture",
            "pathname": "/verification",
            "debug_bundle": {
                "console": [{"level": "error", "message": "boom"}],
                "network": [{"url": "/api/cockpit/health", "status": 200}],
            },
        },
        screenshot={
            "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p0NvwAAAABJRU5ErkJggg==",
            "mime_type": "image/png",
            "filename": "ui-screenshot.png",
            "width": 1,
            "height": 1,
            "captured_at": "2026-04-15T07:31:00Z",
        },
    )

    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert result["capture_kind"] == "ui_issue"
    assert result["report_id"].startswith("ui_issue_")
    assert scheduled == {}
    assert bundle["capture_kind"] == "ui_issue"
    assert bundle["attachments"][0]["kind"] == "screenshot"
    assert bundle["attachments"][0]["relative_path"] == "ui-screenshot.png"
    assert bundle["attachments"][1]["kind"] == "browser_debug"
    assert bundle["attachments"][1]["relative_path"] == "browser-debug.json"
    assert "data_url" not in json.dumps(bundle)
    assert "debug_bundle" not in json.dumps(bundle)
    screenshot_path = Path(bundle["attachments"][0]["absolute_path"])
    assert screenshot_path.exists()
    assert screenshot_path.read_bytes().startswith(b"\x89PNG")
    debug_path = Path(bundle["attachments"][1]["absolute_path"])
    assert debug_path.exists()
    debug_bundle = json.loads(debug_path.read_text(encoding="utf-8"))
    assert debug_bundle["console"][0]["message"] == "boom"
    summary = Path(result["summary_path"]).read_text(encoding="utf-8")
    assert "# Cockpit UI Issue" in summary
    assert "ui-screenshot.png" in summary
    assert "browser-debug.json" in summary
