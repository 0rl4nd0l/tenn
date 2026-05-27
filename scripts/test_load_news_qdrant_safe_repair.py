#!/usr/bin/env python3
"""Tests for safe Qdrant projection repair mode in the news loader."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from load_news_to_qdrant import build_news_projection_target, sync_news_to_qdrant  # noqa: E402


class _FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeCollections:
    def __init__(self, names: list[str]) -> None:
        self.collections = [_FakeCollection(name) for name in names]


class _FakePoint:
    def __init__(self, point_id: str, payload: dict[str, Any]) -> None:
        self.id = point_id
        self.payload = payload


class FakeQdrantClient:
    def __init__(
        self,
        points: dict[str, dict[str, Any]] | None = None,
        *,
        collection: str = "news_chunks",
    ) -> None:
        self.collection = collection
        self.points = {str(pid): dict(payload) for pid, payload in (points or {}).items()}
        self.upserted: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def get_collections(self) -> _FakeCollections:
        return _FakeCollections([self.collection])

    def scroll(
        self,
        *,
        collection_name: str,
        limit: int,
        offset: int | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> tuple[list[_FakePoint], int | None]:
        del collection_name, with_payload, with_vectors
        rows = list(self.points.items())
        start = int(offset or 0)
        end = start + int(limit)
        batch = [_FakePoint(point_id, payload) for point_id, payload in rows[start:end]]
        next_offset = end if end < len(rows) else None
        return batch, next_offset


def _create_articles_db(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    links: list[tuple[str, str]] | None = None,
    relevance: list[tuple[str, str, int, float]] | None = None,
) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE articles (
                article_id TEXT PRIMARY KEY,
                canonical_url TEXT,
                title TEXT,
                description TEXT,
                body TEXT,
                provider_best TEXT,
                language TEXT,
                published_at_utc TEXT,
                quality_score REAL
            );
            CREATE TABLE entity_links (
                article_id TEXT,
                ticker TEXT
            );
            CREATE TABLE article_relevance (
                article_id TEXT,
                ticker TEXT,
                is_primary INTEGER,
                relevance_score REAL
            );
            """
        )
        for row in rows:
            conn.execute(
                """
                INSERT INTO articles(
                    article_id, canonical_url, title, description, body,
                    provider_best, language, published_at_utc, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["article_id"],
                    row.get("canonical_url", f"https://example.com/{row['article_id']}"),
                    row.get("title", f"Title {row['article_id']}"),
                    row.get("description", "Description"),
                    row.get("body", "Body text " * 10),
                    row.get("provider_best", "newspaper4k"),
                    row.get("language", "en"),
                    row.get("published_at_utc", "2026-05-05T00:00:00Z"),
                    row.get("quality_score", 0.9),
                ),
            )
        for article_id, ticker in links or []:
            conn.execute(
                "INSERT INTO entity_links(article_id, ticker) VALUES (?, ?)",
                (article_id, ticker),
            )
        for article_id, ticker, is_primary, score in relevance or []:
            conn.execute(
                """
                INSERT INTO article_relevance(
                    article_id, ticker, is_primary, relevance_score
                ) VALUES (?, ?, ?, ?)
                """,
                (article_id, ticker, is_primary, score),
            )
        conn.commit()
    finally:
        conn.close()


def _embed_texts(texts: list[str]) -> list[list[float]]:
    return [[float(len(text) or 1), 0.0] for text in texts]


def _ensure_collection(
    client: FakeQdrantClient,
    collection: str,
    dim: int,
) -> None:
    del client, collection, dim


def _vector_config(
    client: FakeQdrantClient,
    collection: str,
) -> dict[str, int]:
    del collection
    return {"actual_dim": 2, "points_count": len(client.points)}


def _upsert_points(
    client: FakeQdrantClient,
    collection: str,
    points: list[dict[str, Any]],
) -> None:
    del collection
    client.upserted.extend(points)
    for point in points:
        client.points[str(point["id"])] = dict(point["payload"])


def _delete_points(
    client: FakeQdrantClient,
    collection: str,
    point_ids: list[str],
) -> None:
    del collection
    for point_id in point_ids:
        client.deleted.append(str(point_id))
        client.points.pop(str(point_id), None)


def _raise_if_memo_dispatched(_articles: list[dict[str, Any]]) -> dict[str, Any]:
    raise AssertionError("memo dispatch must not be called")


class NewsQdrantSafeRepairTests(unittest.TestCase):
    def test_dry_run_does_not_mutate_qdrant_sqlite_or_memos(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(db_path, [{"article_id": "dry-run-art"}])
            fake_client = FakeQdrantClient({"999": {"chunk_id": "news:stale:0"}})

            stats = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=fake_client,
                embed_texts_fn=lambda texts: self.fail(f"unexpected embed: {texts}"),
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                memo_dispatch_fn=_raise_if_memo_dispatched,
                dry_run=True,
                cleanup_stale=True,
                dispatch_memos=True,
                write_model_marker=False,
            )

            self.assertEqual(stats["upserted"], 0)
            self.assertEqual(stats["deleted"], 0)
            self.assertEqual(fake_client.upserted, [])
            self.assertEqual(fake_client.deleted, [])
            self.assertEqual(stats["memo_extraction"]["status"], "skipped")
            self.assertEqual(stats["qdrant_diff"]["stale_qdrant_chunks"], 1)
            self.assertFalse(Path(f"{db_path}-wal").exists())
            self.assertFalse(Path(f"{db_path}-shm").exists())

    def test_no_dispatch_memos_prevents_memo_task_on_write_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(db_path, [{"article_id": "memo-art"}])
            fake_client = FakeQdrantClient()

            stats = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=fake_client,
                embed_texts_fn=_embed_texts,
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                memo_dispatch_fn=_raise_if_memo_dispatched,
                dispatch_memos=False,
                write_model_marker=False,
            )

            self.assertEqual(stats["chunks"], 1)
            self.assertEqual(stats["upserted"], 1)
            self.assertEqual(len(fake_client.upserted), 1)
            self.assertEqual(stats["memo_extraction"]["status"], "skipped")

    def test_skip_clean_upserts_leaves_matching_qdrant_points_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(db_path, [{"article_id": "clean-art"}])
            target = build_news_projection_target(db_path)
            expected_point = target["points"][0]
            fake_client = FakeQdrantClient(
                {str(expected_point["id"]): expected_point["payload"]}
            )

            stats = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=fake_client,
                embed_texts_fn=_embed_texts,
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                memo_dispatch_fn=_raise_if_memo_dispatched,
                dispatch_memos=False,
                skip_clean_upserts=True,
                write_model_marker=False,
            )

            self.assertTrue(stats["skip_clean_upserts"])
            self.assertEqual(stats["qdrant_diff"]["missing_expected_chunks"], 0)
            self.assertEqual(stats["qdrant_diff"]["payload_drift_chunks"], 0)
            self.assertEqual(stats["repair_candidate_chunks"], 0)
            self.assertEqual(stats["upserted"], 0)
            self.assertEqual(fake_client.upserted, [])
            self.assertEqual(stats["memo_extraction"]["status"], "skipped")

    def test_skip_clean_upserts_repairs_payload_drift_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(db_path, [{"article_id": "drift-art"}])
            target = build_news_projection_target(db_path)
            expected_point = target["points"][0]
            drifted_payload = dict(expected_point["payload"])
            drifted_payload["title"] = "Old title"
            fake_client = FakeQdrantClient({str(expected_point["id"]): drifted_payload})

            stats = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=fake_client,
                embed_texts_fn=_embed_texts,
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                memo_dispatch_fn=_raise_if_memo_dispatched,
                dispatch_memos=False,
                skip_clean_upserts=True,
                write_model_marker=False,
            )

            self.assertEqual(stats["qdrant_diff"]["payload_drift_chunks"], 1)
            self.assertEqual(stats["repair_candidate_chunks"], 1)
            self.assertEqual(stats["upserted"], 1)
            self.assertEqual(len(fake_client.upserted), 1)
            self.assertEqual(
                fake_client.points[str(expected_point["id"])]["title"],
                expected_point["payload"]["title"],
            )

    def test_explicit_memo_diagnostics_path_reaches_default_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            memos_path = Path(td) / "news_memos.jsonl"
            _create_articles_db(db_path, [{"article_id": "memo-path-art"}])
            fake_client = FakeQdrantClient()
            seen: dict[str, Any] = {}

            def fake_dispatch(
                articles: list[dict[str, Any]],
                *,
                memos_path: str | Path | None = None,
                **_kwargs: Any,
            ) -> dict[str, Any]:
                seen["articles"] = articles
                seen["memos_path"] = memos_path
                return {
                    "status": "pending",
                    "memos_path": str(memos_path or ""),
                    "eligible": len(articles),
                    "completion_observable": False,
                }

            with patch("load_news_to_qdrant.dispatch_news_memos", side_effect=fake_dispatch):
                stats = sync_news_to_qdrant(
                    str(db_path),
                    qdrant_client=fake_client,
                    embed_texts_fn=_embed_texts,
                    upsert_points_fn=_upsert_points,
                    delete_points_fn=_delete_points,
                    ensure_collection_fn=_ensure_collection,
                    get_vector_config_fn=_vector_config,
                    dispatch_memos=True,
                    memo_diagnostics_path=memos_path,
                    write_model_marker=False,
                )

            self.assertEqual(seen["memos_path"], memos_path)
            self.assertEqual(len(seen["articles"]), 1)
            self.assertEqual(stats["memo_extraction"]["memos_path"], str(memos_path))

    def test_stale_cleanup_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(db_path, [{"article_id": "cleanup-art"}])
            target = build_news_projection_target(db_path)
            expected_point = target["points"][0]
            stale_points = {
                str(expected_point["id"]): expected_point["payload"],
                "999": {"chunk_id": "news:stale:0"},
            }

            no_cleanup_client = FakeQdrantClient(stale_points)
            no_cleanup = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=no_cleanup_client,
                embed_texts_fn=_embed_texts,
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                dispatch_memos=False,
                qdrant_only=True,
                write_model_marker=False,
            )
            self.assertEqual(no_cleanup["qdrant_diff"]["stale_qdrant_chunks"], 1)
            self.assertEqual(no_cleanup_client.deleted, [])

            cleanup_client = FakeQdrantClient(stale_points)
            cleanup = sync_news_to_qdrant(
                str(db_path),
                qdrant_client=cleanup_client,
                embed_texts_fn=_embed_texts,
                upsert_points_fn=_upsert_points,
                delete_points_fn=_delete_points,
                ensure_collection_fn=_ensure_collection,
                get_vector_config_fn=_vector_config,
                dispatch_memos=False,
                qdrant_only=True,
                cleanup_stale=True,
                write_model_marker=False,
            )
            self.assertEqual(cleanup["deleted"], 1)
            self.assertEqual(cleanup_client.deleted, ["999"])

    def test_eligible_target_reporting_counts_quality_and_language_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(
                db_path,
                [
                    {"article_id": "eligible-en", "language": "en", "quality_score": 0.3},
                    {"article_id": "eligible-empty", "language": "", "quality_score": 0.8},
                    {"article_id": "eligible-null", "language": None, "quality_score": 0.8},
                    {"article_id": "low-quality", "language": "en", "quality_score": 0.29},
                    {"article_id": "wrong-language", "language": "fr", "quality_score": 0.8},
                ],
            )

            report = build_news_projection_target(db_path)["report"]

            self.assertEqual(report["eligible_articles"], 3)
            self.assertEqual(report["eligible_chunks"], 3)
            self.assertEqual(report["excluded_articles"], 2)
            self.assertEqual(report["excluded_chunks"], 2)
            self.assertEqual(report["excluded_reason_counts"]["low_quality"], 1)
            self.assertEqual(report["excluded_reason_counts"]["unsupported_language"], 1)
            self.assertEqual(report["provider_spread"], {"newspaper4k": 3})

    def test_target_payload_preserves_required_projection_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(
                db_path,
                [
                    {
                        "article_id": "payload-art",
                        "canonical_url": "https://example.com/payload-art",
                        "title": "Payload Article",
                        "body": "Payload body text.",
                    }
                ],
                links=[("payload-art", "BHP")],
                relevance=[("payload-art", "BHP", 1, 0.9)],
            )

            payload = build_news_projection_target(db_path)["points"][0]["payload"]

            for field in (
                "article_id",
                "chunk_id",
                "ticker",
                "tickers",
                "primary_ticker",
                "provider",
                "title",
                "url",
                "published_at",
                "text",
            ):
                self.assertIn(field, payload)
            self.assertEqual(payload["ticker"], "BHP")
            self.assertEqual(payload["tickers"], ["BHP"])
            self.assertEqual(payload["primary_ticker"], "BHP")
            self.assertEqual(payload["title"], "Payload Article")
            self.assertEqual(payload["url"], "https://example.com/payload-art")
            self.assertIn("Payload body text.", payload["text"])

    def test_a2m_projection_payload_preserves_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            _create_articles_db(
                db_path,
                [
                    {
                        "article_id": "a2m-art",
                        "canonical_url": "https://example.com/a2m",
                        "title": "A2M recall update",
                        "body": "The a2 Milk Company referenced ASX:A2M in its recall update.",
                        "provider_best": "newspaper4k",
                        "published_at_utc": "2026-05-05T03:00:00Z",
                    }
                ],
                links=[("a2m-art", "A2M")],
                relevance=[("a2m-art", "A2M", 1, 0.99)],
            )

            payload = build_news_projection_target(db_path)["points"][0]["payload"]

            self.assertEqual(payload["ticker"], "A2M")
            self.assertEqual(payload["primary_ticker"], "A2M")
            self.assertIn("A2M", payload["tickers"])
            self.assertEqual(payload["provider"], "newspaper4k")
            self.assertEqual(payload["title"], "A2M recall update")
            self.assertEqual(payload["url"], "https://example.com/a2m")
            self.assertEqual(payload["published_at"], "2026-05-05T03:00:00Z")


if __name__ == "__main__":
    unittest.main()
