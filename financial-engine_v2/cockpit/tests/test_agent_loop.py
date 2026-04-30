"""Regression tests for AgentLoop hardening (2026-04-14 silent-failure audit).

Covers three defences already present in the implementation:
1. tool_calls entries missing 'id' key — _normalize_tool_calls uses .get() with defaults
2. tool executor returning a non-dict — _execute_tool wraps it into {"result": value}
3. thinking steps with null assessment/plan — null-coerced to "" before on_thinking callback

Plus:
4. Two tool calls with differently shaped results both survive in AgentResult.evidence
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from cockpit.core.agent_loop import AgentLoop


def _make_llm(responses: list[str]) -> MagicMock:
    client = MagicMock()
    client.model = "test-model"
    client.chat.side_effect = list(responses)
    return client


class TestAgentLoopRegressions:
    def test_tool_calls_missing_id_key(self):
        """tool_calls entries without 'id' don't raise KeyError; loop completes normally.

        _normalize_tool_calls uses .get("tool", "unknown") / .get("arguments") so
        the 'id' field is irrelevant — it was never accessed.
        """
        responses = [
            json.dumps({"type": "thinking", "assessment": "need data", "plan": "call tools"}),
            # Deliberately omit the 'id' field that the format doc shows as optional
            json.dumps(
                {
                    "type": "tool_calls",
                    "calls": [{"tool": "search_news", "arguments": {"query": "BHP"}}],
                }
            ),
            json.dumps({"type": "response", "content": "Search complete."}),
            "Search complete.",  # synthesis pass
        ]
        executor = MagicMock(return_value={"hits": [{"title": "BHP news"}]})
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("Tell me about BHP")

        assert result is not None
        assert result.tool_calls_made == 1

    def test_direct_tv_indicator_command_formats_values(self):
        text = AgentLoop._format_direct_command_tool_result(
            SimpleNamespace(tool="get_tv_indicators", arguments={}),
            {
                "ok": True,
                "ticker": "CBA",
                "exchange": "ASX",
                "indicators": {"RSI": 58.2},
            },
        )

        assert text == "ASX:CBA indicators: RSI: 58.2"

    def test_direct_tv_screener_market_movers_formats_rows(self):
        text = AgentLoop._format_direct_command_tool_result(
            SimpleNamespace(tool="tv_screener", arguments={}),
            {
                "ok": True,
                "market": "australia",
                "mode": "market_movers",
                "results": [
                    {
                        "symbol": "ASX:AAA",
                        "name": "Alpha Ltd",
                        "change": 12.5,
                        "close": 0.18,
                        "volume": 1200000,
                        "mover_side": "gainer",
                    },
                    {
                        "symbol": "ASX:CCC",
                        "change": -9.5,
                        "close": 0.04,
                        "mover_side": "decliner",
                    },
                ],
            },
        )

        assert "ASX market movers from TradingView screener:" in text
        assert "ASX:AAA - Alpha Ltd | change +12.50% | close 0.18" in text
        assert "volume 1.2M | gainer" in text
        assert "ASX:CCC | change -9.50% | close 0.04 | decliner" in text

    def test_tool_result_non_dict(self):
        """Tool executor returning a plain string is wrapped into {"result": value}.

        _execute_tool coerces non-dict returns so evidence.append never sees a
        bare string or list — the loop continues and the evidence entry is present.
        """
        responses = [
            json.dumps({"type": "thinking", "assessment": "check news", "plan": "call tool"}),
            json.dumps({"type": "tool_call", "tool": "some_tool", "arguments": {}}),
            json.dumps({"type": "response", "content": "Got it."}),
            "Got it.",  # synthesis
        ]
        executor = MagicMock(return_value="plain string result")
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("Query something")

        assert result is not None
        assert result.tool_calls_made == 1
        assert len(result.evidence) == 1
        assert result.evidence[0]["result"] == {"result": "plain string result"}

    def test_on_thinking_none_fields(self):
        """Thinking step with null assessment and plan calls on_thinking with empty strings.

        Lines 324-325 in agent_loop.py:
            assessment = parsed.assessment or parsed.content or ""
            plan = parsed.plan or ""
        JSON null → Python None → falsy → coerced to "".
        """
        responses = [
            json.dumps({"type": "thinking", "assessment": None, "plan": None}),
            json.dumps({"type": "response", "content": "Hello."}),
            # No evidence → no synthesis call
        ]
        thinking_calls: list[tuple[str, str]] = []

        def on_thinking_spy(assessment: str, plan: str) -> None:
            thinking_calls.append((assessment, plan))

        loop = AgentLoop(llm_client=_make_llm(responses))
        result = loop.run("Hi", on_thinking=on_thinking_spy)

        assert result is not None
        assert len(thinking_calls) == 1
        assessment, plan = thinking_calls[0]
        assert assessment == ""
        assert plan == ""

    def test_evidence_collects_from_mixed_formats(self):
        """Two tools returning differently shaped results both appear in AgentResult.evidence.

        The agent loop always wraps results in {tool, arguments, result} regardless of
        what shape the result dict takes — both entries survive to the final AgentResult.
        """
        responses = [
            json.dumps(
                {"type": "thinking", "assessment": "need two sources", "plan": "call both"}
            ),
            json.dumps(
                {
                    "type": "tool_calls",
                    "calls": [
                        {"tool": "search_news", "arguments": {"query": "ASX"}},
                        {"tool": "gather_local_context", "arguments": {"query": "ASX"}},
                    ],
                }
            ),
            json.dumps({"type": "response", "content": "Done."}),
            "Done.",  # synthesis
        ]

        def executor(tool_name: str, arguments: dict) -> dict:
            # search_news returns an "orchestrator-format" shaped result
            if tool_name == "search_news":
                return {"type": "local_context", "details": {"hits": []}}
            # gather_local_context returns the flatter agent-loop format
            return {"hits": [{"title": "doc 1"}]}

        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("What's happening on ASX?")

        assert result is not None
        assert len(result.evidence) == 2
        tools_in_evidence = {e["tool"] for e in result.evidence}
        assert tools_in_evidence == {"search_news", "gather_local_context"}

    def test_followup_news_explanation_requires_current_turn_tooling(self):
        """News/event follow-ups must not answer directly from prior session text alone."""
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "The user wants more detail on earlier broker upgrades.",
                    "plan": "I can explain them.",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "Ampol was upgraded because margins improved.",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_news",
                    "arguments": {"query": "broker upgrades today"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "The available news only lists broker upgrades and downgrades; it does not verify company-specific catalysts.",
                }
            ),
        ]
        executor = MagicMock(
            return_value={
                "hits": [
                    {
                        "title": "Broker moves round-up",
                        "published_at": "2026-04-16T07:00:00Z",
                        "url": "https://example.com/broker-moves",
                    }
                ]
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run(
            "explain the upgrades",
            conversation_history=[
                {
                    "role": "assistant",
                    "content": "Upgrades included ALD, IRE, ABB, and MIN.",
                }
            ],
        )

        assert result is not None
        assert result.tool_calls_made == 1
        assert result.evidence[0]["tool"] == "search_news"
        executor.assert_called_once_with(
            "search_news",
            {"query": "broker upgrades today"},
        )
        assert "does not verify company-specific catalysts" in result.text

    def test_substantive_financial_question_requires_current_turn_tooling(self):
        """Direct substantive answers without current-turn evidence must be redirected into tooling."""
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "The user wants BHP revenue.",
                    "plan": "I can answer directly.",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP revenue was $55bn.",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "BHP"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "I found current financials for BHP and can answer from them.",
                }
            ),
        ]
        executor = MagicMock(return_value={"financials": [{"ticker": "BHP", "revenue": 55_000_000_000}]})
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("What is BHP revenue?", ticker="BHP")

        assert result is not None
        assert result.tool_calls_made == 1
        executor.assert_called_once_with("get_financials", {"ticker": "BHP"})
        assert "I found current financials" in result.text

    def test_direct_price_lookup_executes_tool_without_forced_thinking(self):
        """Ticker price lookups should execute get_price even if the model starts with tool_call."""
        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_price",
                    "arguments": {"ticker": "FGR"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "FGR last close is A$1.23.",
                }
            ),
            "FGR last close is A$1.23.",
        ]
        executor = MagicMock(
            return_value={
                "ok": True,
                "ticker": "FGR",
                "price": {"current": {"close": 1.23}},
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("fgr price")

        assert result is not None
        assert result.tool_calls_made == 1
        assert result.iterations_used == 2
        executor.assert_called_once_with("get_price", {"ticker": "FGR"})
        assert "FGR last close is A$1.23." in result.text

    def test_watch_youtube_channel_command_executes_direct_tool(self):
        executor = MagicMock(
            return_value={
                "ok": True,
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": False,
            }
        )
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("watch youtube channel Kneppy Invests")

        assert result is not None
        assert result.mode == "command"
        assert result.action_preview is None
        assert result.tool_calls_made == 1
        assert result.evidence[0]["tool"] == "watch_youtube_channel"
        assert "Added YouTube channel Kneppy Invests (UCabc123)" in result.text
        executor.assert_called_once_with(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        llm.chat.assert_not_called()

    def test_watch_youtube_channel_command_reports_tool_failure(self):
        executor = MagicMock(
            return_value={"ok": False, "error": "backend API client not configured"}
        )
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("watch youtube channel Kneppy Invests")

        assert result is not None
        assert result.action_preview is None
        assert "backend API client not configured" in result.text
        executor.assert_called_once_with(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        llm.chat.assert_not_called()

    def test_check_youtube_channel_recent_videos_command_executes_direct_tool(self):
        executor = MagicMock(
            return_value={
                "ok": True,
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "videos": [
                    {
                        "title": "BHP quarterly results breakdown",
                        "published_at": "2026-04-28T00:00:00Z",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123",
                        "duration_seconds": 1200,
                        "scores": {"overall": 0.91},
                    }
                ],
            }
        )
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("check youtube channel Kneppy Invests")

        assert result is not None
        assert result.mode == "command"
        assert result.tool_calls_made == 1
        assert "Recent videos from Kneppy Invests (UCabc123)" in result.text
        assert "BHP quarterly results breakdown" in result.text
        assert "Reply with the video URL" in result.text
        executor.assert_called_once_with(
            "check_youtube_channel_recent_videos",
            {"channel_name": "Kneppy Invests", "limit": 8},
        )
        llm.chat.assert_not_called()

    def test_action_command_still_returns_confirmation_preview(self):
        executor = MagicMock()
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("ingest BHP news")

        assert result is not None
        assert result.mode == "command"
        assert result.action_preview is not None
        assert result.action_preview["action_id"] == "daily_news_ingest"
        assert result.action_preview["args"]["tickers"] == "BHP"
        executor.assert_not_called()
        llm.chat.assert_not_called()

    def test_cloud_prefix_forces_grounding_even_when_query_classifier_is_weak(self):
        """`/cloud` turns must call a grounding tool before a substantive answer is accepted."""
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "The user wants an update on BHP.",
                    "plan": "I can answer directly.",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP reported strong results this quarter.",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "BHP"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "I checked current-turn financial data before answering.",
                }
            ),
        ]
        executor = MagicMock(
            return_value={"financials": [{"ticker": "BHP", "period_end": "2025-12-31"}]}
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("/cloud BHP update")

        assert result is not None
        assert result.tool_calls_made == 1
        executor.assert_called_once_with("get_financials", {"ticker": "BHP"})

    def test_cloud_prefix_rejects_non_grounding_tool_evidence(self):
        """`/cloud` turns must not treat unrelated tools as sufficient grounding evidence."""
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "Need context quickly.",
                    "plan": "I will scan local files first.",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_files",
                    "arguments": {"pattern": "bhp"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP reported strong results this quarter.",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP shares rallied on the announcement.",
                }
            ),
        ]
        executor = MagicMock(return_value={"matches": [{"path": "reports/bhp.txt"}]})
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("/cloud BHP update")

        assert result is not None
        assert result.tool_calls_made == 1
        executor.assert_called_once_with("search_files", {"pattern": "bhp"})
        assert "I need to look that up before I can answer reliably." in result.text

    def test_time_sensitive_market_update_rejects_stale_news_evidence(self):
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "Need latest movers",
                    "plan": "Fetch market news first",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_news",
                    "arguments": {"query": "market movers today"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "Top movers today were BHP and RIO.",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP rose 3% today.",
                }
            ),
        ]
        executor = MagicMock(
            return_value={
                "ok": True,
                "hits": [{"title": "Old market wrap", "published_at": "2026-04-10T00:00:00Z"}],
                "freshness_warning": "Most recent article is 5 day(s) old.",
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("market update today")

        assert result is not None
        assert result.tool_calls_made == 1
        assert "I need to look that up before I can answer reliably." in result.text

    def test_data_insufficient_news_is_not_grounding_evidence(self):
        assert not AgentLoop._has_grounding_evidence(
            [
                {
                    "tool": "search_news",
                    "result": {
                        "ok": False,
                        "data_insufficient": True,
                        "hits": [{"title": "Old market wrap"}],
                    },
                }
            ]
        )

    def test_news_evidence_summary_preserves_freshness_warning(self):
        summary = AgentLoop._summarize_evidence(
            [
                {
                    "tool": "search_news",
                    "result": {
                        "ok": False,
                        "data_insufficient": True,
                        "hits": [{"title": "Old market wrap"}],
                        "freshness_warning": "Most recent article is 5 day(s) old.",
                        "suggestion": "Only historical news was returned.",
                    },
                }
            ]
        )

        assert "freshness_warning=Most recent article is 5 day(s) old." in summary
        assert "data_insufficient=true" in summary
        assert "Only historical news was returned." in summary

    def test_time_sensitive_market_update_accepts_fresh_news_evidence(self):
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        responses = [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "Need current mover context",
                    "plan": "Use search_news then answer",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_news",
                    "arguments": {"query": "market movers today"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "Today's movers include BHP and RIO based on current-turn news hits.",
                }
            ),
        ]
        executor = MagicMock(
            return_value={
                "ok": True,
                "hits": [{"title": "ASX movers update", "published_at": now_iso}],
                "freshness_warning": "",
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("market update today")

        assert result is not None
        assert result.tool_calls_made == 1
        assert "current-turn news hits" in result.text

    def test_evidence_summary_does_not_surface_internal_truncation_metadata(self):
        summary = AgentLoop._summarize_evidence(
            [
                {
                    "tool": "query_ticker_data",
                    "result": {
                        "tool": "query_ticker_data",
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 71_178,
                        "ticker": "PLS",
                        "price": {
                            "symbol": "PLS.AX",
                            "current": {
                                "price": 5.945,
                                "previous_close": 6.11,
                                "change_percent": -2.7,
                            },
                        },
                        "docs": [
                            {
                                "title": "PLS - March 2026 Quarterly Activities Report advisory",
                                "published_at": "2026-04-02T00:00:00Z",
                            }
                        ],
                        "financials": [],
                    },
                }
            ]
        )

        assert "_truncated" not in summary
        assert "_original_chars" not in summary
        assert "financial_rows=0" in summary
        assert "previous_close=6.11" in summary
