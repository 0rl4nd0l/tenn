from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from cockpit.core.chat import ChatController


class _FakeAgentLoop:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._turn_force_backend = None

    def run(
        self,
        message,
        ticker=None,
        conversation_history=None,
        on_chunk=None,
        on_status=None,
        on_thinking=None,
        **kwargs,
    ):
        self.calls.append(
            {
                "mode": "run",
                "message": message,
                "kwargs": {
                    "ticker": ticker,
                    "conversation_history": conversation_history,
                    "on_chunk": on_chunk,
                    "on_status": on_status,
                    "on_thinking": on_thinking,
                    **kwargs,
                },
            }
        )
        return SimpleNamespace(
            text="Agent API answer.",
            evidence=[],
            action_preview=None,
            mode="agent",
            routing_metadata={
                "source": "api",
                "model": "claude-sonnet-test",
                "latency_ms": 12,
                "cost_usd": 0.01,
            },
            tool_traces=[],
        )

    def synthesize_final_answer(self, evidence, **kwargs):
        self.calls.append(
            {
                "mode": "sync",
                "evidence": evidence,
                "kwargs": kwargs,
                "force_backend": self._turn_force_backend,
            }
        )
        return kwargs["draft_answer"]

    def synthesize_final_answer_stream(self, evidence, on_chunk, **kwargs):
        self.calls.append(
            {
                "mode": "stream",
                "evidence": evidence,
                "kwargs": kwargs,
                "force_backend": self._turn_force_backend,
            }
        )
        text = "Final streamed answer."
        for chunk in ("Final ", "streamed ", "answer."):
            on_chunk(chunk)
        return text


class _FakeHybridRouter:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._last_attempt = {
            "source": "api",
            "model": "claude-sonnet-test",
            "latency_ms": 25,
            "cost_usd": 0.002,
            "routing_reason": "policy:api_only",
        }

    def chat(
        self,
        prompt,
        timeout=120.0,
        prior_messages=None,
        on_chunk=None,
        force_backend=None,
        on_status=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "timeout": timeout,
                "prior_messages": prior_messages,
                "force_backend": force_backend,
                "on_status": on_status,
            }
        )
        text = "BHP API synthesis."
        if on_chunk is not None:
            on_chunk(text)
        return text

    def last_attempt_metadata(self):
        return dict(self._last_attempt)


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
    ctrl._recent_youtube_channel = None
    ctrl._recent_youtube_video_options = []
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
    ctrl._recent_youtube_channel = None
    ctrl._recent_youtube_video_options = []
    ctrl._agent_loop = _FakeAgentLoop()
    return ctrl, calls


def test_recent_youtube_options_prioritize_last_numbered_user_selection():
    ctrl = ChatController.__new__(ChatController)
    ctrl._thread_id = "chat-youtube"
    ctrl._recent_youtube_video_options = [
        {"position": 1, "title": "One", "webpage_url": "https://www.youtube.com/watch?v=one11111111"},
        {"position": 2, "title": "Two", "webpage_url": "https://www.youtube.com/watch?v=two22222222"},
    ]

    class _StateStore:
        def get_chat_messages(self, _thread_id: str, limit: int = 12):
            return [
                {"role": "user", "content": "takeaways from video 2?"},
                {"role": "assistant", "content": "I need to process that transcript first."},
                {"role": "user", "content": "process it"},
            ]

    ctrl._state_store = _StateStore()

    options = ctrl._recent_youtube_video_options_from_context()

    assert options[0]["title"] == "Two"
    assert options[0]["webpage_url"] == "https://www.youtube.com/watch?v=two22222222"


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


def _general_result():
    return SimpleNamespace(
        intent="general",
        entities={"primary_ticker": None, "tickers": []},
        source_plan=(),
        financial_truth_results={},
        company_memory_results={},
        market_memory_results={},
        raw_supporting_evidence={},
        answer_input="general draft",
        answer={"source_status": {}},
    )


def _recovery_only_result(*, ticker: str | None = "BHP"):
    source_plan = ("financial_truth", "company_memory", "market_memory")
    raw = {
        "financial_truth": {
            "status": "ok",
            "ticker": ticker,
            "items": [],
            "latest_financial_snapshot": {},
            "financials": [],
            "docs": [],
            "announcement_context": [],
        },
        "company_memory": {"status": "ok", "items": []},
        "market_memory": {
            "status": "ok",
            "sector": None,
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
        answer_input="Final verdict: abstain until blocking evidence gaps are resolved.",
        answer={"source_status": {name: "ok" for name in source_plan}},
        missing_data_recovery={
            "attempted": True,
            "sources": list(source_plan),
            "resolved_categories": [],
            "remaining_categories": ["financials", "business_profile_context"],
        },
        missing_categories_before_recovery=(
            "financials",
            "business_profile_context",
        ),
        missing_categories_after_recovery=(
            "financials",
            "business_profile_context",
        ),
        sufficient_for_analysis=False,
    )


def _insufficient_sector_result():
    source_plan = ("market_memory",)
    market_memory = {
        "status": "ok",
        "sector": "Energy",
        "sector_items": [],
        "macro_items": [],
        "items": [],
    }
    return SimpleNamespace(
        intent="market",
        entities={"primary_ticker": None, "tickers": [], "sector": "Energy"},
        source_plan=source_plan,
        financial_truth_results={},
        company_memory_results={},
        market_memory_results=market_memory,
        raw_supporting_evidence={"market_memory": market_memory},
        answer_input="Final verdict: abstain until blocking evidence gaps are resolved.",
        answer={"source_status": {"market_memory": "ok"}},
        missing_data_recovery={
            "attempted": False,
            "sources": [],
            "resolved_categories": [],
            "remaining_categories": ["market_context"],
        },
        missing_categories_before_recovery=("market_context",),
        missing_categories_after_recovery=("market_context",),
        sufficient_for_analysis=False,
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


def test_insufficient_sector_orchestration_does_not_fall_back_to_agent_loop() -> None:
    ctrl = _controller(_insufficient_sector_result())

    response = ctrl.build_chat_response("/cloud tell me about hydrogen industry")

    assert response.routing_metadata["source"] == "orchestrator"
    assert response.routing_metadata["intent"] == "market"
    assert response.text.startswith("Final verdict: abstain")
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "market_memory",
    ]
    assert ctrl._agent_loop.calls[-1]["mode"] == "sync"


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
        last_attempt_metadata=lambda: {
            "source": "api",
            "model": "claude-haiku",
            "latency_ms": 35,
            "cost_usd": 0.005,
        },
        cost_log=lambda: [
            {
                "source": "api",
                "model": "claude-sonnet",
                "latency_ms": 42,
                "cost_usd": 0.01,
                "routing_reason": "policy:api_preferred",
            }
        ],
        total_cost_usd=lambda: 0.02,
    )

    response = ctrl.build_chat_response("Why did BHP margins fall?")

    assert response.routing_metadata["source"] == "orchestrator"
    assert response.routing_metadata["synthesis_source"] == "api"
    assert response.routing_metadata["intent"] == "mixed"
    assert response.routing_metadata["model"] == "claude-sonnet"
    assert response.routing_metadata["latency_ms"] == 42
    assert response.routing_metadata["cost_usd"] == 0.01
    assert response.routing_metadata["total_session_cost_usd"] == 0.02
    assert response.routing_metadata["routing_reason"] == "policy:api_preferred"


def test_general_orchestrator_result_falls_through_to_agent_loop() -> None:
    ctrl = _controller(_general_result())

    response = ctrl.build_chat_response("Reply exactly ok.")

    assert response.text == "Agent API answer."
    assert response.routing_metadata["source"] == "api"
    assert ctrl._agent_loop.calls[-1]["mode"] == "run"
    assert ctrl.tool_router.gather_local_context.call_count == 0


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


def test_orchestrated_sources_list_consumes_evidence_envelope() -> None:
    result = _result("mixed", ("financial_truth", "company_memory"))
    result.evidence_envelope = {
        "source_label_taxonomy_version": "source_label_semantics_v1",
        "source_coverage_status": "context_only",
        "evidence_labels": ["financial_truth", "context_only", "memory_context"],
        "source_label_counts": {
            "financial_truth": 1,
            "context_only": 1,
            "memory_context": 1,
        },
        "claim_verified_source_count": 0,
        "missing_categories": [],
        "sufficient_for_analysis": True,
        "sources": [
            {
                "source_name": "financial_truth",
                "source_id": "financial_truth",
                "status": "ok",
                "source_role_labels": ["financial_truth"],
                "evidence_label": "financial_truth",
                "evidence_labels": ["financial_truth"],
                "item_count": 1,
                "has_evidence": True,
                "claim_verified": False,
                "no_hit": False,
                "degraded": False,
                "missing_required_evidence": False,
                "missing_categories": [],
                "error": None,
            },
            {
                "source_name": "company_memory",
                "source_id": "company_memory",
                "status": "ok",
                "source_role_labels": ["memory_context"],
                "evidence_label": "context_only",
                "evidence_labels": ["context_only", "memory_context"],
                "item_count": 1,
                "has_evidence": True,
                "claim_verified": False,
                "no_hit": False,
                "degraded": False,
                "missing_required_evidence": False,
                "missing_categories": [],
                "error": None,
            },
        ],
    }
    ctrl = _controller(result)

    response = ctrl.build_chat_response("Why did BHP margins fall?")
    sources_response = ctrl._handle_slash_command("/sources list")

    assert response.evidence[0]["details"]["evidence_envelope"] is result.evidence_envelope
    assert sources_response is not None
    assert "Sources list (evidence envelope" in sources_response.text
    assert "labels=financial_truth" in sources_response.text
    assert "labels=context_only, memory_context" in sources_response.text
    assert "Evidence taxonomy: unavailable" not in sources_response.text


def test_unrelated_query_does_not_leak_prior_ticker_into_orchestrator() -> None:
    ctrl, calls = _controller_with_context_capture(
        _result("market", ("market_memory",), ticker=None)
    )

    response = ctrl.build_chat_response("how are things going?", prior_ticker="BHP")

    assert response.routing_metadata["intent"] == "market"
    assert calls == [
        {
            "prior_ticker": None,
            "analysis_mode": None,
            "request_standard": None,
        }
    ]


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


def test_recovery_attempted_orchestrator_result_does_not_fall_back_to_local_context() -> (
    None
):
    ctrl = _controller(_recovery_only_result())
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [],
            "doc_snippets": [],
            "financials": [],
            "price": {},
            "price_state": {},
            "sources": {},
        }
    )

    response = ctrl.build_chat_response("full company analysis on BHP")

    assert response.routing_metadata["source"] == "orchestrator"
    assert response.text.startswith(
        "Final verdict: abstain until blocking evidence gaps are resolved."
    )
    assert "Coverage and Failure Signals:" in response.text
    assert "Unresolved evidence gaps: financials, business_profile_context" in response.text
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "financial_truth",
        "company_memory",
        "market_memory",
    ]
    assert ctrl.tool_router.gather_local_context.call_count == 0


def test_orchestrated_response_surfaces_retrieval_failures_when_answer_is_thin() -> None:
    failing_result = SimpleNamespace(
        intent="mixed",
        entities={"primary_ticker": "PPT", "tickers": ["PPT"]},
        source_plan=("financial_truth", "company_memory", "market_memory"),
        financial_truth_results={},
        company_memory_results={},
        market_memory_results={},
        raw_supporting_evidence={
            "financial_truth": {
                "status": "partial_error",
                "errors": ["context endpoint timed out"],
            },
            "company_memory": {"status": "ok", "items": []},
            "market_memory": {"status": "ok", "items": []},
        },
        answer_input="Here is a quick overview.",
        answer={
            "source_status": {
                "financial_truth": "partial_error",
                "company_memory": "ok",
                "market_memory": "ok",
            }
        },
        missing_data_recovery={"attempted": True},
        missing_categories_after_recovery=("financials",),
        sufficient_for_analysis=False,
    )
    ctrl = _controller(failing_result)
    response = ctrl.build_chat_response("analyse PPT")

    assert response.text.startswith("Here is a quick overview.")
    assert "Coverage and Failure Signals:" in response.text
    assert "Unresolved evidence gaps: financials" in response.text
    assert "financial_truth retrieval status: partial_error" in response.text
    assert "financial_truth retrieval errors: context endpoint timed out" in response.text


def test_cloud_company_analysis_uses_orchestrator_evidence_with_api_synthesis() -> None:
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory"), ticker="BHP"))

    response = ctrl.build_chat_response("/cloud analyse BHP")

    assert response.routing_metadata["source"] == "orchestrator"
    assert [item["type"] for item in response.evidence] == [
        "orchestrator",
        "financial_truth",
        "company_memory",
    ]
    assert ctrl._agent_loop.calls[-1]["mode"] == "sync"
    assert ctrl._agent_loop.calls[-1]["force_backend"] == "api"
    assert ctrl._agent_loop._turn_force_backend is None


def test_recent_update_queries_prefer_local_context_and_keep_backfill_as_optional_followup() -> (
    None
):
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory")))
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [],
            "doc_snippets": [],
            "financials": [],
            "price": {
                "ok": True,
                "symbol": "BHP.AX",
                "current": {
                    "price": 44.0,
                    "previous_close": 43.5,
                    "change_percent": 1.15,
                },
                "recent_history": [
                    {"timestamp": "2026-04-14T00:00:00Z", "close": 41.0},
                    {"timestamp": "2026-04-15T00:00:00Z", "close": 41.5},
                    {"timestamp": "2026-04-16T00:00:00Z", "close": 42.0},
                    {"timestamp": "2026-04-17T00:00:00Z", "close": 43.0},
                    {"timestamp": "2026-04-18T00:00:00Z", "close": 44.0},
                ],
            },
            "price_state": {"trend_regime": "bullish", "last_close": 44.0},
            "qual_context_news": {
                "hits": [
                    {
                        "title": "BHP copper expansion gathers pace",
                        "published_at": "2026-04-18T01:00:00Z",
                        "text": "Recent coverage focused on BHP expanding its copper footprint.",
                        "source_corpus": "news",
                    }
                ]
            },
            "qual_context": {"hits": []},
            "sources": {},
        }
    )
    ctrl.ollama_client.chat.return_value = (
        "BHP rose this week and recent coverage centred on copper expansion."
    )
    ctrl.action_registry.preview.return_value = SimpleNamespace(
        command=["python", "scripts/full_history_ticker_sync.py", "--ticker", "BHP"],
        estimated_impact="mutates local data and reports",
        timeout_seconds=14400,
    )

    response = ctrl.build_chat_response("what happened with BHP this week")

    assert response.text.startswith(
        "BHP rose this week and recent coverage centred on copper expansion."
    )
    assert response.action_preview is not None
    assert response.action_preview["action_id"] == "single_ticker_announcement_backfill"
    assert response.evidence == [
        {
            "type": "local_context",
            "details": ctrl.tool_router.gather_local_context.return_value.payload,
        }
    ]
    assert ctrl._agent_loop.calls == []


def test_keyword_context_path_uses_hybrid_router_instead_of_direct_local_llm() -> None:
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory")))
    hybrid_router = _FakeHybridRouter()
    ctrl._hybrid_router = hybrid_router
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "BHP",
            "docs": [],
            "doc_snippets": [],
            "financials": [],
            "price": {
                "ok": True,
                "symbol": "BHP.AX",
                "current": {
                    "price": 44.0,
                    "previous_close": 43.5,
                    "change_percent": 1.15,
                },
                "recent_history": [
                    {"timestamp": "2026-04-14T00:00:00Z", "close": 41.0},
                    {"timestamp": "2026-04-18T00:00:00Z", "close": 44.0},
                ],
            },
            "price_state": {"trend_regime": "bullish", "last_close": 44.0},
            "qual_context_news": {"hits": []},
            "qual_context": {"hits": []},
            "sources": {},
        }
    )
    ctrl.action_registry.preview.return_value = SimpleNamespace(
        command=["python", "scripts/full_history_ticker_sync.py", "--ticker", "BHP"],
        estimated_impact="mutates local data and reports",
        timeout_seconds=14400,
    )

    response = ctrl.build_chat_response("what happened with BHP this week")

    assert response.text.startswith("BHP API synthesis.")
    assert response.routing_metadata["source"] == "api"
    assert response.routing_metadata["model"] == "claude-sonnet-test"
    assert hybrid_router.calls[0]["force_backend"] is None
    ctrl.ollama_client.chat.assert_not_called()
    assert ctrl._agent_loop.calls == []


def test_recent_update_missing_financial_guard_keeps_event_summary() -> None:
    ctrl = _controller(_result("mixed", ("financial_truth", "company_memory"), ticker="GNC"))
    ctrl.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "ticker": "GNC",
            "docs": [
                {
                    "title": "Ceasing to be a substantial holder",
                    "published_at": "2026-03-24T00:00:00Z",
                }
            ],
            "doc_snippets": [],
            "financials": [],
            "price": {
                "ok": True,
                "symbol": "GNC.AX",
                "current": {
                    "price": 6.155,
                    "previous_close": 6.14,
                    "change_percent": 0.24,
                },
                "recent_history": [
                    {"timestamp": "2026-04-24T00:00:00Z", "close": 6.0},
                    {"timestamp": "2026-04-27T00:00:00Z", "close": 6.05},
                    {"timestamp": "2026-04-28T00:00:00Z", "close": 6.1},
                    {"timestamp": "2026-04-29T00:00:00Z", "close": 6.14},
                    {"timestamp": "2026-04-30T00:00:00Z", "close": 6.155},
                ],
            },
            "price_state": {"trend_regime": "neutral", "last_close": 6.155},
            "qual_context_news": {"hits": []},
            "qual_context": {"hits": []},
            "sources": {},
        }
    )
    ctrl.ollama_client.chat.return_value = (
        "| Metric | Value |\n|---|---|\n| Profit margin | 5% |"
    )
    ctrl.action_registry.preview.return_value = SimpleNamespace(
        command=["python", "scripts/full_history_ticker_sync.py", "--ticker", "GNC"],
        estimated_impact="mutates local data and reports",
        timeout_seconds=14400,
    )

    response = ctrl.build_chat_response("what happened with gnc")

    assert "**GNC recent update**" in response.text
    assert "Recent price action for GNC.AX" in response.text
    assert "Ceasing to be a substantial holder" in response.text
    assert "No recent indexed news hits" in response.text
    assert "Detailed extracted financial metrics are not currently available" not in response.text
    assert response.action_preview is not None
    assert response.action_preview["action_id"] == "update_ticker_financials"


def test_cloud_prefix_bypasses_local_document_grounding_and_uses_agent_loop() -> None:
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

    response = ctrl.build_chat_response("/cloud What does the document say about BHP?")

    assert response.text == "Agent API answer."
    assert response.routing_metadata["source"] == "api"
    assert ctrl.tool_router.gather_local_context.call_count == 0
    assert ctrl._agent_loop.calls[0]["mode"] == "run"
    assert ctrl._agent_loop.calls[0]["message"] == "/cloud What does the document say about BHP?"


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


def test_collect_cockpit_local_memory_uses_active_thread_for_watchlist_history() -> None:
    ctrl = ChatController.__new__(ChatController)
    ctrl._thread_id = "global-main"
    ctrl._dossier_service = None
    ctrl._strategy_service = None

    class _StateStore:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, int]] = []

        def get_entity_observations(self, ticker: str, limit: int = 200):
            return []

        def list_update_events(
            self,
            thread_id: str,
            *,
            ticker: str | None = None,
            limit: int = 10,
            status: str | None = None,
        ):
            self.calls.append((thread_id, str(ticker), limit))
            if thread_id != "global-main":
                return []
            return [
                {
                    "thread_id": thread_id,
                    "ticker": str(ticker),
                    "action_id": "watchlist:add",
                    "status": "applied",
                    "summary": {"decision": "watchlist"},
                    "created_at": "2026-04-18T00:00:00Z",
                }
            ]

    ctrl._state_store = _StateStore()

    payload = ctrl._collect_cockpit_local_memory("BHP")

    assert ctrl._state_store.calls == [("global-main", "BHP", 100)]
    assert payload["watchlist_history"] == [
        {
            "thread_id": "global-main",
            "ticker": "BHP",
            "action_id": "watchlist:add",
            "status": "applied",
            "summary": {"decision": "watchlist"},
            "created_at": "2026-04-18T00:00:00Z",
        }
    ]
