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
from unittest.mock import MagicMock, call

from cockpit.core.agent_loop import AgentLoop
from cockpit.core.query_intent import QueryIntent
from cockpit.core.response_classification import ResponseClassification


def _make_llm(responses: list[str]) -> MagicMock:
    client = MagicMock()
    client.model = "test-model"
    client.chat.side_effect = list(responses)
    return client


class TestAgentLoopRegressions:
    def test_ticker_company_overview_prefetches_ticker_filtered_news(self):
        responses = [
            json.dumps(
                {
                    "type": "response",
                    "content": "A2M recall evidence was found in local news.",
                }
            ),
            "A2M recall evidence was found in local news.",
        ]
        executor = MagicMock(
            return_value={
                "ok": True,
                "ticker": "A2M",
                "hits": [
                    {
                        "title": (
                            "A2 Milk shares plunge after finding toxins in infant formula"
                        ),
                        "snippet": (
                            "A2 Milk recall evidence says infant formula was recalled."
                        ),
                        "published_at": "2026-05-03T22:52:00Z",
                        "url": "https://example.com/a2m-recall",
                        "ticker": "A2M",
                    }
                ],
                "hit_count": 1,
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("tell me about A2M", ticker="A2M")

        assert result is not None
        assert result.evidence[0]["tool"] == "search_news"
        assert result.evidence[0]["result"]["hits"][0]["ticker"] == "A2M"
        assert result.tool_calls_made == 1
        executor.assert_has_calls(
            [
                call(
                    "search_news",
                    {"query": "tell me about A2M", "ticker": "A2M", "limit": 5},
                )
            ]
        )
        assert "recall evidence" in result.text

    def test_ticker_news_prefetch_skips_holdings_questions(self):
        assert (
            AgentLoop._should_prefetch_ticker_news(
                message="tell me about my holdings for A2M",
                ticker="A2M",
                intent=QueryIntent.TICKER_SPECIFIC,
            )
            is False
        )

    def test_no_resolved_ticker_does_not_prefetch_news(self):
        assert (
            AgentLoop._should_prefetch_ticker_news(
                message="Broad market outlook",
                ticker=None,
                intent=QueryIntent.MARKET_WIDE,
            )
            is False
        )

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

    def test_direct_run_analysis_command_formats_module_summary(self):
        text = AgentLoop._format_direct_command_tool_result(
            SimpleNamespace(tool="run_analysis", arguments={}),
            {
                "ok": True,
                "ticker": "BHP",
                "summary_text": "Analysis Summary for BHP",
                "modules": [
                    {
                        "module": "valuation",
                        "status": "complete",
                        "metrics": {"P/E": 12.3},
                        "narrative": "Valuation looks reasonable.",
                    }
                ],
            },
        )

        assert "Analysis Summary for BHP" in text
        assert "valuation: complete; P/E: 12.3" in text
        assert "Valuation looks reasonable." in text

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

    def test_vague_company_request_allows_conversational_clarification(self):
        responses = [
            json.dumps(
                {
                    "type": "response",
                    "content": (
                        "Which company do you mean? I can check financials, "
                        "recent news, or announcements first."
                    ),
                }
            )
        ]
        executor = MagicMock()
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("analyse this company")

        assert result is not None
        assert "Which company do you mean?" in result.text
        assert "$" not in result.text
        assert result.tool_calls_made == 0
        assert result.routing_metadata == {
            "response_classification": (
                ResponseClassification.CONVERSATIONAL_CLARIFICATION.value
            )
        }
        executor.assert_not_called()

    def test_normal_conversational_planning_does_not_require_tool_evidence(self):
        responses = [
            json.dumps(
                {
                    "type": "response",
                    "content": (
                        "We should check financials, recent announcements, price "
                        "context, and data quality next."
                    ),
                }
            )
        ]
        executor = MagicMock()
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("what should we check next?")

        assert result is not None
        assert result.text.startswith("We should check financials")
        assert result.tool_calls_made == 0
        assert result.routing_metadata == {
            "response_classification": ResponseClassification.PLANNING_RESPONSE.value
        }
        executor.assert_not_called()

    def test_unsupported_financial_claim_is_hard_blocked_after_nudge(self):
        responses = [
            json.dumps({"type": "response", "content": "BHP revenue was $55bn."}),
            json.dumps({"type": "response", "content": "BHP revenue was $55bn."}),
        ]
        executor = MagicMock()
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("What is BHP revenue?", ticker="BHP")

        assert result is not None
        assert "I need to look that up before I can answer reliably." in result.text
        assert "$55bn" not in result.text
        assert result.routing_metadata == {
            "response_classification": (
                ResponseClassification.UNSUPPORTED_FINANCIAL_CLAIM.value
            ),
            "grounding_guard": "unsupported_financial_claim",
        }
        executor.assert_not_called()

    def test_missing_financial_rows_proposes_next_read_only_checks_without_numbers(self):
        responses = [
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
                    "content": (
                        "No canonical financial rows were returned. I can check "
                        "data quality or source documents before proposing metric "
                        "extraction."
                    ),
                }
            ),
            (
                "No canonical financial rows were returned. I can check data quality "
                "or source documents before proposing metric extraction."
            ),
        ]
        executor = MagicMock(
            return_value={
                "ok": True,
                "ticker": "BHP",
                "financials": [],
                "data_insufficient": True,
                "suggestion": (
                    "No canonical financial rows were returned. Check data quality "
                    "or source documents before proposing metric extraction or backfill."
                ),
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("What is BHP revenue?", ticker="BHP")

        assert result is not None
        assert result.tool_calls_made == 1
        assert result.evidence[0]["result"]["data_insufficient"] is True
        assert "No canonical financial rows" in result.text
        assert "$" not in result.text
        executor.assert_called_once_with("get_financials", {"ticker": "BHP"})

    def test_degraded_tool_result_is_reflected_in_final_routing_metadata(self):
        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_web",
                    "arguments": {"query": "BHP latest announcement"},
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": (
                        "Web search failed, so I cannot verify current web evidence."
                    ),
                }
            ),
            "Web search failed, so I cannot verify current web evidence.",
        ]
        executor = MagicMock(
            return_value={
                "ok": False,
                "query": "BHP latest announcement",
                "error": "search timed out",
                "evidence_labels": ["degraded_runtime", "operational_trace"],
                "source_coverage_status": "degraded_runtime",
                "runtime_degradation": "search_web_failed",
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("search the web for BHP latest announcement")

        assert result is not None
        assert result.tool_calls_made == 1
        assert result.routing_metadata is not None
        assert result.routing_metadata["system_status"] == "degraded"
        assert result.routing_metadata["runtime_degradation"] == "tool_runtime_failure"
        assert result.routing_metadata["source_coverage_status"] == "degraded_runtime"
        assert "degraded_runtime" in result.routing_metadata["evidence_labels"]
        assert "claim_verified" not in result.routing_metadata["evidence_labels"]

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
        assert "ingest most recent video" in result.text
        executor.assert_called_once_with(
            "check_youtube_channel_recent_videos",
            {"channel_name": "Kneppy Invests", "limit": 8},
        )
        llm.chat.assert_not_called()

    def test_cloud_recent_youtube_followup_uses_channel_context(self):
        executor = MagicMock(
            return_value={
                "ok": True,
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "videos": [
                    {
                        "title": "Latest ASX breakdown",
                        "published_at": "2026-04-29T00:00:00Z",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123def45",
                    }
                ],
            }
        )
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run(
            "/cloud most recent video?",
            recent_youtube_channel="Kneppy Invests",
        )

        assert result is not None
        assert result.mode == "command"
        assert "Recent videos from Kneppy Invests (UCabc123)" in result.text
        assert "Latest ASX breakdown" in result.text
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

    def test_tool_action_proposal_stops_remaining_tool_calls(self):
        responses = [
            json.dumps(
                {
                    "type": "tool_calls",
                    "calls": [
                        {"tool": "run_backfill", "arguments": {"ticker": "PPT", "years": 2}},
                        {
                            "tool": "search_news",
                            "arguments": {"query": "Perpetual Limited PPT"},
                        },
                    ],
                }
            )
        ]
        executor = MagicMock(
            return_value={
                "tool": "run_backfill",
                "ok": True,
                "type": "action_proposal",
                "action_id": "single_ticker_announcement_backfill",
                "action_label": "Single ticker backfill",
                "arguments": {"ticker": "PPT", "years": 2},
                "requires_confirmation": True,
                "is_mutating": True,
                "timeout_seconds": 14400,
            }
        )
        loop = AgentLoop(llm_client=_make_llm(responses), tool_executor=executor)

        result = loop.run("prepare source plan", ticker="PPT")

        assert result.action_preview is not None
        assert result.action_preview["action_id"] == "single_ticker_announcement_backfill"
        assert result.action_preview["args"] == {"ticker": "PPT", "years": 2}
        assert result.tool_calls_made == 1
        assert [item["tool"] for item in result.evidence] == ["run_backfill"]
        executor.assert_called_once_with("run_backfill", {"ticker": "PPT", "years": 2})

    def test_source_gather_command_uses_active_ticker_without_llm(self):
        executor = MagicMock()
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("Okay gather the sources", ticker="PPT")

        assert result.mode == "command"
        assert result.action_preview is not None
        assert result.action_preview["action_id"] == "single_ticker_announcement_backfill"
        assert result.action_preview["args"] == {"ticker": "PPT", "years": 2}
        executor.assert_not_called()
        llm.chat.assert_not_called()

    def test_analyse_command_executes_analysis_pipeline_directly(self):
        executor = MagicMock(
            return_value={
                "ok": True,
                "ticker": "BHP",
                "summary_text": "Analysis Summary for BHP",
                "modules": [{"module": "risk", "status": "complete", "metrics": {}}],
            }
        )
        llm = _make_llm([])
        loop = AgentLoop(llm_client=llm, tool_executor=executor)

        result = loop.run("analyse BHP")

        assert result is not None
        assert result.mode == "command"
        assert result.tool_calls_made == 1
        assert result.evidence[0]["tool"] == "run_analysis"
        assert "Analysis Summary for BHP" in result.text
        executor.assert_called_once_with("run_analysis", {"ticker": "BHP"})
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

    def test_bare_cloud_error_does_not_route_to_market_news(self):
        """A bare operator error report is not a market-data question."""
        executor = MagicMock()
        loop = AgentLoop(llm_client=_make_llm([]), tool_executor=executor)

        result = loop.run("/cloud Error")

        assert result is not None
        assert "specific error details" in result.text
        assert result.tool_calls_made == 0
        assert result.evidence == []
        executor.assert_not_called()
        loop._llm.chat.assert_not_called()

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

    def test_failed_price_payload_is_not_grounding_evidence(self):
        failed_price = {
            "tool": "get_price",
            "result": {
                "ok": False,
                "ticker": "XJO",
                "price": {
                    "ok": False,
                    "ticker": "XJO",
                    "error": "market price provider returned HTTP 404",
                },
                "price_state": {
                    "ok": False,
                    "ticker": "XJO",
                    "last_close": None,
                    "error": "market price provider returned HTTP 404",
                },
            },
        }

        assert not AgentLoop._has_grounding_evidence([failed_price])
        assert not AgentLoop._has_fresh_grounding_evidence([failed_price])

    def test_price_grounding_requires_observed_price_data(self):
        assert AgentLoop._has_grounding_evidence(
            [
                {
                    "tool": "get_price",
                    "result": {
                        "ok": True,
                        "ticker": "FGR",
                        "price": {"current": {"close": 1.23}},
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
                        "doc_snippets": [
                            {
                                "title": "Operations overview",
                                "excerpt": "Pilbara described production and shipment activity.",
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
        assert "Pilbara described production" in summary

    def test_evidence_summary_preserves_announcement_source_url(self):
        summary = AgentLoop._summarize_evidence(
            [
                {
                    "tool": "search_announcements",
                    "result": {
                        "tool": "search_announcements",
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 21_157,
                        "ticker": "WTC",
                        "documents": [
                            {
                                "title": "WTC 1H26 Appendix 4D and financial report",
                                "published_at": "2026-02-25T00:00:00Z",
                                "source_url": "https://example.com/wtc-1h26.pdf",
                            }
                        ],
                    },
                }
            ]
        )

        assert "_truncated" not in summary
        assert "WTC 1H26 Appendix 4D" in summary
        assert "2026-02-25" in summary
        assert "https://example.com/wtc-1h26.pdf" in summary

    def test_financial_truth_summary_preserves_announcement_context_without_rows(self):
        summary = AgentLoop._summarize_evidence(
            [
                {
                    "tool": "financial_truth",
                    "result": {
                        "status": "ok",
                        "ticker": "PPT",
                        "financials": [],
                        "latest_financial_snapshot": {},
                        "announcement_context": [
                            {
                                "title": "Sale of Wealth Management business",
                                "published_at": "2026-03-16T00:00:00Z",
                            }
                        ],
                    },
                }
            ]
        )

        assert "no canonical financial rows returned" in summary
        assert "Sale of Wealth Management business" in summary
