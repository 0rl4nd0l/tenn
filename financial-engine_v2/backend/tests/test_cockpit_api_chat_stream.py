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
                on_chunk("Recent BHP news ")
                on_chunk("is mixed.")
            if on_status is not None:
                on_status("Resolving request context")
            if on_thinking is not None:
                on_thinking("internal assessment", "internal plan")
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
    chunk_events = [event for event in data_events if event.get("type") == "chunk"]
    assert [event["data"]["text"] for event in chunk_events] == [
        "Recent BHP news ",
        "is mixed.",
    ]
    assert all('{"type"' not in event["data"]["text"] for event in chunk_events)
    assert not [event for event in data_events if event.get("type") == "thinking"]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert (
        done_events[-1]["data"]["text"]
        == "Recent BHP news is mixed, with coverage focused on operations and commodity outlook."
    )


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
                text="Plain response.",
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
        json={"message": "tell me about BHP", "stream": False},
    )

    assert response.status_code == 200
    assert called["used"] is True
    assert response.json()["data"]["text"] == "Plain response."


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
            assert kwargs["flagged_message"]["content"] == "Bad answer"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
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


def test_cockpit_feedback_flag_read_route_returns_flag_payload(monkeypatch) -> None:
    class FakeService:
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
    assert payload["bundle"]["ticker"] == "BHP"


def test_cockpit_feedback_flag_route_supports_good_feedback(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["feedback_type"] == "good"
            return {
                "ok": True,
                "report_id": "good_20260410_abc123",
                "feedback_type": "good",
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
        "evidence": [],
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
    assert scheduled["report_id"] == result["report_id"]
    assert scheduled["analysis_path"] == analysis_path


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
    assert result["report_id"].startswith("good_")
    assert scheduled == {}
