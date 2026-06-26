"""Tests for tenn_chat helpers and source_weighting news_article configuration."""

from __future__ import annotations

import pytest

from app.services.commentary_decay import compute_recency_decay
from app.services.source_weighting import (
    DEFAULT_HALF_LIFE_DAYS,
    DEFAULT_SOURCE_WEIGHTS,
    apply_source_weighting,
    apply_weighting_to_chunk,
    half_life_for_type,
    source_weight_for_type,
)
from app.services import tenn_chat
from app.services.tenn_chat import (
    _apply_chat_strategy,
    _context_rows,
    _evidence_context_rows,
    _normalize_confidence,
    _normalize_insights,
    _normalize_news_chunk,
    _normalize_supporting_evidence,
    _retrieve_chat_context,
    _safe_float,
)


class TestSourceWeightingNewsArticle:
    def test_news_article_weight_explicit(self):
        assert "news_article" in DEFAULT_SOURCE_WEIGHTS
        assert DEFAULT_SOURCE_WEIGHTS["news_article"] == 0.5

    def test_news_article_half_life_explicit(self):
        assert "news_article" in DEFAULT_HALF_LIFE_DAYS
        assert DEFAULT_HALF_LIFE_DAYS["news_article"] == 1.0

    def test_source_weight_for_type_news_article(self):
        assert source_weight_for_type("news_article") == 0.5

    def test_half_life_for_type_news_article(self):
        assert half_life_for_type("news_article") == 1.0

    @pytest.mark.parametrize(
        ("source_type", "expected_weight"),
        [
            ("news_article", 0.5),
            ("youtube_transcript", 0.55),
            ("framework_pdf", 1.0),
        ],
    )
    def test_default_final_score_uses_single_resolved_credibility(
        self, source_type, expected_weight
    ):
        result = apply_source_weighting(
            relevance_score=1.0,
            source_type=source_type,
            credibility_weight=None,
            recency_decay=1.0,
        )

        assert result["source_weight"] == expected_weight
        assert result["credibility_weight"] == expected_weight
        assert result["final_score"] == pytest.approx(expected_weight)

    def test_explicit_credibility_overrides_default_source_weight(self):
        result = apply_source_weighting(
            relevance_score=0.8,
            source_type="news_article",
            credibility_weight=0.75,
            recency_decay=0.5,
        )

        assert result["source_weight"] == 0.5
        assert result["credibility_weight"] == 0.75
        assert result["final_score"] == pytest.approx(0.3)

    def test_apply_weighting_news_chunk_fresh(self):
        """Fresh news (today) should not be heavily decayed."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        chunk = {
            "source_type": "news_article",
            "vector_score": 0.8,
            "published_at": now.isoformat(),
        }
        result = apply_weighting_to_chunk(chunk)
        # recency_decay near 1.0 for fresh content
        assert result["recency_decay"] > 0.95
        assert result["source_weight"] == 0.5
        assert result["final_score"] == pytest.approx(
            0.8 * result["source_weight"] * result["recency_decay"]
        )

    def test_apply_weighting_news_chunk_stale(self):
        """Old news (90 days) should decay significantly with 1-day half-life."""
        import datetime as dt

        ninety_days_ago = (
            dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(days=90)
        ).isoformat()
        chunk = {
            "source_type": "news_article",
            "vector_score": 0.8,
            "published_at": ninety_days_ago,
        }
        result = apply_weighting_to_chunk(chunk)
        # 90 days / 1-day half-life = 90 half-lives → decay effectively 0
        assert result["recency_decay"] < 0.02

    def test_recency_decay_matches_true_half_life_contract(self):
        now = "2026-06-02T00:00:00Z"

        one_half_life = compute_recency_decay(
            published_at="2026-06-01T00:00:00Z",
            half_life_days=1.0,
            now=now,
        )
        two_half_lives = compute_recency_decay(
            published_at="2026-05-31T00:00:00Z",
            half_life_days=1.0,
            now=now,
        )

        assert one_half_life == pytest.approx(0.5)
        assert two_half_lives == pytest.approx(0.25)

    def test_apply_weighting_news_article_one_half_life(self):
        result = apply_weighting_to_chunk(
            {
                "source_type": "news_article",
                "vector_score": 0.8,
                "published_at": "2026-06-01T00:00:00Z",
            },
            now="2026-06-02T00:00:00Z",
        )

        assert result["decay_half_life"] == 1.0
        assert result["recency_decay"] == pytest.approx(0.5)

    def test_apply_weighting_market_commentary_one_half_life(self):
        result = apply_weighting_to_chunk(
            {
                "source_type": "market_commentary",
                "vector_score": 0.8,
                "published_at": "2026-05-26T00:00:00Z",
            },
            now="2026-06-02T00:00:00Z",
        )

        assert result["decay_half_life"] == 7.0
        assert result["recency_decay"] == pytest.approx(0.5)

    def test_apply_weighting_malformed_published_at_uses_neutral_recency_with_warning(self):
        chunk = {
            "source_type": "news_article",
            "vector_score": 0.8,
            "published_at": "not-a-date",
        }

        result = apply_weighting_to_chunk(chunk)

        assert result["recency_decay"] == 1.0
        assert result["recency_status"] == "malformed_published_at"
        assert result["recency_warning"] == "invalid_published_at"
        assert "not-a-date" in result["published_at_parse_error"]

    def test_apply_weighting_invalid_half_life_is_not_reported_as_bad_date(self):
        chunk = {
            "source_type": "news_article",
            "vector_score": 0.8,
            "published_at": "2026-06-01T00:00:00Z",
            "decay_half_life": "not-a-number",
        }

        with pytest.raises(ValueError):
            apply_weighting_to_chunk(chunk)


class TestNormalizeNewsChunk:
    def test_sets_source_name_from_title(self):
        chunk = {"title": "ASX closes higher", "provider": "Reuters"}
        result = _normalize_news_chunk(chunk)
        assert result["source_name"] == "ASX closes higher"

    def test_sets_source_name_from_provider_when_no_title(self):
        chunk = {"provider": "Reuters"}
        result = _normalize_news_chunk(chunk)
        assert result["source_name"] == "Reuters"

    def test_does_not_override_existing_source_name(self):
        chunk = {"source_name": "Reuters Wire", "title": "Headline"}
        result = _normalize_news_chunk(chunk)
        assert result["source_name"] == "Reuters Wire"

    def test_sets_default_source_type(self):
        chunk = {}
        result = _normalize_news_chunk(chunk)
        assert result["source_type"] == "news_article"

    def test_does_not_override_existing_source_type(self):
        chunk = {"source_type": "market_commentary"}
        result = _normalize_news_chunk(chunk)
        assert result["source_type"] == "market_commentary"

    def test_returns_copy_not_mutation(self):
        original = {"title": "Title"}
        result = _normalize_news_chunk(original)
        assert result is not original
        assert "source_name" not in original


class TestContextRows:
    def test_url_field_included(self):
        chunks = [
            {
                "text": "Article body",
                "source_name": "Reuters",
                "url": "https://example.com/article",
                "relevance_score": 0.9,
                "recency_decay": 0.8,
                "final_score": 0.72,
                "source_type": "news_article",
                "published_at": "2026-01-01T00:00:00Z",
                "retrieval_strategies": ["vector"],
            }
        ]
        rows = _context_rows(chunks)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://example.com/article"

    def test_url_empty_when_not_in_chunk(self):
        chunks = [{"text": "body", "source_name": "src"}]
        rows = _context_rows(chunks)
        assert rows[0]["url"] == ""

    def test_all_fields_present(self):
        rows = _context_rows([{}])
        required = {
            "chunk_id",
            "article_id",
            "document_id",
            "text",
            "source_name",
            "url",
            "ticker",
            "provider",
            "relevance_score",
            "recency_decay",
            "final_score",
            "source_type",
            "published_at",
            "retrieval_strategies",
        }
        assert required == set(rows[0].keys())


class TestRetrieveChatContext:
    def test_apply_chat_strategy_keeps_valid_neighbor_with_malformed_date(
        self, monkeypatch
    ):
        monkeypatch.setattr(tenn_chat, "get_active_strategy_state", lambda: {})

        ranked = _apply_chat_strategy(
            [
                {
                    "chunk_id": "bad-date",
                    "source_name": "Bad timestamp",
                    "source_type": "news_article",
                    "vector_score": 0.9,
                    "published_at": "not-a-date",
                },
                {
                    "chunk_id": "valid-neighbor",
                    "source_name": "Valid neighbor",
                    "source_type": "news_article",
                    "vector_score": 0.8,
                },
            ]
        )

        assert {chunk["chunk_id"] for chunk in ranked} == {
            "bad-date",
            "valid-neighbor",
        }
        bad_date = next(chunk for chunk in ranked if chunk["chunk_id"] == "bad-date")
        assert bad_date["recency_status"] == "malformed_published_at"
        assert bad_date["recency_warning"] == "invalid_published_at"

    def test_returns_commentary_and_ticker_news_rows(self, monkeypatch):
        monkeypatch.setattr(
            tenn_chat,
            "query_rag",
            lambda **_: {"hits": [], "research_context": {"evidence_chunks": []}},
        )
        monkeypatch.setattr(
            tenn_chat, "_apply_chat_strategy", lambda chunks: list(chunks)
        )

        class FakeRetriever:
            def __init__(self, *, collection_name):
                self.collection_name = collection_name

            def retrieve(self, **kwargs):
                if self.collection_name == "commentary_chunks":
                    return {
                        "chunks": [
                            {
                                "chunk_id": "commentary-1",
                                "text": "BHP commentary context",
                                "source_name": "Analyst note",
                                "source_type": "market_commentary",
                                "final_score": 0.9,
                            }
                        ]
                    }
                assert self.collection_name == "news_chunks"
                assert kwargs["ticker"] == "BHP"
                return {
                    "chunks": [
                        {
                            "article_id": "news-1",
                            "text": "BHP news context",
                            "title": "BHP headline",
                            "ticker": "BHP",
                            "provider": "Wire",
                            "final_score": 0.8,
                        }
                    ]
                }

        monkeypatch.setattr(tenn_chat, "HybridRetriever", FakeRetriever)

        bundle = _retrieve_chat_context(
            normalized_query="what changed with BHP",
            normalized_ticker="BHP",
        )

        assert bundle.news_retrieval_attempted is True
        assert bundle.news_retrieval_failed is False
        assert [row["source_name"] for row in bundle.context_rows] == [
            "BHP headline",
            "Analyst note",
        ]
        assert bundle.context_rows[0]["source_type"] == "news_article"

    def test_news_failure_is_nonfatal_when_commentary_context_exists(self, monkeypatch):
        monkeypatch.setattr(
            tenn_chat,
            "query_rag",
            lambda **_: {"hits": [], "research_context": {"evidence_chunks": []}},
        )
        monkeypatch.setattr(
            tenn_chat, "_apply_chat_strategy", lambda chunks: list(chunks)
        )

        class FakeRetriever:
            def __init__(self, *, collection_name):
                self.collection_name = collection_name

            def retrieve(self, **kwargs):
                if self.collection_name == "news_chunks":
                    raise RuntimeError("news unavailable")
                return {
                    "chunks": [
                        {
                            "chunk_id": "commentary-1",
                            "text": "BHP commentary context",
                            "source_name": "Analyst note",
                        }
                    ]
                }

        monkeypatch.setattr(tenn_chat, "HybridRetriever", FakeRetriever)

        bundle = _retrieve_chat_context(
            normalized_query="what changed with BHP",
            normalized_ticker="BHP",
        )

        assert bundle.news_retrieval_attempted is True
        assert bundle.news_retrieval_failed is True
        assert [row["source_name"] for row in bundle.context_rows] == ["Analyst note"]

    def test_rag_evidence_rows_are_used_when_chunk_retrieval_is_empty(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            tenn_chat,
            "query_rag",
            lambda **_: {
                "hits": [],
                "research_context": {
                    "evidence_chunks": [
                        {
                            "title": "BHP announcement",
                            "text": "BHP announced an update.",
                            "document_id": "doc-1",
                            "score": 0.77,
                        }
                    ]
                },
            },
        )
        monkeypatch.setattr(
            tenn_chat, "_apply_chat_strategy", lambda chunks: list(chunks)
        )

        class FakeRetriever:
            def __init__(self, *, collection_name):
                self.collection_name = collection_name

            def retrieve(self, **kwargs):
                return {"chunks": []}

        monkeypatch.setattr(tenn_chat, "HybridRetriever", FakeRetriever)

        bundle = _retrieve_chat_context(
            normalized_query="summarize BHP",
            normalized_ticker=None,
        )

        assert bundle.news_retrieval_attempted is False
        assert bundle.news_retrieval_failed is False
        assert bundle.context_rows == [
            {
                "chunk_id": "",
                "article_id": "",
                "document_id": "doc-1",
                "text": "BHP announced an update.",
                "source_name": "BHP announcement",
                "url": "",
                "ticker": "",
                "provider": "",
                "relevance_score": 0.77,
                "recency_decay": 1.0,
                "final_score": 0.77,
                "source_type": "",
                "published_at": "",
                "retrieval_strategies": ["rag_vector"],
            }
        ]


class TestEvidenceContextRows:
    def test_normalizes_rag_fallback_hits_to_full_row_shape(self):
        rows = _evidence_context_rows(
            [
                {
                    "text": "BHP updated guidance.",
                    "title": "BHP guidance update",
                    "document_id": "doc-1",
                    "score": 0.87,
                    "doc_class": "asx_announcement",
                    "published_at": "2026-03-31T00:00:00Z",
                }
            ]
        )
        assert rows == [
            {
                "chunk_id": "",
                "article_id": "",
                "document_id": "doc-1",
                "text": "BHP updated guidance.",
                "source_name": "BHP guidance update",
                "url": "",
                "ticker": "",
                "provider": "",
                "relevance_score": 0.87,
                "recency_decay": 1.0,
                "final_score": 0.87,
                "source_type": "asx_announcement",
                "published_at": "2026-03-31T00:00:00Z",
                "retrieval_strategies": ["rag_vector"],
            }
        ]

    def test_skips_empty_hits(self):
        rows = _evidence_context_rows([{"title": ""}, {}])
        assert rows == []


class TestChatPayloadNormalization:
    def test_confidence_defaults_to_zero_for_non_numeric_value(self):
        assert _normalize_confidence("high") == 0.0

    def test_confidence_clamps_and_rejects_non_finite_values(self):
        assert _normalize_confidence(9.5) == 1.0
        assert _normalize_confidence(-2) == 0.0
        assert _normalize_confidence(float("nan")) == 0.0

    def test_insights_requires_list(self):
        assert _normalize_insights("single string") == []
        assert _normalize_insights(["a", "", " b "]) == ["a", "b"]

    def test_supporting_evidence_requires_list(self):
        assert _normalize_supporting_evidence({"a": 1}) == []
        assert _normalize_supporting_evidence([{"a": 1}]) == [{"a": 1}]

    def test_supporting_evidence_rejects_non_finite_nested_values(self):
        assert _normalize_supporting_evidence(
            [{"score": float("nan"), "nested": [1.0, float("inf")]}]
        ) == [{"score": None, "nested": [1.0, None]}]

    def test_safe_float_rejects_non_finite_values(self):
        assert _safe_float(float("nan"), default=0.0) == 0.0
        assert _safe_float(float("inf"), default=1.0) == 1.0
