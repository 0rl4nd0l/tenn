from __future__ import annotations

import sqlite3
from pathlib import Path

from cockpit.core.tools import ToolRouter


def _make_router(repo_root: Path) -> ToolRouter:
    return ToolRouter(
        db_reader=None,
        file_indexer=None,
        web_fetcher=None,
        repo_root=repo_root,
        web_default_enabled=False,
    )


def test_get_local_news_article_reads_body_from_workspace_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    engine_root = workspace_root / "financial-engine_v2"
    db_dir = workspace_root / "reports" / "qual_context"
    db_dir.mkdir(parents=True)
    engine_root.mkdir(parents=True)
    db_path = db_dir / "news_articles.sqlite"

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE articles (
                article_id TEXT,
                canonical_url TEXT,
                title TEXT,
                description TEXT,
                body TEXT,
                provider_best TEXT,
                published_at_utc TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO articles (article_id, canonical_url, title, description, body, provider_best, published_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "a1",
                "https://kalkinemedia.com/nz/news/market-updates",
                "Market News and Updates on NZX Stocks",
                "desc",
                "Full article body",
                "kalkine",
                "2026-04-08T03:30:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setenv("TENN_NEWS_ARTIFACT_ROOT", str(db_dir))
    router = _make_router(engine_root)
    result = router.get_local_news_article(
        "https://kalkinemedia.com/nz/news/market-updates"
    )

    assert result["ok"] is True
    assert result["title"] == "Market News and Updates on NZX Stocks"
    assert result["body"] == "Full article body"
    assert result["source"] == "local_news_corpus"
