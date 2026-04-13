"""Celery tasks for the news ingestion pipeline."""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    _default_scripts = str(Path(__file__).resolve().parents[3] / "scripts")
except IndexError:
    _default_scripts = ""
SCRIPTS_DIR = os.environ.get("SCRIPTS_ROOT", _default_scripts)
if SCRIPTS_DIR and SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

BACKEND_ROOT = os.environ.get("BACKEND_APP_ROOT", "/app_backend")
if BACKEND_ROOT and BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from .celery_app import celery  # noqa: E402


@celery.task(name="run_daily_news_pipeline")
def run_daily_news_pipeline(since_hours: int = 36, providers: str = "newspaper4k") -> dict:
    """Run the daily news provider fetch pipeline.

    Default provider changed from eodhd,gdelt → newspaper4k (2026-03-27).
    Reason: eodhd and gdelt produce low-quality results for ASX news.
    newspaper4k scrapes 54 AU finance sources (AFR, Stockhead, MarketIndex,
    SMH, ABC, The Australian, etc.) with Scrapling/Playwright fallback.

    To use legacy providers (not recommended):
        run_daily_news_pipeline.delay(providers="eodhd,gdelt")
    """
    import fetch_daily_news as pipeline  # noqa: F401
    result = pipeline.main(["--since-hours", str(since_hours), "--providers", providers])
    return {"exit_code": result}


@celery.task(name="build_news_chunks")
def build_news_chunks_task(
    lane: str = "high_precision",
    embed_backend: str = "hash",
    hash_dim: int = 384,
) -> dict:
    """Rebuild news.sqlite chunk store from news_articles.sqlite.

    Uses hash-based pseudo-embeddings by default (no Ollama required).
    The output feeds the cockpit SQLite fallback path in get_news_context.
    """
    from pathlib import Path

    from news_pipeline.chunk_builder import build_news_chunks
    from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB, DEFAULT_NEWS_CONTEXT_DB

    stats = build_news_chunks(
        from_db=Path(DEFAULT_NEWS_ARTICLES_DB),
        to_db=Path(DEFAULT_NEWS_CONTEXT_DB),
        lane=lane,
        embed_backend=embed_backend,
        hash_dim=hash_dim,
    )
    return stats


@celery.task(name="sync_news_qdrant")
def sync_news_qdrant(
    db_path: str = "",
    qdrant_url: str = "",
    collection: str = "news_chunks",
    batch_size: int = 64,
    since_hours: int = 4,
) -> dict:
    """Sync recent news chunks from SQLite into Qdrant."""
    from load_news_to_qdrant import sync_news_to_qdrant  # noqa: F401

    _db_path = db_path or os.environ.get(
        "NEWS_ARTICLES_DB",
        str(Path(SCRIPTS_DIR).parents[0] / "reports" / "qual_context" / "news_articles.sqlite"),
    )
    _qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://qdrant:6333")
    _since: int | None = int(since_hours) if int(since_hours) > 0 else None

    stats = sync_news_to_qdrant(
        db_path=_db_path,
        qdrant_url=_qdrant_url,
        collection=collection,
        batch_size=int(batch_size),
        since_hours=_since,
    )
    return stats
