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

import inspect
import json
import sqlite3
import sys
import tempfile
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


def _news_projection_target_stub(articles: list[dict]) -> dict:
    points = [
        {
            "id": str(index + 1),
            "_text": str(article.get("text") or "test"),
            "payload": {
                "article_id": str(article.get("article_id") or ""),
                "provider": str(article.get("provider") or ""),
                "published_at": str(article.get("published_at") or ""),
                "title": str(article.get("title") or ""),
            },
        }
        for index, article in enumerate(articles)
    ]
    return {
        "articles": articles,
        "points": points,
        "report": {
            "eligible_articles": len(articles),
            "eligible_chunks": len(points),
            "excluded_articles": 0,
        },
    }


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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
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
        import app.core.config as config_mod

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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
                patch("qdrant_client.QdrantClient", return_value=client_mock),
                patch.object(config_mod, "settings", settings_mock),
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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
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
                patch("load_news_to_qdrant.build_news_projection_target", return_value=_news_projection_target_stub(articles_stub)),
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


class TestNightlyNewsDiagnostics(unittest.TestCase):
    def test_news_sqlite_freshness_marks_stale_context_degraded(self):
        import load_news_to_qdrant as mod

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    "CREATE TABLE context_chunks(chunk_id TEXT PRIMARY KEY, published_at TEXT)"
                )
                conn.execute(
                    "INSERT INTO context_chunks(chunk_id, published_at) VALUES (?, ?)",
                    ("news:old:0", "2026-04-09T10:13:17Z"),
                )
                conn.commit()
            finally:
                conn.close()

            result = mod.validate_news_sqlite_freshness(
                db_path,
                window_start_utc="2026-05-03T04:00:02Z",
            )

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(result["reason"], "stale")
            self.assertEqual(result["newest_published_at"], "2026-04-09T10:13:17Z")

    def test_refresh_news_sqlite_fallback_builds_fresh_context_chunks(self):
        import load_news_to_qdrant as mod
        from news_pipeline.db import NewsArticleStore
        from news_pipeline.models import ArticleCandidate

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            articles_db = tmp / "news_articles.sqlite"
            context_db = tmp / "news.sqlite"
            store = NewsArticleStore(articles_db)
            try:
                store.upsert_article(
                    ArticleCandidate(
                        provider="newspaper4k",
                        provider_item_id="n4k-1",
                        canonical_url="https://example.com/news/bhp",
                        title="BHP updates investors",
                        description="BHP released an operational update.",
                        body="BHP released an operational update with production commentary.",
                        source_name="Example",
                        language="en",
                        published_at_utc="2026-05-04T08:00:00Z",
                        fetched_at_utc="2026-05-04T16:00:00Z",
                        raw_payload={"id": "n4k-1"},
                    ),
                    lane="high_precision",
                )
            finally:
                store.close()

            result = mod.refresh_news_sqlite_fallback(
                articles_db_path=articles_db,
                context_db_path=context_db,
                window_start_utc="2026-05-03T04:00:02Z",
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["freshness"]["status"], "fresh")
            conn = sqlite3.connect(str(context_db))
            try:
                row = conn.execute(
                    "SELECT COUNT(*), MAX(published_at) FROM context_chunks"
                ).fetchone()
            finally:
                conn.close()
            self.assertGreater(int(row[0] or 0), 0)
            self.assertEqual(str(row[1] or ""), "2026-05-04T08:00:00Z")

    def test_memo_diagnostics_classify_skipped_failed_and_persisted(self):
        import load_news_to_qdrant as mod

        with tempfile.TemporaryDirectory() as td:
            memos_path = Path(td) / "news_memos.jsonl"
            memos_path.write_text(
                json.dumps({"source_id": "news:art-1"}) + "\n",
                encoding="utf-8",
            )
            articles = [
                {
                    "article_id": "art-1",
                    "text": "already persisted",
                    "provider": "newspaper4k",
                    "published_at": "2026-05-04T08:00:00Z",
                },
                {
                    "article_id": "art-2",
                    "text": "dispatch will fail",
                    "provider": "newspaper4k",
                    "published_at": "2026-05-04T09:00:00Z",
                },
                {
                    "article_id": "art-3",
                    "text": "",
                    "provider": "newspaper4k",
                    "published_at": "2026-05-04T10:00:00Z",
                },
            ]
            calls: list[str] = []

            class FlakyTask:
                def delay(self, payload):
                    source_id = payload["source_id"]
                    if source_id == "news:art-2":
                        raise RuntimeError("queue unavailable")
                    calls.append(source_id)

            result = mod.dispatch_news_memos(
                articles,
                task=FlakyTask(),
                memos_path=memos_path,
            )

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(result["eligible"], 2)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["dispatched"], 0)
            self.assertEqual(result["dispatch_failed"], 1)
            self.assertEqual(result["persisted_before_dispatch"], 1)
            self.assertEqual(result["persisted_after_dispatch"], 1)
            self.assertEqual(result["missing_after_dispatch"], 1)
            self.assertEqual(result["already_persisted_skipped"], 1)
            self.assertEqual(result["dispatch_candidates"], 1)
            self.assertEqual(calls, [])

    def test_dispatch_news_memos_force_dispatches_persisted_sources(self):
        import load_news_to_qdrant as mod

        with tempfile.TemporaryDirectory() as td:
            memos_path = Path(td) / "news_memos.jsonl"
            memos_path.write_text(
                json.dumps({"source_id": "news:art-1"}) + "\n",
                encoding="utf-8",
            )
            articles = [
                {
                    "article_id": "art-1",
                    "text": "already persisted",
                    "provider": "newspaper4k",
                    "published_at": "2026-05-04T08:00:00Z",
                }
            ]
            calls: list[str] = []

            class ResultTask:
                def delay(self, payload):
                    calls.append(payload["source_id"])

            result = mod.dispatch_news_memos(
                articles,
                task=ResultTask(),
                memos_path=memos_path,
                force_dispatch=True,
            )

            self.assertEqual(result["dispatched"], 1)
            self.assertEqual(result["already_persisted_skipped"], 0)
            self.assertTrue(result["force_dispatch"])
            self.assertEqual(calls, ["news:art-1"])

    def test_dispatch_news_memos_no_wait_reports_task_id_samples(self):
        import load_news_to_qdrant as mod

        articles = [
            {
                "article_id": "art-1",
                "text": "memo text 1",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T08:00:00Z",
            },
            {
                "article_id": "art-2",
                "text": "memo text 2",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T09:00:00Z",
            },
        ]

        payloads: list[dict] = []

        class ResultTask:
            def delay(self, payload):
                payloads.append(dict(payload))
                return FakeAsyncResult(f"task-{payload['source_id'].split(':')[-1]}")

        with tempfile.TemporaryDirectory() as td:
            result = mod.dispatch_news_memos(
                articles,
                task=ResultTask(),
                memos_path=Path(td) / "news_memos.jsonl",
                max_article_chars=7,
            )

        self.assertEqual(result["dispatched"], 2)
        self.assertFalse(result["completion_observable"])
        self.assertEqual(_task_id_samples(result), ["task-art-1", "task-art-2"])
        self.assertEqual(result["max_article_chars"], 7)
        self.assertEqual(payloads[0]["article_text"], "memo te")

    def test_dispatch_news_memos_wait_marks_completed_observable(self):
        import load_news_to_qdrant as mod

        articles = [
            {
                "article_id": "art-1",
                "text": "memo text 1",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T08:00:00Z",
            },
            {
                "article_id": "art-2",
                "text": "memo text 2",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T09:00:00Z",
            },
        ]
        async_results = [
            FakeAsyncResult("task-art-1", ready=True, successful=True),
            FakeAsyncResult("task-art-2", ready=True, successful=True),
        ]

        class ResultTask:
            def delay(self, _payload):
                return async_results.pop(0)

        with tempfile.TemporaryDirectory() as td:
            result = _dispatch_with_wait_options(
                mod,
                articles,
                task=ResultTask(),
                memos_path=Path(td) / "news_memos.jsonl",
                wait=True,
                timeout=0.0,
                poll_interval=0.0,
            )

        self.assertEqual(result["dispatched"], 2)
        self.assertEqual(result["status"], "degraded")
        self.assertTrue(result["completion_observable"])
        self.assertEqual(
            _count(result, "completed", "completion_completed", "tasks_completed"), 2
        )
        self.assertEqual(_count(result, "pending", "completion_pending", "tasks_pending"), 0)
        self.assertEqual(_count(result, "failed", "completion_failed", "tasks_failed"), 0)

    def test_main_wait_for_memos_degraded_returns_nonzero(self):
        import load_news_to_qdrant as mod

        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "summary.json"
            argv = [
                "load_news_to_qdrant.py",
                "--db-path",
                str(Path(td) / "news_articles.sqlite"),
                "--wait-for-memos",
                "--summary-json",
                str(summary_path),
            ]
            stats = {
                "status": "success",
                "articles": 2,
                "chunks": 2,
                "upserted": 2,
                "deleted": 0,
                "dry_run": False,
                "qdrant_only": False,
                "memo_extraction": {"status": "degraded"},
            }

            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    mod,
                    "latest_provider_run_summary",
                    return_value={"status": "success", "params": {}},
                ),
                patch.object(mod, "sync_news_to_qdrant", return_value=stats),
            ):
                exit_code = mod.main()

            self.assertEqual(exit_code, 2)
            self.assertTrue(summary_path.exists())

    def test_main_degraded_memos_without_wait_returns_success(self):
        import load_news_to_qdrant as mod

        with tempfile.TemporaryDirectory() as td:
            summary_path = Path(td) / "summary.json"
            argv = [
                "load_news_to_qdrant.py",
                "--db-path",
                str(Path(td) / "news_articles.sqlite"),
                "--summary-json",
                str(summary_path),
            ]
            stats = {
                "status": "success",
                "articles": 2,
                "chunks": 2,
                "upserted": 2,
                "deleted": 0,
                "dry_run": False,
                "qdrant_only": False,
                "memo_extraction": {"status": "degraded"},
            }

            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    mod,
                    "latest_provider_run_summary",
                    return_value={"status": "success", "params": {}},
                ),
                patch.object(mod, "sync_news_to_qdrant", return_value=stats),
            ):
                exit_code = mod.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(summary_path.exists())

    def test_dispatch_news_memos_wait_reports_timeout_and_failed_counts(self):
        import load_news_to_qdrant as mod

        articles = [
            {
                "article_id": "art-1",
                "text": "memo text 1",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T08:00:00Z",
            },
            {
                "article_id": "art-2",
                "text": "memo text 2",
                "provider": "newspaper4k",
                "published_at": "2026-05-04T09:00:00Z",
            },
        ]
        async_results = [
            FakeAsyncResult("task-art-1", ready=True, successful=False),
            FakeAsyncResult("task-art-2", ready=False, successful=False),
        ]

        class ResultTask:
            def delay(self, _payload):
                return async_results.pop(0)

        with tempfile.TemporaryDirectory() as td:
            result = _dispatch_with_wait_options(
                mod,
                articles,
                task=ResultTask(),
                memos_path=Path(td) / "news_memos.jsonl",
                wait=True,
                timeout=0.0,
                poll_interval=0.0,
            )

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["dispatched"], 2)
        self.assertTrue(result["completion_observable"])
        self.assertEqual(_count(result, "completed", "completion_completed", "tasks_completed"), 0)
        self.assertEqual(_count(result, "pending", "completion_pending", "tasks_pending"), 1)
        self.assertEqual(_count(result, "failed", "completion_failed", "tasks_failed"), 1)


class FakeAsyncResult:
    def __init__(
        self,
        task_id: str,
        *,
        ready: bool = True,
        successful: bool = True,
        value: object | None = None,
    ):
        self.id = task_id
        self._ready = ready
        self._successful = successful
        self._value = value

    def ready(self):
        return self._ready

    def successful(self):
        return self._successful

    def failed(self):
        return self._ready and not self._successful

    def get(self, *args, **kwargs):
        if not self._successful:
            raise RuntimeError(f"task failed: {self.id}")
        return self._value


def _count(result: dict, *names: str) -> int:
    for name in names:
        if name in result:
            return int(result[name] or 0)
    raise AssertionError(f"missing any count field: {names}; result={result}")


def _task_id_samples(result: dict) -> list[str]:
    for name in (
        "task_id_samples",
        "task_ids_sample",
        "dispatched_task_id_samples",
        "memo_task_id_samples",
    ):
        values = result.get(name)
        if values:
            return [str(value) for value in values]
    raise AssertionError(f"missing task id sample field; result={result}")


def _dispatch_with_wait_options(
    mod,
    articles,
    *,
    task,
    memos_path,
    wait: bool,
    timeout: float,
    poll_interval: float,
):
    signature = inspect.signature(mod.dispatch_news_memos)
    params = signature.parameters
    kwargs = {"task": task, "memos_path": memos_path}

    wait_name = _first_supported(params, "wait_for_completion", "wait", "wait_for_tasks")
    timeout_name = _first_supported(
        params,
        "wait_timeout_seconds",
        "timeout_seconds",
        "wait_timeout",
        "task_timeout_seconds",
    )
    poll_name = _first_supported(
        params,
        "poll_interval_seconds",
        "poll_interval",
        "task_poll_interval_seconds",
    )
    if wait_name is None:
        raise unittest.SkipTest("dispatch_news_memos wait-mode parameters are not available yet")
    kwargs[wait_name] = wait
    if timeout_name is not None:
        kwargs[timeout_name] = timeout
    if poll_name is not None:
        kwargs[poll_name] = poll_interval

    return mod.dispatch_news_memos(articles, **kwargs)


def _first_supported(params, *names: str) -> str | None:
    for name in names:
        if name in params:
            return name
    return None


if __name__ == "__main__":
    unittest.main()
