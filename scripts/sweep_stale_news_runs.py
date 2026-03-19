#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB, resolve_path  # noqa: E402
from news_pipeline.db import NewsArticleStore  # noqa: E402


def _stale_running_rows(db_path: Path, older_than_hours: int) -> list[dict[str, str]]:
    hours = int(max(1, older_than_hours))
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT run_id, provider, mode, started_at
              FROM provider_runs
             WHERE status = 'running'
               AND datetime(replace(replace(started_at, 'T', ' '), 'Z', '')) < datetime('now', ?)
             ORDER BY started_at
            """,
            (f"-{hours} hours",),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mark stale news provider runs stuck in 'running' as failed.")
    ap.add_argument("--news-articles-db", default=str(DEFAULT_NEWS_ARTICLES_DB), help="Canonical article DB path")
    ap.add_argument("--older-than-hours", type=int, default=2, help="Staleness threshold in hours")
    ap.add_argument(
        "--to-status",
        default="failed",
        choices=["failed", "partial_failed"],
        help="Final status to apply to stale runs",
    )
    ap.add_argument("--dry-run", action="store_true", help="Report stale runs without updating the DB")
    args = ap.parse_args(argv)

    db_path = resolve_path(args.news_articles_db)
    if not db_path.exists():
        print(json.dumps({"error": f"news_articles_db not found: {db_path}"}, indent=2, sort_keys=True))
        return 2

    stale_before = _stale_running_rows(db_path=db_path, older_than_hours=int(args.older_than_hours))
    updated = 0
    if not bool(args.dry_run):
        store = NewsArticleStore(db_path)
        try:
            updated = int(
                store.finalize_stale_running_runs(
                    older_than_hours=int(max(1, args.older_than_hours)),
                    to_status=str(args.to_status),
                )
            )
        finally:
            store.close()

    payload = {
        "news_articles_db": str(db_path),
        "older_than_hours": int(max(1, args.older_than_hours)),
        "to_status": str(args.to_status),
        "dry_run": bool(args.dry_run),
        "stale_before_count": len(stale_before),
        "updated_count": int(updated),
        "stale_before": stale_before,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
