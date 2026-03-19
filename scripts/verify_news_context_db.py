#!/usr/bin/env python3
"""
Verify the canonical news context DB (reports/qual_context/news.sqlite).

Checks:
  - Count per corpus
  - Count per ticker (and company for news)
  - Duplicate chunk_id (must be zero; PK enforces, this is a sanity check)
  - Optional: news-only mode (corpus LIKE 'news%')

Exit 0 if all invariants pass; non-zero otherwise.
See docs/architecture/15_news_substrate.md.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_NEWS_SQLITE = REPO_ROOT / "reports" / "qual_context" / "news.sqlite"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify news context DB: counts, duplicate check, invariants")
    ap.add_argument(
        "--db",
        default=str(DEFAULT_NEWS_SQLITE),
        help="Path to news context SQLite (default: reports/qual_context/news.sqlite)",
    )
    ap.add_argument(
        "--news-only",
        action="store_true",
        help="Restrict checks to rows where corpus LIKE 'news%'",
    )
    ap.add_argument(
        "--out-json",
        default="",
        help="Write verification result JSON to this path",
    )
    args = ap.parse_args(argv)

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"[verify_news_context_db] DB not found: {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check table exists
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='context_chunks'"
    )
    if not cur.fetchone():
        print("[verify_news_context_db] Table context_chunks not found", file=sys.stderr)
        conn.close()
        return 2

    where_news = " WHERE corpus LIKE 'news%'" if args.news_only else ""
    and_news = " AND corpus LIKE 'news%'" if args.news_only else ""

    # Total count
    cur.execute(f"SELECT COUNT(*) AS n FROM context_chunks{where_news}")
    total = cur.fetchone()[0]

    # Count per corpus
    cur.execute(
        f"SELECT corpus, COUNT(*) AS n FROM context_chunks{where_news} GROUP BY corpus ORDER BY n DESC"
    )
    by_corpus = [{"corpus": row["corpus"], "count": row["n"]} for row in cur.fetchall()]

    # Count per ticker (non-empty ticker)
    cur.execute(
        f"SELECT ticker, COUNT(*) AS n FROM context_chunks WHERE (ticker IS NOT NULL AND ticker != ''){and_news} GROUP BY ticker ORDER BY n DESC LIMIT 500"
    )
    by_ticker = [{"ticker": row["ticker"], "count": row["n"]} for row in cur.fetchall()]

    # Count per company (for news, company often holds primary ticker)
    cur.execute(
        f"SELECT company, COUNT(*) AS n FROM context_chunks WHERE (company IS NOT NULL AND company != ''){and_news} GROUP BY company ORDER BY n DESC LIMIT 500"
    )
    by_company = [{"company": row["company"], "count": row["n"]} for row in cur.fetchall()]

    # Duplicate chunk_id check (should be 0; PK prevents duplicates, this is sanity)
    cur.execute(
        "SELECT chunk_id, COUNT(*) AS n FROM context_chunks GROUP BY chunk_id HAVING COUNT(*) > 1"
    )
    duplicates = cur.fetchall()
    duplicate_count = len(duplicates)
    duplicate_sample = [row["chunk_id"] for row in duplicates[:10]] if duplicates else []

    conn.close()

    # Invariants: no duplicate chunk_id (PK enforces; this is a sanity check)
    invariant_duplicate_ok = duplicate_count == 0
    all_ok = invariant_duplicate_ok

    payload = {
        "db": str(db_path),
        "news_only": args.news_only,
        "total_chunks": total,
        "by_corpus": by_corpus,
        "by_ticker_sample": by_ticker[:50],
        "by_company_sample": by_company[:50],
        "duplicate_chunk_ids": duplicate_count,
        "duplicate_sample": duplicate_sample,
        "invariants": {
            "no_duplicate_chunk_ids": invariant_duplicate_ok,
        },
        "ok": all_ok,
    }

    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"[verify_news_context_db] wrote {out_path}")

    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    if not invariant_duplicate_ok:
        print("[verify_news_context_db] FAIL: duplicate chunk_id found", file=sys.stderr)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
