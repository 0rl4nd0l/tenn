#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_NEWS_RUNS_DIR,
    add_common_gdelt_args,
    add_common_provider_args,
    build_provider,
    gdelt_kwargs_from_args,
    load_tickers,
    parse_ticker_list,
    parse_provider_list,
    resolve_path,
)
from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.ingest import run_provider_daily  # noqa: E402
from news_pipeline.reporting import write_run_reports  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch daily ASX news from one or more providers.")
    ap.add_argument(
        "--providers",
        default="eodhd,gdelt",
        help="Comma-separated provider list (eodhd,gdelt,worldmonitor)",
    )
    ap.add_argument("--since-hours", type=int, default=36, help="Lookback window in hours")
    ap.add_argument("--lane", default="high_precision", choices=["high_precision", "high_recall"], help="Article lane label")
    ap.add_argument("--max-tickers", type=int, default=0, help="Optional cap for ticker universe while testing")
    ap.add_argument(
        "--asx-wide",
        action="store_true",
        help="Fetch provider-wide ASX news without ticker-expanded provider queries.",
    )
    ap.add_argument("--tickers", default="", help="Optional comma/space-separated ticker list (overrides --tickers-file)")
    ap.add_argument("--news-runs-root", default=str(DEFAULT_NEWS_RUNS_DIR), help="Output root for per-run reports")
    ap.add_argument("--eodhd-api-key", default="", help="EODHD API key (overrides EODHD_API_KEY env)")
    add_common_provider_args(ap)
    add_common_gdelt_args(ap)
    args = ap.parse_args(argv)

    providers = parse_provider_list(args.providers)
    if not providers:
        print("No providers were specified.", file=sys.stderr)
        return 2

    news_articles_db = resolve_path(args.news_articles_db)
    tickers_file = resolve_path(args.tickers_file)
    identity_map_path = resolve_path(args.identity_map_path)
    eodhd_capture_dir = resolve_path(args.eodhd_capture_dir)
    worldmonitor_capture_path = resolve_path(args.worldmonitor_capture_path)
    runs_root = resolve_path(args.news_runs_root)
    eodhd_key = str(args.eodhd_api_key or "").strip() or str(os.getenv("EODHD_API_KEY") or "").strip()
    gdelt_kwargs = gdelt_kwargs_from_args(args)

    explicit_tickers = parse_ticker_list(args.tickers)
    asx_wide = bool(args.asx_wide)
    if asx_wide:
        tickers = []
    elif explicit_tickers:
        tickers = explicit_tickers
    else:
        tickers = load_tickers(tickers_file, limit=int(args.max_tickers or 0))
    if not tickers and not asx_wide:
        print("No tickers resolved for ingest.", file=sys.stderr)
        return 2

    linker_ticker_path = tickers_file
    temp_ticker_file: Path | None = None
    if explicit_tickers and not asx_wide:
        merged = sorted(set(load_tickers(tickers_file, limit=0)) | set(explicit_tickers))
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="news_pipeline_tickers_", suffix=".txt") as tf:
            for ticker in merged:
                tf.write(f"{ticker}\n")
            temp_ticker_file = Path(tf.name)
        linker_ticker_path = temp_ticker_file

    try:
        store = NewsArticleStore(news_articles_db)
        try:
            linker = EntityLinker(ticker_universe_path=linker_ticker_path, identity_map_path=identity_map_path)
            runs = []
            for provider_name in providers:
                provider = build_provider(
                    provider_name=provider_name,
                    eodhd_api_key=eodhd_key,
                    eodhd_capture_dir=eodhd_capture_dir,
                    allow_missing_eodhd_captures=bool(args.allow_missing_eodhd_captures),
                    worldmonitor_api_cache_url=str(args.worldmonitor_api_cache_url or ""),
                    worldmonitor_capture_path=worldmonitor_capture_path,
                    gdelt_kwargs=gdelt_kwargs,
                )
                run_id, failures = run_provider_daily(
                    store=store,
                    linker=linker,
                    provider=provider,
                    lane=args.lane,
                    tickers=tickers,
                    since_hours=int(args.since_hours),
                    run_id="",
                )
                run_dir = runs_root / run_id
                report_summary = write_run_reports(
                    db_path=news_articles_db,
                    run_id=run_id,
                    out_dir=run_dir,
                    ticker_universe_path=linker_ticker_path,
                    failures=failures,
                )
                runs.append(
                    {
                        "provider": provider_name,
                        "run_id": run_id,
                        "report_dir": str(run_dir),
                        "report_summary": report_summary,
                    }
                )
        finally:
            store.close()

        payload = {
            "mode": "daily",
            "news_articles_db": str(news_articles_db),
            "providers": providers,
            "runs": runs,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        if temp_ticker_file is not None:
            try:
                temp_ticker_file.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
