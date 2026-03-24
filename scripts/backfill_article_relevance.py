#!/usr/bin/env python3
"""Backfill article_relevance rows from existing entity_links without re-fetching.

Safe to re-run (idempotent: replace_article_relevance deletes then inserts per article).
Processes all articles that have entity_links but no article_relevance row (unless --all).

Usage:
    python3 scripts/backfill_article_relevance.py
    python3 scripts/backfill_article_relevance.py --all          # recompute for all articles
    python3 scripts/backfill_article_relevance.py --dry-run      # print stats, no writes
    python3 scripts/backfill_article_relevance.py --db-path /path/to/news_articles.sqlite
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB  # noqa: E402
from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.models import EntityLink  # noqa: E402
from news_pipeline.relevance import score_article_relevance  # noqa: E402


def _load_articles_needing_relevance(
    conn: sqlite3.Connection,
    *,
    recompute_all: bool,
) -> List[Dict[str, Any]]:
    """Return articles that have entity_links but missing (or all, if --all) article_relevance rows."""
    if recompute_all:
        sql = """
            SELECT a.article_id, a.title, a.description, a.body
              FROM articles a
             WHERE EXISTS (SELECT 1 FROM entity_links el WHERE el.article_id = a.article_id)
             ORDER BY a.published_at_utc DESC
        """
    else:
        sql = """
            SELECT a.article_id, a.title, a.description, a.body
              FROM articles a
             WHERE EXISTS (SELECT 1 FROM entity_links el WHERE el.article_id = a.article_id)
               AND NOT EXISTS (SELECT 1 FROM article_relevance ar WHERE ar.article_id = a.article_id)
             ORDER BY a.published_at_utc DESC
        """
    return [dict(row) for row in conn.execute(sql).fetchall()]


def _load_entity_links_for_article(
    conn: sqlite3.Connection,
    article_id: str,
    published_at_utc: str,
) -> List[EntityLink]:
    rows = conn.execute(
        """
        SELECT ticker, confidence, lane, method, matched_alias,
               matched_span_start, matched_span_end
          FROM entity_links
         WHERE article_id = ?
        """,
        (article_id,),
    ).fetchall()
    return [
        EntityLink(
            article_id=article_id,
            ticker=str(row[0] or ""),
            confidence=float(row[1] or 0.0),
            lane=str(row[2] or ""),
            method=str(row[3] or ""),
            matched_alias=str(row[4] or ""),
            matched_span_start=row[5],
            matched_span_end=row[6],
            published_at_utc=published_at_utc,
        )
        for row in rows
    ]


def backfill_article_relevance(
    db_path: str,
    *,
    recompute_all: bool = False,
    dry_run: bool = False,
) -> Dict[str, int]:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        print(f"[error] DB not found: {db}", file=sys.stderr)
        sys.exit(1)

    # Read-only connection for loading articles and links.
    ro_conn = sqlite3.connect(str(db))
    ro_conn.row_factory = sqlite3.Row
    try:
        articles = _load_articles_needing_relevance(ro_conn, recompute_all=recompute_all)
        # Pre-load published_at per article for EntityLink construction.
        published_at_map: Dict[str, str] = {}
        if articles:
            ids = [str(a["article_id"]) for a in articles]
            marks = ",".join(["?"] * len(ids))
            for row in ro_conn.execute(
                f"SELECT article_id, published_at_utc FROM articles WHERE article_id IN ({marks})",
                tuple(ids),
            ).fetchall():
                published_at_map[str(row[0])] = str(row[1] or "")
    finally:
        ro_conn.close()

    total = len(articles)
    print(f"[backfill_article_relevance] articles_to_process={total} dry_run={dry_run}")
    if total == 0:
        return {"processed": 0, "written": 0, "skipped": 0}

    if dry_run:
        return {"processed": 0, "written": 0, "skipped": total}

    store = NewsArticleStore(db)
    try:
        written = 0
        skipped = 0
        for i, article in enumerate(articles):
            article_id = str(article["article_id"])
            title = str(article["title"] or "")
            description = str(article["description"] or "")
            body = str(article["body"] or "")
            published_at = published_at_map.get(article_id, "")

            links = _load_entity_links_for_article(store.conn, article_id, published_at)
            if not links:
                skipped += 1
                continue

            relevance_rows = score_article_relevance(
                article_id=article_id,
                title=title,
                description=description,
                body=body,
                links=links,
            )
            store.replace_article_relevance(article_id, relevance_rows)
            written += 1

            if (i + 1) % 50 == 0:
                print(f"[backfill_article_relevance] progress {i + 1}/{total} written={written}")
    finally:
        store.close()

    print(f"[backfill_article_relevance] done written={written} skipped={skipped}")
    return {"processed": total, "written": written, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill article_relevance from existing entity_links.")
    ap.add_argument("--db-path", default=str(DEFAULT_NEWS_ARTICLES_DB), help="news_articles SQLite path")
    ap.add_argument("--all", dest="recompute_all", action="store_true", help="Recompute even articles that already have relevance rows")
    ap.add_argument("--dry-run", action="store_true", help="Print stats only, no writes")
    args = ap.parse_args(argv)

    import json
    stats = backfill_article_relevance(
        db_path=args.db_path,
        recompute_all=args.recompute_all,
        dry_run=args.dry_run,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
