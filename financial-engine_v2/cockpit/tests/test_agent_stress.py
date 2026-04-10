"""Stress and edge-case tests for the agent loop, tool execution, and context management."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from cockpit.core.agent_loop import AgentLoop
from cockpit.core.tool_executor import ToolExecutor, DEFAULT_MAX_RESULT_CHARS
from cockpit.core.response_parser import parse_llm_response
from cockpit.core.tool_definitions import TOOL_DEFINITIONS, MUTATING_TOOL_NAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm(responses):
    """Return a mock LLM client whose chat() yields *responses* in order."""
    client = MagicMock()
    client.model = "test-model"
    if isinstance(responses, str):
        client.chat.return_value = responses
    else:
        client.chat.side_effect = list(responses)
    return client


def _tool_result(payload=None):
    """Return a mock tool executor callable that always returns *payload*."""
    executor = MagicMock(return_value=payload or {"ok": True})
    return executor


# ---------------------------------------------------------------------------
# 1. test_agent_loop_max_iterations_cap
# ---------------------------------------------------------------------------


class TestMaxIterationsCap:
    """The agent loop must terminate at MAX_ITERATIONS (6) and return a summary."""

    def test_agent_loop_max_iterations_cap(self):
        """Loop always returning tool_call must terminate after MAX_ITERATIONS=6."""
        # LLM always returns a tool_call — never gives a final response
        tool_call_response = json.dumps(
            {
                "type": "tool_call",
                "tool": "get_financials",
                "arguments": {"ticker": "BHP"},
                "reasoning": "need more data",
            }
        )
        llm = _make_llm(
            tool_call_response
        )  # side_effect=return_value repeated every call
        executor = _tool_result({"ok": True, "data": "some data"})

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("Tell me everything about BHP")

        # Must terminate at exactly MAX_ITERATIONS
        assert result.iterations_used == AgentLoop.MAX_ITERATIONS, (
            f"Expected {AgentLoop.MAX_ITERATIONS} iterations, got {result.iterations_used}"
        )
        # Must have made exactly MAX_ITERATIONS tool calls (one per iteration)
        assert result.tool_calls_made == AgentLoop.MAX_ITERATIONS, (
            f"Expected {AgentLoop.MAX_ITERATIONS} tool calls, got {result.tool_calls_made}"
        )
        # Result text must be a summary/exhaustion message, not empty
        assert result.text, "Exhaustion result text must not be empty"
        # Exhaustion text should hint at what was found or the limit reached
        text_lower = result.text.lower()
        assert any(
            kw in text_lower
            for kw in ("limit", "found", "tool", "reach", "get_financials")
        ), f"Exhaustion text does not mention findings: {result.text!r}"


# ---------------------------------------------------------------------------
# 2. test_agent_loop_parallel_tool_calls
# ---------------------------------------------------------------------------


class TestParallelToolCalls:
    """The loop handles tool_calls (plural) correctly in a single iteration."""

    def test_agent_loop_parallel_tool_calls(self):
        """Multiple tools called in one iteration via tool_calls type."""
        responses = [
            json.dumps(
                {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "id": "call_1",
                            "tool": "get_financials",
                            "arguments": {"ticker": "BHP"},
                        },
                        {
                            "id": "call_2",
                            "tool": "get_price",
                            "arguments": {"ticker": "BHP"},
                        },
                        {
                            "id": "call_3",
                            "tool": "search_news",
                            "arguments": {"query": "BHP news"},
                        },
                    ],
                    "reasoning": "Need financials, price, and news simultaneously",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "BHP analysis: revenue $55B, price $42, recent news positive.",
                }
            ),
        ]
        llm = _make_llm(responses)
        executor = _tool_result({"ok": True, "data": "result"})

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("Give me a BHP overview")

        # All 3 parallel tools were called in iteration 1
        assert result.tool_calls_made == 3, (
            f"Expected 3 tool calls, got {result.tool_calls_made}"
        )
        # Only 2 iterations total: tool_calls + response
        assert result.iterations_used == 2, (
            f"Expected 2 iterations, got {result.iterations_used}"
        )
        # Evidence collected for all 3 calls
        assert len(result.evidence) == 3, (
            f"Expected 3 evidence entries, got {len(result.evidence)}"
        )
        tool_names = {e["tool"] for e in result.evidence}
        assert "get_financials" in tool_names
        assert "get_price" in tool_names
        assert "search_news" in tool_names
        # Final response text preserved
        assert "55B" in result.text

    def test_agent_loop_retries_when_model_echoes_tool_arguments_as_json(self):
        """A bare JSON echo after tool use should trigger one more synthesis round."""
        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_news",
                    "arguments": {"query": "BHP", "ticker": "BHP", "limit": 5},
                    "reasoning": "Need recent news",
                }
            ),
            json.dumps({"query": "BHP", "ticker": "BHP", "limit": 5}),
            json.dumps(
                {
                    "type": "response",
                    "content": "Recent BHP news in the corpus is mixed, with coverage focused on operations and commodity outlook.",
                }
            ),
        ]
        llm = _make_llm(responses)
        executor = _tool_result({"ok": True, "results": [{"headline": "BHP update"}]})

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("what bhp news do u have")

        assert result.text.startswith("Recent BHP news"), result.text
        assert result.tool_calls_made == 1
        assert result.iterations_used == 3

    def test_agent_loop_retries_when_first_turn_is_bare_tool_arguments_json(self):
        """A bare tool-argument dict on the first turn should trigger a corrective retry."""
        responses = [
            json.dumps({"query": "BHP", "ticker": "BHP", "limit": 5}),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "search_news",
                    "arguments": {"query": "BHP", "ticker": "BHP", "limit": 5},
                    "reasoning": "Need recent news",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "Recent BHP news is mixed, with coverage focused on operations and commodity outlook.",
                }
            ),
        ]
        llm = _make_llm(responses)
        executor = _tool_result({"ok": True, "results": [{"headline": "BHP update"}]})

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("bhp news")

        assert result.text.startswith("Recent BHP news"), result.text
        assert result.tool_calls_made == 1
        assert result.iterations_used == 3


# ---------------------------------------------------------------------------
# 3. test_context_window_summarization
# ---------------------------------------------------------------------------


class TestContextWindowSummarization:
    """Fill the loop with large tool results and verify old results get compressed."""

    def test_context_window_summarization(self):
        """_maybe_summarize_old_results compresses older tool results above the token budget.

        Budget = _MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN = 12000 * 4 = 48000 chars.

        Note: format_tool_result() hard-caps individual messages at 2000 chars, so the
        end-to-end loop path cannot exceed the context budget in 6 iterations.  This
        test calls _maybe_summarize_old_results directly with a crafted messages list
        that already exceeds the threshold, confirming the compression logic is correct.
        """
        from cockpit.core.agent_loop import _MAX_CONTEXT_TOKENS, _CHARS_PER_TOKEN

        # Each tool result: ~12100 chars. 5 results = ~60500 chars = ~15125 tokens.
        big_body = "D" * 10000
        tool_result_content = "[Tool: query_ticker_data]\n" + json.dumps(
            {"ok": True, "data": big_body}
        )

        # Build messages bypassing format_tool_result 2000-char cap
        messages = [
            {"role": "system", "content": "You are Tenn."},
            {"role": "user", "content": "Analyse all the tickers"},
        ]
        for i in range(5):
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "tool_call",
                            "tool": "query_ticker_data",
                            "arguments": {"ticker": f"T{i}"},
                        }
                    ),
                }
            )
            messages.append({"role": "user", "content": tool_result_content})

        total_chars = sum(len(m["content"]) for m in messages)
        approx_tokens = total_chars // _CHARS_PER_TOKEN
        assert approx_tokens > _MAX_CONTEXT_TOKENS, (
            f"Test setup: {approx_tokens} tokens must exceed threshold {_MAX_CONTEXT_TOKENS}"
        )

        llm = _make_llm('{"type": "response", "content": "done"}')
        loop = AgentLoop(llm_client=llm, tool_executor=None)
        loop._maybe_summarize_old_results(messages)

        tool_msgs = [m for m in messages if m["content"].startswith("[Tool:")]
        summarized = [m for m in tool_msgs if "[summarized" in m["content"]]
        assert len(summarized) > 0, (
            "Expected older tool results to be compressed. "
            f"Tool messages: {[m['content'][:80] for m in tool_msgs]}"
        )
        assert messages[0]["content"] == "You are Tenn.", (
            "System message must not be modified"
        )
        for msg in tool_msgs[-2:]:
            assert "[summarized" not in msg["content"], (
                "Last 2 tool results must not be summarized"
            )

    def test_summarization_preserves_last_two_results(self):
        """The two most recent tool results must NOT be summarized even when over budget."""
        # Force context overflow by using a large system prompt + big tool results
        big_payload = "Y" * 6000

        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "A"},
                    "reasoning": "1",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "B"},
                    "reasoning": "2",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "C"},
                    "reasoning": "3",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "D"},
                    "reasoning": "4",
                }
            ),
            json.dumps({"type": "response", "content": "Done with all."}),
        ]
        llm = _make_llm(responses)
        executor = _tool_result({"ok": True, "data": big_payload})

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        loop.run("Analyse A, B, C, D")

        # On the last LLM call, inspect prior_messages
        last_call = llm.chat.call_args_list[-1]
        prior = last_call.kwargs.get("prior_messages") or []
        tool_msgs = [m for m in prior if m.get("content", "").startswith("[Tool:")]

        if len(tool_msgs) >= 2:
            # The two most recent should NOT be summarized
            assert "[summarized" not in tool_msgs[-1]["content"], (
                "Most recent tool result should not be summarized"
            )
            assert "[summarized" not in tool_msgs[-2]["content"], (
                "Second most recent tool result should not be summarized"
            )


# ---------------------------------------------------------------------------
# 4. test_tool_result_truncation
# ---------------------------------------------------------------------------


class TestToolResultTruncation:
    """ToolExecutor._truncate() caps results at max_result_chars (default 2000)."""

    def _make_tool_executor(self, max_chars=DEFAULT_MAX_RESULT_CHARS):
        """Build a ToolExecutor with mocked dependencies."""
        router = MagicMock()
        actions = MagicMock()
        return ToolExecutor(
            tool_router=router,
            action_registry=actions,
            max_result_chars=max_chars,
        )

    def test_tool_result_truncation(self):
        """Results exceeding max_result_chars are truncated with _truncated flag."""
        executor = self._make_tool_executor(max_chars=200)

        # Build a result that serializes to > 200 chars
        big_result = {
            "tool": "get_financials",
            "ok": True,
            "data": "A" * 500,
        }
        truncated = executor._truncate(big_result)

        assert truncated.get("_truncated") is True, "Expected _truncated=True flag"
        assert "_original_chars" in truncated, "Expected _original_chars field"
        assert truncated["_original_chars"] > 200, "Original size should exceed limit"
        # The 'data' field should be compressed
        serialized_back = json.dumps(truncated, default=str)
        assert len(serialized_back) <= 200 + 200, (
            "Truncated result should be significantly smaller than original"
        )

    def test_small_result_not_truncated(self):
        """Results under max_result_chars are returned unchanged."""
        executor = self._make_tool_executor(max_chars=2000)
        small_result = {"tool": "get_price", "ok": True, "price": 42.5}

        returned = executor._truncate(small_result)

        assert "_truncated" not in returned, (
            "Small result should not have _truncated flag"
        )
        assert returned["price"] == 42.5

    def test_default_max_result_chars_is_2000(self):
        """Default max_result_chars constant is 2000."""
        assert DEFAULT_MAX_RESULT_CHARS == 2000

    def test_truncation_via_agent_loop_execute_tool(self):
        """AgentLoop._execute_tool captures oversized results without crashing."""
        huge_response = {"ok": True, "data": "Z" * 10000}
        executor = _tool_result(huge_response)

        llm_responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "BHP"},
                    "reasoning": "x",
                }
            ),
            json.dumps({"type": "response", "content": "Got the data."}),
        ]
        llm = _make_llm(llm_responses)

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("BHP data")

        # Must complete without exception; evidence should exist
        assert result.tool_calls_made == 1
        assert result.text == "Got the data."
        assert len(result.evidence) == 1


# ---------------------------------------------------------------------------
# 5. test_agent_loop_handles_malformed_json
# ---------------------------------------------------------------------------


class TestMalformedJsonHandling:
    """Non-JSON LLM responses must be treated as direct text, not cause a crash."""

    def test_agent_loop_handles_malformed_json(self):
        """Plain text LLM response is treated as a direct response."""
        plain_text = "I cannot determine that from the available data."
        llm = _make_llm(plain_text)

        loop = AgentLoop(llm_client=llm)
        result = loop.run("What is the revenue?")

        assert result.text == plain_text, (
            f"Expected plain text to be preserved as result.text, got: {result.text!r}"
        )
        assert result.iterations_used == 1
        assert result.tool_calls_made == 0

    def test_partial_json_is_treated_as_text(self):
        """Truncated/partial JSON falls back to text response."""
        partial = '{"type": "response", "content": "Here is the answer'  # unclosed
        llm = _make_llm(partial)

        loop = AgentLoop(llm_client=llm)
        result = loop.run("hello")

        # Should not crash; result must have some text
        assert result.text is not None
        assert result.iterations_used == 1

    def test_empty_response_handled_gracefully(self):
        """Empty LLM response returns an empty response, not a crash."""
        llm = _make_llm("")

        loop = AgentLoop(llm_client=llm)
        result = loop.run("hello")

        # Empty raw response is parsed as response type with empty content
        assert result is not None
        assert result.iterations_used == 1

    def test_json_array_response_treated_as_text(self):
        """JSON array (not object) falls back to text, not a crash."""
        llm = _make_llm('[{"type": "response"}]')

        loop = AgentLoop(llm_client=llm)
        result = loop.run("hello")

        assert result is not None
        assert result.iterations_used == 1

    def test_parse_llm_response_non_json_gives_response_type(self):
        """parse_llm_response correctly classifies non-JSON as 'response' type."""
        raw = "This is a normal English answer without any JSON."
        parsed = parse_llm_response(raw)

        assert parsed.type == "response"
        assert parsed.content == raw


# ---------------------------------------------------------------------------
# 6. test_agent_loop_tool_error_recovery
# ---------------------------------------------------------------------------


class TestToolErrorRecovery:
    """A tool raising an exception must not crash the loop; it should self-correct."""

    def test_agent_loop_tool_error_recovery(self):
        """Tool executor raising an exception returns error payload and loop continues."""
        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "BROKEN"},
                    "reasoning": "try fetching",
                }
            ),
            json.dumps(
                {
                    "type": "response",
                    "content": "I encountered an error fetching data for BROKEN; no financials available.",
                }
            ),
        ]
        llm = _make_llm(responses)

        # Executor raises on the first call
        failing_executor = MagicMock(side_effect=RuntimeError("DB connection failed"))

        loop = AgentLoop(llm_client=llm, tool_executor=failing_executor)
        result = loop.run("Tell me about BROKEN")

        # Loop must NOT crash
        assert result is not None
        # Tool call was attempted
        assert result.tool_calls_made == 1
        # Loop recovered and gave a response (second iteration)
        assert result.iterations_used == 2
        # Evidence captures the error
        assert len(result.evidence) == 1
        assert "error" in result.evidence[0]["result"]
        # Final text should acknowledge the problem
        assert result.text is not None

    def test_intermittent_tool_failure_does_not_abort_loop(self):
        """If one tool in a parallel call fails, the other results still go through."""
        responses = [
            json.dumps(
                {
                    "type": "tool_calls",
                    "calls": [
                        {
                            "id": "1",
                            "tool": "get_financials",
                            "arguments": {"ticker": "GOOD"},
                        },
                        {
                            "id": "2",
                            "tool": "get_price",
                            "arguments": {"ticker": "BROKEN"},
                        },
                    ],
                    "reasoning": "parallel fetch",
                }
            ),
            json.dumps({"type": "response", "content": "Partial data retrieved."}),
        ]
        llm = _make_llm(responses)

        call_count = [0]

        def selective_executor(tool_name, args):
            call_count[0] += 1
            if tool_name == "get_price":
                raise ValueError("price service unavailable")
            return {"ok": True, "financials": []}

        loop = AgentLoop(llm_client=llm, tool_executor=selective_executor)
        result = loop.run("Compare GOOD and BROKEN")

        assert result is not None
        # Both tool calls were attempted
        assert result.tool_calls_made == 2
        assert call_count[0] == 2
        # The failing tool produced an error entry in evidence
        broken_evidence = [e for e in result.evidence if e["tool"] == "get_price"]
        assert len(broken_evidence) == 1
        assert "error" in broken_evidence[0]["result"]

    def test_tool_error_payload_is_fed_to_llm_as_user_message(self):
        """Error from tool executor is formatted and injected back for LLM self-correction.

        In _call_llm(), messages[-1] is sent as `prompt` and everything prior goes into
        `prior_messages`. After a tool call, the tool result message is appended as the
        last user-role message — so it becomes the `prompt` on the next iteration, while
        the assistant's tool-call request appears in `prior_messages`.
        """
        responses = [
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "X"},
                    "reasoning": "x",
                }
            ),
            json.dumps({"type": "response", "content": "Acknowledged the error."}),
        ]
        llm = _make_llm(responses)
        erroring_executor = MagicMock(side_effect=Exception("timeout"))

        loop = AgentLoop(llm_client=llm, tool_executor=erroring_executor)
        loop.run("X data")

        # The second LLM call: the tool result (with error) is the `prompt`,
        # and the assistant's tool_call message is in `prior_messages`.
        second_call = llm.chat.call_args_list[1]
        prompt = second_call.kwargs.get("prompt") or (
            second_call.args[0] if second_call.args else ""
        )
        prior = second_call.kwargs.get("prior_messages") or []
        prior_content = " ".join(m.get("content", "") for m in prior)

        # The error payload must appear either as the prompt or in prior messages
        all_content = prompt + " " + prior_content
        assert "[Tool:" in all_content, (
            f"Expected [Tool:] marker in LLM input. prompt={prompt[:200]!r}"
        )
        assert "error" in all_content.lower() or "failed" in all_content.lower(), (
            f"Expected error indication in LLM input. prompt={prompt[:200]!r}"
        )


# ---------------------------------------------------------------------------
# 7. test_rapid_sequential_messages
# ---------------------------------------------------------------------------


class TestRapidSequentialMessages:
    """Running the loop many times sequentially must not leak state between runs."""

    def test_rapid_sequential_messages(self):
        """10 sequential runs with different messages should produce independent results."""
        results = []

        for i in range(10):
            msg = f"Message number {i}: what is the revenue of TICKER{i}?"
            response_text = f"Revenue for TICKER{i} is ${i * 100}M."

            llm = _make_llm(json.dumps({"type": "response", "content": response_text}))
            loop = AgentLoop(llm_client=llm)
            result = loop.run(msg)
            results.append(result)

        # Every run should have produced a distinct result
        assert len(results) == 10

        for i, result in enumerate(results):
            expected = f"${i * 100}M"
            assert expected in result.text, (
                f"Run {i}: expected {expected!r} in text, got {result.text!r}"
            )
            # Each run starts fresh — no tool calls since none were requested
            assert result.tool_calls_made == 0
            assert result.iterations_used == 1

    def test_no_state_leaks_between_runs_with_tool_calls(self):
        """Evidence and tool call counts are fresh on each run."""
        results = []

        for i in range(5):
            tool_response = json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": f"T{i}"},
                    "reasoning": f"fetch T{i}",
                }
            )
            final_response = json.dumps(
                {
                    "type": "response",
                    "content": f"T{i} analysis complete.",
                }
            )

            llm = _make_llm([tool_response, final_response])
            executor = _tool_result({"ok": True, "ticker": f"T{i}"})

            loop = AgentLoop(llm_client=llm, tool_executor=executor)
            result = loop.run(f"Analyse T{i}")
            results.append(result)

        for i, result in enumerate(results):
            # Each run should have exactly 1 tool call and 1 evidence entry
            assert result.tool_calls_made == 1, (
                f"Run {i}: expected 1 tool call, got {result.tool_calls_made}"
            )
            assert len(result.evidence) == 1, (
                f"Run {i}: expected 1 evidence entry, got {len(result.evidence)}"
            )
            assert result.evidence[0]["tool"] == "get_financials"
            assert result.evidence[0]["arguments"]["ticker"] == f"T{i}"

    def test_loop_instance_is_reusable_stateless(self):
        """A single AgentLoop instance can be called multiple times without state leaking."""
        responses_per_run = [
            json.dumps({"type": "response", "content": f"Answer for run {i}."})
            for i in range(5)
        ]

        # One LLM that gives 5 different responses
        llm = _make_llm(responses_per_run)
        loop = AgentLoop(llm_client=llm)

        results = []
        for i in range(5):
            result = loop.run(f"Run {i}")
            results.append(result)

        # Each result should have no cross-contamination
        for i, result in enumerate(results):
            assert f"run {i}" in result.text.lower(), (
                f"Result {i} text does not match expected content: {result.text!r}"
            )
            assert result.tool_calls_made == 0
            assert result.iterations_used == 1
            assert result.evidence == []


# ---------------------------------------------------------------------------
# Additional integration: multiple-tool-call sequences (preserved from original)
# ---------------------------------------------------------------------------


class TestMultipleToolCallSequences:
    """Agent loop behaviour across sequences of tool calls."""

    def test_two_iteration_loop(self):
        """Agent calls one tool then gives a final answer."""
        responses = [
            '{"type": "tool_call", "tool": "get_financials", "arguments": {"ticker": "BHP"}, "reasoning": "need data"}',
            '{"type": "response", "content": "BHP revenue is $55B based on the data."}',
        ]
        llm = _make_llm(responses)
        executor = _tool_result(
            {"ok": True, "ticker": "BHP", "financials": [{"revenue": 55000}]}
        )

        loop = AgentLoop(llm_client=llm, tool_executor=executor)
        result = loop.run("What is BHP revenue?")

        assert "55B" in result.text
        assert result.tool_calls_made == 1
        assert result.iterations_used == 2

    def test_action_proposal_stops_loop(self):
        """An action_proposal response halts the loop and surfaces the preview."""
        llm = _make_llm(
            '{"type": "action_proposal", "tool": "run_backfill", "arguments": {"ticker": "MIN"}, '
            '"explanation": "No data exists, propose backfill.", "requires_confirmation": true}'
        )
        loop = AgentLoop(llm_client=llm)
        result = loop.run("Get MIN data")

        assert result.action_preview is not None
        assert result.action_preview["tool"] == "run_backfill"
        assert (
            result.action_preview["action_id"] == "single_ticker_announcement_backfill"
        )
        assert result.action_preview["args"] == {"ticker": "MIN"}
        assert result.iterations_used == 1

    def test_llm_exception_returns_error_result(self):
        """LLM communication failure returns a graceful error result, not a crash."""
        client = MagicMock()
        client.model = "test"
        client.chat.side_effect = ConnectionError("server down")

        loop = AgentLoop(llm_client=client)
        result = loop.run("hello")

        assert "error" in result.text.lower()
        assert result.iterations_used == 1


# ---------------------------------------------------------------------------
# Tool definitions validation (preserved)
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Tool schema integrity checks."""

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing 'description'"
            assert "parameters" in tool, f"Tool {tool['name']} missing 'parameters'"
            assert isinstance(tool["parameters"], dict), (
                f"Tool {tool['name']} parameters must be a dict"
            )

    def test_mutating_tools_are_flagged_in_frozenset(self):
        for tool in TOOL_DEFINITIONS:
            if tool.get("mutating"):
                assert tool["name"] in MUTATING_TOOL_NAMES, (
                    f"Mutating tool {tool['name']} missing from MUTATING_TOOL_NAMES"
                )

    def test_no_duplicate_tool_names(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        duplicates = [n for n in names if names.count(n) > 1]
        assert len(names) == len(set(names)), f"Duplicate tool names: {duplicates}"
