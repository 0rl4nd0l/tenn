from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.query_orchestrator import (
    QueryOrchestrator,
    build_plan,
    classify,
    orchestrate_query,
    resolve,
)


def test_classify_financial_fact_query() -> None:
    assert classify("What was BHP revenue last half?") == "financial_fact"


def test_classify_financial_interpretation_query() -> None:
    assert classify("What does BHP net debt imply about balance sheet strength?") == (
        "financial_interpretation"
    )


def test_classify_strategy_query() -> None:
    assert classify("What is the investment thesis for BHP?") == "strategy"


def test_classify_risk_catalyst_query() -> None:
    assert classify("What are the key risks and catalysts for BHP?") == (
        "risk_catalyst"
    )


def test_classify_market_query() -> None:
    assert classify("How is the iron ore sector trading right now?") == "market"


def test_classify_mixed_query() -> None:
    assert classify("Compare BHP revenue growth with the iron ore market outlook") == (
        "mixed"
    )


def test_build_plan_routes_financial_fact_to_financial_truth_only() -> None:
    plan = build_plan("financial_fact")

    assert plan.sources == ("financial_truth",)
    assert plan.needs_numbers is True
    assert plan.needs_meaning is False
    assert plan.needs_environment is False


def test_build_plan_routes_interpretation_to_all_layers() -> None:
    plan = build_plan("financial_interpretation")

    assert plan.sources == (
        "financial_truth",
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    )
    assert plan.needs_numbers is True
    assert plan.needs_meaning is True
    assert plan.needs_environment is True


def test_orchestrator_calls_only_financial_truth_for_fact_query() -> None:
    class FinancialTruthProvider:
        def __init__(self) -> None:
            self.calls = 0

        def retrieve(self, *, query, entities, intent):
            self.calls += 1
            return {
                "source": "financial_truth",
                "items": [{"ticker": entities["primary_ticker"]}],
            }

    class MemoryProvider:
        def __init__(self) -> None:
            self.calls = 0

        def retrieve(self, *, query, entities, intent):
            self.calls += 1
            return {"items": []}

    truth = FinancialTruthProvider()
    company = MemoryProvider()
    market = MemoryProvider()

    result = orchestrate_query(
        "What was BHP revenue?",
        financial_truth_provider=truth,
        company_memory_provider=company,
        market_memory_provider=market,
    )

    assert result.intent == "financial_fact"
    assert result.entities["primary_ticker"] == "BHP"
    assert truth.calls == 1
    assert company.calls == 0
    assert market.calls == 0
    assert result.evidence["financial_truth"]["items"][0]["ticker"] == "BHP"


def test_orchestrator_calls_company_and_market_memory_for_risk_query() -> None:
    class Provider:
        def __init__(self, name: str) -> None:
            self.name = name
            self.calls = 0

        def retrieve(self, *, query, entities, intent):
            self.calls += 1
            return {"source": self.name, "items": [intent, entities["primary_ticker"]]}

    truth = Provider("financial_truth")
    company = Provider("company_memory")
    market = Provider("market_memory")

    result = QueryOrchestrator(
        financial_truth_provider=truth,
        company_memory_provider=company,
        market_memory_provider=market,
    ).orchestrate_query("What are the risks and catalysts for BHP?")

    assert result.intent == "risk_catalyst"
    assert truth.calls == 0
    assert company.calls == 1
    assert market.calls == 1
    assert result.plan.sources == (
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    )
    assert result.answer["sources_used"] == [
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    ]


def test_orchestrator_uses_all_layers_for_mixed_query() -> None:
    class Provider:
        def __init__(self, name: str) -> None:
            self.name = name

        def retrieve(self, *, query, entities, intent):
            return {
                "source": self.name,
                "query": query,
                "ticker": entities["primary_ticker"],
            }

    result = orchestrate_query(
        "Compare BHP revenue growth with the iron ore market outlook",
        financial_truth_provider=Provider("financial_truth"),
        company_memory_provider=Provider("company_memory"),
        market_memory_provider=Provider("market_memory"),
    )

    assert result.intent == "mixed"
    assert result.plan.sources == (
        "financial_truth",
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    )
    assert result.answer["sources_used"] == [
        "financial_truth",
        "company_memory",
        "market_memory",
        "user_thesis_memory",
    ]


def test_orchestrator_returns_unavailable_note_when_provider_missing() -> None:
    result = orchestrate_query("What was BHP revenue?")

    assert result.intent == "financial_fact"
    assert result.answer["sources_used"] == ["financial_truth"]
    assert "not configured" in " ".join(result.answer["notes"]).lower()


def test_resolve_ignores_tell_as_fake_ticker_before_real_ticker() -> None:
    entities = resolve("tell me about BHP")

    assert entities["primary_ticker"] == "BHP"
    assert entities["tickers"] == ["BHP"]


def test_resolve_keeps_summary_prompt_fillers_out_of_ticker_list() -> None:
    entities = resolve("Summarize BHP in one sentence")

    assert entities["primary_ticker"] == "BHP"
    assert entities["tickers"] == ["BHP"]


def test_resolve_rejects_plain_language_false_ticker() -> None:
    entities = resolve("How are things going?")

    assert entities["primary_ticker"] is None
    assert entities["tickers"] == []


def test_resolve_keeps_document_prompt_from_promoting_say_to_ticker() -> None:
    entities = resolve("What does the document say about BHP?")

    assert entities["primary_ticker"] == "BHP"
    assert entities["tickers"] == ["BHP"]


def test_resolve_keeps_sector_prompt_tickerless() -> None:
    entities = resolve("How is the iron ore sector trading right now?")

    assert entities["primary_ticker"] is None
    assert entities["tickers"] == []
    assert entities["sector"] == "Materials"


def test_resolve_hydrogen_industry_as_energy_sector_without_ticker() -> None:
    entities = resolve("tell me about hydrogen industry")

    assert entities["primary_ticker"] is None
    assert entities["tickers"] == []
    assert entities["sector"] == "Energy"


def test_financial_fact_answer_input_keeps_only_financial_truth_section() -> None:
    class TruthProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "latest_financial_snapshot": {
                    "period_end": "2025-12-31",
                    "revenue": 55000,
                    "net_debt": 3200,
                },
                "financials": [
                    {"period_end": "2025-12-31"},
                    {"period_end": "2025-06-30"},
                ],
            }

    result = orchestrate_query(
        "What was BHP revenue?",
        financial_truth_provider=TruthProvider(),
    )

    assert "Facts from financial truth:" in result.answer_input
    assert "Interpretation from company memory:" not in result.answer_input
    assert "External context from market memory:" not in result.answer_input
    assert (
        "Numbers must come from canonical financial truth only." in result.answer_input
    )


def test_strategy_answer_input_prioritizes_company_memory_signal_quality() -> None:
    class CompanyProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "items": [
                    {
                        "type": "interpretation",
                        "statement": "The setup looks interesting.",
                        "active_score": 0.4,
                        "metadata": {"themes": ["growth"]},
                    },
                    {
                        "type": "strategic_initiative",
                        "statement": "BHP is expanding copper capacity through the South Australia program.",
                        "active_score": 0.86,
                        "metadata": {"themes": ["growth"]},
                    },
                    {
                        "type": "management_guidance",
                        "statement": "Management is prioritising free cash flow discipline.",
                        "active_score": 0.8,
                        "metadata": {"themes": ["costs"]},
                    },
                ],
            }

    result = orchestrate_query(
        "What is the investment thesis for BHP?",
        company_memory_provider=CompanyProvider(),
    )

    assert "Interpretation from company memory:" in result.answer_input
    assert (
        "strategic initiative: BHP is expanding copper capacity through the South Australia program."
        in result.answer_input
    )
    assert "The setup looks interesting." not in result.answer_input


def test_market_answer_input_uses_market_budgets_and_context_only() -> None:
    class MarketProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "sector": "Materials",
                "sector_items": [
                    {
                        "type": "sector_trend",
                        "statement": "Iron ore supply discipline is improving.",
                        "active_score": 0.82,
                        "metadata": {"themes": ["supply"]},
                    },
                    {
                        "type": "sector_risk",
                        "statement": "Port congestion is re-emerging.",
                        "active_score": 0.74,
                        "metadata": {"themes": ["operations"]},
                    },
                ],
                "macro_items": [
                    {
                        "type": "macro_theme",
                        "statement": "China demand remains supportive.",
                        "active_score": 0.79,
                        "metadata": {"themes": ["demand"]},
                    }
                ],
            }

    result = orchestrate_query(
        "How is the iron ore sector trading right now?",
        market_memory_provider=MarketProvider(),
    )

    assert "Facts from financial truth:" not in result.answer_input
    assert "Interpretation from company memory:" not in result.answer_input
    assert "External context from market memory:" in result.answer_input
    assert "- relevant sector: Materials" in result.answer_input
    assert "- sector: Iron ore supply discipline is improving." in result.answer_input
    assert "- macro: China demand remains supportive." in result.answer_input


def test_hydrogen_sector_prompt_uses_backend_market_memory_scope() -> None:
    class MarketProvider:
        def __init__(self) -> None:
            self.entities: dict | None = None

        def retrieve(self, *, query, entities, intent):
            self.entities = entities
            return {
                "status": "ok",
                "sector": entities.get("sector"),
                "sector_items": [
                    {
                        "type": "sector_trend",
                        "statement": "Hydrogen project economics remain sensitive to offtake demand.",
                        "active_score": 0.82,
                        "metadata": {"themes": ["hydrogen"]},
                    }
                ],
                "macro_items": [],
                "items": [
                    {
                        "type": "sector_trend",
                        "statement": "Hydrogen project economics remain sensitive to offtake demand.",
                    }
                ],
            }

    market = MarketProvider()
    result = orchestrate_query(
        "tell me about hydrogen industry",
        market_memory_provider=market,
    )

    assert result.intent == "market"
    assert market.entities == {
        "primary_ticker": None,
        "tickers": [],
        "sector": "Energy",
    }
    assert result.market_memory_results["sector"] == "Energy"
    assert "- relevant sector: Energy" in result.answer_input
    assert "Hydrogen project economics remain sensitive" in result.answer_input
    assert result.sufficient_for_analysis is True


def test_sector_prompt_with_no_market_memory_abstains_without_agent_fallback() -> None:
    class EmptyMarketProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "sector": entities.get("sector"),
                "sector_items": [],
                "macro_items": [],
                "items": [],
            }

    result = orchestrate_query(
        "tell me about hydrogen industry",
        market_memory_provider=EmptyMarketProvider(),
    )

    assert result.entities["sector"] == "Energy"
    assert result.sufficient_for_analysis is False
    assert result.missing_categories_after_recovery == ("market_context",)
    assert "Final verdict: abstain" in result.answer_input
    assert "- market_context" in result.answer_input


def test_mixed_answer_input_separates_facts_interpretation_and_context() -> None:
    class Provider:
        def __init__(self, payload):
            self.payload = payload

        def retrieve(self, *, query, entities, intent):
            return self.payload

    result = orchestrate_query(
        "Compare BHP revenue growth with the iron ore market outlook",
        financial_truth_provider=Provider(
            {
                "status": "ok",
                "latest_financial_snapshot": {
                    "period_end": "2025-12-31",
                    "revenue": 55000,
                    "ebit": 21000,
                },
                "financials": [
                    {"period_end": "2025-12-31"},
                    {"period_end": "2025-06-30"},
                    {"period_end": "2024-12-31"},
                ],
            }
        ),
        company_memory_provider=Provider(
            {
                "status": "ok",
                "items": [
                    {
                        "type": "management_guidance",
                        "statement": "Management expects copper growth to offset softer iron ore grades.",
                        "active_score": 0.84,
                        "metadata": {"themes": ["growth"]},
                    }
                ],
            }
        ),
        market_memory_provider=Provider(
            {
                "status": "ok",
                "sector": "Materials",
                "sector_items": [
                    {
                        "type": "sector_trend",
                        "statement": "Iron ore pricing remains range-bound.",
                        "active_score": 0.78,
                        "metadata": {"themes": ["pricing"]},
                    }
                ],
                "macro_items": [
                    {
                        "type": "macro_theme",
                        "statement": "China demand remains uneven.",
                        "active_score": 0.76,
                        "metadata": {"themes": ["demand"]},
                    }
                ],
            }
        ),
    )

    assert "Facts from financial truth:" in result.answer_input
    assert "Interpretation from company memory:" in result.answer_input
    assert "External context from market memory:" in result.answer_input
    assert result.answer_input.index(
        "Facts from financial truth:"
    ) < result.answer_input.index("Interpretation from company memory:")
    assert result.answer_input.index(
        "Interpretation from company memory:"
    ) < result.answer_input.index("External context from market memory:")


def test_company_analysis_runs_bounded_missing_data_recovery_and_recovers_financials() -> None:
    class FinancialTruthProvider:
        def __init__(self) -> None:
            self.calls = 0

        def retrieve(self, *, query, entities, intent):
            self.calls += 1
            if str(entities.get("recovery_level") or "").strip().lower() == "deep":
                return {
                    "status": "ok",
                    "ticker": entities.get("primary_ticker"),
                    "financials": [{"period_end": "2025-12-31", "revenue": 55000}],
                    "latest_financial_snapshot": {
                        "period_end": "2025-12-31",
                        "revenue": 55000,
                    },
                    "docs": [
                        {
                            "title": "FY25 Results",
                            "published_at": "2026-04-20T01:00:00Z",
                        }
                    ],
                    "announcement_context": [
                        {
                            "title": "Quarterly Update",
                            "published_at": "2026-04-19T01:00:00Z",
                        }
                    ],
                    "extraction_failures": [],
                    "low_confidence_financials": [],
                }
            return {
                "status": "ok",
                "ticker": entities.get("primary_ticker"),
                "financials": [],
                "latest_financial_snapshot": {},
                "docs": [],
                "announcement_context": [],
                "extraction_failures": [],
                "low_confidence_financials": [],
            }

    class CompanyProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "items": [
                    {
                        "type": "management_guidance",
                        "statement": "Management is prioritising balance sheet strength.",
                        "active_score": 0.8,
                        "metadata": {"themes": ["balance sheet"]},
                    }
                ],
            }

    result = QueryOrchestrator(
        financial_truth_provider=FinancialTruthProvider(),
        company_memory_provider=CompanyProvider(),
    ).orchestrate_query_with_context(
        "Give me a deep company analysis on BHP",
        context={"request_standard": "company_analysis", "analysis_mode": "deep"},
    )

    assert result.missing_data_recovery["attempted"] is True
    assert "financials" in result.missing_categories_before_recovery
    assert "financials" not in result.missing_categories_after_recovery
    assert result.sufficient_for_analysis is True
    assert "Recovery outcome: sufficient evidence available" in result.answer_input
    assert "Final verdict: abstain" not in result.answer_input


def test_company_analysis_abstains_after_recovery_when_blockers_remain() -> None:
    class EmptyProvider:
        def retrieve(self, *, query, entities, intent):
            return {
                "status": "ok",
                "financials": [],
                "latest_financial_snapshot": {},
                "docs": [],
                "announcement_context": [],
                "items": [],
                "sector_items": [],
                "macro_items": [],
                "extraction_failures": [],
                "low_confidence_financials": [],
            }

    result = QueryOrchestrator(
        financial_truth_provider=EmptyProvider(),
        company_memory_provider=EmptyProvider(),
        market_memory_provider=EmptyProvider(),
    ).orchestrate_query_with_context(
        "Full company analysis for BHP",
        context={"request_standard": "company_analysis", "analysis_mode": "deep"},
    )

    assert result.missing_data_recovery["attempted"] is True
    assert result.sufficient_for_analysis is False
    assert "Final verdict: abstain" in result.answer_input
    assert "financials" in result.missing_categories_after_recovery
