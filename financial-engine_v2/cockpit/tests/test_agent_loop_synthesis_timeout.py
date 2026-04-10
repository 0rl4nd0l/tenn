"""Focused regression tests for post-tool synthesis behavior in AgentLoop."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from cockpit.core.agent_loop import AgentLoop


def _make_llm(responses: list[object]) -> MagicMock:
    client = MagicMock()
    client.model = "test-model"
    client.chat.side_effect = list(responses)
    return client


def test_synthesis_pass_uses_shorter_timeout_after_tool_call():
    responses = [
        json.dumps(
            {
                "type": "thinking",
                "assessment": "Need company financials before answering.",
                "plan": "Call get_financials then summarize the result.",
            }
        ),
        json.dumps(
            {
                "type": "tool_call",
                "tool": "get_financials",
                "arguments": {"ticker": "BHP"},
                "reasoning": "Need source data",
            }
        ),
        json.dumps({"type": "response", "content": "BHP revenue is $55B."}),
        "BHP revenue is $55B.",
    ]
    llm = _make_llm(responses)
    executor = MagicMock(return_value={"ok": True, "financials": [{"revenue": 55000}]})

    loop = AgentLoop(
        llm_client=llm,
        tool_executor=executor,
        llm_timeout=120.0,
        synthesis_timeout=30.0,
    )
    result = loop.run("What is BHP revenue?")

    assert result.text == "BHP revenue is $55B."
    timeouts = [call.kwargs.get("timeout") for call in llm.chat.call_args_list]
    assert timeouts == [120.0, 120.0, 30.0, 30.0]


def test_default_synthesis_timeout_is_not_capped_to_30_seconds() -> None:
    loop = AgentLoop(
        llm_client=_make_llm([]),
        tool_executor=MagicMock(),
        llm_timeout=120.0,
    )

    assert loop._synthesis_timeout == 90.0


def test_synthesis_timeout_returns_evidence_summary():
    llm = _make_llm(
        [
            json.dumps(
                {
                    "type": "thinking",
                    "assessment": "Need company financials before answering.",
                    "plan": "Call get_financials then summarize the result.",
                }
            ),
            json.dumps(
                {
                    "type": "tool_call",
                    "tool": "get_financials",
                    "arguments": {"ticker": "BHP"},
                    "reasoning": "Need source data",
                }
            ),
            TimeoutError("timed out while synthesizing"),
        ]
    )
    executor = MagicMock(return_value={"ok": True, "financials": [{"revenue": 55000}]})
    statuses: list[str] = []

    loop = AgentLoop(
        llm_client=llm,
        tool_executor=executor,
        llm_timeout=120.0,
        synthesis_timeout=15.0,
    )
    result = loop.run("What is BHP revenue?", on_status=statuses.append)

    assert result.text.startswith("Based on available evidence:")
    assert "get_financials" in result.text
    assert result.tool_calls_made == 1
    assert result.iterations_used == 2
    assert any("timed out" in status.lower() for status in statuses)


def test_final_synthesis_streams_only_plain_text_chunks():
    class FakeClient:
        def __init__(self) -> None:
            self.model = "test-model"
            self.calls: list[dict] = []

        def chat(
            self, prompt, timeout=120.0, prior_messages=None, on_chunk=None, **kwargs
        ):
            self.calls.append(
                {
                    "prompt": prompt,
                    "timeout": timeout,
                    "prior_messages": prior_messages,
                    "has_on_chunk": on_chunk is not None,
                }
            )
            call_index = len(self.calls)
            if call_index == 1:
                return json.dumps(
                    {
                        "type": "thinking",
                        "assessment": "Need company financials before answering.",
                        "plan": "Call get_financials then summarize the result.",
                    }
                )
            if call_index == 2:
                return json.dumps(
                    {
                        "type": "tool_call",
                        "tool": "get_financials",
                        "arguments": {"ticker": "BHP"},
                        "reasoning": "Need source data",
                    }
                )
            if call_index == 3:
                return json.dumps(
                    {
                        "type": "response",
                        "content": "BHP revenue is $55B based on the tool output.",
                    }
                )

            chunks = ["BHP ", "revenue ", "is $55B."]
            for chunk in chunks:
                if on_chunk is not None:
                    on_chunk(chunk)
            return "".join(chunks)

    client = FakeClient()
    executor = MagicMock(return_value={"ok": True, "financials": [{"revenue": 55000}]})
    chunks: list[str] = []

    loop = AgentLoop(
        llm_client=client,
        tool_executor=executor,
        llm_timeout=120.0,
        synthesis_timeout=15.0,
    )
    result = loop.run("What is BHP revenue?", on_chunk=chunks.append)

    assert result.text == "BHP revenue is $55B."
    assert "".join(chunks) == "BHP revenue is $55B."
    assert all(not call["has_on_chunk"] for call in client.calls[:3])
    assert client.calls[3]["has_on_chunk"] is True
    assert '{"type"' not in "".join(chunks)


def test_synthesis_timeout_streams_plain_text_fallback():
    class TimeoutOnSynthesisClient:
        def __init__(self) -> None:
            self.model = "test-model"
            self.calls = 0

        def chat(
            self, prompt, timeout=120.0, prior_messages=None, on_chunk=None, **kwargs
        ):
            self.calls += 1
            if self.calls == 1:
                return json.dumps(
                    {
                        "type": "thinking",
                        "assessment": "Need company financials before answering.",
                        "plan": "Call get_financials then summarize the result.",
                    }
                )
            if self.calls == 2:
                return json.dumps(
                    {
                        "type": "tool_call",
                        "tool": "get_financials",
                        "arguments": {"ticker": "BHP"},
                        "reasoning": "Need source data",
                    }
                )
            if self.calls == 3:
                return json.dumps(
                    {
                        "type": "response",
                        "content": "BHP revenue is $55B based on the tool output.",
                    }
                )
            raise TimeoutError("stream synthesis timed out")

    client = TimeoutOnSynthesisClient()
    executor = MagicMock(return_value={"ok": True, "financials": [{"revenue": 55000}]})
    chunks: list[str] = []

    loop = AgentLoop(
        llm_client=client,
        tool_executor=executor,
        llm_timeout=120.0,
        synthesis_timeout=15.0,
    )
    result = loop.run("What is BHP revenue?", on_chunk=chunks.append)

    assert result.text.startswith("Based on available evidence:")
    assert "get_financials" in result.text
    assert "".join(chunks) == result.text
    assert '{"type"' not in result.text


def test_summarize_evidence_understands_orchestrator_type_details_payloads() -> None:
    summary = AgentLoop._summarize_evidence(
        [
            {
                "type": "orchestrator",
                "details": {
                    "intent": "mixed",
                    "source_plan": ["financial_truth", "company_memory"],
                },
            },
            {
                "type": "financial_truth",
                "details": {
                    "latest_financial_snapshot": {
                        "period_end": "2025-12-31",
                        "revenue": 55000,
                    }
                },
            },
            {
                "type": "company_memory",
                "details": {
                    "items": [
                        {
                            "type": "management_guidance",
                            "statement": "Management expects margin improvement.",
                        }
                    ]
                },
            },
        ]
    )

    assert (
        "orchestrator: intent=mixed; sources=financial_truth, company_memory" in summary
    )
    assert "financial_truth: period_end=2025-12-31, revenue=55000" in summary
    assert (
        "company_memory: management guidance: Management expects margin improvement."
        in summary
    )
