from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from cockpit.core.agent_loop import AgentLoop
from cockpit.core.command_router import route_command
from cockpit.core.query_intent import QueryIntent, classify_intent
from cockpit.core.turn_continuity import (
    ContinuityTurnKind,
    build_previous_tool_trace_response,
    build_thesis_save_response,
    classify_continuity_turn,
    resolve_compare_referents,
)
from shared.ticker_inference import detect_primary_ticker


def _prior_tool_turn() -> dict:
    return {
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
                "result": {"ok": True, "ticker": "HZR", "docs": [{}], "financials": []},
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
    }


def test_meta_question_uses_prior_tool_trace_no_rows() -> None:
    response = build_previous_tool_trace_response(
        message="why didnt it work for your compare run",
        latest_turn=_prior_tool_turn(),
    )

    assert response.routing_metadata["continuity_turn"] == "previous_tool_trace_question"
    assert "did use tools" in response.text
    assert "screen_tickers, tv_screener, query_ticker_data, get_price" in response.text
    assert "TradingView screener returned no rows for australia." in response.text
    assert "not proof that the whole analysis failed" in response.text


def test_correction_turn_acknowledges_prior_tool_use() -> None:
    response = build_previous_tool_trace_response(
        message="no you did do that",
        latest_turn=_prior_tool_turn(),
        correction=True,
    )

    assert response.text.startswith("You're right.")
    assert "did use tools" in response.text
    assert "ticker=DATA" not in response.text


def test_compare_them_resolves_last_discussed_ticker_set() -> None:
    resolution = resolve_compare_referents(
        message="compare them",
        latest_turn=None,
        recent_messages=[
            {
                "role": "assistant",
                "content": "ASX hydrogen companies discussed: HZR, FHE, PRL.",
            }
        ],
    )

    assert resolution.matched is True
    assert resolution.resolved_tickers == ["HZR", "FHE", "PRL"]
    assert "Compare HZR, FHE, PRL" in str(resolution.rewritten_message)


def test_compare_it_to_explicit_ticker_resolves_previous_referent() -> None:
    resolution = resolve_compare_referents(
        message="compare it to RIO",
        latest_turn={
            "ticker": "BHP",
            "response_text": "BHP iron ore margins were the current topic.",
        },
        recent_messages=[],
    )

    assert resolution.matched is True
    assert resolution.resolved_tickers == ["BHP", "RIO"]
    assert "Compare BHP, RIO" in str(resolution.rewritten_message)


def test_company_why_question_does_not_become_meta_turn() -> None:
    assert classify_continuity_turn("why did BHP fall today") is None
    assert classify_intent("why did BHP fall today") == QueryIntent.TICKER_SPECIFIC


def test_save_that_as_thesis_note_builds_confirmation_gated_action() -> None:
    response = build_thesis_save_response(
        message="save that as a thesis note",
        latest_turn={
            "ticker": "BHP",
            "response_text": "BHP copper growth supports a watchlist thesis.",
        },
        recent_messages=[],
    )

    assert response is not None
    assert response.action_preview is not None
    assert response.action_preview["action_id"] == "create_thesis"
    assert response.action_preview["args"]["ticker"] == "BHP"
    assert response.action_preview["args"]["thesis"].startswith("BHP copper growth")
    assert response.action_preview["requires_confirmation"] is True


def test_common_nouns_do_not_become_tickers_in_meta_or_save_contexts() -> None:
    assert classify_continuity_turn("no you did use DATA") == ContinuityTurnKind.CORRECTION_TURN
    assert classify_intent("no you did use DATA") == QueryIntent.CORRECTION_TURN
    assert classify_intent("save that as a thesis NOTE") == QueryIntent.THESIS_SAVE
    assert detect_primary_ticker("save that as a thesis NOTE") is None
    assert route_command("ingest data").matched is False
    assert route_command("ingest notes").matched is False


def test_direct_tv_screener_no_rows_distinguishes_no_result() -> None:
    text = AgentLoop._format_direct_command_tool_result(
        SimpleNamespace(tool="tv_screener", arguments={}),
        {"ok": True, "market": "australia", "results": []},
    )

    assert "TradingView screener returned no rows for AUSTRALIA" in text
    assert "not an overall analysis failure" in text


def test_unsupported_financial_claim_blocking_still_works() -> None:
    llm = MagicMock()
    llm.chat.side_effect = [
        '{"type":"response","content":"BHP revenue was $55bn."}',
        '{"type":"response","content":"BHP revenue was $55bn."}',
    ]
    loop = AgentLoop(llm_client=llm, tool_executor=MagicMock())

    result = loop.run("What is BHP revenue?", ticker="BHP")

    assert "I need to look that up before I can answer reliably." in result.text
    assert "$55bn" not in result.text
    assert result.routing_metadata["grounding_guard"] == "unsupported_financial_claim"
