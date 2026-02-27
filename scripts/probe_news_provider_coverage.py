#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_TICKER_UNIVERSE,
    add_common_gdelt_args,
    build_provider,
    gdelt_kwargs_from_args,
    parse_provider_list,
    resolve_path,
)
from news_pipeline.utils import load_ticker_universe  # noqa: E402

DEFAULT_TICKERS = ["BHP", "CBA", "CSL", "WBC", "NAB", "MQG", "WES", "WOW", "FMG", "RIO"]


def _normalize_ticker(value: str) -> str:
    txt = str(value or "").strip().upper()
    if not txt:
        return ""
    txt = txt.replace("ASX:", "").replace("ASX-", "")
    if "." in txt:
        txt = txt.split(".", 1)[0]
    txt = "".join(ch for ch in txt if ch.isalnum())
    return txt


def _parse_ticker_list(raw: str) -> List[str]:
    out = []
    for part in re.split(r"[,\s;]+", str(raw or "")):
        tok = _normalize_ticker(part)
        if tok and tok not in out:
            out.append(tok)
    return out


def _window_bounds(days: int) -> tuple[str, str]:
    now = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    start = now - dt.timedelta(days=int(max(1, days)))
    return start.isoformat().replace("+00:00", "Z"), now.isoformat().replace("+00:00", "Z")


def _row_mentions_ticker(row: Dict[str, Any], ticker: str) -> bool:
    symbol = _normalize_ticker(ticker)
    if not symbol:
        return False
    text_fields = [
        str(row.get("title") or ""),
        str(row.get("headline") or ""),
        str(row.get("snippet") or ""),
        str(row.get("description") or ""),
        str(row.get("url") or ""),
        str(row.get("link") or ""),
    ]
    haystack = "\n".join(text_fields)
    strong_patterns = [
        rf"\bASX\s*[:\-]\s*{re.escape(symbol)}\b",
        rf"(?<![A-Za-z0-9]){re.escape(symbol)}\.AX(?![A-Za-z0-9])",
    ]
    for pattern in strong_patterns:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            return True
    plain_token_pattern = rf"(?<![A-Za-z0-9]){re.escape(symbol)}(?![A-Za-z0-9])"
    if len(symbol) <= 3:
        # Short symbols collide across exchanges (e.g., WES on NYSE). Keep them unless foreign-exchange cues appear.
        if not re.search(plain_token_pattern, haystack, flags=re.IGNORECASE):
            return False
        foreign_exchange_conflict_patterns = [
            rf"\b(?:NYSE|NASDAQ|AMEX|TSX|LSE|HKEX|OTC|NMS)\s*[:\-]\s*{re.escape(symbol)}\b",
            rf"(?<![A-Za-z0-9]){re.escape(symbol)}\.(?:US|L|TO|HK)(?![A-Za-z0-9])",
        ]
        for conflict in foreign_exchange_conflict_patterns:
            if re.search(conflict, haystack, flags=re.IGNORECASE):
                return False
        return True
    if re.search(plain_token_pattern, haystack, flags=re.IGNORECASE):
        return True
    return False


def _probe_provider(
    *,
    provider_name: str,
    provider_obj: Any,
    tickers: List[str],
    window_start_utc: str,
    window_end_utc: str,
    asx_wide: bool = False,
) -> Dict[str, Any]:
    provider_summary: Dict[str, Any] = {"provider": provider_name, "tickers": {}, "window_start_utc": window_start_utc, "window_end_utc": window_end_utc}
    if asx_wide:
        try:
            rows = provider_obj.fetch_window(
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                tickers=[],
            )
        except Exception as exc:
            provider_summary["asx_wide"] = {"articles_returned": 0, "error": str(exc)}
            return provider_summary

        parsed = []
        sources = set()
        samples = []
        for row in rows:
            try:
                result = provider_obj.parse_item(row, fetched_at_utc=window_end_utc)
            except Exception as exc:
                if len(samples) < 5:
                    samples.append({"title": "", "url": "", "error": str(exc)})
                continue
            if result.candidate is not None:
                parsed.append(result.candidate)
                if result.candidate.source_name:
                    sources.add(result.candidate.source_name)
                if len(samples) < 5:
                    samples.append({"title": result.candidate.title, "url": result.candidate.canonical_url})
            elif len(samples) < 5:
                samples.append({"title": str(row.get("title") or row.get("headline") or ""), "url": str(row.get("url") or row.get("link") or "")})

        valid_pub = len(parsed)
        total = len(rows)
        provider_summary["provider_articles_fetched_total"] = int(total)
        provider_summary["asx_wide"] = {
            "articles_returned": total,
            "valid_published_at": valid_pub,
            "pct_valid_published_at": round((100.0 * valid_pub / total), 4) if total > 0 else 0.0,
            "unique_sources": sorted(sources),
            "sample_titles_urls": samples,
        }
        return provider_summary

    if provider_name == "gdelt":
        try:
            rows = provider_obj.fetch_window(
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                tickers=tickers,
            )
        except Exception as exc:
            for ticker in tickers:
                provider_summary["tickers"][ticker] = {"error": str(exc), "articles_returned": 0}
            return provider_summary
        provider_summary["provider_articles_fetched_total"] = int(len(rows))

        matched_any = 0
        for ticker in tickers:
            ticker_rows = [row for row in rows if _row_mentions_ticker(row, ticker)]
            if ticker_rows:
                matched_any += len(ticker_rows)
            parsed = []
            sources = set()
            samples = []
            for row in ticker_rows:
                try:
                    result = provider_obj.parse_item(row, fetched_at_utc=window_end_utc)
                except Exception as exc:
                    if len(samples) < 3:
                        samples.append({"title": "", "url": "", "error": str(exc)})
                    continue
                if result.candidate is not None:
                    parsed.append(result.candidate)
                    if result.candidate.source_name:
                        sources.add(result.candidate.source_name)
                    if len(samples) < 3:
                        samples.append({"title": result.candidate.title, "url": result.candidate.canonical_url})
                elif len(samples) < 3:
                    samples.append({"title": str(row.get("title") or row.get("headline") or ""), "url": str(row.get("url") or row.get("link") or "")})

            valid_pub = len(parsed)
            total = len(ticker_rows)
            provider_summary["tickers"][ticker] = {
                "articles_returned": total,
                "valid_published_at": valid_pub,
                "pct_valid_published_at": round((100.0 * valid_pub / total), 4) if total > 0 else 0.0,
                "unique_sources": sorted(sources),
                "sample_titles_urls": samples,
            }
        provider_summary["provider_articles_matched_total"] = int(matched_any)
        if rows and matched_any <= 0:
            provider_summary["unmatched_sample_titles"] = [
                str((row.get("title") or row.get("headline") or "")).strip()
                for row in rows[:5]
            ]
        return provider_summary

    for ticker in tickers:
        try:
            if provider_name == "eodhd" and hasattr(provider_obj, "fetch_symbol_window"):
                rows = provider_obj.fetch_symbol_window(
                    ticker=ticker,
                    window_start_utc=window_start_utc,
                    window_end_utc=window_end_utc,
                )
            else:
                rows = provider_obj.fetch_window(
                    window_start_utc=window_start_utc,
                    window_end_utc=window_end_utc,
                    tickers=[ticker],
                )
        except Exception as exc:
            provider_summary["tickers"][ticker] = {"error": str(exc), "articles_returned": 0}
            continue

        parsed = []
        sources = set()
        samples = []
        for row in rows:
            try:
                result = provider_obj.parse_item(row, fetched_at_utc=window_end_utc)
            except Exception as exc:
                if len(samples) < 3:
                    samples.append({"title": "", "url": "", "error": str(exc)})
                continue
            if result.candidate is not None:
                parsed.append(result.candidate)
                if result.candidate.source_name:
                    sources.add(result.candidate.source_name)
                if len(samples) < 3:
                    samples.append({"title": result.candidate.title, "url": result.candidate.canonical_url})
            elif len(samples) < 3:
                samples.append({"title": str(row.get("title") or row.get("headline") or ""), "url": str(row.get("url") or row.get("link") or "")})

        valid_pub = len(parsed)
        total = len(rows)
        provider_summary["tickers"][ticker] = {
            "articles_returned": total,
            "valid_published_at": valid_pub,
            "pct_valid_published_at": round((100.0 * valid_pub / total), 4) if total > 0 else 0.0,
            "unique_sources": sorted(sources),
            "sample_titles_urls": samples,
        }
    return provider_summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Probe ASX provider coverage for a fixed ticker set and date window.")
    ap.add_argument("--provider", default="eodhd", help="Primary provider to probe")
    ap.add_argument("--also-provider", default="", help="Optional second provider, e.g. gdelt")
    ap.add_argument("--window-days", type=int, default=30, help="Lookback window size in days")
    ap.add_argument(
        "--asx-wide",
        action="store_true",
        help="Probe provider-wide ASX query yield (no per-ticker matching).",
    )
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS), help="Comma-separated tickers to probe")
    ap.add_argument("--tickers-file", default=str(DEFAULT_TICKER_UNIVERSE), help="Ticker universe path (validation only)")
    ap.add_argument("--eodhd-capture-dir", default="reports/provider_captures/eodhd", help="EODHD capture contract path")
    ap.add_argument("--allow-missing-eodhd-captures", action="store_true", help="Allow live EODHD probe without local captures")
    ap.add_argument("--eodhd-api-key", default="", help="EODHD API key (overrides EODHD_API_KEY env)")
    add_common_gdelt_args(ap)
    args = ap.parse_args(argv)

    tickers_file = resolve_path(args.tickers_file)
    ticker_universe = set(load_ticker_universe(tickers_file))
    if bool(args.asx_wide):
        requested_tickers = []
        unknown_tickers = []
        tickers: List[str] = []
    else:
        requested_tickers = _parse_ticker_list(args.tickers) or list(DEFAULT_TICKERS)
        if not requested_tickers:
            print("No valid tickers to probe.", file=sys.stderr)
            return 2
        unknown_tickers = [ticker for ticker in requested_tickers if ticker_universe and ticker not in ticker_universe]
        tickers = list(requested_tickers)

    providers = [str(args.provider or "").strip().lower()]
    if str(args.also_provider or "").strip():
        for item in parse_provider_list(args.also_provider):
            if item not in providers:
                providers.append(item)

    eodhd_key = str(args.eodhd_api_key or "").strip() or str(os.getenv("EODHD_API_KEY") or "").strip()
    gdelt_kwargs = gdelt_kwargs_from_args(args)
    eodhd_capture_dir = resolve_path(args.eodhd_capture_dir)
    window_start_utc, window_end_utc = _window_bounds(args.window_days)

    summaries = []
    for provider_name in providers:
        provider = build_provider(
            provider_name=provider_name,
            eodhd_api_key=eodhd_key,
            eodhd_capture_dir=eodhd_capture_dir,
            allow_missing_eodhd_captures=bool(args.allow_missing_eodhd_captures),
            gdelt_kwargs=gdelt_kwargs,
        )
        summaries.append(
            _probe_provider(
                provider_name=provider_name,
                provider_obj=provider,
                tickers=tickers,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                asx_wide=bool(args.asx_wide),
            )
        )

    payload = {
        "generated_at_utc": window_end_utc,
        "window_days": int(args.window_days),
        "asx_wide": bool(args.asx_wide),
        "tickers": tickers,
        "unknown_tickers_not_in_universe": unknown_tickers,
        "providers": summaries,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
