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

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_NEWS_ARTICLES_DB,
    DEFAULT_NEWS_RUNS_DIR,
    DEFAULT_TICKER_UNIVERSE,
    resolve_path,
)
from news_pipeline.reporting import write_run_reports  # noqa: E402


def _latest_run_id(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            """
            SELECT run_id
              FROM provider_runs
             ORDER BY started_at DESC, run_id DESC
             LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return ""
    return str(row[0] or "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate ASX news coverage reports for a provider run.")
    ap.add_argument("--news-articles-db", default=str(DEFAULT_NEWS_ARTICLES_DB), help="Canonical article DB path")
    ap.add_argument("--run-id", default="", help="Provider run_id (defaults to latest)")
    ap.add_argument("--window-days", type=int, default=7, help="Compatibility flag (report always emits 1/7/30-day coverage)")
    ap.add_argument("--tickers-file", default=str(DEFAULT_TICKER_UNIVERSE), help="ASX ticker universe path")
    ap.add_argument("--news-runs-root", default=str(DEFAULT_NEWS_RUNS_DIR), help="Output root for run reports")
    args = ap.parse_args(argv)

    news_articles_db = resolve_path(args.news_articles_db)
    tickers_file = resolve_path(args.tickers_file)
    runs_root = resolve_path(args.news_runs_root)
    run_id = str(args.run_id or "").strip() or _latest_run_id(news_articles_db)
    if not run_id:
        print("No provider run found in news_articles DB.", file=sys.stderr)
        return 2
    out_dir = runs_root / run_id
    summary = write_run_reports(
        db_path=news_articles_db,
        run_id=run_id,
        out_dir=out_dir,
        ticker_universe_path=tickers_file,
        failures=None,
    )
    payload = {
        "run_id": run_id,
        "window_days_arg": int(args.window_days),
        "report_dir": str(out_dir),
        "summary": summary,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

