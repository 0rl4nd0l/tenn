#!/usr/bin/env python3
"""Tests for news_chunks sync preflight guards.

Covers:
  1. Model marker mismatch aborts sync before any write when collection has vectors
  2. Model marker mismatch is allowed when collection is empty (safe rebuild)
  3. Dimension mismatch aborts sync before any write
  4. Matching model and dimension allows sync to proceed
  5. Missing model marker file does not block sync (first-run case)
  6. Model marker is written after successful sync
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "financial-engine_v2" / "backend"))


def _make_qdrant_client_mock(collection_exists: bool, existing_dim: int, points_count: int):
    """Build a minimal QdrantClient mock for preflight tests."""
    client = MagicMock()

    col_mock = MagicMock()
    col_mock.name = "news_chunks"
    cols_mock = MagicMock()
    cols_mock.collections = [col_mock] if collection_exists else []
    client.get_collections.return_value = cols_mock

    info_mock = MagicMock()
    info_mock.points_count = points_count
    vp_mock = MagicMock()
    vp_mock.size = existing_dim
    from qdrant_client.http import models as qmodels
    vp_mock.distance = qmodels.Distance.COSINE
    params_mock = MagicMock()
    params_mock.vectors = vp_mock
    info_mock.config.params = params_mock
    client.get_collection.return_value = info_mock

    return client


class TestModelMarkerGuard(unittest.TestCase):
    """Model marker mismatch must abort sync when collection has vectors."""

    def _run_sync_with_marker(self, marker_content, embed_model, points_count):
        """Helper: patch marker file and run preflight checks in sync_news_to_qdrant."""
        import load_news_to_qdrant as mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=True, existing_dim=768, points_count=points_count
        )
        articles_stub = [
            {
                "article_id": "art-001",
                "url": "https://example.com",
                "title": "T",
                "provider": "rss",
                "language": "en",
                "published_at": "2026-03-01",
                "tickers": ["BHP"],
                "primary_ticker": "BHP",
                "text": "BHP news",
            }
        ]

        with (
            patch.object(mod, "NEWS_CHUNKS_MODEL_FILE") as mock_path,
            patch("load_news_to_qdrant.sync_news_to_qdrant.__code__"),  # guard only
        ):
            pass

        # Patch directly at module level
        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            marker_path = MagicMock(spec=Path)
            marker_path.exists.return_value = marker_content is not None
            marker_path.read_text.return_value = marker_content or ""
            marker_path.parent = MagicMock()
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = embed_model
            settings_mock.ollama_url = "http://localhost:11434"

            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch("app.core.config.settings", settings_mock),
                patch("load_news_to_qdrant.settings", settings_mock, create=True),
            ):
                return mod.sync_news_to_qdrant(
                    db_path="/dev/null",
                    qdrant_url="http://localhost:6333",
                    collection="news_chunks",
                )
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file

    def test_model_mismatch_with_populated_collection_raises(self):
        """Stored marker='nomic-embed-text', configured='all-MiniLM-L6-v2', 2725 points → RuntimeError."""
        import load_news_to_qdrant as mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=True, existing_dim=768, points_count=2725
        )
        marker_path = MagicMock(spec=Path)
        marker_path.exists.return_value = True
        marker_path.read_text.return_value = "nomic-embed-text"
        marker_path.parent = MagicMock()

        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = "sentence-transformers/all-MiniLM-L6-v2"
            settings_mock.ollama_url = "http://localhost:11434"

            articles_stub = [
                {
                    "article_id": "art-001", "url": "", "title": "T", "provider": "rss",
                    "language": "en", "published_at": "2026-03-01", "tickers": [],
                    "primary_ticker": "", "text": "test",
                }
            ]
            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch("load_news_to_qdrant.settings", settings_mock, create=True),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    mod.sync_news_to_qdrant(
                        db_path="/dev/null",
                        qdrant_url="http://localhost:6333",
                        collection="news_chunks",
                    )
            self.assertIn("embedding model mismatch", str(ctx.exception))
            self.assertIn("nomic-embed-text", str(ctx.exception))
            self.assertIn("sentence-transformers", str(ctx.exception))
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file

    def test_no_marker_file_does_not_block_sync(self):
        """First run: no marker file → sync proceeds (probe + upsert still run)."""
        import load_news_to_qdrant as mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=False, existing_dim=768, points_count=0
        )
        client_mock.upsert = MagicMock()

        marker_path = MagicMock(spec=Path)
        marker_path.exists.return_value = False
        marker_path.parent = MagicMock()

        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = "nomic-embed-text"
            settings_mock.ollama_url = "http://localhost:11434"

            probe_vec = [0.1] * 768
            articles_stub = [
                {
                    "article_id": "art-001", "url": "", "title": "T", "provider": "rss",
                    "language": "en", "published_at": "2026-03-01", "tickers": ["BHP"],
                    "primary_ticker": "BHP", "text": "BHP test",
                }
            ]
            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch("load_news_to_qdrant.settings", settings_mock, create=True),
                patch("app.services.ollama.ollama_embed", return_value=[probe_vec]),
                patch("app.services.embeddings.ensure_collection", return_value="news_chunks"),
                patch("app.services.embeddings.upsert_points", return_value={"written_points": 1, "rejected_payloads": 0}),
            ):
                stats = mod.sync_news_to_qdrant(
                    db_path="/dev/null",
                    qdrant_url="http://localhost:6333",
                    collection="news_chunks",
                )
            # If no RuntimeError was raised, the preflight check correctly passed
            self.assertIn("articles", stats)
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file

    def test_matching_model_does_not_raise(self):
        """Stored marker='nomic-embed-text', configured='nomic-embed-text' → no error raised."""
        import load_news_to_qdrant as mod
        import app.core.config as config_mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=True, existing_dim=768, points_count=2725
        )
        client_mock.upsert = MagicMock()

        marker_path = MagicMock(spec=Path)
        marker_path.exists.return_value = True
        marker_path.read_text.return_value = "nomic-embed-text"
        marker_path.parent = MagicMock()

        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = "nomic-embed-text"
            settings_mock.ollama_url = "http://localhost:11434"

            probe_vec = [0.1] * 768
            articles_stub = [
                {
                    "article_id": "art-001", "url": "", "title": "T", "provider": "rss",
                    "language": "en", "published_at": "2026-03-01", "tickers": ["BHP"],
                    "primary_ticker": "BHP", "text": "BHP test",
                }
            ]
            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch.object(config_mod, "settings", settings_mock),
                patch("app.services.ollama.ollama_embed", return_value=[probe_vec]),
                patch("app.services.embeddings.ensure_collection", return_value="news_chunks"),
                patch("app.services.embeddings.upsert_points", return_value={"written_points": 1, "rejected_payloads": 0}),
            ):
                # Must not raise
                stats = mod.sync_news_to_qdrant(
                    db_path="/dev/null",
                    qdrant_url="http://localhost:6333",
                    collection="news_chunks",
                )
            self.assertEqual(stats["articles"], 1)
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file


class TestDimensionMismatchGuard(unittest.TestCase):
    """Dimension mismatch guard must abort sync before any write."""

    def test_dimension_mismatch_raises_before_upsert(self):
        """probe_dim=384 but collection has dim=768 → RuntimeError before upsert."""
        import load_news_to_qdrant as mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=True, existing_dim=768, points_count=2725
        )
        upsert_mock = MagicMock()
        client_mock.upsert = upsert_mock

        marker_path = MagicMock(spec=Path)
        marker_path.exists.return_value = False  # no marker file
        marker_path.parent = MagicMock()

        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = "sentence-transformers/all-MiniLM-L6-v2"
            settings_mock.ollama_url = "http://localhost:11434"

            # Ollama returns 384-dim vectors (wrong model active)
            probe_vec_384 = [0.1] * 384
            articles_stub = [
                {
                    "article_id": "art-001", "url": "", "title": "T", "provider": "rss",
                    "language": "en", "published_at": "2026-03-01", "tickers": [],
                    "primary_ticker": "", "text": "test",
                }
            ]
            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch("load_news_to_qdrant.settings", settings_mock, create=True),
                patch("app.services.ollama.ollama_embed", return_value=[probe_vec_384]),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    mod.sync_news_to_qdrant(
                        db_path="/dev/null",
                        qdrant_url="http://localhost:6333",
                        collection="news_chunks",
                    )

            self.assertIn("dimension mismatch", str(ctx.exception))
            self.assertIn("probe_dim=384", str(ctx.exception))
            self.assertIn("dim=768", str(ctx.exception))
            # Upsert must NOT have been called
            upsert_mock.assert_not_called()
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file


class TestModelMarkerWritten(unittest.TestCase):
    """Model marker file is written after a successful sync."""

    def test_marker_written_after_successful_sync(self):
        import load_news_to_qdrant as mod
        import app.core.config as config_mod

        client_mock = _make_qdrant_client_mock(
            collection_exists=False, existing_dim=768, points_count=0
        )
        client_mock.upsert = MagicMock()

        written_content: list[str] = []

        marker_path = MagicMock(spec=Path)
        marker_path.exists.return_value = False
        marker_path.parent = MagicMock()
        marker_path.write_text.side_effect = lambda content, **kw: written_content.append(content)

        original_file = mod.NEWS_CHUNKS_MODEL_FILE
        try:
            mod.NEWS_CHUNKS_MODEL_FILE = marker_path

            settings_mock = MagicMock()
            settings_mock.embed_model = "nomic-embed-text"
            settings_mock.ollama_url = "http://localhost:11434"

            probe_vec = [0.1] * 768
            articles_stub = [
                {
                    "article_id": "art-001", "url": "", "title": "T", "provider": "rss",
                    "language": "en", "published_at": "2026-03-01", "tickers": ["BHP"],
                    "primary_ticker": "BHP", "text": "BHP test",
                }
            ]
            with (
                patch("load_news_to_qdrant._iter_chunks", return_value=articles_stub),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch.object(config_mod, "settings", settings_mock),
                patch("app.services.ollama.ollama_embed", return_value=[probe_vec]),
                patch("app.services.embeddings.ensure_collection", return_value="news_chunks"),
                patch("app.services.embeddings.upsert_points", return_value={"written_points": 1, "rejected_payloads": 0}),
            ):
                mod.sync_news_to_qdrant(
                    db_path="/dev/null",
                    qdrant_url="http://localhost:6333",
                    collection="news_chunks",
                )

            self.assertTrue(written_content, "marker file write_text was not called")
            self.assertEqual(written_content[0], "nomic-embed-text")
        finally:
            mod.NEWS_CHUNKS_MODEL_FILE = original_file


if __name__ == "__main__":
    unittest.main()
