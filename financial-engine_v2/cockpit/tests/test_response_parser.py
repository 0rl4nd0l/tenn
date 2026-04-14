"""Tests for cockpit.core.response_parser — structured LLM response parsing.

Covers:
- Single valid JSON objects (thinking, response, tool_call, action_proposal)
- Multi-object responses (thinking + response in one completion)
- Fallback to plain text on malformed JSON
- JSON repair (trailing commas)
"""

from cockpit.core.response_parser import parse_llm_response


# ---------------------------------------------------------------------------
# Single-object: well-formed structured outputs
# ---------------------------------------------------------------------------


class TestSingleObject:
    def test_response_type(self):
        raw = '{"type": "response", "content": "Hello, world!"}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "Hello, world!"

    def test_thinking_type(self):
        raw = '{"type": "thinking", "assessment": "trivial", "plan": "respond directly"}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "thinking"
        assert parsed.assessment == "trivial"
        assert parsed.plan == "respond directly"

    def test_tool_call_type(self):
        raw = '{"type": "tool_call", "tool": "query_ticker_data", "arguments": {"ticker": "BHP"}}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "tool_call"
        assert parsed.tool == "query_ticker_data"
        assert parsed.arguments == {"ticker": "BHP"}

    def test_action_proposal_type(self):
        raw = '{"type": "action_proposal", "tool": "ingest", "arguments": {"ticker": "CSL"}, "explanation": "Will ingest CSL"}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "action_proposal"
        assert parsed.explanation == "Will ingest CSL"


# ---------------------------------------------------------------------------
# Multi-object: thinking + response concatenated in one completion
# (The bug that caused raw JSON to leak to chat)
# ---------------------------------------------------------------------------


class TestMultiObject:
    def test_thinking_then_response_extracts_content(self):
        """The exact pattern from the flagged chat report."""
        raw = (
            '{"type": "thinking", "assessment": "The user just typed h", '
            '"plan": "Ask for clarification"}\n\n'
            '{"type": "response", "content": "Looks like an accidental keystroke!"}'
        )
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "Looks like an accidental keystroke!"
        # Thinking metadata should be preserved
        assert parsed.assessment == "The user just typed h"
        assert parsed.plan == "Ask for clarification"

    def test_thinking_then_response_no_newline_gap(self):
        raw = (
            '{"type": "thinking", "assessment": "quick", "plan": "answer"}'
            '{"type": "response", "content": "Here is the answer."}'
        )
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "Here is the answer."

    def test_thinking_then_tool_call(self):
        raw = (
            '{"type": "thinking", "assessment": "need data", "plan": "query BHP"}\n\n'
            '{"type": "tool_call", "tool": "query_ticker_data", "arguments": {"ticker": "BHP"}}'
        )
        parsed = parse_llm_response(raw)
        # No response block, so it should fall to the last object (tool_call)
        assert parsed.type == "tool_call"
        assert parsed.tool == "query_ticker_data"

    def test_multi_response_takes_last(self):
        raw = (
            '{"type": "response", "content": "first draft"}\n'
            '{"type": "response", "content": "revised answer"}'
        )
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "revised answer"

    def test_nested_json_in_content_not_confused(self):
        """A single response with JSON inside content should still parse as one object."""
        raw = '{"type": "response", "content": "The data is {\\\"key\\\": \\\"val\\\"}"}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert "key" in parsed.content


# ---------------------------------------------------------------------------
# Edge cases and fallbacks
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string(self):
        parsed = parse_llm_response("")
        assert parsed.type == "response"
        assert parsed.content == ""

    def test_plain_text_fallback(self):
        raw = "I don't know enough to answer that question."
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == raw

    def test_trailing_comma_repair(self):
        raw = '{"type": "response", "content": "fixed",}'
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "fixed"

    def test_markdown_fence_stripping(self):
        raw = '```json\n{"type": "response", "content": "fenced"}\n```'
        parsed = parse_llm_response(raw)
        assert parsed.type == "response"
        assert parsed.content == "fenced"

    def test_raw_always_preserved(self):
        raw = '{"type": "response", "content": "test"}'
        parsed = parse_llm_response(raw)
        assert parsed.raw == raw
