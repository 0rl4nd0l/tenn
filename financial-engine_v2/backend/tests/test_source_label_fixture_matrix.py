from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat_evidence_guard import (  # noqa: E402
    RECENT_NEWS_EVENT,
    RECENT_NEWS_OR_UPDATE,
    evaluate_chat_evidence_requirements,
    evidence_categories_for_source,
)


SOURCE_LABEL_MATRIX = [
    {
        "name": "live_price_source",
        "source": {
            "title": "CSL live price data",
            "source_id": "price:CSL:current:1d",
            "kind": "context",
            "snippet": "Provider: yahoo. Market time: 2026-05-31.",
            "evidence_labels": ["operational_trace"],
            "claim_verified": False,
        },
        "expected_categories": {"market_data", "price_series"},
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT, "no_hit"},
        "direct_claim_verified": False,
    },
    {
        "name": "historical_financial_source",
        "source": {
            "title": "BHP FY24 annual report",
            "source_id": "asx_document:BHP:FY24",
            "kind": "document",
            "doc_type": "annual_report",
            "snippet": "Historical financial statement context.",
            "evidence_labels": ["context_only"],
            "claim_verified": False,
        },
        "expected_categories": {
            "context_only",
            "extracted_metric",
            "financial_statement",
            "financial_truth_numeric",
            "filing",
        },
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "weak_local_news_context",
        "source": {
            "title": "CSL scan-list mention",
            "source_id": "news:scan-list:1",
            "kind": "news",
            "doc_type": "news",
            "snippet": "Ticker appeared in a local scan list.",
            "evidence_labels": ["context_only", "local_news_context"],
            "claim_verified": False,
        },
        "expected_categories": {"context_only", "news"},
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "data_missing",
        "source": {
            "title": "Missing required evidence",
            "kind": "context",
            "doc_type": "missing_required_evidence",
            "evidence_labels": ["missing_required_evidence"],
            "claim_verified": False,
        },
        "expected_categories": {"no_hit"},
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "no_hit",
        "source": {
            "title": "TradingView screener no rows",
            "kind": "context",
            "doc_type": "operational_no_hit",
            "source_id": "tv_screener:ASX",
            "snippet": "Screener returned no rows for this query.",
            "evidence_labels": ["no_hit", "operational_trace"],
            "claim_verified": False,
        },
        "expected_categories": {"no_hit"},
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "degraded_runtime",
        "source": {
            "title": "Provider timeout",
            "kind": "context",
            "doc_type": "runtime_failure",
            "source_id": "runtime_failure:price-provider",
            "evidence_labels": ["degraded_runtime"],
            "claim_verified": False,
        },
        "expected_categories": {"degraded_runtime", "no_hit"},
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "memory_context",
        "source": {
            "title": "Company memory note",
            "kind": "context",
            "source_id": "memory:company:CSL",
            "snippet": "Stored company-memory note.",
            "evidence_labels": ["memory_context"],
            "claim_verified": False,
        },
        "expected_categories": set(),
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "external_web_context",
        "source": {
            "title": "External web snippet",
            "kind": "context",
            "source_id": "web:snippet:1",
            "snippet": "External search snippet context.",
            "evidence_labels": ["external_web_context"],
            "claim_verified": False,
        },
        "expected_categories": set(),
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "unknown_unclassified_snippet",
        "source": {
            "title": "Snippet-only context",
            "kind": "context",
            "snippet": "Unclassified context without source identity.",
            "evidence_labels": ["unknown_unclassified"],
            "claim_verified": False,
        },
        "expected_categories": set(),
        "forbidden_categories": {"claim_verified", RECENT_NEWS_EVENT},
        "direct_claim_verified": False,
    },
    {
        "name": "direct_claim_verified_news_event",
        "source": {
            "title": "CSL verified news event",
            "source_id": "news:csl-verified-event:1",
            "kind": "news",
            "doc_type": "news",
            "snippet": "Directly supports the latest event claim.",
            "evidence_labels": ["claim_verified"],
            "source_role_labels": ["recent_news_event"],
            "claim_verified": True,
        },
        "expected_categories": {
            "claim_verified",
            "event_source",
            "news",
            RECENT_NEWS_EVENT,
        },
        "forbidden_categories": {"context_only", "no_hit", "degraded_runtime"},
        "direct_claim_verified": True,
    },
]


@pytest.mark.parametrize("row", SOURCE_LABEL_MATRIX, ids=lambda row: row["name"])
def test_backend_source_label_fixture_matrix_category_boundaries(row: dict) -> None:
    categories = evidence_categories_for_source(row["source"])

    assert row["expected_categories"] <= categories
    assert categories.isdisjoint(row["forbidden_categories"])
    assert ("claim_verified" in categories) is row["direct_claim_verified"]


@pytest.mark.parametrize("row", SOURCE_LABEL_MATRIX, ids=lambda row: row["name"])
def test_recent_news_requires_direct_claim_verified_event(row: dict) -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL latest news update describes a verified event.",
        sources=[row["source"]],
    )

    assert RECENT_NEWS_OR_UPDATE in result["claim_families"]
    if row["direct_claim_verified"]:
        assert RECENT_NEWS_EVENT in result["evidence_categories"]
        assert "recent_news" not in result["missing_evidence_categories"]
        assert RECENT_NEWS_OR_UPDATE not in result["unsupported_claim_families"]
        return

    assert RECENT_NEWS_EVENT not in result["evidence_categories"]
    assert "recent_news" in result["missing_evidence_categories"]
    assert "insufficient_for_recent_news" in result["evidence_requirement_labels"]
    assert RECENT_NEWS_OR_UPDATE in result["unsupported_claim_families"]
