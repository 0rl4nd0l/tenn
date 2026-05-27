from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .providers import (
    EodhdProvider,
    GdeltProvider,
    Newspaper4kProvider,
    ProviderClient,
    RssProvider,
    WorldMonitorProvider,
)
from .providers.newspaper4k import DEFAULT_SOURCE_PROFILE, NEWSPAPER4K_SOURCE_PROFILES
from .utils import load_ticker_universe

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PACKAGE_ROOT = REPO_ROOT / "financial-engine_v2"
if str(SHARED_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_PACKAGE_ROOT))

from shared.news_artifacts import (  # noqa: E402
    default_news_articles_db,
    default_news_context_db,
    default_news_runs_root,
    resolve_news_artifact_root,
)

DEFAULT_TICKER_UNIVERSE = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_IDENTITY_MAP = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"
DEFAULT_EODHD_CAPTURE_DIR = REPO_ROOT / "reports" / "provider_captures" / "eodhd"
DEFAULT_WORLDMONITOR_CAPTURE_PATH = REPO_ROOT / "reports" / "provider_captures" / "worldmonitor" / "api-cache.json"
DEFAULT_WORLDMONITOR_THEATER_MAP_PATH = REPO_ROOT / "financial-engine_v2" / "config" / "worldmonitor_theater_ticker_map.json"
DEFAULT_NEWS_ARTIFACT_ROOT, DEFAULT_NEWS_ARTIFACT_ROOT_SOURCE = resolve_news_artifact_root(repo_root=REPO_ROOT)
DEFAULT_NEWS_ARTICLES_DB = default_news_articles_db(DEFAULT_NEWS_ARTIFACT_ROOT)
DEFAULT_NEWS_CONTEXT_DB = default_news_context_db(DEFAULT_NEWS_ARTIFACT_ROOT)
DEFAULT_NEWS_RUNS_DIR = default_news_runs_root(DEFAULT_NEWS_ARTIFACT_ROOT)
DEFAULT_NEWS_BASELINE_JSON = DEFAULT_NEWS_ARTIFACT_ROOT / "news_baseline.json"


def describe_news_artifact_paths(
    *,
    news_articles_db: Path | None = None,
    news_context_db: Path | None = None,
    news_runs_root: Path | None = None,
) -> Dict[str, str]:
    return {
        "news_artifact_root": str(DEFAULT_NEWS_ARTIFACT_ROOT),
        "news_artifact_root_source": DEFAULT_NEWS_ARTIFACT_ROOT_SOURCE,
        "news_articles_db": str(news_articles_db or DEFAULT_NEWS_ARTICLES_DB),
        "news_context_db": str(news_context_db or DEFAULT_NEWS_CONTEXT_DB),
        "news_runs_root": str(news_runs_root or DEFAULT_NEWS_RUNS_DIR),
    }


def _has_capture_payload_files(capture_dir: Path | None) -> bool:
    if capture_dir is None:
        return False
    path = Path(capture_dir).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        return False
    for pattern in ("*.json", "*.jsonl"):
        for item in path.glob(pattern):
            if item.is_file():
                return True
    return False


def resolve_eodhd_capture_policy(
    *,
    capture_dir: Path,
    eodhd_api_key: str,
    allow_missing_eodhd_captures: bool,
    auto_live_when_capture_missing: bool = False,
) -> Dict[str, Any]:
    capture_contract_available = _has_capture_payload_files(capture_dir)
    api_key_present = bool(str(eodhd_api_key or "").strip())
    explicit_live = bool(allow_missing_eodhd_captures)
    allow_live_without_captures = explicit_live
    require_capture_contract = not explicit_live
    mode = "explicit_live" if explicit_live else "capture_contract"
    auto_live_effective = bool(auto_live_when_capture_missing) or (
        not explicit_live and not capture_contract_available and api_key_present
    )
    if (
        not explicit_live
        and auto_live_effective
    ):
        allow_live_without_captures = True
        require_capture_contract = False
        mode = "auto_live_missing_capture"
    return {
        "mode": mode,
        "capture_dir": str(Path(capture_dir).expanduser().resolve()),
        "capture_contract_available": bool(capture_contract_available),
        "api_key_present": bool(api_key_present),
        "allow_live_without_captures": bool(allow_live_without_captures),
        "require_capture_contract": bool(require_capture_contract),
        "auto_live_when_capture_missing": bool(auto_live_when_capture_missing),
        "auto_live_when_capture_missing_effective": bool(auto_live_effective),
        "allow_missing_eodhd_captures_flag": bool(allow_missing_eodhd_captures),
    }


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
    auto_live_when_capture_missing: bool = False,
    eodhd_symbols_only: bool = False,
    worldmonitor_api_cache_url: str = "",
    worldmonitor_capture_path: Path | None = None,
    worldmonitor_theater_map_path: Path | None = None,
    gdelt_kwargs: Dict[str, Any] | None = None,
    newspaper4k_kwargs: Dict[str, Any] | None = None,
) -> ProviderClient:
    name = str(provider_name or "").strip().lower()
    if name == "eodhd":
        policy = resolve_eodhd_capture_policy(
            capture_dir=eodhd_capture_dir,
            eodhd_api_key=eodhd_api_key,
            allow_missing_eodhd_captures=allow_missing_eodhd_captures,
            auto_live_when_capture_missing=auto_live_when_capture_missing,
        )
        provider = EodhdProvider(
            api_key=eodhd_api_key,
            capture_dir=eodhd_capture_dir,
            require_capture_contract=bool(policy.get("require_capture_contract")),
            allow_live_without_captures=bool(policy.get("allow_live_without_captures")),
            symbols_only=bool(eodhd_symbols_only),
        )
        setattr(
            provider,
            "_tenn_provider_settings",
            {
                "provider": "eodhd",
                "capture_policy": policy,
                "symbols_only": bool(eodhd_symbols_only),
            },
        )
        return provider
    if name == "gdelt":
        kwargs = dict(gdelt_kwargs or {})
        provider = GdeltProvider(**kwargs)
        settings: Dict[str, Any] = {
            "provider": "gdelt",
            "max_records": int(provider.max_records),
            "ticker_query_batch_size": int(provider.ticker_query_batch_size),
            "max_ticker_batches": int(provider.max_ticker_batches),
            "request_retries": int(provider.request_retries),
        }
        if str(provider.query_base).strip():
            settings["query_base"] = str(provider.query_base)
        setattr(provider, "_tenn_provider_settings", settings)
        return provider
    if name == "worldmonitor":
        kwargs: Dict[str, Any] = {}
        if str(worldmonitor_api_cache_url or "").strip():
            kwargs["api_cache_url"] = str(worldmonitor_api_cache_url).strip()
        if worldmonitor_capture_path is not None:
            kwargs["capture_path"] = worldmonitor_capture_path
        if worldmonitor_theater_map_path is not None:
            kwargs["theater_map_path"] = worldmonitor_theater_map_path
        provider = WorldMonitorProvider(**kwargs)
        setattr(
            provider,
            "_tenn_provider_settings",
            {
                "provider": "worldmonitor",
                "capture_path": str(worldmonitor_capture_path) if worldmonitor_capture_path is not None else "",
                "theater_map_path": str(worldmonitor_theater_map_path) if worldmonitor_theater_map_path is not None else "",
                "api_cache_url_override": str(worldmonitor_api_cache_url or "").strip(),
            },
        )
        return provider
    if name == "rss":
        return RssProvider()
    if name == "newspaper4k":
        return Newspaper4kProvider(**dict(newspaper4k_kwargs or {}))
    raise RuntimeError(f"Unsupported provider: {provider_name}")


def provider_settings(provider: ProviderClient) -> Dict[str, Any]:
    raw = getattr(provider, "_tenn_provider_settings", None)
    if isinstance(raw, dict):
        return dict(raw)
    return {"provider": str(getattr(provider, "name", "provider"))}


def newspaper4k_kwargs_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    def int_arg(name: str, default: int) -> int:
        raw = getattr(args, name, default)
        return default if raw is None else int(raw)

    def float_arg(name: str, default: float) -> float:
        raw = getattr(args, name, default)
        return default if raw is None else float(raw)

    raw_source_profile = getattr(
        args, "newspaper4k_source_profile", DEFAULT_SOURCE_PROFILE
    )
    source_profile = str(raw_source_profile or DEFAULT_SOURCE_PROFILE).strip().lower()
    sources_file = str(getattr(args, "newspaper4k_sources_file", "") or "").strip()
    no_playwright = bool(getattr(args, "newspaper4k_no_playwright", False))
    if (
        not no_playwright
        and not sources_file
        and source_profile == DEFAULT_SOURCE_PROFILE
    ):
        no_playwright = True
    kwargs: Dict[str, Any] = {
        "source_profile": source_profile,
        "max_articles_per_source": int_arg("newspaper4k_max_articles_per_source", 15),
        "max_total_articles": int_arg("newspaper4k_max_total_articles", 60),
        "request_timeout_seconds": int_arg(
            "newspaper4k_request_timeout_seconds", 10
        ),
        "sleep_seconds": float_arg("newspaper4k_sleep_seconds", 0.5),
        "no_playwright": no_playwright,
    }
    if sources_file:
        kwargs["sources_file"] = resolve_path(sources_file)
    return kwargs


def add_common_provider_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--news-articles-db",
        default=str(DEFAULT_NEWS_ARTICLES_DB),
        help=(
            "Canonical article DB path. Defaults under TENN_NEWS_ARTIFACT_ROOT, "
            "then live report mounts, then repo-local reports/qual_context."
        ),
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
        "--auto-live-when-capture-missing",
        action="store_true",
        help=(
            "Auto-enable live EODHD when captures are missing but an API key exists. "
            "Ignored when --allow-missing-eodhd-captures is set."
        ),
    )
    ap.add_argument(
        "--eodhd-symbols-only",
        action="store_true",
        help="Skip EODHD global market feed; fetch only per-symbol ASX news (.AU).",
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
    ap.add_argument(
        "--worldmonitor-theater-map-path",
        default=str(DEFAULT_WORLDMONITOR_THEATER_MAP_PATH),
        help="Optional WorldMonitor theater-to-ticker JSON mapping path.",
    )
    ap.add_argument(
        "--newspaper4k-source-profile",
        default=DEFAULT_SOURCE_PROFILE,
        choices=sorted(NEWSPAPER4K_SOURCE_PROFILES),
        help=(
            "newspaper4k source profile: daily is bounded RSS, "
            "broad is the full source crawl."
        ),
    )
    ap.add_argument(
        "--newspaper4k-sources-file",
        default="",
        help=(
            "Override newspaper4k source file path. Takes precedence over "
            "--newspaper4k-source-profile."
        ),
    )
    ap.add_argument(
        "--newspaper4k-max-articles-per-source",
        type=int,
        default=15,
        help="Maximum newspaper4k articles to keep per source.",
    )
    ap.add_argument(
        "--newspaper4k-max-total-articles",
        type=int,
        default=60,
        help="Maximum newspaper4k articles to keep for the run.",
    )
    ap.add_argument(
        "--newspaper4k-request-timeout-seconds",
        type=int,
        default=10,
        help="Per-request newspaper4k timeout in seconds.",
    )
    ap.add_argument(
        "--newspaper4k-sleep-seconds",
        type=float,
        default=0.5,
        help="Delay between newspaper4k sources.",
    )
    ap.add_argument(
        "--newspaper4k-no-playwright",
        action="store_true",
        help="Disable Playwright rendering for newspaper4k collection.",
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
        default=5,
        help="Number of tickers per expanded GDELT query batch (default 5 to avoid API 'query too long').",
    )
    ap.add_argument(
        "--gdelt-max-ticker-batches",
        type=int,
        default=3,
        help="Maximum expanded ticker query batches in one fetch window (default 3 to avoid API 'query too long').",
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
