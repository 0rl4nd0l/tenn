from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .providers import EodhdProvider, GdeltProvider, ProviderClient, WorldMonitorProvider
from .utils import load_ticker_universe

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TICKER_UNIVERSE = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_IDENTITY_MAP = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"
DEFAULT_NEWS_ARTICLES_DB = REPO_ROOT / "reports" / "qual_context" / "news_articles.sqlite"
DEFAULT_NEWS_CONTEXT_DB = REPO_ROOT / "reports" / "qual_context" / "news.sqlite"
DEFAULT_EODHD_CAPTURE_DIR = REPO_ROOT / "reports" / "provider_captures" / "eodhd"
DEFAULT_WORLDMONITOR_CAPTURE_PATH = REPO_ROOT / "reports" / "provider_captures" / "worldmonitor" / "api-cache.json"
DEFAULT_NEWS_RUNS_DIR = REPO_ROOT / "reports" / "qual_context" / "news_runs"


def resolve_path(raw: str) -> Path:
    path = Path(str(raw or "").strip()).expanduser()
    if path.is_absolute():
        return path.resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / path).resolve()


def parse_provider_list(raw: str) -> List[str]:
    values = []
    for part in str(raw or "").split(","):
        token = part.strip().lower()
        if token and token not in values:
            values.append(token)
    return values


def normalize_ticker_token(raw: str) -> str:
    txt = str(raw or "").strip().upper()
    if not txt:
        return ""
    txt = txt.replace("ASX:", "").replace("ASX-", "")
    if "." in txt:
        txt = txt.split(".", 1)[0]
    txt = "".join(ch for ch in txt if ch.isalnum())
    return txt


def parse_ticker_list(raw: str) -> List[str]:
    out: List[str] = []
    for part in re.split(r"[,\s;]+", str(raw or "")):
        token = normalize_ticker_token(part)
        if token and token not in out:
            out.append(token)
    return out


def load_tickers(path: Path, limit: int = 0) -> List[str]:
    tickers = load_ticker_universe(path)
    if int(limit) > 0:
        return tickers[: int(limit)]
    return tickers


def build_provider(
    *,
    provider_name: str,
    eodhd_api_key: str,
    eodhd_capture_dir: Path,
    allow_missing_eodhd_captures: bool,
    worldmonitor_api_cache_url: str = "",
    worldmonitor_capture_path: Path | None = None,
    gdelt_kwargs: Dict[str, Any] | None = None,
) -> ProviderClient:
    name = str(provider_name or "").strip().lower()
    if name == "eodhd":
        return EodhdProvider(
            api_key=eodhd_api_key,
            capture_dir=eodhd_capture_dir,
            require_capture_contract=not allow_missing_eodhd_captures,
            allow_live_without_captures=allow_missing_eodhd_captures,
        )
    if name == "gdelt":
        kwargs = dict(gdelt_kwargs or {})
        return GdeltProvider(**kwargs)
    if name == "worldmonitor":
        kwargs: Dict[str, Any] = {}
        if str(worldmonitor_api_cache_url or "").strip():
            kwargs["api_cache_url"] = str(worldmonitor_api_cache_url).strip()
        if worldmonitor_capture_path is not None:
            kwargs["capture_path"] = worldmonitor_capture_path
        return WorldMonitorProvider(**kwargs)
    raise RuntimeError(f"Unsupported provider: {provider_name}")


def add_common_provider_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--news-articles-db",
        default=str(DEFAULT_NEWS_ARTICLES_DB),
        help="Canonical article DB path",
    )
    ap.add_argument(
        "--tickers-file",
        default=str(DEFAULT_TICKER_UNIVERSE),
        help="ASX ticker universe file",
    )
    ap.add_argument(
        "--identity-map-path",
        default=str(DEFAULT_IDENTITY_MAP),
        help="ASX ticker identity map JSON",
    )
    ap.add_argument(
        "--eodhd-capture-dir",
        default=str(DEFAULT_EODHD_CAPTURE_DIR),
        help="EODHD capture contract path",
    )
    ap.add_argument(
        "--allow-missing-eodhd-captures",
        action="store_true",
        help="Allow live EODHD usage even when capture contracts are missing.",
    )
    ap.add_argument(
        "--worldmonitor-api-cache-url",
        default="",
        help="Override WorldMonitor api-cache JSON URL.",
    )
    ap.add_argument(
        "--worldmonitor-capture-path",
        default=str(DEFAULT_WORLDMONITOR_CAPTURE_PATH),
        help="Optional local WorldMonitor api-cache capture path (used if present).",
    )


def add_common_gdelt_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--gdelt-query-base",
        default="",
        help="Override GDELT base query string.",
    )
    ap.add_argument(
        "--gdelt-max-records",
        type=int,
        default=250,
        help="GDELT max records per API request (1-250).",
    )
    ap.add_argument(
        "--gdelt-ticker-query-batch-size",
        type=int,
        default=10,
        help="Number of tickers per expanded GDELT query batch.",
    )
    ap.add_argument(
        "--gdelt-max-ticker-batches",
        type=int,
        default=5,
        help="Maximum expanded ticker query batches in one fetch window.",
    )
    ap.add_argument(
        "--gdelt-request-retries",
        type=int,
        default=3,
        help="Retry count for GDELT request failures (429/network/json).",
    )
    ap.add_argument(
        "--gdelt-retry-backoff-seconds",
        type=float,
        default=2.0,
        help="Initial backoff (seconds) for GDELT retries.",
    )
    ap.add_argument(
        "--gdelt-max-retry-sleep-seconds",
        type=float,
        default=120.0,
        help="Maximum per-attempt sleep (seconds) for GDELT retry backoff.",
    )


def gdelt_kwargs_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if str(getattr(args, "gdelt_query_base", "") or "").strip():
        out["query_base"] = str(args.gdelt_query_base).strip()
    out["max_records"] = int(getattr(args, "gdelt_max_records", 250))
    out["ticker_query_batch_size"] = int(getattr(args, "gdelt_ticker_query_batch_size", 10))
    out["max_ticker_batches"] = int(getattr(args, "gdelt_max_ticker_batches", 5))
    out["request_retries"] = int(getattr(args, "gdelt_request_retries", 3))
    out["retry_backoff_seconds"] = float(getattr(args, "gdelt_retry_backoff_seconds", 2.0))
    out["max_retry_sleep_seconds"] = float(getattr(args, "gdelt_max_retry_sleep_seconds", 120.0))
    return out
