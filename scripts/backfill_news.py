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
    provider_settings,
    resolve_path,
)
from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.ingest import run_provider_backfill  # noqa: E402
from news_pipeline.reporting import write_run_reports  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill canonical ASX news articles by provider and date range.")
    ap.add_argument("--provider", required=True, help="Provider name (eodhd|gdelt|worldmonitor)")
    ap.add_argument("--from", dest="from_day", required=True, help="Inclusive date YYYY-MM-DD")
    ap.add_argument("--to", dest="to_day", required=True, help="Inclusive date YYYY-MM-DD")
    ap.add_argument("--lane", default="high_recall", choices=["high_precision", "high_recall"], help="Article lane label")
    ap.add_argument("--run-id", default="", help="Optional run_id for resumable continuation")
    ap.add_argument("--no-resume", action="store_true", help="Do not skip windows already completed in this run_id")
    ap.add_argument("--max-days", type=int, default=0, help="Cap number of days to process (0 = no cap). Use to avoid long runs, e.g. --max-days 7")
    ap.add_argument("--max-tickers", type=int, default=0, help="Optional cap for ticker universe while testing")
    ap.add_argument(
        "--asx-wide",
        action="store_true",
        help="Fetch provider-wide ASX news without ticker-expanded provider queries.",
    )
    ap.add_argument("--tickers", default="", help="Optional comma/space-separated ticker list (overrides --tickers-file)")
    ap.add_argument("--news-runs-root", default=str(DEFAULT_NEWS_RUNS_DIR), help="Output root for per-run reports")
    ap.add_argument("--eodhd-api-key", default="", help="EODHD API key (overrides EODHD_API_KEY env)")
    ap.add_argument("--sweep-stale-runs-hours", type=int, default=2, help="Mark stale provider_runs stuck in 'running' older than N hours")
    ap.add_argument("--no-sweep-stale-runs", action="store_true", help="Disable stale provider_runs auto-heal step")
    ap.add_argument("--dry-run", action="store_true", help="Print resolved run plan and exit without writes")
    add_common_provider_args(ap)
    add_common_gdelt_args(ap)
    args = ap.parse_args(argv)

    news_articles_db = resolve_path(args.news_articles_db)
    tickers_file = resolve_path(args.tickers_file)
    identity_map_path = resolve_path(args.identity_map_path)
    eodhd_capture_dir = resolve_path(args.eodhd_capture_dir)
    worldmonitor_capture_path = resolve_path(args.worldmonitor_capture_path)
    worldmonitor_theater_map_path = resolve_path(args.worldmonitor_theater_map_path)
    runs_root = resolve_path(args.news_runs_root)
    gdelt_kwargs = gdelt_kwargs_from_args(args)

    eodhd_key = str(args.eodhd_api_key or "").strip() or str(os.getenv("EODHD_API_KEY") or "").strip()
    provider = build_provider(
        provider_name=args.provider,
        eodhd_api_key=eodhd_key,
        eodhd_capture_dir=eodhd_capture_dir,
        allow_missing_eodhd_captures=bool(args.allow_missing_eodhd_captures),
        auto_live_when_capture_missing=bool(getattr(args, "auto_live_when_capture_missing", False)),
        worldmonitor_api_cache_url=str(args.worldmonitor_api_cache_url or ""),
        worldmonitor_capture_path=worldmonitor_capture_path,
        worldmonitor_theater_map_path=worldmonitor_theater_map_path,
        gdelt_kwargs=gdelt_kwargs,
    )
    cfg = provider_settings(provider)
    capture_policy = cfg.get("capture_policy") if isinstance(cfg, dict) else None
    if isinstance(capture_policy, dict) and str(capture_policy.get("mode") or "") == "auto_live_missing_capture":
        print(
            "[backfill_news] eodhd capture contract missing; auto-enabling live API fetch "
            "because an EODHD API key is available.",
            file=sys.stderr,
        )
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
    if bool(args.dry_run):
        payload = {
            "dry_run": True,
            "mode": "backfill",
            "provider": str(args.provider),
            "from_day": str(args.from_day),
            "to_day": str(args.to_day),
            "lane": str(args.lane),
            "run_id": str(args.run_id or ""),
            "resume": not bool(args.no_resume),
            "max_days": int(args.max_days or 0),
            "news_articles_db": str(news_articles_db),
            "news_runs_root": str(runs_root),
            "asx_wide": asx_wide,
            "tickers_count": len(tickers),
            "tickers_sample": tickers[:20],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

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
            if not bool(args.no_sweep_stale_runs):
                stale_swept = store.finalize_stale_running_runs(
                    older_than_hours=int(max(1, args.sweep_stale_runs_hours)),
                    to_status="failed",
                )
                if stale_swept > 0:
                    print(
                        f"[backfill_news] marked {stale_swept} stale provider_runs as failed",
                        file=sys.stderr,
                    )
            linker = EntityLinker(ticker_universe_path=linker_ticker_path, identity_map_path=identity_map_path)
            run_id, failures = run_provider_backfill(
                store=store,
                linker=linker,
                provider=provider,
                lane=args.lane,
                tickers=tickers,
                from_day=args.from_day,
                to_day=args.to_day,
                resume=not bool(args.no_resume),
                run_id=str(args.run_id or ""),
                max_days=int(args.max_days) if args.max_days and args.max_days > 0 else None,
            )
        finally:
            store.close()

        run_out_dir = runs_root / run_id
        report_summary = write_run_reports(
            db_path=news_articles_db,
            run_id=run_id,
            out_dir=run_out_dir,
            ticker_universe_path=linker_ticker_path,
            failures=failures,
        )
        payload = {
            "run_id": run_id,
            "provider": provider.name,
            "mode": "backfill",
            "news_articles_db": str(news_articles_db),
            "report_dir": str(run_out_dir),
            "report_summary": report_summary,
            "provider_settings": cfg,
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
