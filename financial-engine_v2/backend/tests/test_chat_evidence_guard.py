from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.chat_evidence_guard import (
    BUYBACK_ACTIVITY,
    FINANCIAL_METRIC,
    MARKET_PRICE_OR_TECHNICAL_TREND,
    RECENT_NEWS_OR_UPDATE,
    TARIFF_REGULATORY,
    apply_visible_evidence_gap_labels,
    enrich_chat_metadata_with_evidence_guard,
    evaluate_chat_evidence_requirements,
)


def test_filing_only_context_cannot_verify_price_trend_claim() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text=(
            "CSL looks bearish on the current price trend, while the filing shows "
            "a buy-back notice."
        ),
        sources=[
            {
                "title": "CSL Appendix 3C buy-back notice",
                "kind": "document",
                "doc_type": "asx_announcement",
                "snippet": "CSL lodged an on-market buy-back notice.",
                "evidence_labels": ["context_only"],
                "claim_verified": False,
            }
        ],
        metadata={"source_coverage_status": "context_only"},
    )

    assert MARKET_PRICE_OR_TECHNICAL_TREND in result["claim_families"]
    assert "filing" in result["evidence_categories"]
    assert "market_data" in result["missing_evidence_categories"]
    assert "market_data_missing" in result["evidence_requirement_labels"]
    assert "unsupported_or_not_verified" in result["evidence_requirement_labels"]
    assert MARKET_PRICE_OR_TECHNICAL_TREND in result["unsupported_claim_families"]
    assert BUYBACK_ACTIVITY not in result["unsupported_claim_families"]


def test_price_evidence_satisfies_price_trend_requirement() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL price trend is weakening based on visible price data.",
        sources=[
            {
                "title": "CSL price data",
                "source_id": "price:CSL:1y:1d",
                "kind": "context",
                "snippet": "Provider: yahoo. Market time: 2026-05-24.",
                "evidence_labels": ["operational_trace"],
            }
        ],
    )

    assert MARKET_PRICE_OR_TECHNICAL_TREND in result["claim_families"]
    assert "market_data" in result["evidence_categories"]
    assert "price_series" in result["evidence_categories"]
    assert result["missing_evidence_categories"] == []
    assert MARKET_PRICE_OR_TECHNICAL_TREND not in result["unsupported_claim_families"]


def test_price_status_today_does_not_require_news_evidence() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL current price trend today is flat based on visible price data.",
        sources=[
            {
                "title": "CSL price data",
                "source_id": "price:CSL:current:1d",
                "kind": "context",
                "snippet": "price: 284.50; market time: 2026-05-24.",
                "evidence_labels": ["operational_trace"],
            }
        ],
    )

    assert MARKET_PRICE_OR_TECHNICAL_TREND in result["claim_families"]
    assert RECENT_NEWS_OR_UPDATE not in result["claim_families"]
    assert "insufficient_for_recent_news" not in result["evidence_requirement_labels"]
    assert result["missing_evidence_categories"] == []


def test_missing_financial_statement_marks_metric_extraction_missing() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL revenue and EBITDA margin improved in the latest period.",
        sources=[
            {
                "title": "CSL ASX announcement excerpt",
                "kind": "document",
                "doc_type": "asx_announcement",
                "snippet": "Company announcement context only.",
                "evidence_labels": ["context_only"],
            }
        ],
    )

    assert FINANCIAL_METRIC in result["claim_families"]
    assert "metric_extraction" in result["missing_evidence_categories"]
    assert "metric_extraction_missing" in result["evidence_requirement_labels"]
    assert FINANCIAL_METRIC in result["unsupported_claim_families"]


def test_missing_canonical_financial_rows_marks_metric_extraction_missing() -> None:
    metadata = enrich_chat_metadata_with_evidence_guard(
        {"source_coverage_status": "context_only"},
        answer_text="Facts from financial truth:\n- no canonical financial rows were returned",
        sources=[
            {
                "title": "CSL announcement excerpt",
                "kind": "document",
                "doc_type": "asx_announcement",
                "evidence_labels": ["context_only"],
            }
        ],
    )

    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert metadata["sufficient_for_analysis"] is False
    assert "metric_extraction_missing" in metadata["evidence_labels"]
    assert "missing_required_evidence" in metadata["evidence_labels"]
    assert metadata["missing_categories_after_recovery"] == ["metric_extraction"]


def test_financial_truth_source_satisfies_metric_requirement() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL revenue improved in the latest period.",
        sources=[
            {
                "title": "CSL FY25 revenue",
                "kind": "document",
                "doc_type": "annual_report",
                "source_id": "financial_truth:CSL:revenue:FY25",
                "evidence_labels": ["financial_truth", "claim_verified"],
                "claim_verified": True,
            }
        ],
    )

    assert FINANCIAL_METRIC in result["claim_families"]
    assert "financial_statement" in result["evidence_categories"]
    assert result["missing_evidence_categories"] == []
    assert FINANCIAL_METRIC not in result["unsupported_claim_families"]


def test_recent_news_question_with_only_price_data_is_insufficient() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="BHP rose this week after the latest update.",
        sources=[
            {
                "title": "BHP price data",
                "source_id": "local_price:BHP:current:1d",
                "kind": "context",
                "snippet": "price: 44.0; change: 1.15",
                "evidence_labels": ["operational_trace"],
            }
        ],
    )

    assert RECENT_NEWS_OR_UPDATE in result["claim_families"]
    assert "market_data" in result["evidence_categories"]
    assert "news" not in result["evidence_categories"]
    assert "recent_news" in result["missing_evidence_categories"]
    assert "insufficient_for_recent_news" in result["evidence_requirement_labels"]
    assert RECENT_NEWS_OR_UPDATE in result["unsupported_claim_families"]


def test_financial_truth_numeric_context_does_not_verify_recent_event_claim() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="BHP recent update this week was driven by an event.",
        sources=[
            {
                "title": "BHP HY revenue",
                "source_id": "financial_truth:BHP:revenue:HY26",
                "kind": "document",
                "doc_type": "half_year",
                "snippet": "revenue: 55000",
                "evidence_labels": ["financial_truth"],
                "claim_verified": False,
            }
        ],
    )

    assert RECENT_NEWS_OR_UPDATE in result["claim_families"]
    assert "financial_truth_numeric" in result["evidence_categories"]
    assert "claim_verified" not in result["evidence_categories"]
    assert "recent_news" in result["missing_evidence_categories"]
    assert "insufficient_for_recent_news" in result["evidence_requirement_labels"]


def test_buyback_and_tariff_filing_claims_remain_context_only_when_supported() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text=(
            "The CSL filing records buy-back activity and a tariff-related "
            "regulatory update."
        ),
        sources=[
            {
                "title": "CSL buy-back and tariff filing",
                "kind": "document",
                "doc_type": "asx_announcement",
                "snippet": "Appendix 3C buy-back notice and tariff regulatory update.",
                "evidence_labels": ["context_only"],
            }
        ],
        metadata={"source_coverage_status": "context_only"},
    )

    assert BUYBACK_ACTIVITY in result["claim_families"]
    assert TARIFF_REGULATORY in result["claim_families"]
    assert result["missing_evidence_categories"] == []
    assert BUYBACK_ACTIVITY not in result["unsupported_claim_families"]
    assert TARIFF_REGULATORY not in result["unsupported_claim_families"]
    assert BUYBACK_ACTIVITY in result["context_only_claim_families"]
    assert TARIFF_REGULATORY in result["context_only_claim_families"]


def test_no_hit_market_tool_does_not_satisfy_price_trend_requirement() -> None:
    result = evaluate_chat_evidence_requirements(
        answer_text="CSL looks bearish on the current price trend.",
        sources=[
            {
                "title": "TradingView screener",
                "kind": "context",
                "doc_type": "operational_no_hit",
                "source_id": "tv_screener:ASX:CSL",
                "snippet": "Screener returned no rows.",
                "evidence_labels": ["no_hit", "operational_trace"],
                "claim_verified": False,
            }
        ],
    )

    assert "no_hit" in result["evidence_categories"]
    assert "market_data" not in result["evidence_categories"]
    assert "market_data_missing" in result["evidence_requirement_labels"]
    assert MARKET_PRICE_OR_TECHNICAL_TREND in result["unsupported_claim_families"]


def test_degraded_runtime_label_remains_visible() -> None:
    metadata = enrich_chat_metadata_with_evidence_guard(
        {"source_coverage_status": "degraded_runtime"},
        answer_text="The runtime failed before a source-backed answer could be generated.",
        sources=[
            {
                "title": "Runtime failure",
                "source_id": "runtime_failure:get_price:CSL",
                "doc_type": "runtime_failure",
                "evidence_labels": ["degraded_runtime", "operational_trace"],
            }
        ],
    )

    assert "degraded_runtime" in metadata["evidence_labels"]
    assert metadata["source_coverage_status"] == "degraded_runtime"


def test_enriched_metadata_demotes_claim_verified_status_when_required_evidence_missing() -> None:
    metadata = enrich_chat_metadata_with_evidence_guard(
        {
            "evidence_labels": ["claim_verified", "context_only"],
            "source_coverage_status": "claim_verified",
            "claim_verified_source_count": 1,
        },
        answer_text="CSL looks bearish on the current price trend.",
        sources=[
            {
                "title": "CSL filing excerpt",
                "kind": "document",
                "doc_type": "asx_announcement",
                "evidence_labels": ["claim_verified", "context_only"],
                "claim_verified": True,
            }
        ],
    )

    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert "market_data_missing" in metadata["evidence_labels"]
    assert "unsupported_or_not_verified" in metadata["evidence_labels"]
    assert metadata["missing_categories_after_recovery"] == ["market_data"]
    assert metadata["sufficient_for_analysis"] is False


def test_visible_gap_labels_qualify_company_memory_price_context() -> None:
    rendered = apply_visible_evidence_gap_labels(
        "\n".join(
            [
                "Facts from financial truth:",
                "- no canonical financial rows were returned",
                "Interpretation from company memory:",
                "- observed fact: CSL's share price dropped amid chaotic trading",
            ]
        ),
        {
            "evidence_labels": [
                "market_data_missing",
                "metric_extraction_missing",
                "missing_required_evidence",
                "unsupported_or_not_verified",
            ],
            "missing_evidence_categories": ["market_data", "metric_extraction"],
            "source_coverage_status": "missing_required_evidence",
        },
    )

    assert rendered.startswith("DATA_MISSING / evidence gaps:")
    assert "market_data_missing: price or technical trend claims" in rendered
    assert "metric_extraction_missing: canonical metric" in rendered
    assert "unsupported_or_not_verified: treat unsupported claim families" in rendered
    assert (
        "Context-only company memory (not verified market/technical evidence):"
        in rendered
    )
    assert "context-only company memory note (not market-verified)" in rendered
