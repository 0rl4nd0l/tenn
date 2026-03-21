#!/usr/bin/env python3
"""TDD: verify news chunk payloads include corpus='news' for Qdrant filter support."""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from load_news_to_qdrant import _build_chunk_payload  # noqa: E402


_SAMPLE_ART = {
    "article_id": "art-001",
    "url": "https://example.com/news/bhp",
    "title": "BHP posts record profit",
    "provider": "eodhd",
    "language": "en",
    "published_at": "2026-03-21T00:00:00Z",
    "tickers": ["BHP"],
}


class NewsQdrantCorpusPayloadTests(unittest.TestCase):
    def test_payload_includes_corpus_news(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=0)
        self.assertEqual(payload.get("corpus"), "news", "corpus field must be 'news' for RAG corpus filtering")

    def test_payload_includes_standard_fields(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=0)
        for field in ("article_id", "chunk_id", "provider", "ticker", "published_at", "language", "title", "url"):
            self.assertIn(field, payload, f"missing field: {field}")

    def test_payload_chunk_id_encodes_article_and_index(self):
        payload = _build_chunk_payload(_SAMPLE_ART, idx=2)
        self.assertEqual(payload["chunk_id"], "news:art-001:2")

    def test_payload_first_ticker_used_when_multi_ticker(self):
        art = dict(_SAMPLE_ART, tickers=["BHP", "RIO"])
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["ticker"], "BHP")

    def test_payload_ticker_is_empty_string_when_no_tickers(self):
        art = dict(_SAMPLE_ART, tickers=[])
        payload = _build_chunk_payload(art, idx=0)
        self.assertEqual(payload["ticker"], "")


if __name__ == "__main__":
    unittest.main()
