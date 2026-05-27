#!/usr/bin/env python3
"""
Main news pipeline orchestrator.

Runs provider fetches (optionally with incremental fetch windows), optionally
calls fetch_gdelt_doc_api.py, and triggers chunk build.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_NEWS_ARTICLES_DB,
    DEFAULT_NEWS_CONTEXT_DB,
    DEFAULT_NEWS_RUNS_DIR,
    add_common_gdelt_args,
    add_common_provider_args,
    build_provider,
    describe_news_artifact_paths,
    gdelt_kwargs_from_args,
    load_tickers,
    parse_provider_list,
    parse_ticker_list,
    resolve_path,
)
from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.ingest import run_provider_daily  # noqa: E402
from news_pipeline.reporting import write_run_reports  # noqa: E402

log = logging.getLogger(__name__)


def _max_window_end_utc(db_path: Path, provider: str) -> Optional[str]:
    """Return MAX(window_end_utc) for a provider from provider_run_windows, or None."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT MAX(window_end_utc) FROM provider_run_windows WHERE provider = ?",
                (provider,),
            ).fetchone()
            if row and row[0]:
                return str(row[0])
        finally:
            conn.close()
    except Exception:
        return None
    return None


def _build_rss_provider(feeds_file: Path):
    """Instantiate RssProvider; imported lazily to avoid hard dep at module level."""
    from news_pipeline.providers.rss import RssProvider

    return RssProvider(feeds_file=feeds_file)


def _run_gdelt_doc_api(out_jsonl: Path) -> bool:
    """Call fetch_gdelt_doc_api main() as an in-process step. Returns True on success."""
    try:
        import fetch_gdelt_doc_api as gdelt_doc

        argv = [
            "--query",
            '("ASX" OR "Australian Securities Exchange" OR "ASX listed")',
            "--out",
            str(out_jsonl),
            "--timespan",
            "24h",
            "--skip-article-fetch",
        ]
        # fetch_gdelt_doc_api.main() uses sys.argv; call directly with argv override.
        import sys as _sys

        old_argv = _sys.argv
        _sys.argv = ["fetch_gdelt_doc_api"] + argv
        try:
            exit_code = gdelt_doc.main()
        finally:
            _sys.argv = old_argv
        return exit_code == 0
    except Exception as exc:
        log.warning("fetch_gdelt_doc_api failed: %s", exc)
        return False


def _merge_gdelt_doc_jsonl(
    jsonl_path: Path, store: NewsArticleStore, linker: EntityLinker
) -> int:
    """Merge JSONL rows from fetch_gdelt_doc_api into the article store. Returns inserted count."""
    if not jsonl_path.exists():
        return 0
    from news_pipeline.providers.gdelt import GdeltProvider
    from news_pipeline.utils import now_utc_iso

    provider = GdeltProvider()
    fetched_at = now_utc_iso()
    inserted = 0
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            try:
                result = provider.parse_item(item, fetched_at_utc=fetched_at)
            except Exception:
                continue
            if result.candidate is None:
                continue
            try:
                upsert = store.upsert_article(result.candidate, lane="high_recall")
                store.insert_article_version(upsert.article_id, result.candidate)
                links = linker.link_article(
                    article_id=upsert.article_id,
                    title=result.candidate.title,
                    description=result.candidate.description,
                    body=result.candidate.body,
                    published_at_utc=result.candidate.published_at_utc,
                )
                store.replace_entity_links(upsert.article_id, links)
                if upsert.inserted:
                    inserted += 1
            except Exception:
                continue
    return inserted


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the full news ingestion pipeline.")
    ap.add_argument(
        "--providers",
        default="newspaper4k",
        help="Comma-separated provider list (newspaper4k,rss,eodhd,gdelt,worldmonitor)",
    )
    ap.add_argument(
        "--since-hours",
        type=int,
        default=36,
        help="Lookback window in hours (default mode)",
    )
    ap.add_argument(
        "--lane", default="high_precision", choices=["high_precision", "high_recall"]
    )
    ap.add_argument("--max-tickers", type=int, default=0)
    ap.add_argument("--asx-wide", action="store_true")
    ap.add_argument("--tickers", default="")
    ap.add_argument("--news-runs-root", default=str(DEFAULT_NEWS_RUNS_DIR))
    ap.add_argument("--eodhd-api-key", default="")
    ap.add_argument(
        "--incremental-fetch",
        action="store_true",
        help=(
            "For each provider use MAX(window_end_utc) from provider_run_windows as "
            "fetch start time, falling back to now-36h if no prior window exists."
        ),
    )
    ap.add_argument(
        "--skip-gdelt-doc-api",
        action="store_true",
        help="Skip the optional fetch_gdelt_doc_api step.",
    )
    ap.add_argument(
        "--rss-feeds-file",
        default=str(
            Path(__file__).resolve().parents[1]
            / "integrations"
            / "newspaper4k_au"
            / "sources_au_finance_rss_only.txt"
        ),
        help="Path to RSS feed list for the rss provider.",
    )
    add_common_provider_args(ap)
    add_common_gdelt_args(ap)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    providers = parse_provider_list(args.providers)
    if not providers:
        log.error("No providers specified.")
        return 2

    news_articles_db = resolve_path(args.news_articles_db)
    tickers_file = resolve_path(args.tickers_file)
    identity_map_path = resolve_path(args.identity_map_path)
    eodhd_capture_dir = resolve_path(args.eodhd_capture_dir)
    worldmonitor_capture_path = resolve_path(args.worldmonitor_capture_path)
    runs_root = resolve_path(args.news_runs_root)
    eodhd_key = (
        str(args.eodhd_api_key or "").strip()
        or str(os.getenv("EODHD_API_KEY") or "").strip()
    )
    gdelt_kwargs = gdelt_kwargs_from_args(args)

    explicit_tickers = parse_ticker_list(args.tickers)
    if bool(args.asx_wide):
        tickers: List[str] = []
    elif explicit_tickers:
        tickers = explicit_tickers
    else:
        tickers = load_tickers(tickers_file, limit=int(args.max_tickers or 0))

    if not tickers and not bool(args.asx_wide):
        log.error("No tickers resolved for ingest.")
        return 2

    linker_ticker_path = tickers_file
    temp_ticker_file: Path | None = None
    if explicit_tickers and not bool(args.asx_wide):
        merged = sorted(
            set(load_tickers(tickers_file, limit=0)) | set(explicit_tickers)
        )
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            prefix="run_news_pipeline_tickers_",
            suffix=".txt",
        ) as tf:
            for ticker in merged:
                tf.write(f"{ticker}\n")
            temp_ticker_file = Path(tf.name)
        linker_ticker_path = temp_ticker_file

    runs = []
    try:
        store = NewsArticleStore(news_articles_db)
        try:
            linker = EntityLinker(
                ticker_universe_path=linker_ticker_path,
                identity_map_path=identity_map_path,
            )

            for provider_name in providers:
                # Determine fetch window for incremental mode.
                since_hours_effective = int(args.since_hours)
                if bool(args.incremental_fetch):
                    last_end = _max_window_end_utc(news_articles_db, provider_name)
                    if last_end:
                        try:
                            last_dt = dt.datetime.fromisoformat(
                                last_end.replace("Z", "+00:00")
                            ).astimezone(dt.timezone.utc)
                            now_dt = dt.datetime.now(tz=dt.timezone.utc)
                            delta_hours = (now_dt - last_dt).total_seconds() / 3600.0
                            since_hours_effective = max(1, int(delta_hours) + 1)
                        except Exception:
                            since_hours_effective = 36
                    else:
                        since_hours_effective = 36

                if provider_name == "rss":
                    try:
                        provider = _build_rss_provider(Path(args.rss_feeds_file))
                    except Exception as exc:
                        log.warning("Could not build rss provider: %s", exc)
                        continue
                else:
                    try:
                        provider = build_provider(
                            provider_name=provider_name,
                            eodhd_api_key=eodhd_key,
                            eodhd_capture_dir=eodhd_capture_dir,
                            allow_missing_eodhd_captures=bool(
                                args.allow_missing_eodhd_captures
                            ),
                            worldmonitor_api_cache_url=str(
                                args.worldmonitor_api_cache_url or ""
                            ),
                            worldmonitor_capture_path=worldmonitor_capture_path,
                            gdelt_kwargs=gdelt_kwargs,
                        )
                    except Exception as exc:
                        log.warning(
                            "Could not build provider %s: %s", provider_name, exc
                        )
                        continue

                run_id, failures = run_provider_daily(
                    store=store,
                    linker=linker,
                    provider=provider,
                    lane=args.lane,
                    tickers=tickers,
                    since_hours=since_hours_effective,
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

            # Optional GDELT DOC API step.
            if not bool(args.skip_gdelt_doc_api):
                gdelt_doc_jsonl = runs_root / "gdelt_doc_api_latest.jsonl"
                success = _run_gdelt_doc_api(gdelt_doc_jsonl)
                if success:
                    merged_count = _merge_gdelt_doc_jsonl(
                        gdelt_doc_jsonl, store, linker
                    )
                    log.info("gdelt_doc_api merged %d articles", merged_count)
                else:
                    log.warning(
                        "gdelt_doc_api step failed or produced no output; continuing."
                    )

        finally:
            store.close()
    finally:
        if temp_ticker_file is not None:
            try:
                temp_ticker_file.unlink(missing_ok=True)
            except Exception:
                pass

    payload = {
        "mode": "daily",
        "incremental_fetch": bool(args.incremental_fetch),
        "skip_gdelt_doc_api": bool(args.skip_gdelt_doc_api),
        "paths": describe_news_artifact_paths(
            news_articles_db=news_articles_db,
            news_context_db=resolve_path(str(DEFAULT_NEWS_CONTEXT_DB)),
            news_runs_root=runs_root,
        ),
        "news_articles_db": str(news_articles_db),
        "providers": providers,
        "runs": runs,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
