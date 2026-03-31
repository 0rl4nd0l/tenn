"""Tests for tenn_chat helpers and source_weighting news_article configuration."""
from __future__ import annotations

import pytest

from app.services.source_weighting import (
    DEFAULT_HALF_LIFE_DAYS,
    DEFAULT_SOURCE_WEIGHTS,
    apply_weighting_to_chunk,
    half_life_for_type,
    source_weight_for_type,
)
from app.services.tenn_chat import _context_rows, _evidence_context_rows, _normalize_news_chunk


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
        required = {"text", "source_name", "url", "relevance_score",
                    "recency_decay", "final_score", "source_type",
                    "published_at", "retrieval_strategies"}
        assert required == set(rows[0].keys())


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
                "text": "BHP updated guidance.",
                "source_name": "BHP guidance update",
                "url": "",
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
