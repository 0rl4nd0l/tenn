from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from cockpit.core.chat import ChatController


class _FakeAgentLoop:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def synthesize_final_answer(self, evidence, **kwargs):
        self.calls.append({"mode": "sync", "evidence": evidence, "kwargs": kwargs})
        return kwargs["draft_answer"]

    def synthesize_final_answer_stream(self, evidence, on_chunk, **kwargs):
        self.calls.append({"mode": "stream", "evidence": evidence, "kwargs": kwargs})
        text = "Final streamed answer."
        for chunk in ("Final ", "streamed ", "answer."):
            on_chunk(chunk)
        return text


def _controller(orchestration_result):
    ctrl = ChatController.__new__(ChatController)
    ctrl.repo_root = Path("/tmp")
    ctrl.ollama_client = MagicMock()
    ctrl.tool_router = MagicMock()
    ctrl.action_registry = MagicMock()
    ctrl._cockpit_llm = {}
    ctrl.llm_timeout_seconds = 60.0
    ctrl.last_ticker = None
    ctrl._state_store = None
    ctrl._thread_id = "global-main"
    ctrl._memory = None
    ctrl._query_orchestrator = SimpleNamespace(
        orchestrate_query_with_context=lambda query, context=None: orchestration_result
    )
    ctrl._ov_session_id = "session-1"
    ctrl._context_gather_lock = None
    ctrl._hybrid_router = None
    ctrl._dossier_service = None
    ctrl._strategy_service = None
    ctrl._agent_loop = _FakeAgentLoop()
    return ctrl


def _controller_with_context_capture(orchestration_result):
    ctrl = ChatController.__new__(ChatController)
    ctrl.repo_root = Path("/tmp")
    ctrl.ollama_client = MagicMock()
    ctrl.tool_router = MagicMock()
    ctrl.action_registry = MagicMock()
    ctrl._cockpit_llm = {}
    ctrl.llm_timeout_seconds = 60.0
    ctrl.last_ticker = None
    ctrl._state_store = None
    ctrl._thread_id = "global-main"
    ctrl._memory = None
    calls: list[dict | None] = []
    ctrl._query_orchestrator = SimpleNamespace(
        orchestrate_query_with_context=lambda query, context=None: (
            calls.append(context),
            orchestration_result,
        )[1]
    )
    ctrl._ov_session_id = "session-1"
    ctrl._context_gather_lock = None
    ctrl._hybrid_router = None
    ctrl._dossier_service = None
    ctrl._strategy_service = None
    ctrl._agent_loop = _FakeAgentLoop()
    return ctrl, calls


def _result(intent: str, source_plan: tuple[str, ...], *, ticker: str | None = "BHP"):
    financial_truth = {
        "status": "ok",
        "ticker": ticker,
        "items": [{"ticker": ticker, "revenue": 55000}],
        "latest_financial_snapshot": {
            "ticker": ticker,
            "revenue": 55000,
            "period_end": "2025-12-31",
        },
    }
    company_memory = {
        "status": "ok",
        "items": [
            {
                "type": "claim",
                "statement": "Management is prioritising cost-out initiatives.",
            }
        ],
    }
    market_memory = {
        "status": "ok",
        "sector": "Materials",
        "sector_items": [{"statement": "Iron ore market sentiment is improving."}],
        "macro_items": [{"statement": "China demand remains supportive."}],
        "items": [
            {"statement": "Iron ore market sentiment is improving."},
            {"statement": "China demand remains supportive."},
        ],
    }
    raw = {
        "financial_truth": financial_truth,
        "company_memory": company_memory,
        "market_memory": market_memory,
    }
    return SimpleNamespace(
        intent=intent,
        entities={"primary_ticker": ticker, "tickers": [ticker] if ticker else []},
        source_plan=source_plan,
        financial_truth_results=financial_truth
        if "financial_truth" in source_plan
        else {},
        company_memory_results=company_memory
        if "company_memory" in source_plan
        else {},
        market_memory_results=market_memory if "market_memory" in source_plan else {},
        raw_supporting_evidence={name: raw[name] for name in source_plan},
        answer_input=f"draft for {intent}",
        answer={"source_status": {name: "ok" for name in source_plan}},
    )


def _empty_result(*, ticker: str | None = "BHP"):
    source_plan = ("financial_truth", "company_memory", "market_memory")
    raw = {
        "financial_truth": {
            "status": "ok",
            "ticker": ticker,
            "items": [],
            "latest_financial_snapshot": {},
        },
        "company_memory": {
            "status": "ok",
            "items": [],
        },
        "market_memory": {
            "status": "ok",
            "sector": "Materials",
            "sector_items": [],
            "macro_items": [],
            "items": [],
        },
    }
    return SimpleNamespace(
        intent="mixed",
        entities={"primary_ticker": ticker, "tickers": [ticker] if ticker else []},
        source_plan=source_plan,
        financial_truth_results=raw["financial_truth"],
        company_memory_results=raw["company_memory"],
        market_memory_results=raw["market_memory"],
        raw_supporting_evidence=raw,
        answer_input="draft with no evidence",
        answer={"source_status": {name: "ok" for name in source_plan}},
    )


def test_financial_fact_queries_use_financial_truth_only() -> None:
    ctrl = _controller(_result("financial_fact", ("financial_truth",)))

    response = ctrl.build_chat_response("What was BHP revenue?")

    assert response.routing_metadata["intent"] == "financial_fact"
    assert response.routing_metadata["sources"] == ["financial_truth"]
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "financial_truth",
    ]
    assert [item["tool"] for item in response.evidence] == [
        "orchestrator",
        "financial_truth",
    ]
    assert "draft for financial_fact" == response.text
    assert ctrl._agent_loop.calls[0]["kwargs"]["ticker"] == "BHP"


def test_strategy_queries_use_company_memory_first() -> None:
    ctrl = _controller(_result("strategy", ("company_memory",)))

    response = ctrl.build_chat_response("What is the investment thesis for BHP?")

    assert response.routing_metadata["intent"] == "strategy"
    assert response.routing_metadata["sources"] == ["company_memory"]
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "company_memory",
    ]


def test_market_queries_use_market_memory_shared_context() -> None:
    ctrl = _controller(_result("market", ("market_memory",), ticker=None))

    response = ctrl.build_chat_response("How is the iron ore market trading?")

    assert response.routing_metadata["intent"] == "market"
    assert response.routing_metadata["sources"] == ["market_memory"]
    assert response.evidence[1]["details"]["sector"] == "Materials"


def test_mixed_queries_preserve_source_order() -> None:
    ctrl = _controller(
        _result(
            "mixed",
            ("financial_truth", "company_memory", "market_memory"),
        )
    )

    response = ctrl.build_chat_response("Why did BHP margins fall?")

    assert response.routing_metadata["sources"] == [
        "financial_truth",
        "company_memory",
        "market_memory",
    ]
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "financial_truth",
        "company_memory",
        "market_memory",
    ]


def test_orchestrated_metadata_includes_routing_reason_when_router_log_available() -> (
    None
):
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory")))
    ctrl._hybrid_router = SimpleNamespace(
        cost_log=lambda: [
            {
                "source": "api",
                "model": "claude-sonnet",
                "latency_ms": 42,
                "cost_usd": 0.01,
                "routing_reason": "policy:api_preferred",
            }
        ],
    )

    response = ctrl.build_chat_response("Why did BHP margins fall?")

    assert response.routing_metadata["source"] == "orchestrator"
    assert response.routing_metadata["intent"] == "mixed"
    assert response.routing_metadata["routing_reason"] == "policy:api_preferred"


def test_orchestrated_responses_stream_plain_text_only() -> None:
    ctrl = _controller(
        _result(
            "financial_interpretation",
            ("financial_truth", "company_memory", "market_memory"),
        )
    )
    chunks: list[str] = []

    response = ctrl.build_chat_response(
        "What does BHP's margin trend mean?",
        on_chunk=chunks.append,
    )

    assert response.text == "Final streamed answer."
    assert "".join(chunks) == "Final streamed answer."
    assert '{"type"' not in "".join(chunks)
    assert ctrl._agent_loop.calls[0]["mode"] == "stream"


def test_orchestrated_evidence_is_compatible_with_tool_style_synthesis() -> None:
    ctrl = _controller(
        _result(
            "mixed",
            ("financial_truth", "company_memory", "market_memory"),
        )
    )

    ctrl.build_chat_response("Why did BHP margins fall?")

    evidence = ctrl._agent_loop.calls[0]["evidence"]
    assert [item["tool"] for item in evidence] == [
        "orchestrator",
        "financial_truth",
        "company_memory",
        "market_memory",
    ]


def test_unrelated_query_does_not_leak_prior_ticker_into_orchestrator() -> None:
    ctrl, calls = _controller_with_context_capture(
        _result("market", ("market_memory",), ticker=None)
    )

    response = ctrl.build_chat_response("how are things going?", prior_ticker="BHP")

    assert response.routing_metadata["intent"] == "market"
    assert calls == [{"prior_ticker": None}]


def test_empty_orchestrator_result_falls_back_to_local_context() -> None:
    ctrl = _controller(_empty_result())
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [
                {
                    "title": "Half Yearly Report and Accounts",
                    "doc_class": "half_year",
                    "published_at": "2026-02-17T00:00:00Z",
                }
            ],
            "doc_snippets": [
                {
                    "title": "Half Yearly Report and Accounts",
                    "excerpt": "BHP released its half-yearly report and accounts.",
                }
            ],
            "financials": [],
            "price": {},
            "price_state": {},
            "sources": {},
        }
    )
    ctrl.ollama_client.chat.return_value = (
        "BHP has recent ASX filings available, but no extracted financial metrics yet."
    )

    response = ctrl.build_chat_response("tell me about BHP")

    assert response.text == (
        "BHP has recent ASX filings available, but no extracted financial metrics yet."
    )
    assert response.evidence == [
        {
            "type": "local_context",
            "details": ctrl.tool_router.gather_local_context.return_value.payload,
        }
    ]
    assert response.mode.value == "fast"
    system_prompt = ctrl.ollama_client.chat.call_args.kwargs["prior_messages"][0][
        "content"
    ]
    assert "Do not emit tool-call JSON" in system_prompt
    assert "Tool Selection Guide" not in system_prompt
    assert "Canonical financial metrics are not available" in system_prompt


def test_document_grounded_queries_prefer_local_context_even_with_orchestrator_evidence() -> (
    None
):
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory")))
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [
                {
                    "title": "Quarterly Activities Report",
                    "doc_class": "quarterly",
                    "published_at": "2026-01-20T00:00:00Z",
                }
            ],
            "doc_snippets": [
                {
                    "title": "Quarterly Activities Report",
                    "excerpt": "The release highlighted operational performance across iron ore and copper.",
                }
            ],
            "financials": [
                {
                    "ticker": "BHP",
                    "period_end": "2025-12-31",
                    "period_type": "HY",
                    "revenue": 55000,
                }
            ],
            "price": {},
            "price_state": {},
            "sources": {},
        }
    )
    ctrl.ollama_client.chat.return_value = "Based on the BHP release, operations remained the main focus while canonical revenue was 55000."

    response = ctrl.build_chat_response("What does the document say about BHP?")

    assert response.text == (
        "Based on the BHP release, operations remained the main focus while canonical revenue was 55000."
    )
    assert response.evidence == [
        {
            "type": "local_context",
            "details": ctrl.tool_router.gather_local_context.return_value.payload,
        }
    ]


def test_local_context_replaces_invented_financial_table_when_financials_missing() -> (
    None
):
    ctrl = _controller(_empty_result())
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [
                {
                    "title": "Half Yearly Report and Accounts",
                    "published_at": "2026-02-17T00:00:00Z",
                }
            ],
            "doc_snippets": [],
            "financials": [],
            "price": {},
            "price_state": {"trend_regime": "neutral"},
            "sources": {},
        }
    )
    ctrl.ollama_client.chat.return_value = (
        "| Metric | Value |\n|---|---|\n| Revenue | US$27.9bn |\n| Profit | US$5.6bn |"
    )

    response = ctrl.build_chat_response("tell me about BHP")

    assert "US$27.9bn" not in response.text
    assert (
        "Detailed extracted financial metrics are not currently available"
        in response.text
    )
