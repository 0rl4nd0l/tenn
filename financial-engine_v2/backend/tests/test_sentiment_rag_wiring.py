"""test_sentiment_rag_wiring.py — Tests for sentiment module RAG integration.

Covers:
  - SentimentModule.rag_queries property
  - _merge_context_requests collecting module RAG queries
  - _categorize_rag_label handling news/commentary/guidance labels
  - SentimentModule scoring news and commentary RAG hits
  - analysis_rag_adapter normalizing Qdrant payloads
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
from app.modules.sentiment import SentimentModule, _categorize_rag_label
from app.modules.ticker_context import (
    RAGHit,
    RAGQuerySpec,
    RAGResult,
    RiskNote,
    TickerContext,
)

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


def _risk_note() -> RiskNote:
    return RiskNote(
        document_id="doc1",
        risk_summary="Commodity price risk remains elevated due to oversupply",
        risk_bullets=("Iron ore oversupply concerns",),
        guidance_summary="FY25 production guidance raised to 260Mt",
    )


def _news_rag_result() -> RAGResult:
    return RAGResult(
        label="news_sentiment",
        query="BHP latest news outlook market sentiment",
        collection="news_chunks",
        hits=(
            RAGHit(text="BHP shares surged after strong quarterly results beat expectations",
                   score=0.85, document_id="news_1", title="BHP Q3 results"),
            RAGHit(text="Iron ore prices decline amid China property downturn fears",
                   score=0.78, document_id="news_2", title="Iron ore outlook"),
        ),
    )


def _commentary_rag_result() -> RAGResult:
    return RAGResult(
        label="commentary_sentiment",
        query="BHP earnings guidance management commentary outlook",
        collection="commentary_chunks",
        hits=(
            RAGHit(text="Management remains confident in long-term growth strategy and raised guidance",
                   score=0.82, document_id="comm_1", title="Earnings call Q3"),
            RAGHit(text="Cost pressures from labour and energy are a persistent headwind",
                   score=0.75, document_id="comm_2", title="Analyst day"),
        ),
    )


# ---------------------------------------------------------------------------
# SentimentModule.rag_queries
# ---------------------------------------------------------------------------


class TestSentimentRagQueries:
    def test_declares_news_and_commentary_queries(self) -> None:
        mod = SentimentModule()
        queries = mod.rag_queries
        assert len(queries) == 2
        labels = {q.label for q in queries}
        assert labels == {"news_sentiment", "commentary_sentiment"}

    def test_news_query_targets_news_chunks(self) -> None:
        mod = SentimentModule()
        news_q = next(q for q in mod.rag_queries if q.label == "news_sentiment")
        assert news_q.collection == "news_chunks"
        assert "{ticker}" in news_q.query_template
        assert news_q.top_k > 0

    def test_commentary_query_targets_commentary_chunks(self) -> None:
        mod = SentimentModule()
        comm_q = next(q for q in mod.rag_queries if q.label == "commentary_sentiment")
        assert comm_q.collection == "commentary_chunks"
        assert "{ticker}" in comm_q.query_template


# ---------------------------------------------------------------------------
# _merge_context_requests collects RAG queries
# ---------------------------------------------------------------------------


class TestMergeContextRequests:
    def test_collects_sentiment_rag_queries(self) -> None:
        registry = {"sentiment": SentimentModule()}
        request = _merge_context_requests(registry)
        assert len(request.rag_queries) == 2
        labels = {q.label for q in request.rag_queries}
        assert "news_sentiment" in labels
        assert "commentary_sentiment" in labels

    def test_deduplicates_by_label(self) -> None:
        registry = {"s1": SentimentModule(), "s2": SentimentModule()}
        request = _merge_context_requests(registry)
        labels = [q.label for q in request.rag_queries]
        assert len(labels) == len(set(labels))

    def test_preserves_other_flags(self) -> None:
        registry = {"sentiment": SentimentModule()}
        request = _merge_context_requests(registry)
        assert request.needs_risk_notes is True


# ---------------------------------------------------------------------------
# _categorize_rag_label
# ---------------------------------------------------------------------------


class TestCategorizeRagLabel:
    @pytest.mark.parametrize("label,expected", [
        ("news_sentiment", "news"),
        ("market_overview", "news"),
        ("commentary_sentiment", "guidance"),
        ("guidance_update", "guidance"),
        ("outlook_2025", "guidance"),
        ("filing_risk", "filing"),
        ("unknown_label", "filing"),
    ])
    def test_label_routing(self, label: str, expected: str) -> None:
        assert _categorize_rag_label(label) == expected


# ---------------------------------------------------------------------------
# SentimentModule.run() with news + commentary
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_nltk, reason="nltk not installed")
class TestSentimentWithRag:
    def test_scores_news_hits(self) -> None:
        ctx = _make_context(rag_results=(_news_rag_result(),))
        result = SentimentModule().run(ctx)
        assert result.completeness != Completeness.FAILED
        data = result.structured
        assert data["category_counts"]["news"] == 2
        assert data["news_sentiment"] is not None

    def test_scores_commentary_as_guidance(self) -> None:
        ctx = _make_context(rag_results=(_commentary_rag_result(),))
        result = SentimentModule().run(ctx)
        data = result.structured
        assert data["category_counts"]["guidance"] == 2
        assert data["guidance_sentiment"] is not None

    def test_full_context_all_categories(self) -> None:
        ctx = _make_context(
            risk_notes=(_risk_note(),),
            rag_results=(_news_rag_result(), _commentary_rag_result()),
        )
        result = SentimentModule().run(ctx)
        assert result.completeness == Completeness.COMPLETE
        data = result.structured
        assert data["category_counts"]["filing"] > 0
        assert data["category_counts"]["news"] > 0
        assert data["category_counts"]["guidance"] > 0
        assert data["overall_sentiment"] is not None
        assert data["passage_count"] >= 7  # 3 risk + 2 news + 2 commentary

    def test_empty_context_fails(self) -> None:
        ctx = _make_context()
        result = SentimentModule().run(ctx)
        assert result.completeness == Completeness.FAILED

    def test_evidence_chain_present(self) -> None:
        ctx = _make_context(
            risk_notes=(_risk_note(),),
            rag_results=(_news_rag_result(),),
        )
        result = SentimentModule().run(ctx)
        assert len(result.evidence) == 2
        labels = {e.evidence_id for e in result.evidence}
        assert "sentiment_BHP_most_positive" in labels
        assert "sentiment_BHP_most_negative" in labels


# ---------------------------------------------------------------------------
# analysis_rag_adapter payload normalization
# ---------------------------------------------------------------------------


class TestAnalysisRagAdapter:
    @patch("app.services.analysis_rag_adapter.embed_texts")
    @patch("app.services.analysis_rag_adapter._build_client")
    @patch("app.services.analysis_rag_adapter.ensure_collection")
    @patch("app.services.analysis_rag_adapter.settings")
    def test_normalizes_commentary_payload(
        self, mock_settings: Any, mock_ensure: Any,
        mock_client_fn: Any, mock_embed: Any,
    ) -> None:
        from app.services.analysis_rag_adapter import analysis_rag_query

        mock_settings.enable_qdrant = True
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        mock_hit = MagicMock()
        mock_hit.score = 0.85
        mock_hit.payload = {
            "text": "Management raised guidance",
            "source_id": "src_123",
            "source_name": "Earnings call",
        }

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_hit]
        mock_client_fn.return_value = mock_client

        results = analysis_rag_query("BHP guidance", "commentary_chunks", 5)

        assert len(results) == 1
        assert results[0]["text"] == "Management raised guidance"
        assert results[0]["document_id"] == "src_123"
        assert results[0]["title"] == "Earnings call"
        assert results[0]["score"] == 0.85

    @patch("app.services.analysis_rag_adapter.embed_texts")
    @patch("app.services.analysis_rag_adapter._build_client")
    @patch("app.services.analysis_rag_adapter.ensure_collection")
    @patch("app.services.analysis_rag_adapter.settings")
    def test_normalizes_news_payload(
        self, mock_settings: Any, mock_ensure: Any,
        mock_client_fn: Any, mock_embed: Any,
    ) -> None:
        from app.services.analysis_rag_adapter import analysis_rag_query

        mock_settings.enable_qdrant = True
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        mock_hit = MagicMock()
        mock_hit.score = 0.78
        mock_hit.payload = {
            "text": "Iron ore falls 3%",
            "document_id": "news_456",
            "title": "Market update",
        }

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_hit]
        mock_client_fn.return_value = mock_client

        results = analysis_rag_query("BHP news", "news_chunks", 3)

        assert len(results) == 1
        assert results[0]["text"] == "Iron ore falls 3%"
        assert results[0]["document_id"] == "news_456"
        assert results[0]["title"] == "Market update"

    @patch("app.services.analysis_rag_adapter.settings")
    def test_returns_empty_when_qdrant_disabled(self, mock_settings: Any) -> None:
        from app.services.analysis_rag_adapter import analysis_rag_query

        mock_settings.enable_qdrant = False
        results = analysis_rag_query("BHP news", "news_chunks", 5)
        assert results == []

    @patch("app.services.analysis_rag_adapter.embed_texts")
    @patch("app.services.analysis_rag_adapter.settings")
    def test_returns_empty_on_embedding_failure(
        self, mock_settings: Any, mock_embed: Any,
    ) -> None:
        from app.services.analysis_rag_adapter import analysis_rag_query

        mock_settings.enable_qdrant = True
        mock_embed.return_value = []
        results = analysis_rag_query("BHP news", "news_chunks", 5)
        assert results == []
