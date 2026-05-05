from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from cockpit.core.chat import ChatController, ResponseMode, _build_attached_source_bundle


def _write_staged_source(tmp_path: Path, source_id: str, texts: list[str]) -> None:
    rows = [
        {
            "payload": {
                "source_id": source_id,
                "source_name": "Marketplace Listing",
                "source_type": "market_commentary",
                "published_at": "2026-04-18T10:00:00Z",
                "text": text,
            }
        }
        for text in texts
    ]
    (tmp_path / f"{source_id}.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows),
        encoding="utf-8",
    )


def test_keyword_chat_inlines_attached_source_context(tmp_path, monkeypatch) -> None:
    source_id = "market_commentary:listing:abc123"
    _write_staged_source(
        tmp_path,
        source_id,
        [
            "Title: 2018 Excavator",
            "Price: $28,000",
            "Location: Melbourne VIC",
        ],
    )
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    monkeypatch.setattr("cockpit.core.chat.record_turn", lambda *args, **kwargs: None)

    old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
    os.environ["COCKPIT_AGENT_MODE"] = "keyword"
    try:
        controller = ChatController(
            ollama_client=MagicMock(),
            tool_router=MagicMock(),
            action_registry=MagicMock(),
        )
        controller.tool_router.gather_local_context.return_value = SimpleNamespace(
            payload={
                "ticker": None,
                "docs": [],
                "doc_snippets": [],
                "financials": [],
                "price": {},
                "price_state": {},
                "sources": {},
            }
        )
        controller.ollama_client.chat.return_value = "The listing is priced at $28,000."

        response = controller.build_chat_response(
            "What stands out about this listing?",
            attached_sources=[{"source_id": source_id, "source_kind": "concat"}],
        )
    finally:
        if old_agent_mode is None:
            os.environ.pop("COCKPIT_AGENT_MODE", None)
        else:
            os.environ["COCKPIT_AGENT_MODE"] = old_agent_mode

    prompt = controller.ollama_client.chat.call_args.args[0]
    assert "Attached source evidence provided by the user" in prompt
    assert "2018 Excavator" in prompt
    assert any(item["type"] == "attached_source" for item in response.evidence)


def test_agent_loop_receives_attached_source_context(tmp_path, monkeypatch) -> None:
    source_id = "market_commentary:listing:def456"
    _write_staged_source(
        tmp_path,
        source_id,
        [
            "Title: Utility Trailer",
            "Price: $5,500",
            "Seller: Seller A",
        ],
    )
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    monkeypatch.setattr(
        "cockpit.core.chat.get_session_context",
        lambda *args, **kwargs: [],
    )

    captured: dict[str, str] = {}

    class _FakeAgentLoop:
        def run(self, message, **kwargs):
            captured["message"] = message
            return SimpleNamespace(
                text="Agent answer.",
                evidence=[],
                action_preview=None,
                mode="fast",
                routing_metadata=None,
                tool_traces=[],
            )

    controller = ChatController.__new__(ChatController)
    controller.last_ticker = None
    controller._state_store = None
    controller._thread_id = "global-main"
    controller._memory = None
    controller._strategy_service = None
    controller._ov_session_id = "session-1"
    controller._hybrid_router = None
    controller._agent_loop = _FakeAgentLoop()
    controller._recent_youtube_video_options = []
    controller._record_answer_side_effects = lambda **kwargs: None  # type: ignore[method-assign]
    controller._set_latest_sources_payloads = lambda evidence: None  # type: ignore[method-assign]
    controller._recent_conversation_history = lambda: []  # type: ignore[method-assign]

    bundle = _build_attached_source_bundle(
        [{"source_id": source_id, "source_kind": "concat"}]
    )
    response = controller._run_agent_loop(
        "Compare this listing with dealer pricing.",
        enable_web=False,
        prior_ticker=None,
        on_chunk=None,
        on_status=None,
        analysis_mode=None,
        attached_bundle=bundle,
    )

    assert "Attached source evidence provided by the user" in captured["message"]
    assert "Utility Trailer" in captured["message"]
    assert any(item["type"] == "attached_source" for item in response.evidence)


def test_missing_attached_source_context_shortcircuits_before_llm(
    tmp_path, monkeypatch
) -> None:
    source_id = "youtube_transcript:missing:abc123"
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    monkeypatch.setattr("cockpit.core.chat.record_turn", lambda *args, **kwargs: None)

    old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
    os.environ["COCKPIT_AGENT_MODE"] = "keyword"
    try:
        controller = ChatController(
            ollama_client=MagicMock(),
            tool_router=MagicMock(),
            action_registry=MagicMock(),
        )

        response = controller.build_chat_response(
            "tell me about the video",
            attached_sources=[{"source_id": source_id, "source_kind": "ephemeral"}],
        )
    finally:
        if old_agent_mode is None:
            os.environ.pop("COCKPIT_AGENT_MODE", None)
        else:
            os.environ["COCKPIT_AGENT_MODE"] = old_agent_mode

    assert response.mode == ResponseMode.FAST
    assert "transcript or chunk text is not available" in response.text
    controller.ollama_client.chat.assert_not_called()
    controller.tool_router.gather_local_context.assert_not_called()


def test_ultra_short_prompt_shortcircuits_before_llm(monkeypatch) -> None:
    monkeypatch.setattr("cockpit.core.chat.record_turn", lambda *args, **kwargs: None)

    old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
    os.environ["COCKPIT_AGENT_MODE"] = "keyword"
    try:
        controller = ChatController(
            ollama_client=MagicMock(),
            tool_router=MagicMock(),
            action_registry=MagicMock(),
        )

        response = controller.build_chat_response("s")
    finally:
        if old_agent_mode is None:
            os.environ.pop("COCKPIT_AGENT_MODE", None)
        else:
            os.environ["COCKPIT_AGENT_MODE"] = old_agent_mode

    assert response.mode == ResponseMode.FAST
    assert "Please enter a clearer question" in response.text
    controller.ollama_client.chat.assert_not_called()
    controller.tool_router.gather_local_context.assert_not_called()
