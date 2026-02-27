#!/usr/bin/env python3
"""
Run identity-aware ASX coverage evaluation for baseline and RSS corpora.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS_DB = REPO_ROOT / "reports" / "qual_context" / "news.sqlite"
DEFAULT_ASX_TICKERS = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_IDENTITY_MAP = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "analysis" / "asx_headline_coverage_eval.json"


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_path(value: str) -> Path:
    path = Path(str(value or "").strip()).expanduser()
    if path.is_absolute():
        return path.resolve()
    cwd = (Path.cwd() / path).resolve()
    if cwd.exists():
        return cwd
    return (REPO_ROOT / path).resolve()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _load_quant_module():
    module_path = (REPO_ROOT / "scripts" / "quantify_asx_news_identity_coverage.py").resolve()
    spec = importlib.util.spec_from_file_location("quantify_asx_news_identity_coverage_eval", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _build_metrics(payload: dict[str, Any], corpus: str) -> dict[str, Any]:
    summary = payload.get("asx_identity_summary")
    summary = summary if isinstance(summary, dict) else {}
    pct = _safe_float(summary.get("pct_chunks_strong_or_medium"))
    zero_hits = payload.get("tickers_with_zero_strong_hits")
    zero_count = len(zero_hits) if isinstance(zero_hits, list) else 0
    return {
        "corpus": corpus,
        "pct_chunks_strong_or_medium": round(pct, 4),
        "tickers_zero_hits": int(zero_count),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run identity-aware ASX headline coverage eval for baseline and RSS corpora.")
    ap.add_argument("--news-db-path", default=str(DEFAULT_NEWS_DB), help="Path to news SQLite DB")
    ap.add_argument("--asx-tickers-file", default=str(DEFAULT_ASX_TICKERS), help="ASX ticker universe path")
    ap.add_argument("--identity-map-path", default=str(DEFAULT_IDENTITY_MAP), help="Ticker identity map path")
    ap.add_argument("--baseline-corpus", default="news", help="Baseline corpus label")
    ap.add_argument("--rss-corpus", default="news_asx_rss", help="RSS corpus label")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output summary JSON path")
    args = ap.parse_args(argv)

    news_db_path = _resolve_path(args.news_db_path)
    asx_tickers_file = _resolve_path(args.asx_tickers_file)
    identity_map_path = _resolve_path(args.identity_map_path)
    out_json = _resolve_path(args.out_json)

    try:
        mod = _load_quant_module()
        baseline_payload = mod.quantify_asx_news_identity_coverage(
            news_db_path=news_db_path,
            corpus=str(args.baseline_corpus or "").strip(),
            asx_tickers_file=asx_tickers_file,
            identity_map_path=identity_map_path,
        )
        rss_payload = mod.quantify_asx_news_identity_coverage(
            news_db_path=news_db_path,
            corpus=str(args.rss_corpus or "").strip(),
            asx_tickers_file=asx_tickers_file,
            identity_map_path=identity_map_path,
        )
    except Exception as exc:
        print(f"Coverage evaluation failed: {exc}", file=sys.stderr)
        return 1

    baseline_metrics = _build_metrics(baseline_payload, corpus=str(args.baseline_corpus or "").strip())
    rss_metrics = _build_metrics(rss_payload, corpus=str(args.rss_corpus or "").strip())
    delta = round(
        float(rss_metrics["pct_chunks_strong_or_medium"]) - float(baseline_metrics["pct_chunks_strong_or_medium"]),
        4,
    )

    summary = {
        "generated_at_utc": _iso_utc_now(),
        "baseline": baseline_metrics,
        "rss": rss_metrics,
        "delta_pct_points": delta,
    }
    _atomic_write_json(out_json, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
