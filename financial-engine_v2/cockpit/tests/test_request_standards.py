from __future__ import annotations

from types import SimpleNamespace
from typing import Literal
from unittest.mock import MagicMock

import pytest

from cockpit.core.chat import ChatController, ChatResponse, ResponseMode
from cockpit.core.conversation_commands import derive_conversational_command
from cockpit.core.request_standards import (
    REQUEST_STANDARD_REGISTRY,
    build_request_standard_prompt_guidance,
    company_analysis_prompt_guidance,
    get_request_standard_path,
    normalize_request_standard_type,
    select_request_standard_type,
)


def _classify_routing_class(message: str) -> Literal["llm_guided", "deterministic_bypass"]:
    text = str(message or "").strip()
    if text.startswith("/"):
        return "deterministic_bypass"
    if derive_conversational_command(text):
        return "deterministic_bypass"
    return "llm_guided"


def test_all_registered_standard_paths_exist() -> None:
    for request_type, filename in REQUEST_STANDARD_REGISTRY.items():
        path = get_request_standard_path(request_type)
        assert path is not None
        assert path.name == filename
        assert path.is_file()


def test_unknown_request_standard_returns_none() -> None:
    assert get_request_standard_path("intraday_momentum_scan") is None


def test_request_standard_type_normalization_aliases() -> None:
    assert normalize_request_standard_type("company-analysis") == "company_analysis"
    assert normalize_request_standard_type("industry analysis") == "sector_analysis"
    assert normalize_request_standard_type("watchlist-triage") == "watchlist_triage"
    assert normalize_request_standard_type("not-a-standard") is None


def test_company_analysis_prompt_guidance_contains_required_markers() -> None:
    guidance = company_analysis_prompt_guidance()
    assert "company_analysis.md" in guidance
    assert "Verdict, Evidence, Risks, Counterpoints, Unknowns" in guidance
    assert "confirmation-gated" in guidance


def test_select_request_standard_company_analysis_for_ticker_deep_mode() -> None:
    request_type = select_request_standard_type(
        message="give me a deep investment view on BHP",
        mode="deep_analysis",
        ticker="BHP",
    )
    assert request_type == "company_analysis"


def test_select_request_standard_company_analysis_for_company_review_phrase() -> None:
    request_type = select_request_standard_type(
        message="give me a full company review on BHP",
        mode="fast",
        ticker="BHP",
    )
    assert request_type == "company_analysis"


def test_build_guidance_for_daily_market_update_trigger() -> None:
    guidance = build_request_standard_prompt_guidance(
        message="today's market update please",
        mode="fast",
        ticker=None,
    )
    assert "[daily_market_update]" in guidance
    assert "daily_market_update.md" in guidance
    assert "market-wide update" in guidance


@pytest.mark.parametrize(
    "message",
    (
        "give me a market wrap for today",
        "what were the biggest movers today across the ASX?",
    ),
)
def test_build_guidance_for_daily_market_update_extended_triggers(message: str) -> None:
    guidance = build_request_standard_prompt_guidance(
        message=message,
        mode="fast",
        ticker=None,
    )
    assert "[daily_market_update]" in guidance
    assert "daily_market_update.md" in guidance


def test_build_guidance_for_sector_analysis_trigger() -> None:
    guidance = build_request_standard_prompt_guidance(
        message="can you do a sector analysis on lithium",
        mode="deep_analysis",
        ticker=None,
    )
    assert "[sector_analysis]" in guidance
    assert "sector_analysis.md" in guidance
    assert "sector/industry scope" in guidance


def test_build_guidance_for_watchlist_triage_trigger() -> None:
    guidance = build_request_standard_prompt_guidance(
        message="/watch scan",
        mode="action",
        ticker=None,
    )
    assert "[watchlist_triage]" in guidance
    assert "watchlist_triage.md" in guidance
    assert "prioritization" in guidance


def test_build_guidance_empty_for_non_matching_request() -> None:
    guidance = build_request_standard_prompt_guidance(
        message="hello world",
        mode="fast",
        ticker=None,
    )
    assert guidance == ""


def test_structured_agent_path_receives_request_standard_guidance(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COCKPIT_AGENT_MODE", "structured")

    controller = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
    )
    controller._query_orchestrator = None
    controller._agent_loop = object()

    captured: dict[str, str] = {}

    def _fake_run_agent_loop(
        *_args,
        request_standard_guidance: str = "",
        **_kwargs,
    ) -> ChatResponse:
        captured["guidance"] = request_standard_guidance
        return ChatResponse(text="ok", evidence=[], mode=ResponseMode.FAST)

    controller._run_agent_loop = _fake_run_agent_loop  # type: ignore[method-assign]
    response = controller.build_chat_response(
        "deep analysis analyse BHP with focus on liquidity",
        analysis_mode="deep",
    )

    assert response.text == "ok"
    assert "[company_analysis]" in captured["guidance"]


def test_orchestrated_path_receives_request_standard_guidance(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COCKPIT_AGENT_MODE", "structured")

    controller = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
    )

    controller._query_orchestrator = SimpleNamespace(
        orchestrate_query_with_context=lambda *_args, **_kwargs: SimpleNamespace(
            intent="analysis",
            source_plan=["financial_truth"],
            entities={},
            answer={"source_status": {"financial_truth": {"ok": True}}},
            answer_input="draft answer",
            raw_supporting_evidence={"financial_truth": {"items": [{"ticker": "BHP"}]}},
            financial_truth_results={"items": [{"ticker": "BHP"}]},
            company_memory_results={"items": []},
            market_memory_results={"items": []},
        )
    )
    controller._agent_loop = object()

    captured: dict[str, str] = {}

    def _fake_build_orchestrated_response(**kwargs) -> ChatResponse:
        captured["guidance"] = str(kwargs.get("request_standard_guidance") or "")
        return ChatResponse(text="orchestrated", evidence=[], mode=ResponseMode.FAST)

    controller._build_orchestrated_response = _fake_build_orchestrated_response  # type: ignore[method-assign]

    response = controller.build_chat_response("sector analysis on lithium producers")

    assert response.text == "orchestrated"
    assert "[sector_analysis]" in captured["guidance"]


def test_keyword_path_receives_company_analysis_guidance_for_review_phrase(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COCKPIT_AGENT_MODE", "keyword")
    controller = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
    )
    controller.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "docs": [{"title": "BHP quarterly update"}],
            "financials": [],
            "qual_context": {"hits": []},
            "sources": {},
        }
    )
    controller.ollama_client.chat.return_value = "ok"

    response = controller.build_chat_response("give me a full company review on BHP")

    assert response.text == "ok"
    system_prompt = controller.ollama_client.chat.call_args.kwargs["prior_messages"][0][
        "content"
    ]
    assert "[company_analysis]" in system_prompt


def test_keyword_path_receives_daily_market_update_guidance_for_market_wrap_phrase(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COCKPIT_AGENT_MODE", "keyword")
    controller = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
    )
    controller.tool_router.gather_local_context.return_value = SimpleNamespace(
        payload={
            "docs": [],
            "financials": [],
            "qual_context": {"hits": []},
            "sources": {},
        }
    )
    controller.ollama_client.chat.return_value = "ok"

    response = controller.build_chat_response("give me a market wrap for today")

    assert response.text == "ok"
    system_prompt = controller.ollama_client.chat.call_args.kwargs["prior_messages"][0][
        "content"
    ]
    assert "[daily_market_update]" in system_prompt


def test_daily_market_update_conversational_command_rewrite_bypasses_llm() -> None:
    assert derive_conversational_command("today's market update") == "/market-update final"

    controller = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
        state_store=None,
    )
    response = controller.build_chat_response("today's market update")

    assert "Market-update reports not available" in response.text
    controller.ollama_client.chat.assert_not_called()


@pytest.mark.parametrize(
    ("message", "mode", "ticker", "expected_standard", "expected_routing_class"),
    (
        (
            "give me a full company review on BHP",
            "fast",
            "BHP",
            "company_analysis",
            "llm_guided",
        ),
        (
            "give me an investment thesis on CSL",
            "fast",
            "CSL",
            "company_analysis",
            "llm_guided",
        ),
        (
            "give me a market wrap for today",
            "fast",
            None,
            "daily_market_update",
            "llm_guided",
        ),
        (
            "what were the biggest movers today across the ASX?",
            "fast",
            None,
            "daily_market_update",
            "llm_guided",
        ),
        (
            "can you do a sector analysis on lithium",
            "deep_analysis",
            None,
            "sector_analysis",
            "llm_guided",
        ),
        (
            "triage the watchlist before open",
            "fast",
            None,
            "watchlist_triage",
            "llm_guided",
        ),
        (
            "today's market update",
            "fast",
            None,
            "daily_market_update",
            "deterministic_bypass",
        ),
        (
            "/market-update final",
            "fast",
            None,
            "daily_market_update",
            "deterministic_bypass",
        ),
        (
            "run the market update",
            "fast",
            None,
            None,
            "deterministic_bypass",
        ),
        (
            "scan my watchlist",
            "fast",
            None,
            "watchlist_triage",
            "deterministic_bypass",
        ),
        (
            "/watch scan",
            "action",
            None,
            "watchlist_triage",
            "deterministic_bypass",
        ),
    ),
    ids=(
        "company-review-llm-guided",
        "investment-thesis-llm-guided",
        "market-wrap-llm-guided",
        "biggest-movers-llm-guided",
        "sector-analysis-llm-guided",
        "watchlist-triage-llm-guided",
        "todays-market-update-conversational-bypass",
        "slash-market-update-bypass",
        "run-market-update-bypass",
        "scan-watchlist-conversational-bypass",
        "slash-watch-scan-bypass",
    ),
)
def test_request_standards_conformance_matrix(
    message: str,
    mode: str,
    ticker: str | None,
    expected_standard: str | None,
    expected_routing_class: Literal["llm_guided", "deterministic_bypass"],
) -> None:
    selected_standard = select_request_standard_type(
        message=message,
        mode=mode,
        ticker=ticker,
    )
    routing_class = _classify_routing_class(message)

    assert selected_standard == expected_standard
    assert routing_class == expected_routing_class
