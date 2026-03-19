#!/usr/bin/env python3
"""
Unified news pipeline orchestrator.

Single entrypoint for the canonical news substrate: one news.sqlite, many ingest
sources, deterministic rebuild. See docs/architecture/15_news_substrate.md.

Flow:
  1. Optionally run API ingest (fetch_daily_news) -> news_articles.sqlite
  2. Optionally run newspaper4k collector -> JSONL
  3. Run chunk_builder (news_articles.sqlite -> news.sqlite)
  4. For each JSONL source: build_news_context_db (append to news.sqlite)
  5. Optionally run verification (counts, duplicate check)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_NEWS_SQLITE = REPO_ROOT / "reports" / "qual_context" / "news.sqlite"
DEFAULT_NEWS_ARTICLES_DB = REPO_ROOT / "reports" / "qual_context" / "news_articles.sqlite"
DEFAULT_NEWSPAPER4K_JSONL = REPO_ROOT / "integrations" / "newspaper4k_au" / "out" / "au_finance_news_no_sub_plus_capitalbrief_kalkine.jsonl"
DEFAULT_NEWSPAPER4K_CORPUS = "news_newspaper4k"


def _run(cmd: list[str], step_name: str) -> bool:
    print(f"[run_news_pipeline] >>> {step_name}", flush=True)
    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        print(f"[run_news_pipeline] <<< {step_name} FAILED (exit {result.returncode}) in {elapsed:.1f}s", file=sys.stderr, flush=True)
        return False
    print(f"[run_news_pipeline] <<< {step_name} ok in {elapsed:.1f}s", flush=True)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Unified news pipeline: API ingest + newspaper4k/RSS -> single news.sqlite",
    )
    ap.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Remove existing news.sqlite before building (idempotent full refresh)",
    )
    ap.add_argument(
        "--news-sqlite",
        default=str(DEFAULT_NEWS_SQLITE),
        help="Canonical news RAG DB path (default: reports/qual_context/news.sqlite)",
    )
    ap.add_argument(
        "--news-articles-db",
        default=str(DEFAULT_NEWS_ARTICLES_DB),
        help="Article staging DB for API ingest (default: reports/qual_context/news_articles.sqlite)",
    )
    ap.add_argument("--skip-api", action="store_true", help="Skip API ingest (eodhd/gdelt/worldmonitor)")
    ap.add_argument(
        "--providers",
        default="eodhd,gdelt",
        help="Comma-separated API providers when not --skip-api",
    )
    ap.add_argument("--since-hours", type=int, default=36, help="Lookback hours for API ingest")
    ap.add_argument(
        "--allow-missing-eodhd-captures",
        action="store_true",
        help="Pass through to fetch_daily_news: use live EODHD API when captures are missing",
    )
    ap.add_argument(
        "--auto-live-when-capture-missing",
        action="store_true",
        help=(
            "Pass through to fetch_daily_news: auto-enable live EODHD only when captures are missing "
            "and API key is present."
        ),
    )
    ap.add_argument(
        "--eodhd-symbols-only",
        action="store_true",
        help="Pass through to fetch_daily_news: skip EODHD global market feed, fetch only ASX symbol news (.AU)",
    )
    ap.add_argument(
        "--max-tickers",
        type=int,
        default=0,
        help="Cap ticker count for API ingest (0 = no cap). Use e.g. 30 for a quick small run.",
    )
    ap.add_argument(
        "--progress-every",
        type=int,
        default=500,
        help="Print progress every N rows in build_news_context_db (default 500; 0 = use script default)",
    )
    ap.add_argument(
        "--row-batch-size",
        type=int,
        default=128,
        help="Row batch size for build_news_context_db (default 128 for smaller batches)",
    )
    ap.add_argument(
        "--skip-chunk-builder",
        action="store_true",
        help="Skip building chunks from news_articles.sqlite (e.g. when only appending JSONL)",
    )
    ap.add_argument(
        "--newspaper4k-jsonl",
        default="",
        help="Path to newspaper4k JSONL to append (default: skip). Use 'default' for known path.",
    )
    ap.add_argument(
        "--newspaper4k-corpus",
        default=DEFAULT_NEWSPAPER4K_CORPUS,
        help="Corpus label for newspaper4k chunks",
    )
    ap.add_argument(
        "--run-newspaper4k",
        dest="run_newspaper4k",
        action="store_true",
        default=True,
        help="Run newspaper4k collector before appending (default: on; uses integration venv)",
    )
    ap.add_argument(
        "--skip-newspaper4k",
        dest="run_newspaper4k",
        action="store_false",
        help="Disable the default newspaper4k collector step.",
    )
    ap.add_argument(
        "--run-newspaper4k-backfill",
        action="store_true",
        help="Run newspaper4k collector with extended lookback for older articles (same corpus)",
    )
    ap.add_argument(
        "--newspaper4k-backfill-lookback-hours",
        type=int,
        default=720,
        help="Lookback hours for --run-newspaper4k-backfill (default: 720 = 30 days)",
    )
    ap.add_argument(
        "--newspaper4k-backfill-max-articles",
        type=int,
        default=800,
        help="Max total articles for newspaper4k backfill run (default: 800)",
    )
    ap.add_argument(
        "--newspaper4k-sources",
        default="",
        help="Sources file for --run-newspaper4k (default: sources_finance_no_sub_plus_capitalbrief_kalkine.txt)",
    )
    ap.add_argument(
        "--newspaper-first",
        action="store_true",
        help="Run newspaper4k (and backfill) before api_ingest so newspaper progress is visible first.",
    )
    ap.add_argument(
        "--newspaper4k-max-vol",
        action="store_true",
        help="Max volume: use expanded sources (12), higher per-source/total caps, more download retries.",
    )
    ap.add_argument(
        "--embed-backend",
        default="hash",
        help="Embedding backend for build_news_context_db (hash|sentence-transformers|ollama)",
    )
    ap.add_argument("--verify", action="store_true", help="Run verify_news_context_db.py after build")
    ap.add_argument(
        "--validate-jsonl",
        action="store_true",
        help="Validate newspaper4k (and other) JSONL against canonical schema before build",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print steps only, do not run")
    args = ap.parse_args(argv)

    news_sqlite = Path(args.news_sqlite).expanduser().resolve()
    news_articles_db = Path(args.news_articles_db).expanduser().resolve()

    print("[run_news_pipeline] --- start ---", flush=True)
    print(f"[run_news_pipeline] news_sqlite={news_sqlite} news_articles_db={news_articles_db}", flush=True)
    if not args.skip_api:
        print(f"[run_news_pipeline] api_ingest providers={args.providers} since_hours={args.since_hours} max_tickers={getattr(args, 'max_tickers', 0) or 'all'}", flush=True)
    print("[run_news_pipeline] ---", flush=True)

    steps: list[dict] = []
    ok = True
    newspaper4k_backfill_jsonl: str | None = None
    newspaper4k_main_jsonl: str | None = None

    if args.full_rebuild:
        if news_sqlite.exists():
            if args.dry_run:
                print(f"[dry-run] would remove {news_sqlite}")
            else:
                news_sqlite.unlink()
                print(f"[run_news_pipeline] removed {news_sqlite} (full-rebuild)")
            steps.append({"step": "full_rebuild", "removed": str(news_sqlite)})
        # Clear dedupe DB so JSONL re-ingest (e.g. newspaper4k) is not dropped as duplicate_url.
        # Use the same naming convention as build_news_context_db.dedupe_db_default_path:
        #   - out_path.with_suffix('.dedupe.sqlite') when out_path has a suffix
        #   - out_path / 'news_dedupe.sqlite' when out_path is a directory-like base path
        dedupe_db = news_sqlite.with_suffix(".dedupe.sqlite") if news_sqlite.suffix else news_sqlite / "news_dedupe.sqlite"
        if dedupe_db.exists() and not args.dry_run:
            dedupe_db.unlink()
            print(f"[run_news_pipeline] removed {dedupe_db} (full-rebuild)")
            steps.append({"step": "full_rebuild", "removed_dedupe": str(dedupe_db)})

    def _do_api_ingest() -> None:
        nonlocal ok
        if not args.skip_api:
            report_root = news_sqlite.parent / "news_runs"
            cmd = [
                sys.executable,
                str(SCRIPT_DIR / "fetch_daily_news.py"),
                "--news-articles-db", str(news_articles_db),
                "--news-runs-root", str(report_root),
                "--providers", args.providers,
                "--since-hours", str(args.since_hours),
            ]
            if getattr(args, "allow_missing_eodhd_captures", False):
                cmd.append("--allow-missing-eodhd-captures")
            if getattr(args, "auto_live_when_capture_missing", False):
                cmd.append("--auto-live-when-capture-missing")
            if getattr(args, "eodhd_symbols_only", False):
                cmd.append("--eodhd-symbols-only")
            if getattr(args, "max_tickers", 0) and int(args.max_tickers) > 0:
                cmd.extend(["--max-tickers", str(int(args.max_tickers))])
            if args.dry_run:
                print(f"[dry-run] would run: {' '.join(cmd)}")
            else:
                ok = _run(cmd, "api_ingest (fetch_daily_news)") and ok
            steps.append({
                "step": "api_ingest",
                "providers": args.providers,
                "report_dir": str(report_root),
            })
        else:
            steps.append({"step": "api_ingest", "skipped": True})

    def _do_newspaper_steps() -> None:
        nonlocal ok, newspaper4k_backfill_jsonl, newspaper4k_main_jsonl
        np4k_root = REPO_ROOT / "integrations" / "newspaper4k_au"
        venv_python = np4k_root / ".venv" / "bin" / "python"
        collector = np4k_root / "collect_au_finance_news.py"
        out_dir = np4k_root / "out"
        default_sources = str(np4k_root / "sources_finance_no_sub_plus_capitalbrief_kalkine.txt")
        expanded_sources = str(np4k_root / "sources_finance_no_sub_plus_capitalbrief_kalkine_benzinga_australian.txt")
        max_vol = getattr(args, "newspaper4k_max_vol", False)
        if args.newspaper4k_sources:
            sources = args.newspaper4k_sources
        elif max_vol:
            sources = expanded_sources
        else:
            sources = default_sources
        exempt = (
            "capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au,abc.net.au,theguardian.com,"
            "stockhead.com.au,livewiremarkets.com,marketindex.com.au,benzinga.com,theaustralian.com.au,"
            "skynews.com.au,yahoo.com"
        )
        cookie_file = np4k_root / "secrets" / "the_australian_cookie_header.txt"
        cookie_args = ["--http-cookie-file", str(cookie_file)] if cookie_file.exists() else []
        if args.run_newspaper4k:
            out_jsonl = out_dir / "au_finance_news_orchestrated.jsonl"
            manifest = out_dir / "au_finance_manifest_orchestrated.json"
            if not venv_python.exists() or not collector.exists():
                if args.dry_run:
                    print(
                        "[dry-run] newspaper4k integration missing; command shown for planned step only",
                        flush=True,
                    )
                    steps.append({"step": "newspaper4k_collect", "output": str(out_jsonl), "dry_run_missing_integration": True})
                    if not args.newspaper4k_jsonl:
                        newspaper4k_main_jsonl = str(out_jsonl)
                else:
                    print("[run_news_pipeline] newspaper4k integration not found; skip --run-newspaper4k or set up integrations/newspaper4k_au", file=sys.stderr)
                    ok = False
            else:
                np4k_per_source = "80" if max_vol else "40"
                np4k_total = "600" if max_vol else "300"
                cmd = [
                    str(venv_python),
                    str(collector),
                    "--sources-file", sources,
                    "--output-jsonl", str(out_jsonl),
                    "--manifest-json", str(manifest),
                    "--lookback-hours", "168",
                    "--max-articles-per-source", np4k_per_source,
                    "--max-total-articles", np4k_total,
                    "--finance-url-gate-exempt-domains", exempt,
                    "--article-url-gate-exempt-domains", exempt,
                ]
                cmd.extend(cookie_args)
                if max_vol:
                    cmd.extend(["--download-retries", "3"])
                if args.dry_run:
                    print(f"[dry-run] would run: {' '.join(cmd)}")
                else:
                    ok = _run(cmd, "newspaper4k_collect") and ok
                steps.append({"step": "newspaper4k_collect", "output": str(out_jsonl)})
                if ok and not args.newspaper4k_jsonl:
                    newspaper4k_main_jsonl = str(out_jsonl)
        if args.run_newspaper4k_backfill:
            backfill_jsonl = out_dir / "au_finance_news_backfill.jsonl"
            backfill_manifest = out_dir / "au_finance_manifest_backfill.json"
            if not venv_python.exists() or not collector.exists():
                if args.dry_run:
                    print(
                        "[dry-run] newspaper4k backfill integration missing; command shown for planned step only",
                        flush=True,
                    )
                    steps.append({"step": "newspaper4k_backfill", "output": str(backfill_jsonl), "dry_run_missing_integration": True})
                    newspaper4k_backfill_jsonl = str(backfill_jsonl)
                else:
                    print("[run_news_pipeline] newspaper4k integration not found; skip --run-newspaper4k-backfill or set up integrations/newspaper4k_au", file=sys.stderr)
                    ok = False
            else:
                max_per_source = "120" if max_vol else "100"
                backfill_max = str(args.newspaper4k_backfill_max_articles) if not max_vol else str(max(args.newspaper4k_backfill_max_articles, 4000))
                cmd = [
                    str(venv_python),
                    str(collector),
                    "--sources-file", sources,
                    "--output-jsonl", str(backfill_jsonl),
                    "--manifest-json", str(backfill_manifest),
                    "--lookback-hours", str(args.newspaper4k_backfill_lookback_hours),
                    "--max-articles-per-source", max_per_source,
                    "--max-total-articles", backfill_max,
                    "--finance-url-gate-exempt-domains", exempt,
                    "--article-url-gate-exempt-domains", exempt,
                ]
                cmd.extend(cookie_args)
                if max_vol:
                    cmd.extend(["--download-retries", "3"])
                if args.dry_run:
                    print(f"[dry-run] would run newspaper4k backfill: {' '.join(cmd)}")
                else:
                    ok = _run(cmd, "newspaper4k_backfill") and ok
                steps.append({
                    "step": "newspaper4k_backfill",
                    "output": str(backfill_jsonl),
                    "lookback_hours": args.newspaper4k_backfill_lookback_hours,
                })
                if ok and not args.dry_run and backfill_jsonl.exists():
                    newspaper4k_backfill_jsonl = str(backfill_jsonl)

    if getattr(args, "newspaper_first", False):
        _do_newspaper_steps()
        _do_api_ingest()
    else:
        _do_api_ingest()
        _do_newspaper_steps()

    if not args.skip_chunk_builder:
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "build_news_chunks.py"),
            "--from-db", str(news_articles_db),
            "--to-db", str(news_sqlite),
            "--embed-backend", args.embed_backend,
        ]
        if args.dry_run:
            print(f"[dry-run] would run: {' '.join(cmd)}")
        else:
            ok = _run(cmd, "build_news_chunks") and ok
        steps.append({"step": "chunk_builder", "to_db": str(news_sqlite)})
    else:
        steps.append({"step": "chunk_builder", "skipped": True})

    jsonl_sources: list[tuple[str, str]] = []
    if args.newspaper4k_jsonl:
        path = args.newspaper4k_jsonl
        if path == "default":
            path = str(DEFAULT_NEWSPAPER4K_JSONL)
        jsonl_sources.append((path, args.newspaper4k_corpus))
    elif newspaper4k_main_jsonl:
        jsonl_sources.append((newspaper4k_main_jsonl, args.newspaper4k_corpus))
    if newspaper4k_backfill_jsonl:
        jsonl_sources.append((newspaper4k_backfill_jsonl, args.newspaper4k_corpus))

    for jsonl_path, corpus in jsonl_sources:
        p = Path(jsonl_path).expanduser().resolve()
        if not p.exists():
            print(f"[run_news_pipeline] JSONL not found: {p}", file=sys.stderr)
            ok = False
            steps.append({
                "step": "build_news_context_db",
                "input": str(p),
                "corpus": corpus,
                "skipped": True,
                "reason": "jsonl_not_found",
            })
            continue
        if args.validate_jsonl and not args.dry_run:
            v_cmd = [
                sys.executable,
                str(SCRIPT_DIR / "validate_news_jsonl_schema.py"),
                str(p),
            ]
            if not _run(v_cmd, f"validate_news_jsonl_schema ({p.name})"):
                ok = False
                steps.append({
                    "step": "validate_news_jsonl_schema",
                    "input": str(p),
                    "ok": False,
                })
                continue
        # Build manifest path for this build so downstream tooling can inspect drop reasons.
        manifest_dir = news_sqlite.parent / "news_context_manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        manifest_path = manifest_dir / f"{corpus}_{ts}.json"

        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "build_news_context_db.py"),
            "--input-path", str(p),
            "--out", str(news_sqlite),
            "--corpus", corpus,
            "--embed-backend", args.embed_backend,
            "--research-only-ack",
            "--allow-warning",
            "--row-batch-size", str(max(1, getattr(args, "row_batch_size", 128))),
            "--manifest-json", str(manifest_path),
        ]
        # For the ASX-focused newspaper4k corpus, enable the default ASX ticker allowlist
        # so ticker inference is constrained to the ASX universe.
        if corpus == DEFAULT_NEWSPAPER4K_CORPUS:
            cmd.append("--use-default-asx-allowlist")
        pe = getattr(args, "progress_every", 500)
        if pe > 0:
            cmd.extend(["--progress-every", str(pe)])
        if args.dry_run:
            print(f"[dry-run] would run: {' '.join(cmd)}")
        else:
            ok = _run(cmd, f"build_news_context_db ({corpus})") and ok
        step_entry = {
            "step": "build_news_context_db",
            "input": str(p),
            "corpus": corpus,
            "manifest": str(manifest_path),
        }
        if not args.dry_run and manifest_path.exists():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                step_entry["manifest_summary"] = {
                    "kept_rows": manifest_data.get("stats", {}).get("kept_rows", 0),
                    "output_chunks": manifest_data.get("stats", {}).get("output_chunks", 0),
                    "unique_tickers": manifest_data.get("stats", {}).get("unique_tickers", 0),
                    "input_rows": manifest_data.get("stats", {}).get("input_rows", 0),
                }
            except Exception:
                pass
        steps.append(step_entry)

    if args.verify and not args.dry_run:
        verify_script = SCRIPT_DIR / "verify_news_context_db.py"
        if verify_script.exists():
            ok = _run(
                [sys.executable, str(verify_script), "--db", str(news_sqlite)],
                "verify_news_context_db",
            ) and ok
            steps.append({"step": "verify", "db": str(news_sqlite)})
        else:
            print("[run_news_pipeline] verify_news_context_db.py not found", file=sys.stderr)

    payload = {
        "orchestrator": "run_news_pipeline",
        "news_sqlite": str(news_sqlite),
        "steps": steps,
        "ok": ok,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
