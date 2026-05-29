from __future__ import annotations

import threading
from types import SimpleNamespace

from app.services.cockpit_service import CockpitService
from cockpit.core.chat import ChatResponse
from cockpit.storage.state import StateStore


def _service(tmp_path) -> CockpitService:
    service = CockpitService.__new__(CockpitService)
    service.state_store = StateStore(str(tmp_path / "state.db"))
    service._feedback_lock = threading.Lock()
    service._recent_turn_diagnostics = {}
    service.llm_client = SimpleNamespace(model="")
    service._resolve_thread_id = lambda session_id: session_id or "global-main"
    return service


def _seed_prior_tool_turn(service: CockpitService, thread_id: str = "session-1") -> None:
    service._recent_turn_diagnostics[thread_id] = [
        {
            "request": {"message": "compare the hydrogen names"},
            "response_text": "Compared HZR, FHE and PRL.",
            "evidence": [
                {
                    "tool": "screen_tickers",
                    "arguments": {"tickers": ["HZR", "FHE", "PRL"]},
                    "result": {"ok": True, "results": [{"ticker": "HZR"}]},
                },
                {
                    "tool": "tv_screener",
                    "arguments": {"market": "australia"},
                    "result": {"ok": True, "market": "australia", "results": []},
                },
                {
                    "tool": "query_ticker_data",
                    "arguments": {"ticker": "HZR"},
                    "result": {"ok": True, "ticker": "HZR", "docs": [{}]},
                },
                {
                    "tool": "get_price",
                    "arguments": {"ticker": "HZR"},
                    "result": {
                        "ok": True,
                        "ticker": "HZR",
                        "price": {"recent_history": [{"close": 1.0}]},
                    },
                },
            ],
            "tool_traces": [
                {"tool": "screen_tickers", "ok": True},
                {"tool": "tv_screener", "ok": True},
                {"tool": "query_ticker_data", "ok": True},
                {"tool": "get_price", "ok": True},
            ],
        }
    ]


def test_chat_stream_answers_why_question_from_prior_tool_trace(tmp_path) -> None:
    service = _service(tmp_path)
    _seed_prior_tool_turn(service)

    response = service.chat_stream(
        "why didnt it work for your compare run",
        session_id="session-1",
    )

    assert "did use tools" in response.text
    assert "TradingView screener returned no rows for australia." in response.text
    assert "query_ticker_data" in response.text
    assert "get_price" in response.text
    assert response.routing_metadata["continuity_turn"] == "previous_tool_trace_question"
    messages = service.state_store.get_chat_messages("session-1")
    assert messages[-2]["content"] == "why didnt it work for your compare run"
    assert messages[-1]["role"] == "assistant"


def test_chat_stream_correction_does_not_route_data_as_ticker(tmp_path) -> None:
    service = _service(tmp_path)
    _seed_prior_tool_turn(service)

    response = service.chat_stream("no you did do that DATA", session_id="session-1")

    assert response.text.startswith("You're right.")
    assert response.action_preview is None
    assert response.routing_metadata["continuity_turn"] == "correction_turn"
    assert "DATA" not in response.routing_metadata.get("referenced_tool_names", [])


def test_chat_stream_rewrites_compare_them_when_referents_are_clear(tmp_path) -> None:
    service = _service(tmp_path)
    service.state_store.add_chat_message(
        "session-compare",
        "assistant",
        "ASX hydrogen companies discussed: HZR, FHE, PRL.",
        "2026-05-04T00:00:00+00:00",
    )
    captured: dict[str, str] = {}

    class FakeController:
        def build_chat_response(self, **kwargs):
            captured["message"] = kwargs["message"]
            return ChatResponse(
                text="comparison done",
                evidence=[],
                routing_metadata={"source": "cockpit"},
            )

    service._build_chat_controller = lambda thread_id, **_kwargs: FakeController()

    response = service.chat_stream("compare them", session_id="session-compare")

    assert response.text == "comparison done"
    assert "Compare HZR, FHE, PRL" in captured["message"]
    assert response.routing_metadata["resolved_referent_tickers"] == ["HZR", "FHE", "PRL"]


def test_chat_stream_save_thesis_note_returns_confirmation_gated_proposal(tmp_path) -> None:
    service = _service(tmp_path)
    service._recent_turn_diagnostics["session-thesis"] = [
        {
            "ticker": "BHP",
            "response_text": "BHP copper growth supports a watchlist thesis.",
            "evidence": [],
            "tool_traces": [],
        }
    ]

    response = service.chat_stream(
        "save that as a thesis note",
        session_id="session-thesis",
    )

    assert response.action_preview is not None
    assert response.action_preview["action_id"] == "create_thesis"
    assert response.action_preview["args"]["ticker"] == "BHP"
    assert response.action_preview["requires_confirmation"] is True
    assert response.routing_metadata["memory_write_confirmation_required"] is True
