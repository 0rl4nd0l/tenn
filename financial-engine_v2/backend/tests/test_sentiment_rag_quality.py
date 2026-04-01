"""test_sentiment_rag_quality.py — RAG quality validation for sentiment module.

End-to-end quality checks:
  - Realistic ASX news/commentary passages produce directionally correct scores
  - Mixed sentiment contexts produce balanced overall scores
  - Sentiment categories (filing, news, guidance) are populated from all sources
  - Extreme passages are correctly identified
  - Full pipeline: ContextRequest → merged RAG queries → loader → scoring → artifact
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_has_nltk = True
try:
    import nltk  # noqa: F401
except ImportError:
    _has_nltk = False

from app.modules.base import Completeness
from app.modules.orchestrator import _merge_context_requests
from app.modules.sentiment import SentimentModule, _score_text
from app.modules.ticker_context import (
    RAGHit,
    RAGResult,
    RiskNote,
    TickerContext,
)

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Realistic passage fixtures — actual ASX-style financial text
# ---------------------------------------------------------------------------

# Strongly positive news
_POSITIVE_NEWS = [
    RAGHit(
        text="BHP shares surged 4.2% after the miner reported record iron ore "
        "production for the quarter, beating analyst expectations by 8%. "
        "Revenue growth accelerated to 12% year-on-year with strong demand "
        "from Asian steel mills. Management raised full-year guidance.",
        score=0.92, document_id="news_pos_1", title="BHP Q3 beats expectations",
        collection="news_chunks",
    ),
    RAGHit(
        text="Analysts upgraded BHP to outperform following the quarterly "
        "update, citing margin expansion and cash generation above peers. "
        "The company announced a $2B buyback program.",
        score=0.87, document_id="news_pos_2", title="Analyst upgrades BHP",
        collection="news_chunks",
    ),
]

# Strongly negative news
_NEGATIVE_NEWS = [
    RAGHit(
        text="Iron ore prices plunged 15% this month amid fears of a China "
        "property downturn. BHP faces significant headwinds from declining "
        "commodity prices and margin compression. Analysts downgraded the "
        "stock citing impairment risk on nickel assets.",
        score=0.88, document_id="news_neg_1", title="Iron ore price crash",
        collection="news_chunks",
    ),
    RAGHit(
        text="BHP warned of cost pressures from rising energy prices and "
        "labour shortages. Operating costs per tonne increased 9%. The "
        "company lowered guidance for copper production citing equipment "
        "failures at Olympic Dam.",
        score=0.81, document_id="news_neg_2", title="BHP cost warning",
        collection="news_chunks",
    ),
]

# Mixed commentary
_MIXED_COMMENTARY = [
    RAGHit(
        text="CEO Mike Henry expressed confidence in long-term growth strategy "
        "and reaffirmed guidance for iron ore. However, the nickel division "
        "faces restructuring and potential writedowns of $1.2B.",
        score=0.85, document_id="comm_mix_1", title="CEO address",
        collection="commentary_chunks",
    ),
    RAGHit(
        text="Management highlighted strong demand tailwinds in copper and "
        "potash but acknowledged significant headwind from regulatory costs "
        "in Chile. Dividend maintained despite decline in net profit.",
        score=0.79, document_id="comm_mix_2", title="Earnings call Q3",
        collection="commentary_chunks",
    ),
]


def _make_context(
    *,
    risk_notes: tuple[RiskNote, ...] = (),
    rag_results: tuple[RAGResult, ...] = (),
) -> TickerContext:
    return TickerContext(
        ticker="BHP",
        assembled_at=_NOW,
        risk_notes=risk_notes,
        rag_results=rag_results,
    )


def _filing_risk_note() -> RiskNote:
    return RiskNote(
        document_id="doc_bhp_fy24",
        risk_summary="Commodity price volatility and geopolitical risk remain "
        "the primary threats to earnings stability.",
        risk_bullets=(
            "Iron ore oversupply risk from Brazilian and African expansions",
            "Regulatory uncertainty in Chile affecting copper operations",
            "Nickel market oversupply from Indonesian laterite producers",
        ),
        guidance_summary="FY25 production guidance: iron ore 254-264Mt, "
        "copper 1,845-2,045kt. Capital expenditure expected at $10B. "
        "Company raised full-year dividend guidance by 5%.",
        material_changes="Agreed to acquire OZ Minerals for $6.4B, "
        "expanding copper and nickel exposure.",
    )


# ---------------------------------------------------------------------------
# Quality validation tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_nltk, reason="nltk not installed")
class TestSentimentRagQuality:
    """Validate that realistic financial text produces directionally correct scores."""

    def test_positive_news_scores_positive(self) -> None:
        """Strongly positive news should yield positive news_sentiment."""
        ctx = _make_context(
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_POSITIVE_NEWS)),
            ),
        )
        result = SentimentModule().run(ctx)
        data = result.structured
        assert data["news_sentiment"] > 0.0, (
            f"Positive news should score > 0, got {data['news_sentiment']}"
        )

    def test_negative_news_scores_negative(self) -> None:
        """Strongly negative news should yield negative news_sentiment."""
        ctx = _make_context(
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_NEGATIVE_NEWS)),
            ),
        )
        result = SentimentModule().run(ctx)
        data = result.structured
        assert data["news_sentiment"] < 0.0, (
            f"Negative news should score < 0, got {data['news_sentiment']}"
        )

    def test_commentary_routes_to_guidance_category(self) -> None:
        """Commentary hits should be scored as 'guidance' category."""
        ctx = _make_context(
            rag_results=(
                RAGResult(label="commentary_sentiment", query="BHP commentary",
                          collection="commentary_chunks",
                          hits=tuple(_MIXED_COMMENTARY)),
            ),
        )
        result = SentimentModule().run(ctx)
        data = result.structured
        assert data["category_counts"]["guidance"] == 2
        assert data["guidance_sentiment"] is not None

    def test_full_context_three_categories_populated(self) -> None:
        """With all sources, filing + news + guidance categories should all score."""
        ctx = _make_context(
            risk_notes=(_filing_risk_note(),),
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_POSITIVE_NEWS)),
                RAGResult(label="commentary_sentiment", query="BHP commentary",
                          collection="commentary_chunks",
                          hits=tuple(_MIXED_COMMENTARY)),
            ),
        )
        result = SentimentModule().run(ctx)
        assert result.completeness == Completeness.COMPLETE
        data = result.structured
        assert data["category_counts"]["filing"] > 0
        assert data["category_counts"]["news"] > 0
        assert data["category_counts"]["guidance"] > 0
        assert data["filing_sentiment"] is not None
        assert data["news_sentiment"] is not None
        assert data["guidance_sentiment"] is not None
        assert -1.0 <= data["overall_sentiment"] <= 1.0

    def test_positive_extreme_identified_from_news(self) -> None:
        """Most positive passage should come from the strongly positive news."""
        ctx = _make_context(
            risk_notes=(_filing_risk_note(),),
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_POSITIVE_NEWS)),
            ),
        )
        result = SentimentModule().run(ctx)
        most_pos = result.structured["most_positive"]
        assert most_pos["score"] > 0.0
        # Most positive should reference a news source or positive filing
        assert most_pos["source_category"] in ("news", "guidance")

    def test_negative_extreme_identified(self) -> None:
        """Most negative passage should come from negative news or risk notes."""
        ctx = _make_context(
            risk_notes=(_filing_risk_note(),),
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_NEGATIVE_NEWS)),
            ),
        )
        result = SentimentModule().run(ctx)
        most_neg = result.structured["most_negative"]
        assert most_neg["score"] < 0.0

    def test_evidence_chain_has_excerpts(self) -> None:
        """Evidence items should have non-empty content excerpts."""
        ctx = _make_context(
            risk_notes=(_filing_risk_note(),),
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_POSITIVE_NEWS)),
            ),
        )
        result = SentimentModule().run(ctx)
        for ev in result.evidence:
            assert len(ev.content) > 10, f"Evidence excerpt too short: {ev.content}"
            assert ev.source_id, "Evidence must have source_id"

    def test_passage_count_matches_inputs(self) -> None:
        """Passage count should reflect all scored inputs."""
        ctx = _make_context(
            risk_notes=(_filing_risk_note(),),
            rag_results=(
                RAGResult(label="news_sentiment", query="BHP news",
                          collection="news_chunks", hits=tuple(_POSITIVE_NEWS)),
                RAGResult(label="commentary_sentiment", query="BHP comm",
                          collection="commentary_chunks",
                          hits=tuple(_MIXED_COMMENTARY)),
            ),
        )
        result = SentimentModule().run(ctx)
        data = result.structured
        # risk_note: 3 bullets + 1 risk_summary + 1 guidance_summary + 1 material_changes = 6
        # news: 2 hits, commentary: 2 hits = 4
        # Total: 10
        assert data["passage_count"] == 10


# ---------------------------------------------------------------------------
# Full pipeline integration: merge → load → score
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_nltk, reason="nltk not installed")
class TestSentimentPipelineIntegration:
    """Validate the full pipeline from module declaration to artifact output."""

    def test_merge_propagates_rag_queries_to_request(self) -> None:
        """Orchestrator merge creates a ContextRequest with sentiment RAG queries."""
        registry = {"sentiment": SentimentModule()}
        request = _merge_context_requests(registry)
        labels = {q.label for q in request.rag_queries}
        assert "news_sentiment" in labels
        assert "commentary_sentiment" in labels
        collections = {q.collection for q in request.rag_queries}
        assert "news_chunks" in collections
        assert "commentary_chunks" in collections

    def test_loader_with_mock_rag_fn(self) -> None:
        """TickerContextLoader calls rag_fn for each declared query."""
        from sqlalchemy.orm import Session

        from app.modules.context_loader import TickerContextLoader
        from app.modules.ticker_context import ContextRequest, RAGQuerySpec

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.all.return_value = []

        call_log: list[tuple[str, str]] = []

        def mock_rag_fn(query: str, collection: str, top_k: int) -> list[dict]:
            call_log.append((query, collection))
            return [{"text": f"Mock hit for {collection}", "score": 0.8}]

        request = ContextRequest(
            needs_financials=False,
            needs_risk_notes=False,
            needs_documents=False,
            rag_queries=(
                RAGQuerySpec(label="news_sentiment",
                             query_template="{ticker} news",
                             collection="news_chunks", top_k=3),
                RAGQuerySpec(label="commentary_sentiment",
                             query_template="{ticker} commentary",
                             collection="commentary_chunks", top_k=3),
            ),
        )

        loader = TickerContextLoader(rag_fn=mock_rag_fn)
        ctx = loader.load("BHP", request, db=mock_db)

        # Verify rag_fn was called for both collections
        collections_called = {c for _, c in call_log}
        assert "news_chunks" in collections_called
        assert "commentary_chunks" in collections_called

        # Verify results are in context
        assert len(ctx.rag_results) == 2
        news_r = ctx.rag_by_label("news_sentiment")
        assert news_r is not None
        assert len(news_r.hits) == 1

    def test_end_to_end_scoring_from_loader_output(self) -> None:
        """Sentiment module scores correctly from loader-assembled context."""
        from sqlalchemy.orm import Session

        from app.modules.context_loader import TickerContextLoader
        from app.modules.ticker_context import ContextRequest, RAGQuerySpec

        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.all.return_value = []

        def mock_rag_fn(query: str, collection: str, top_k: int) -> list[dict]:
            if collection == "news_chunks":
                return [
                    {"text": "BHP shares surged after record production beat expectations",
                     "score": 0.9, "document_id": "n1", "title": "BHP beats"},
                    {"text": "Iron ore prices rose 5% on strong demand from China",
                     "score": 0.85, "document_id": "n2", "title": "Iron ore up"},
                ]
            if collection == "commentary_chunks":
                return [
                    {"text": "CEO reaffirmed guidance and expressed confidence in growth strategy",
                     "score": 0.88, "document_id": "c1", "title": "CEO address"},
                ]
            return []

        request = ContextRequest(
            needs_financials=False,
            needs_risk_notes=False,
            needs_documents=False,
            rag_queries=(
                RAGQuerySpec(label="news_sentiment",
                             query_template="{ticker} news",
                             collection="news_chunks", top_k=3),
                RAGQuerySpec(label="commentary_sentiment",
                             query_template="{ticker} commentary",
                             collection="commentary_chunks", top_k=3),
            ),
        )

        loader = TickerContextLoader(rag_fn=mock_rag_fn)
        ctx = loader.load("BHP", request, db=mock_db)

        result = SentimentModule().run(ctx)
        assert result.completeness == Completeness.COMPLETE
        data = result.structured
        assert data["news_sentiment"] > 0.0, "Positive news should score positive"
        assert data["guidance_sentiment"] > 0.0, "Positive commentary should score positive"
        assert data["passage_count"] == 3
        assert data["category_counts"]["news"] == 2
        assert data["category_counts"]["guidance"] == 1
