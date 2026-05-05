#!/usr/bin/env python3
"""TDD: verify news chunk payloads include corpus='news' for Qdrant filter support."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from load_news_to_qdrant import _build_chunk_payload, _iter_chunks  # noqa: E402
from news_pipeline.cli_common import DEFAULT_IDENTITY_MAP  # noqa: E402
from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.models import ArticleCandidate  # noqa: E402
from news_pipeline.relevance import score_article_relevance  # noqa: E402


_SAMPLE_ART = {
    "article_id": "art-001",
    "url": "https://example.com/news/bhp",
    "title": "BHP posts record profit",
    "provider": "eodhd",
    "language": "en",
    "published_at": "2026-03-21T00:00:00Z",
    "tickers": ["BHP"],
}

A2M_RECALL_TITLE = "A2 Milk shares plunge after finding toxins in infant formula"
A2M_RECALL_URL = "https://example.com/news/a2m-infant-formula-recall"
A2M_RECALL_PUBLISHED = "2026-05-05T00:00:00Z"
A2M_RECALL_BODY = (
    "The a2 Milk Company said it was working through a recall of infant formula "
    "after testing found toxins. ASX:A2M investors reacted to the update. "
    "The infant formula recall remained the focus for the company and suppliers. "
    "The article repeated the recall context to exceed the Qdrant sync quality gate."
)


class NewsQdrantCorpusPayloadTests(unittest.TestCase):
    def test_payload_includes_corpus_news(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=0)
        self.assertEqual(
            payload.get("corpus"),
            "news",
            "corpus field must be 'news' for RAG corpus filtering",
        )

    def test_payload_includes_standard_fields(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=0)
        for field in (
            "article_id",
            "chunk_id",
            "provider",
            "ticker",
            "tickers",
            "primary_ticker",
            "published_at",
            "language",
            "title",
            "url",
        ):
            self.assertIn(field, payload, f"missing field: {field}")

    def test_payload_preserves_all_linked_tickers(self):
        art = dict(_SAMPLE_ART, tickers=["BHP", "RIO", " bhp "])
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["tickers"], ["BHP", "RIO"])

    def test_payload_chunk_id_encodes_article_and_index(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=2)
        self.assertEqual(payload["chunk_id"], "news:art-001:2")

    def test_payload_primary_ticker_used_when_relevance_resolved(self):
        """primary_ticker from article_relevance takes precedence over tickers list order."""
        art = dict(_SAMPLE_ART, tickers=["ABC", "BHP", "RIO"], primary_ticker="RIO")
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(
            payload["ticker"], "RIO", "primary_ticker must win over alphabetical first"
        )

    def test_payload_single_ticker_used_as_fallback(self):
        """When primary_ticker is absent but only one ticker is linked, use it."""
        art = dict(_SAMPLE_ART, tickers=["BHP"], primary_ticker="")
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["ticker"], "BHP")

    def test_payload_ticker_empty_when_multi_ticker_and_no_primary(self):
        """When multiple tickers are linked but no primary is resolved, ticker is empty (ambiguous)."""
        art = dict(_SAMPLE_ART, tickers=["BHP", "RIO"], primary_ticker="")
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["ticker"], "")

    def test_payload_ticker_is_empty_string_when_no_tickers(self):
        art = dict(_SAMPLE_ART, tickers=[], primary_ticker="")
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["ticker"], "")

    def test_a2m_raw_entity_metadata_flows_to_qdrant_payload_shape(self):
        with tempfile.TemporaryDirectory() as td:
            raw_db_path = Path(td) / "news_articles.sqlite"
            store = NewsArticleStore(raw_db_path)
            try:
                candidate = ArticleCandidate(
                    provider="newspaper4k",
                    provider_item_id="a2m-recall",
                    canonical_url=A2M_RECALL_URL,
                    title=A2M_RECALL_TITLE,
                    description="Recall and infant formula update.",
                    body=A2M_RECALL_BODY * 3,
                    source_name="Example Finance",
                    language="en",
                    published_at_utc=A2M_RECALL_PUBLISHED,
                    fetched_at_utc="2026-05-05T01:00:00Z",
                    provider_published_at_raw=A2M_RECALL_PUBLISHED,
                    raw_payload={"id": "a2m-recall"},
                )
                upsert = store.upsert_article(candidate, lane="high_precision")
                tickers_path = Path(td) / "tickers.txt"
                tickers_path.write_text("BHP\n", encoding="utf-8")
                linker = EntityLinker(
                    ticker_universe_path=tickers_path,
                    identity_map_path=DEFAULT_IDENTITY_MAP,
                )
                links = linker.link_article(
                    article_id=upsert.article_id,
                    title=A2M_RECALL_TITLE,
                    description="Recall and infant formula update.",
                    body=A2M_RECALL_BODY,
                    published_at_utc=A2M_RECALL_PUBLISHED,
                )
                store.replace_entity_links(upsert.article_id, links)
                store.replace_article_relevance(
                    upsert.article_id,
                    score_article_relevance(
                        article_id=upsert.article_id,
                        title=A2M_RECALL_TITLE,
                        description="Recall and infant formula update.",
                        body=A2M_RECALL_BODY,
                        links=links,
                    ),
                )
            finally:
                store.close()

            conn = sqlite3.connect(str(raw_db_path))
            conn.row_factory = sqlite3.Row
            try:
                articles = _iter_chunks(conn, since_hours=None)
            finally:
                conn.close()

        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article["tickers"], ["A2M"])
        self.assertEqual(article["primary_ticker"], "A2M")

        payload = _build_chunk_payload(article, idx=0, chunk_text=article["text"])
        self.assertEqual(payload["ticker"], "A2M")
        self.assertEqual(payload["primary_ticker"], "A2M")
        self.assertIn("A2M", payload["tickers"])
        self.assertEqual(payload["provider"], "newspaper4k")
        self.assertEqual(payload["title"], A2M_RECALL_TITLE)
        self.assertEqual(payload["url"], A2M_RECALL_URL)
        self.assertEqual(payload["published_at"], A2M_RECALL_PUBLISHED)


if __name__ == "__main__":
    unittest.main()
