from __future__ import annotations

from cockpit.core.agent_loop import AgentLoop
from cockpit.core.response_parser import ParsedResponse


def test_json_guard_flags_fetch_url_argument_blob() -> None:
    parsed = ParsedResponse(
        type="response",
        content=None,
        raw='{"url":"https://example.com/article","max_chars":8000}',
    )

    assert AgentLoop._looks_like_json_non_answer(
        '{"url":"https://example.com/article","max_chars":8000}',
        parsed,
        evidence=[{"tool": "fetch_url", "result": {"ok": True}}],
    )


def test_json_guard_does_not_flag_normal_text_response() -> None:
    parsed = ParsedResponse(
        type="response",
        content="Here is a summary.",
        raw='{"content":"Here is a summary."}',
    )

    assert not AgentLoop._looks_like_json_non_answer(
        '{"content":"Here is a summary."}',
        parsed,
        evidence=[{"tool": "fetch_url", "result": {"ok": True}}],
    )
