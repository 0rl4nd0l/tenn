import pytest
from app.services.query_orchestrator import _is_sufficient_for_company_analysis, OrchestratedQueryResult

def test_is_sufficient_for_company_analysis_speculative():
    # Scenario: No financials, but docs exist
    evidence = {
        "financial_truth": {
            "financials": [],
            "latest_financial_snapshot": {},
            "docs": [{"title": "Annual Report 2025"}]
        },
        "company_memory": {"items": []},
        "market_memory": {"items": []}
    }
    # "financials" is missing
    missing_categories = ["financials"]
    
    sufficient, speculative = _is_sufficient_for_company_analysis(
        evidence=evidence,
        missing_categories=missing_categories
    )
    
    assert sufficient is True
    assert speculative is True

def test_is_sufficient_for_company_analysis_insufficient():
    # Scenario: No financials, no docs
    evidence = {
        "financial_truth": {
            "financials": [],
            "latest_financial_snapshot": {},
            "docs": []
        },
        "company_memory": {"items": []},
        "market_memory": {"items": []}
    }
    missing_categories = ["financials", "announcements_news_context"]
    
    sufficient, speculative = _is_sufficient_for_company_analysis(
        evidence=evidence,
        missing_categories=missing_categories
    )
    
    assert sufficient is False
    assert speculative is False

def test_is_sufficient_for_company_analysis_standard():
    # Scenario: Financials exist
    evidence = {
        "financial_truth": {
            "financials": [{"period_end": "2025-06-30"}],
            "docs": []
        },
        "company_memory": {"items": [{"content": "business context"}]},
        "market_memory": {"items": []}
    }
    missing_categories = []
    
    sufficient, speculative = _is_sufficient_for_company_analysis(
        evidence=evidence,
        missing_categories=missing_categories
    )
    
    assert sufficient is True
    assert speculative is False
