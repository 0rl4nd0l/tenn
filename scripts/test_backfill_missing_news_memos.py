from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import backfill_missing_news_memos as backfill  # noqa: E402


def _create_articles_db(path: Path) -> None:
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
        for article_id in ("art-1", "art-2", "art-3"):
            conn.execute(
                """
                INSERT INTO articles(
                    article_id, canonical_url, title, description, body,
                    provider_best, language, published_at_utc, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article_id,
                    f"https://example.com/{article_id}",
                    f"Title {article_id}",
                    "Description",
                    "Body text " * 20,
                    "newspaper4k",
                    "en",
                    "2026-05-05T00:00:00Z",
                    0.9,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def test_backfill_dispatches_only_missing_memos(tmp_path: Path) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    memos_path = tmp_path / "news_memos.jsonl"
    summary_path = tmp_path / "summary.json"
    _create_articles_db(db_path)
    memos_path.write_text(
        json.dumps({"source_id": "news:art-1"}) + "\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_dispatch(articles, **kwargs):
        seen["article_ids"] = [article["article_id"] for article in articles]
        seen["kwargs"] = dict(kwargs)
        return {
            "status": "pending",
            "eligible": len(articles),
            "dispatched": len(articles),
            "missing_after_dispatch": len(articles),
        }

    with patch.object(backfill, "dispatch_news_memos", side_effect=fake_dispatch):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--limit",
                "1",
                "--memo-diagnostics-path",
                str(memos_path),
                "--summary-json",
                str(summary_path),
            ]
        )

    assert exit_code == 0
    assert seen["article_ids"] == ["art-3"]
    assert seen["kwargs"]["force_dispatch"] is False
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["coverage_before"]["persisted"] == 1
    assert summary["selection"]["selected"] == 1


def test_backfill_wait_degraded_returns_nonzero(tmp_path: Path) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    _create_articles_db(db_path)

    with patch.object(
        backfill,
        "dispatch_news_memos",
        return_value={"status": "degraded", "eligible": 1},
    ):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--wait-for-memos",
            ]
        )

    assert exit_code == 2


def test_backfill_wait_batches_unlimited_selection(tmp_path: Path) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    memos_path = tmp_path / "news_memos.jsonl"
    summary_path = tmp_path / "summary.json"
    _create_articles_db(db_path)
    batch_article_ids: list[list[str]] = []

    def fake_dispatch(articles, **kwargs):
        batch_article_ids.append([article["article_id"] for article in articles])
        return {
            "status": "complete",
            "eligible": len(articles),
            "dispatched": len(articles),
            "dispatch_candidates": len(articles),
            "persisted_after_dispatch": len(articles),
            "missing_after_dispatch": 0,
            "tasks_observed": len(articles),
            "tasks_completed": len(articles),
            "completion_observable": True,
            "wait_requested": kwargs["wait_for_completion"],
        }

    with patch.object(backfill, "dispatch_news_memos", side_effect=fake_dispatch):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--limit",
                "0",
                "--wait-for-memos",
                "--dispatch-batch-size",
                "2",
                "--memo-diagnostics-path",
                str(memos_path),
                "--summary-json",
                str(summary_path),
            ]
        )

    assert exit_code == 0
    assert batch_article_ids == [["art-3", "art-2"], ["art-1"]]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["selection"]["selected"] == 3
    assert summary["memo_extraction"]["batched"] is True
    assert summary["memo_extraction"]["batch_size"] == 2
    assert summary["memo_extraction"]["batches_attempted"] == 2
    assert summary["memo_extraction"]["dispatched"] == 3
    assert summary["memo_extraction"]["tasks_completed"] == 3


def test_backfill_wait_batches_continue_after_observed_task_failure(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    memos_path = tmp_path / "news_memos.jsonl"
    summary_path = tmp_path / "summary.json"
    _create_articles_db(db_path)
    batch_article_ids: list[list[str]] = []

    def fake_dispatch(articles, **kwargs):
        article_ids = [article["article_id"] for article in articles]
        batch_article_ids.append(article_ids)
        if article_ids == ["art-3"]:
            return {
                "status": "degraded",
                "eligible": 1,
                "dispatched": 1,
                "dispatch_candidates": 1,
                "missing_after_dispatch": 1,
                "tasks_observed": 1,
                "tasks_completed": 0,
                "tasks_failed": 1,
                "tasks_pending": 0,
                "tasks_unobserved": 0,
                "completion_observable": True,
                "wait_requested": kwargs["wait_for_completion"],
            }
        return {
            "status": "complete",
            "eligible": len(articles),
            "dispatched": len(articles),
            "dispatch_candidates": len(articles),
            "persisted_after_dispatch": len(articles),
            "missing_after_dispatch": 0,
            "tasks_observed": len(articles),
            "tasks_completed": len(articles),
            "tasks_failed": 0,
            "tasks_pending": 0,
            "tasks_unobserved": 0,
            "completion_observable": True,
            "wait_requested": kwargs["wait_for_completion"],
        }

    with patch.object(backfill, "dispatch_news_memos", side_effect=fake_dispatch):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--limit",
                "0",
                "--wait-for-memos",
                "--dispatch-batch-size",
                "1",
                "--memo-diagnostics-path",
                str(memos_path),
                "--summary-json",
                str(summary_path),
            ]
        )

    assert exit_code == 2
    assert batch_article_ids == [["art-3"], ["art-2"], ["art-1"]]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["memo_extraction"]["status"] == "degraded"
    assert summary["memo_extraction"]["batches_attempted"] == 3
    assert summary["memo_extraction"]["batches_continued_after_observed_failures"] == 1
    assert summary["memo_extraction"]["tasks_failed"] == 1
    assert summary["memo_extraction"]["tasks_completed"] == 2


def test_backfill_wait_batches_stop_on_unobserved_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    memos_path = tmp_path / "news_memos.jsonl"
    summary_path = tmp_path / "summary.json"
    _create_articles_db(db_path)
    batch_article_ids: list[list[str]] = []

    def fake_dispatch(articles, **kwargs):
        article_ids = [article["article_id"] for article in articles]
        batch_article_ids.append(article_ids)
        return {
            "status": "degraded",
            "eligible": len(articles),
            "dispatched": len(articles),
            "dispatch_candidates": len(articles),
            "missing_after_dispatch": len(articles),
            "tasks_observed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_pending": 0,
            "tasks_unobserved": len(articles),
            "completion_observable": False,
            "wait_requested": kwargs["wait_for_completion"],
        }

    with patch.object(backfill, "dispatch_news_memos", side_effect=fake_dispatch):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--limit",
                "0",
                "--wait-for-memos",
                "--dispatch-batch-size",
                "1",
                "--memo-diagnostics-path",
                str(memos_path),
                "--summary-json",
                str(summary_path),
            ]
        )

    assert exit_code == 2
    assert batch_article_ids == [["art-3"]]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["memo_extraction"]["batches_attempted"] == 1
    assert summary["memo_extraction"]["batches_continued_after_observed_failures"] == 0
    assert summary["memo_extraction"]["tasks_unobserved"] == 1


def test_backfill_no_wait_does_not_batch(tmp_path: Path) -> None:
    db_path = tmp_path / "news_articles.sqlite"
    memos_path = tmp_path / "news_memos.jsonl"
    _create_articles_db(db_path)
    batch_article_ids: list[list[str]] = []

    def fake_dispatch(articles, **kwargs):
        batch_article_ids.append([article["article_id"] for article in articles])
        return {
            "status": "pending",
            "eligible": len(articles),
            "dispatched": len(articles),
            "wait_requested": kwargs["wait_for_completion"],
        }

    with patch.object(backfill, "dispatch_news_memos", side_effect=fake_dispatch):
        exit_code = backfill.main(
            [
                "--db-path",
                str(db_path),
                "--since-hours",
                "0",
                "--limit",
                "0",
                "--dispatch-batch-size",
                "1",
                "--memo-diagnostics-path",
                str(memos_path),
            ]
        )

    assert exit_code == 0
    assert batch_article_ids == [["art-3", "art-2", "art-1"]]
