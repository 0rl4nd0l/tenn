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
