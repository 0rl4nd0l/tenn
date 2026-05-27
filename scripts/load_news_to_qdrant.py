#!/usr/bin/env python3
"""Sync news chunks from SQLite to Qdrant collection `news_chunks`."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Marker file records the model used to build the news_chunks collection.
# Must match on every subsequent sync to prevent dimension corruption.
NEWS_CHUNKS_MODEL_FILE = (
    REPO_ROOT / "financial-engine_v2" / "reports" / "news_chunks_embedding_model.txt"
)
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_URL_ENV = "OLLAMA_URL"
OLLAMA_URL_SOURCE_CLI = "cli"
OLLAMA_URL_SOURCE_ENV = "env"
OLLAMA_URL_SOURCE_SETTINGS = "settings"
OLLAMA_URL_SOURCE_DEFAULT = "default"

logger = logging.getLogger(__name__)

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_NEWS_ARTICLES_DB,
    DEFAULT_NEWS_CONTEXT_DB,
    describe_news_artifact_paths,
    resolve_path,
)
from news_pipeline.utils import now_utc_iso, parse_datetime_utc  # noqa: E402

DEFAULT_NEWS_MEMO_MAX_ARTICLE_CHARS = 5000
EXCHANGE_TICKER_PATTERN = re.compile(
    r"\b(?:ASX|NYSE|NASDAQ|TSX|TSXV|TSE|LSE|AIM|OTCMKTS|OTC)\s*:\s*"
    r"([A-Z][A-Z0-9.\-]{0,12})\b",
    re.IGNORECASE,
)
MEMO_NON_EQUITY_TICKER_TOKENS = frozenset(
    {
        "AUD",
        "CAD",
        "CHF",
        "CNY",
        "EUR",
        "GBP",
        "HKD",
        "JPY",
        "NZD",
        "USD",
    }
)
MEMO_MARKET_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"asx|sharemarket|stock|stocks|shares|equity|equities|investor|"
    r"market|markets|earnings|revenue|profit|dividend|guidance|analyst|"
    r"price target|merger|acquisition|takeover|ipo|capital raising|"
    r"shareholder|shareholders|disclose|disclosure|stake|bid|sale|"
    r"savings|supply chain|superannuation|super|federal court|court|"
    r"debt|bank|banks|broker|brokers|mortgage|fraud|cyber|regulator|"
    r"regulators|energy|resources|infrastructure|annuity|inflows|"
    r"commodity|commodities|gold|copper|lithium|uranium|oil|gas|"
    r"inflation|interest rate|cash rate|bond|yield|currency|dollar|"
    r"budget|tax|rba|federal reserve|economy|economic"
    r")\b",
    re.IGNORECASE,
)
MEMO_INVESTABLE_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"asx|sharemarket|stock|stocks|shares|equity|equities|investor|"
    r"market|markets|earnings|revenue|profit|dividend|guidance|analyst|"
    r"price target|merger|acquisition|takeover|ipo|capital raising|"
    r"shareholder|shareholders|stake|broker|brokers|mortgage|housing|property|"
    r"company|companies|contract|placement|drilling|production|resource|resources|"
    r"commodity|commodities|gold|copper|lithium|uranium|oil|gas|"
    r"inflation|interest rate|cash rate|bond|yield|currency|dollar|"
    r"superannuation|super|startup|start-up|venture|private capital"
    r")\b|"
    r"\b(?:asx|tsx|lse|nyse|nasdaq)-listed\b|"
    r"\blisted\s+(?:company|companies|stock|stocks|business|businesses)\b|"
    r"\b(?:company|companies|stock|stocks|shares?)\s+listed\b",
    re.IGNORECASE,
)
MEMO_STRONG_FINANCIAL_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"asx|sharemarket|stock|stocks|shares|equity|equities|investor|"
    r"earnings|revenue|profit|dividend|guidance|analyst|price target|"
    r"merger|acquisition|takeover|ipo|capital raising|commodity|commodities|"
    r"gold|copper|lithium|uranium|oil|gas|inflation|interest rate|cash rate|"
    r"bond|yield|currency|dollar|budget|tax|rba|federal reserve|economy|economic"
    r")\b",
    re.IGNORECASE,
)
MEMO_EQUITY_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"asx|sharemarket|stock|stocks|shares|equity|equities|investor|"
    r"earnings|revenue|profit|dividend|guidance|analyst|price target|"
    r"merger|acquisition|takeover|ipo|capital raising|trading halt|broker"
    r")\b",
    re.IGNORECASE,
)
MEMO_FINANCE_ENTITY_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"asx|sharemarket|stock|stocks|shares|equity|equities|listed|investor|"
    r"earnings|revenue|profit|dividend|guidance|analyst|price target|"
    r"merger|acquisition|takeover|ipo|capital raising|company|companies"
    r")\b",
    re.IGNORECASE,
)
MEMO_OBVIOUS_NON_FINANCIAL_PATTERN = re.compile(
    r"\b("
    r"afl|nrl|origin|coach|game|match|finals?|goal|try|football|rugby|"
    r"swans|suns|magpies?|bulldogs?|sharks?|dolphins?|stadium|club|clubs"
    r")\b",
    re.IGNORECASE,
)
MEMO_PUBLIC_POLICY_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"neo-nazi|hate group|racial|racism|antisemitic|minister|mp|parliament|"
    r"coalition|labor|election|government|budget|income tax|tax plan|"
    r"national security|criminal code|home affairs|foreign affairs|"
    r"psychologist|school|footballers?|internet|emoji|decorum"
    r")\b",
    re.IGNORECASE,
)
MEMO_PUBLIC_POLICY_NOISE_PATTERN = re.compile(
    r"\b("
    r"internet|emoji|emojis|tiktok|social media|decorum|hate group|neo-nazi|"
    r"antisemitic|racial|racism"
    r")\b",
    re.IGNORECASE,
)
MEMO_COMPANY_ACTION_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"contract|contracts|sale|sells|sold|acquires|acquired|acquisition|"
    r"raises|raised|placement|stake|shareholders?|drilling|assay|assays|"
    r"production|mine|project|resource|revenue|profit|earnings|guidance|"
    r"outlook|dividend|price target|broker|takeover|merger|ipo|capital raising"
    r")\b",
    re.IGNORECASE,
)


def _source_id_for_article(art: Dict[str, Any]) -> str:
    article_id = str(art.get("article_id") or "").strip()
    return f"news:{article_id}" if article_id else ""


def _normalize_memo_ticker_candidate(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if ":" in raw:
        raw = raw.split(":", 1)[1].strip()
    if not raw or re.search(r"\s", raw):
        return ""
    if raw in MEMO_NON_EQUITY_TICKER_TOKENS:
        return ""
    cleaned = re.sub(r"[^A-Z0-9.]", "", raw)
    if cleaned != raw or not re.fullmatch(r"[A-Z0-9][A-Z0-9.]{0,6}", cleaned):
        return ""
    return cleaned


def _require_http_url(candidate: str, *, source_label: str) -> str:
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    raise ValueError(f"Invalid {source_label}. Expected a http:// or https:// URL.")


def resolve_ollama_url(
    *,
    cli_url: str | None,
    settings_url: str | None,
) -> tuple[str, str]:
    """
    Resolve Ollama base URL with explicit precedence.

    Empty settings values are treated as missing so local jobs can fall back to
    the canonical host default. Explicit CLI/env/settings values must be valid
    URLs and fail fast if malformed.
    """

    if cli_url is not None:
        candidate = str(cli_url or "").strip()
        if not candidate:
            raise ValueError(
                "Invalid --ollama-url. Expected a non-empty http:// or https:// value."
            )
        return _require_http_url(
            candidate,
            source_label="--ollama-url",
        ), OLLAMA_URL_SOURCE_CLI

    env_url = os.getenv(OLLAMA_URL_ENV, "").strip()
    if env_url:
        return _require_http_url(
            env_url,
            source_label=OLLAMA_URL_ENV,
        ), OLLAMA_URL_SOURCE_ENV

    settings_candidate = str(settings_url or "").strip()
    if settings_candidate:
        return _require_http_url(
            settings_candidate,
            source_label="configured settings.ollama_url",
        ), OLLAMA_URL_SOURCE_SETTINGS

    return DEFAULT_OLLAMA_URL, OLLAMA_URL_SOURCE_DEFAULT


def _memo_exchange_ticker_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in EXCHANGE_TICKER_PATTERN.finditer(str(text or "")):
        candidate = _normalize_memo_ticker_candidate(match.group(1))
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def _memo_candidate_tickers_for_article(art: Mapping[str, Any]) -> list[str]:
    raw_candidates: list[Any] = []
    primary = art.get("primary_ticker")
    if primary:
        raw_candidates.append(primary)
    tickers = art.get("tickers")
    if isinstance(tickers, list):
        raw_candidates.extend(tickers)

    candidates: list[str] = []
    seen: set[str] = set()
    text = "\n".join(
        str(art.get(key) or "") for key in ("title", "description", "text")
    )
    exchange_candidates = _memo_exchange_ticker_candidates(text)
    if exchange_candidates:
        return exchange_candidates

    for raw in raw_candidates:
        candidate = _normalize_memo_ticker_candidate(raw)
        if not candidate or candidate in seen:
            continue
        if not _structured_ticker_has_article_support(candidate, text):
            continue
        seen.add(candidate)
        candidates.append(candidate)
    if candidates:
        return candidates

    return candidates


def _structured_ticker_has_article_support(
    candidate: str,
    text: str,
) -> bool:
    escaped = re.escape(candidate)
    exchange_pattern = (
        rf"\b(?:ASX|NYSE|NASDAQ|TSX|TSXV|TSE|LSE|AIM|OTCMKTS|OTC)\s*:"
        rf"\s*{escaped}\b"
    )
    if re.search(exchange_pattern, text, re.IGNORECASE):
        return True
    if re.search(rf"\b{escaped}\b", text, re.IGNORECASE):
        return True
    return False


def _article_has_market_memo_context(art: Mapping[str, Any]) -> bool:
    text = "\n".join(
        str(art.get(key) or "") for key in ("title", "description", "text")
    )
    return bool(MEMO_MARKET_CONTEXT_PATTERN.search(text))


def _article_is_obvious_non_financial(art: Mapping[str, Any]) -> bool:
    text = "\n".join(
        str(art.get(key) or "") for key in ("title", "description", "text")
    )
    return bool(MEMO_OBVIOUS_NON_FINANCIAL_PATTERN.search(text)) and not bool(
        MEMO_EQUITY_CONTEXT_PATTERN.search(text)
    )


def _article_is_non_market_public_policy(art: Mapping[str, Any]) -> bool:
    text = "\n".join(
        str(art.get(key) or "") for key in ("title", "description", "text")
    )
    if not MEMO_PUBLIC_POLICY_CONTEXT_PATTERN.search(text):
        return False
    if (
        MEMO_PUBLIC_POLICY_NOISE_PATTERN.search(text)
        and not MEMO_EQUITY_CONTEXT_PATTERN.search(text)
        and not MEMO_COMPANY_ACTION_CONTEXT_PATTERN.search(text)
        and not _memo_exchange_ticker_candidates(text)
    ):
        return True
    return not bool(MEMO_INVESTABLE_CONTEXT_PATTERN.search(text))


def is_news_memo_candidate_article(art: Mapping[str, Any]) -> bool:
    source_id = _source_id_for_article(dict(art))
    text = str(art.get("text") or "").strip()
    if not source_id or not text:
        return False
    if _article_is_obvious_non_financial(art):
        return False
    if _article_is_non_market_public_policy(art):
        return False
    return bool(_memo_candidate_tickers_for_article(art)) or _article_has_market_memo_context(art)


def resolve_news_memo_max_article_chars(value: int | str | None = None) -> int:
    raw_value = value
    if raw_value in (None, ""):
        raw_value = os.getenv("NEWS_MEMO_MAX_ARTICLE_CHARS", "")
    if raw_value in (None, ""):
        return DEFAULT_NEWS_MEMO_MAX_ARTICLE_CHARS
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError) as exc:
        raise ValueError("NEWS_MEMO_MAX_ARTICLE_CHARS must be a positive integer") from exc


def _read_news_memo_source_ids(memos_path: str | Path | None = None) -> Dict[str, Any]:
    try:
        from app.services.news_memo_extractor import DEFAULT_NEWS_MEMOS_PATH
    except Exception:
        DEFAULT_NEWS_MEMOS_PATH = None  # type: ignore[assignment]

    raw_path = memos_path or DEFAULT_NEWS_MEMOS_PATH
    if raw_path is None:
        return {"path": "", "source_ids": set(), "read_errors": 0, "exists": False}
    resolved = Path(raw_path).expanduser()
    path = resolved.resolve()
    if not path.exists():
        return {"path": str(path), "source_ids": set(), "read_errors": 0, "exists": False}

    source_ids: set[str] = set()
    read_errors = 0
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            text = raw_line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                read_errors += 1
                continue
            if not isinstance(row, dict):
                read_errors += 1
                continue
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                source_ids.add(source_id)
    return {
        "path": str(path),
        "source_ids": source_ids,
        "read_errors": read_errors,
        "exists": True,
    }


def _default_news_memo_skips_path(
    *,
    memos_path: str | Path | None = None,
    skips_path: str | Path | None = None,
) -> str | Path | None:
    if skips_path:
        return skips_path
    if memos_path:
        return Path(memos_path).expanduser().with_name("news_memo_skips.jsonl")
    try:
        from app.services.news_memo_extractor import DEFAULT_NEWS_MEMO_SKIPS_PATH
    except Exception:
        return None
    return DEFAULT_NEWS_MEMO_SKIPS_PATH


def _read_news_memo_skip_source_ids(
    skips_path: str | Path | None = None,
    *,
    memos_path: str | Path | None = None,
) -> Dict[str, Any]:
    raw_path = _default_news_memo_skips_path(
        memos_path=memos_path,
        skips_path=skips_path,
    )
    if raw_path is None:
        return {"path": "", "source_ids": set(), "read_errors": 0, "exists": False}
    resolved = Path(raw_path).expanduser()
    path = resolved.resolve()
    if not path.exists():
        return {"path": str(path), "source_ids": set(), "read_errors": 0, "exists": False}

    source_ids: set[str] = set()
    read_errors = 0
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            text = raw_line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                read_errors += 1
                continue
            if not isinstance(row, dict):
                read_errors += 1
                continue
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                source_ids.add(source_id)
    return {
        "path": str(path),
        "source_ids": source_ids,
        "read_errors": read_errors,
        "exists": True,
    }


def build_memo_coverage_diagnostics(
    articles: List[Dict[str, Any]],
    *,
    memos_path: str | Path | None = None,
    memo_skips_path: str | Path | None = None,
) -> Dict[str, Any]:
    eligible_ids: list[str] = []
    skipped = 0
    for art in articles:
        source_id = _source_id_for_article(art)
        if not source_id or not is_news_memo_candidate_article(art):
            skipped += 1
            continue
        eligible_ids.append(source_id)

    memo_state = _read_news_memo_source_ids(memos_path)
    skip_state = _read_news_memo_skip_source_ids(
        memo_skips_path,
        memos_path=memos_path,
    )
    persisted_ids = memo_state["source_ids"]
    skipped_ids = skip_state["source_ids"]
    terminal_ids = persisted_ids | skipped_ids
    unique_eligible = set(eligible_ids)
    missing_ids = sorted(unique_eligible - terminal_ids)
    persisted = len(unique_eligible & persisted_ids)
    terminal_skipped = len(unique_eligible & skipped_ids)
    read_errors = int(memo_state.get("read_errors") or 0)
    skip_read_errors = int(skip_state.get("read_errors") or 0)
    if read_errors:
        status = "degraded"
    elif not unique_eligible:
        status = "empty"
    elif not missing_ids:
        status = "complete"
    elif persisted or terminal_skipped:
        status = "partial"
    else:
        status = "none"
    if skip_read_errors:
        status = "degraded"
    return {
        "status": status,
        "eligible": len(unique_eligible),
        "skipped": skipped,
        "persisted": persisted,
        "terminal_skipped": terminal_skipped,
        "missing": len(missing_ids),
        "missing_samples": missing_ids[:10],
        "memos_path": str(memo_state.get("path") or ""),
        "memos_file_exists": bool(memo_state.get("exists")),
        "memo_skips_path": str(skip_state.get("path") or ""),
        "memo_skips_file_exists": bool(skip_state.get("exists")),
        "read_errors": read_errors,
        "memo_skips_read_errors": skip_read_errors,
    }


def dispatch_news_memos(
    articles: List[Dict[str, Any]],
    *,
    task: Any | None = None,
    memos_path: str | Path | None = None,
    wait_for_completion: bool = False,
    wait_timeout_seconds: float = 0.0,
    poll_interval_seconds: float = 2.0,
    force_dispatch: bool = False,
    max_article_chars: int | str | None = None,
    llm_url: str | None = None,
    llm_model: str | None = None,
    memo_skips_path: str | Path | None = None,
) -> Dict[str, Any]:
    before = build_memo_coverage_diagnostics(
        articles,
        memos_path=memos_path,
        memo_skips_path=memo_skips_path,
    )
    memo_state = _read_news_memo_source_ids(memos_path)
    skip_state = _read_news_memo_skip_source_ids(
        memo_skips_path,
        memos_path=memos_path,
    )
    persisted_ids = set(memo_state.get("source_ids") or set())
    terminal_ids = persisted_ids | set(skip_state.get("source_ids") or set())
    article_char_cap = resolve_news_memo_max_article_chars(max_article_chars)
    dispatch_task = task
    import_error = ""
    if dispatch_task is None:
        try:
            from app.tasks.news_tasks import extract_news_memo_task  # noqa: E402

            dispatch_task = extract_news_memo_task
        except Exception as exc:
            import_error = str(exc)

    dispatched = 0
    failed = 0
    failed_samples: list[dict[str, str]] = []
    task_results: list[Any] = []
    task_ids: list[str] = []
    already_persisted_skipped = 0
    dispatch_candidates = 0
    if dispatch_task is not None:
        for art in articles:
            source_id = _source_id_for_article(art)
            text = str(art.get("text") or "")
            if not source_id or not is_news_memo_candidate_article(art):
                continue
            if not force_dispatch and source_id in terminal_ids:
                already_persisted_skipped += 1
                continue
            dispatch_candidates += 1
            memo_payload = {
                "source_id": source_id,
                "article_text": text[:article_char_cap],
                "provider": str(art.get("provider") or ""),
                "published_at": str(art.get("published_at") or ""),
                "candidate_tickers": _memo_candidate_tickers_for_article(art),
                "max_article_chars": article_char_cap,
            }
            if llm_url:
                memo_payload["llm_url"] = str(llm_url).strip()
            if llm_model:
                memo_payload["llm_model"] = str(llm_model).strip()
            if memos_path:
                memo_payload["memos_path"] = str(Path(memos_path).expanduser().resolve())
            if memo_skips_path:
                memo_payload["memo_skips_path"] = str(
                    Path(memo_skips_path).expanduser().resolve()
                )
            try:
                async_result = dispatch_task.delay(memo_payload)
                dispatched += 1
                if async_result is not None:
                    task_results.append(async_result)
                    task_id = _task_result_id(async_result)
                    if task_id:
                        task_ids.append(task_id)
            except Exception as exc:
                failed += 1
                if len(failed_samples) < 10:
                    failed_samples.append({"source_id": source_id, "error": str(exc)})

    wait_diagnostics = _wait_for_news_memo_tasks(
        task_results,
        wait_for_completion=wait_for_completion,
        timeout_seconds=wait_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    after = build_memo_coverage_diagnostics(
        articles,
        memos_path=memos_path,
        memo_skips_path=memo_skips_path,
    )
    unobserved_tasks = max(0, dispatched - wait_diagnostics["observed"])
    skipped_successes = int(wait_diagnostics.get("completed_skipped") or 0)
    missing_after_dispatch = int(after["missing"])
    if import_error:
        status = "unavailable"
    elif wait_for_completion and (
        failed
        or wait_diagnostics["failed"]
        or wait_diagnostics["pending"]
        or unobserved_tasks
        or after["read_errors"]
        or missing_after_dispatch > skipped_successes
    ):
        status = "degraded"
    elif wait_for_completion and missing_after_dispatch:
        status = "complete_with_skips"
    elif wait_for_completion and missing_after_dispatch == 0:
        status = "complete"
    elif failed:
        status = "degraded"
    elif missing_after_dispatch == 0:
        status = "complete"
    elif dispatched:
        status = "pending"
    else:
        status = after["status"]
    return {
        "status": status,
        "eligible": before["eligible"],
        "skipped": before["skipped"],
        "already_persisted_skipped": already_persisted_skipped,
        "dispatch_candidates": dispatch_candidates,
        "force_dispatch": bool(force_dispatch),
        "max_article_chars": article_char_cap,
        "llm_url": str(llm_url or "").strip(),
        "llm_url_source": "payload" if str(llm_url or "").strip() else "worker_default",
        "llm_model": str(llm_model or "").strip(),
        "llm_model_source": "payload" if str(llm_model or "").strip() else "worker_default",
        "dispatched": dispatched,
        "dispatch_failed": failed,
        "dispatch_failed_samples": failed_samples,
        "persisted_before_dispatch": before["persisted"],
        "persisted_after_dispatch": after["persisted"],
        "terminal_skipped_before_dispatch": before["terminal_skipped"],
        "terminal_skipped_after_dispatch": after["terminal_skipped"],
        "missing_after_dispatch": after["missing"],
        "missing_samples": after["missing_samples"],
        "memos_path": after["memos_path"],
        "memos_file_exists": after["memos_file_exists"],
        "memo_skips_path": after["memo_skips_path"],
        "memo_skips_file_exists": after["memo_skips_file_exists"],
        "read_errors": after["read_errors"],
        "memo_skips_read_errors": after["memo_skips_read_errors"],
        "import_error": import_error,
        "completion_observable": bool(wait_for_completion),
        "task_ids_count": len(task_ids),
        "task_ids_sample": task_ids[:10],
        "tasks_observed": wait_diagnostics["observed"],
        "tasks_completed": wait_diagnostics["completed"],
        "tasks_completed_skipped": skipped_successes,
        "tasks_failed": wait_diagnostics["failed"],
        "tasks_pending": wait_diagnostics["pending"],
        "tasks_unobserved": unobserved_tasks,
        "task_failure_samples": wait_diagnostics["failure_samples"],
        "task_skipped_samples": wait_diagnostics["skipped_samples"],
        "wait_requested": bool(wait_for_completion),
        "wait_timeout_seconds": wait_diagnostics["timeout_seconds"],
        "wait_poll_interval_seconds": wait_diagnostics["poll_interval_seconds"],
    }


def _task_result_id(result: Any) -> str:
    return str(
        getattr(result, "id", None)
        or getattr(result, "task_id", None)
        or getattr(result, "uuid", None)
        or ""
    )


def _task_result_ready(result: Any) -> bool:
    ready = getattr(result, "ready", None)
    if callable(ready):
        return bool(ready())
    state = str(
        getattr(result, "state", None) or getattr(result, "status", "") or ""
    ).upper()
    return state in {"SUCCESS", "FAILURE", "REVOKED"}


def _task_result_failed(result: Any) -> bool:
    failed = getattr(result, "failed", None)
    if callable(failed):
        return bool(failed())
    successful = getattr(result, "successful", None)
    if callable(successful):
        return not bool(successful())
    state = str(
        getattr(result, "state", None) or getattr(result, "status", "") or ""
    ).upper()
    return state in {"FAILURE", "REVOKED"}


def _task_failure_error(result: Any) -> str:
    result_value = getattr(result, "result", None)
    if result_value:
        return str(result_value)
    info = getattr(result, "info", None)
    return str(info or "")


def _task_success_payload(result: Any) -> Any:
    get_result = getattr(result, "get", None)
    if callable(get_result):
        try:
            return get_result(timeout=0)
        except Exception:
            pass
    return getattr(result, "result", None)


def _wait_for_news_memo_tasks(
    task_results: List[Any],
    *,
    wait_for_completion: bool,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> Dict[str, Any]:
    timeout = max(0.0, float(timeout_seconds or 0.0))
    poll_interval = max(0.1, float(poll_interval_seconds or 0.1))
    if wait_for_completion and task_results:
        deadline = time.monotonic() + timeout
        while True:
            if all(_task_result_ready(result) for result in task_results):
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))

    completed = 0
    completed_skipped = 0
    failed = 0
    pending = 0
    failure_samples: list[dict[str, str]] = []
    skipped_samples: list[dict[str, str]] = []
    if wait_for_completion:
        for result in task_results:
            task_id = _task_result_id(result)
            if not _task_result_ready(result):
                pending += 1
                continue
            if _task_result_failed(result):
                failed += 1
                if len(failure_samples) < 10:
                    failure_samples.append(
                        {"task_id": task_id, "error": _task_failure_error(result)}
                    )
                continue
            completed += 1
            payload = _task_success_payload(result)
            if isinstance(payload, dict) and str(payload.get("status") or "") == "skipped":
                completed_skipped += 1
                if len(skipped_samples) < 10:
                    skipped_samples.append(
                        {
                            "task_id": task_id,
                            "source_id": str(payload.get("source_id") or ""),
                            "reason": str(payload.get("skip_reason") or ""),
                        }
                    )
    return {
        "observed": len(task_results),
        "completed": completed,
        "completed_skipped": completed_skipped,
        "failed": failed,
        "pending": pending,
        "failure_samples": failure_samples,
        "skipped_samples": skipped_samples,
        "timeout_seconds": timeout,
        "poll_interval_seconds": poll_interval,
    }


def latest_provider_run_summary(db_path: str | Path) -> Dict[str, Any]:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        return {"status": "missing_db", "db_path": str(db)}
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT *
              FROM provider_runs
             ORDER BY started_at DESC, run_id DESC
             LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {"status": "missing_run", "db_path": str(db)}
        payload = dict(row)
        try:
            params = json.loads(str(payload.get("params_json") or "{}"))
        except json.JSONDecodeError:
            params = {}
        payload["params"] = params
        payload.pop("params_json", None)
        errors = conn.execute(
            """
            SELECT reason, COUNT(*) AS count
              FROM rejected_items
             WHERE run_id = ?
             GROUP BY reason
             ORDER BY reason
            """,
            (str(payload.get("run_id") or ""),),
        ).fetchall()
        payload["errors_by_class"] = {
            str(item["reason"]): int(item["count"] or 0) for item in errors
        }
        return payload
    finally:
        conn.close()


def validate_news_sqlite_freshness(
    db_path: str | Path,
    *,
    window_start_utc: str = "",
) -> Dict[str, Any]:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        return {
            "status": "degraded",
            "reason": "missing_db",
            "db_path": str(db),
            "window_start_utc": window_start_utc,
        }
    conn = sqlite3.connect(str(db))
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='context_chunks'"
        ).fetchone()
        if table is None:
            return {
                "status": "degraded",
                "reason": "missing_context_chunks",
                "db_path": str(db),
                "window_start_utc": window_start_utc,
            }
        row = conn.execute(
            "SELECT COUNT(*) AS chunks, MAX(published_at) AS newest FROM context_chunks"
        ).fetchone()
    finally:
        conn.close()

    chunks = int((row[0] if row else 0) or 0)
    newest = str((row[1] if row else "") or "")
    newest_norm = parse_datetime_utc(newest) or ""
    window_start_norm = parse_datetime_utc(window_start_utc) or ""
    stale = bool(window_start_norm and (not newest_norm or newest_norm < window_start_norm))
    return {
        "status": "degraded" if stale else "fresh",
        "reason": "stale" if stale else "",
        "db_path": str(db),
        "chunks": chunks,
        "newest_published_at": newest,
        "window_start_utc": window_start_utc,
    }


def refresh_news_sqlite_fallback(
    *,
    articles_db_path: str | Path,
    context_db_path: str | Path,
    lane: str = "high_precision",
    window_start_utc: str = "",
) -> Dict[str, Any]:
    from news_pipeline.chunk_builder import build_news_chunks

    stats = build_news_chunks(
        from_db=Path(articles_db_path),
        to_db=Path(context_db_path),
        lane=lane,
        embed_backend="hash",
    )
    freshness = validate_news_sqlite_freshness(
        context_db_path,
        window_start_utc=window_start_utc,
    )
    return {
        "status": "success" if freshness["status"] == "fresh" else "degraded",
        "build": stats,
        "freshness": freshness,
    }


def write_summary_json(path: str | Path, payload: Dict[str, Any]) -> None:
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _chunk_point_id(chunk_id: str) -> str:
    """Deterministic integer-like ID derived from chunk_id via sha1."""
    digest = hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()
    # Qdrant accepts unsigned 64-bit integers; map first 16 hex chars to int.
    return str(int(digest[:16], 16))


def _connect_news_articles_db(db_path: str | Path, *, read_only: bool) -> sqlite3.Connection:
    db = Path(db_path).expanduser().resolve()
    if read_only and not db.exists():
        raise FileNotFoundError(f"news articles SQLite DB not found: {db}")
    if read_only:
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def _loader_where_clauses(
    since_hours: Optional[int],
    *,
    include_eligibility: bool,
) -> tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []
    if include_eligibility:
        where_clauses.extend(
            [
                "(a.language IN ('en', '') OR a.language IS NULL)",
                "a.quality_score >= 0.3",
            ]
        )

    if since_hours is not None and int(since_hours) > 0:
        cutoff = (
            (dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=int(since_hours)))
            .isoformat()
            .replace("+00:00", "Z")
        )
        where_clauses.append("a.published_at_utc >= ?")
        params.append(cutoff)
    return where_clauses, params


def _iter_chunks(
    conn: sqlite3.Connection,
    since_hours: Optional[int],
) -> List[Dict[str, Any]]:
    """Read articles + entity_links from the news articles DB."""
    where_clauses, params = _loader_where_clauses(
        since_hours,
        include_eligibility=True,
    )
    where_sql = " AND ".join(where_clauses)
    sql = f"""
        SELECT
            a.article_id,
            a.canonical_url,
            a.title,
            a.description,
            a.body,
            a.provider_best AS provider,
            a.language,
            a.published_at_utc
        FROM articles a
        WHERE {where_sql}
        ORDER BY a.published_at_utc DESC, a.article_id DESC
    """
    rows = conn.execute(sql, tuple(params)).fetchall()
    if not rows:
        return []

    article_ids = [str(r["article_id"]) for r in rows]
    marks = ",".join(["?"] * len(article_ids))
    link_rows = conn.execute(
        f"""
        SELECT article_id, ticker
          FROM entity_links
         WHERE article_id IN ({marks})
         GROUP BY article_id, ticker
        """,
        tuple(article_ids),
    ).fetchall()
    tickers_by_article: Dict[str, List[str]] = {}
    for lr in link_rows:
        aid = str(lr["article_id"])
        tickers_by_article.setdefault(aid, []).append(str(lr["ticker"]))

    # Resolve primary ticker from article_relevance (is_primary=1, then highest relevance_score).
    # Falls back to empty string when article_relevance has no rows for an article.
    primary_ticker_by_article: Dict[str, str] = {}
    rel_rows = conn.execute(
        f"""
        SELECT article_id, ticker
          FROM article_relevance
         WHERE article_id IN ({marks})
         ORDER BY article_id ASC, is_primary DESC, relevance_score DESC
        """,
        tuple(article_ids),
    ).fetchall()
    for rr in rel_rows:
        aid = str(rr["article_id"])
        if aid not in primary_ticker_by_article:
            primary_ticker_by_article[aid] = str(rr["ticker"])

    out = []
    for r in rows:
        article_id = str(r["article_id"])
        title = str(r["title"] or "")
        description = str(r["description"] or "")
        body = str(r["body"] or "")
        parts = [p for p in (title, description, body) if p.strip()]
        text = "\n\n".join(parts)
        if not text.strip():
            continue
        linked = sorted(set(tickers_by_article.get(article_id, [])))
        out.append(
            {
                "article_id": article_id,
                "url": str(r["canonical_url"] or ""),
                "title": title,
                "provider": str(r["provider"] or ""),
                "language": str(r["language"] or "en"),
                "published_at": str(r["published_at_utc"] or ""),
                "tickers": linked,
                "primary_ticker": primary_ticker_by_article.get(article_id, ""),
                "text": text,
            }
        )
    return out


def _iter_article_report_rows(
    conn: sqlite3.Connection,
    since_hours: Optional[int],
) -> List[Dict[str, Any]]:
    where_clauses, params = _loader_where_clauses(
        since_hours,
        include_eligibility=False,
    )
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    rows = conn.execute(
        f"""
        SELECT
            a.article_id,
            a.canonical_url,
            a.title,
            a.description,
            a.body,
            a.provider_best AS provider,
            a.language,
            a.quality_score,
            a.published_at_utc
        FROM articles a
        WHERE {where_sql}
        ORDER BY a.published_at_utc DESC, a.article_id DESC
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


def _build_chunk_payload(
    art: Dict[str, Any], idx: int, chunk_text: str = ""
) -> Dict[str, Any]:
    """Build the Qdrant point payload for one chunk of a news article.

    Uses `primary_ticker` (from article_relevance) when available.
    Falls back to the single linked ticker when there is exactly one, otherwise empty.
    """
    primary_ticker = str(art.get("primary_ticker") or "").strip()
    if not primary_ticker:
        tickers = art.get("tickers") or []
        primary_ticker = tickers[0] if len(tickers) == 1 else ""
    linked_tickers = list(
        dict.fromkeys(
            str(t).strip().upper() for t in (art.get("tickers") or []) if str(t).strip()
        )
    )
    return {
        "corpus": "news",
        "article_id": art["article_id"],
        "chunk_id": f"news:{art['article_id']}:{idx}",
        "provider": art["provider"],
        "ticker": primary_ticker,
        "tickers": linked_tickers,
        "primary_ticker": primary_ticker,
        "published_at": art["published_at"],
        "language": art["language"],
        "title": art["title"],
        "url": art["url"],
        "source_type": "news_article",
        "text": chunk_text,
    }


def _split_chunks(
    text: str, max_chars: int = 1200, overlap_words: int = 60
) -> List[str]:
    """Simple character-level chunker with word-boundary overlap."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for word in words:
        wl = len(word) + 1
        if current_len + wl > max_chars and current:
            chunks.append(" ".join(current))
            overlap = current[-overlap_words:] if overlap_words > 0 else []
            current = list(overlap)
            current_len = sum(len(w) + 1 for w in current)
        current.append(word)
        current_len += wl
    if current:
        chunks.append(" ".join(current))
    return chunks


def _article_text_from_row(row: Mapping[str, Any]) -> str:
    return "\n\n".join(
        str(row.get(field) or "")
        for field in ("title", "description", "body")
        if str(row.get(field) or "").strip()
    )


def _is_loader_language(language: Any) -> bool:
    return language is None or str(language) in {"en", ""}


def _exclusion_reason(row: Mapping[str, Any]) -> str:
    if not _is_loader_language(row.get("language")):
        return "unsupported_language"
    try:
        quality_score = float(row.get("quality_score") or 0.0)
    except (TypeError, ValueError):
        quality_score = 0.0
    if quality_score < 0.3:
        return "low_quality"
    if not _article_text_from_row(row).strip():
        return "missing_text"
    return ""


def _build_target_points(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for art in articles:
        chunks = _split_chunks(str(art.get("text") or ""))
        for idx, chunk_text in enumerate(chunks):
            payload = _build_chunk_payload(art, idx, chunk_text)
            points.append(
                {
                    "id": _chunk_point_id(payload["chunk_id"]),
                    "_text": chunk_text,
                    "payload": payload,
                }
            )
    return points


def _build_target_report(
    *,
    all_article_rows: List[Dict[str, Any]],
    articles: List[Dict[str, Any]],
    points: List[Dict[str, Any]],
) -> Dict[str, Any]:
    eligible_article_ids = {str(art.get("article_id") or "") for art in articles}
    excluded_rows = [
        row
        for row in all_article_rows
        if str(row.get("article_id") or "") not in eligible_article_ids
    ]
    excluded_reasons: Counter[str] = Counter()
    excluded_chunks = 0
    for row in excluded_rows:
        reason = _exclusion_reason(row) or "unknown"
        excluded_reasons[reason] += 1
        text = _article_text_from_row(row)
        if text.strip():
            excluded_chunks += len(_split_chunks(text))

    provider_spread = Counter(
        str(art.get("provider") or "unknown").strip() or "unknown" for art in articles
    )
    article_primary = Counter()
    article_any = Counter()
    for art in articles:
        if str(art.get("primary_ticker") or "").strip():
            article_primary["articles_with_primary_ticker"] += 1
        if art.get("tickers"):
            article_any["articles_with_any_ticker"] += 1

    ticker_counts: Counter[str] = Counter()
    chunks_with_primary = 0
    chunks_with_any = 0
    for point in points:
        payload = dict(point.get("payload") or {})
        if str(payload.get("primary_ticker") or "").strip():
            chunks_with_primary += 1
        tickers = payload.get("tickers") or []
        if tickers:
            chunks_with_any += 1
        for ticker in tickers:
            symbol = str(ticker or "").strip().upper()
            if symbol:
                ticker_counts[symbol] += 1

    return {
        "eligible_articles": len(articles),
        "eligible_chunks": len(points),
        "excluded_articles": len(excluded_rows),
        "excluded_chunks": excluded_chunks,
        "total_articles_considered": len(all_article_rows),
        "excluded_reason_counts": dict(sorted(excluded_reasons.items())),
        "provider_spread": dict(sorted(provider_spread.items())),
        "ticker_coverage_summary": {
            "articles_with_primary_ticker": int(
                article_primary["articles_with_primary_ticker"]
            ),
            "articles_with_any_ticker": int(article_any["articles_with_any_ticker"]),
            "chunks_with_primary_ticker": chunks_with_primary,
            "chunks_with_any_ticker": chunks_with_any,
            "unique_tickers": len(ticker_counts),
            "top_tickers": dict(ticker_counts.most_common(20)),
        },
    }


def build_news_projection_target(
    db_path: str | Path,
    *,
    since_hours: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the deterministic loader-eligible news projection target."""
    conn = _connect_news_articles_db(db_path, read_only=True)
    try:
        articles = _iter_chunks(conn, since_hours)
        all_article_rows = _iter_article_report_rows(conn, since_hours)
    finally:
        conn.close()
    points = _build_target_points(articles)
    report = _build_target_report(
        all_article_rows=all_article_rows,
        articles=articles,
        points=points,
    )
    return {"articles": articles, "points": points, "report": report}


def _point_payload(point: Any) -> Dict[str, Any]:
    if isinstance(point, Mapping):
        return dict(point.get("payload") or {})
    return dict(getattr(point, "payload", None) or {})


def _point_id(point: Any) -> str:
    if isinstance(point, Mapping):
        return str(point.get("id") or "")
    return str(getattr(point, "id", "") or "")


def read_qdrant_payloads(
    client: Any,
    collection: str,
    *,
    page_size: int = 512,
) -> Dict[str, Dict[str, Any]]:
    payloads: Dict[str, Dict[str, Any]] = {}
    offset: Any | None = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            limit=int(page_size),
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            point_id = _point_id(point)
            if point_id:
                payloads[point_id] = _point_payload(point)
        if next_offset is None:
            break
        offset = next_offset
    return payloads


_DRIFT_FIELDS = (
    "ticker",
    "tickers",
    "primary_ticker",
    "provider",
    "title",
    "url",
    "published_at",
    "text",
)


def _normalize_payload_value(value: Any) -> Any:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return ""
    return str(value)


def diff_qdrant_projection(
    target_points: List[Dict[str, Any]],
    current_payloads: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    expected_by_id = {str(point["id"]): point for point in target_points}
    expected_ids = set(expected_by_id)
    current_ids = {str(point_id) for point_id in current_payloads}
    missing_ids = sorted(expected_ids - current_ids)
    stale_ids = sorted(current_ids - expected_ids)
    drift_counts: Counter[str] = Counter()
    drift_ids: set[str] = set()

    for point_id in sorted(expected_ids & current_ids):
        expected_payload = dict(expected_by_id[point_id].get("payload") or {})
        current_payload = dict(current_payloads.get(point_id) or {})
        for field in _DRIFT_FIELDS:
            if _normalize_payload_value(expected_payload.get(field)) != _normalize_payload_value(
                current_payload.get(field)
            ):
                drift_counts[field] += 1
                drift_ids.add(point_id)

    def chunk_sample(point_ids: List[str]) -> List[str]:
        samples: List[str] = []
        for point_id in point_ids[:10]:
            expected_payload = dict(expected_by_id.get(point_id, {}).get("payload") or {})
            current_payload = dict(current_payloads.get(point_id) or {})
            chunk_id = str(
                expected_payload.get("chunk_id") or current_payload.get("chunk_id") or point_id
            )
            samples.append(chunk_id)
        return samples

    return {
        "status": "available",
        "expected_chunks": len(expected_ids),
        "current_qdrant_chunks": len(current_ids),
        "missing_expected_chunks": len(missing_ids),
        "stale_qdrant_chunks": len(stale_ids),
        "payload_drift_chunks": len(drift_ids),
        "payload_drift_counts": {
            field: int(drift_counts.get(field, 0)) for field in _DRIFT_FIELDS
        },
        "missing_samples": chunk_sample(missing_ids),
        "stale_samples": chunk_sample(stale_ids),
        "payload_drift_samples": chunk_sample(sorted(drift_ids)),
    }


def _unavailable_qdrant_diff(target_points: List[Dict[str, Any]], exc: Exception) -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "expected_chunks": len(target_points),
        "current_qdrant_chunks": None,
        "missing_expected_chunks": None,
        "stale_qdrant_chunks": None,
        "payload_drift_chunks": None,
        "payload_drift_counts": {},
        "error": str(exc),
    }


def _build_qdrant_diff(
    *,
    client: Any,
    collection: str,
    target_points: List[Dict[str, Any]],
    allow_unavailable: bool,
) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    try:
        current_payloads = read_qdrant_payloads(client, collection)
    except Exception as exc:
        if allow_unavailable:
            return _unavailable_qdrant_diff(target_points, exc), {}
        raise
    return diff_qdrant_projection(target_points, current_payloads), current_payloads


def _repair_point_ids(
    target_points: List[Dict[str, Any]],
    current_payloads: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    expected_by_id = {str(point["id"]): point for point in target_points}
    repair_ids = set(expected_by_id) - {str(point_id) for point_id in current_payloads}
    for point_id, point in expected_by_id.items():
        if point_id not in current_payloads:
            continue
        expected_payload = dict(point.get("payload") or {})
        current_payload = dict(current_payloads.get(point_id) or {})
        if any(
            _normalize_payload_value(expected_payload.get(field))
            != _normalize_payload_value(current_payload.get(field))
            for field in _DRIFT_FIELDS
        ):
            repair_ids.add(point_id)
    return repair_ids


def _memo_skipped(reason: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    diagnostics = build_memo_coverage_diagnostics(articles)
    return {
        "status": "skipped",
        "reason": reason,
        "eligible": diagnostics["eligible"],
        "skipped": diagnostics["skipped"],
        "dispatched": 0,
        "dispatch_failed": 0,
        "missing_after_dispatch": diagnostics["missing"],
        "completion_observable": False,
        "task_ids_count": 0,
        "task_ids_sample": [],
        "tasks_observed": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "tasks_pending": 0,
        "tasks_unobserved": 0,
        "task_failure_samples": [],
        "wait_requested": False,
    }


def _coerce_qdrant_point_id(point_id: str) -> int | str:
    text = str(point_id)
    return int(text) if text.isdigit() else text


def _delete_qdrant_points(
    client: Any,
    collection: str,
    point_ids: List[str],
) -> None:
    from qdrant_client.http import models as qmodels

    if not point_ids:
        return
    client.delete(
        collection_name=collection,
        points_selector=qmodels.PointIdsList(
            points=[_coerce_qdrant_point_id(point_id) for point_id in point_ids]
        ),
    )


def sync_news_to_qdrant(
    db_path: str,
    qdrant_url: str = "http://localhost:6333",
    collection: str = "news_chunks",
    batch_size: int = 64,
    since_hours: Optional[int] = None,
    *,
    dry_run: bool = False,
    dispatch_memos: bool = True,
    cleanup_stale: bool = False,
    qdrant_only: bool = False,
    target_contract_report: bool = False,
    qdrant_client: Any | None = None,
    embed_texts_fn: Callable[[List[str]], List[List[float]]] | None = None,
    upsert_points_fn: Callable[[Any, str, List[Dict[str, Any]]], None] | None = None,
    delete_points_fn: Callable[[Any, str, List[str]], None] | None = None,
    ensure_collection_fn: Callable[[Any, str, int], None] | None = None,
    get_vector_config_fn: Callable[[Any, str], Dict[str, Any]] | None = None,
    memo_dispatch_fn: Callable[[List[Dict[str, Any]]], Dict[str, Any]] | None = None,
    memo_diagnostics_path: str | Path | None = None,
    memo_wait_for_completion: bool = False,
    memo_wait_timeout_seconds: float = 0.0,
    memo_wait_poll_interval_seconds: float = 2.0,
    memo_force_dispatch: bool = False,
    memo_max_article_chars: int | str | None = None,
    embed_model: str | None = None,
    ollama_url: str | None = None,
    write_model_marker: bool = True,
) -> Dict[str, Any]:
    """
    Read news chunks from SQLite and upsert into Qdrant.

    Safe to re-run (idempotent via deterministic point IDs).
    """
    if cleanup_stale and since_hours is not None and int(since_hours) > 0:
        raise ValueError("--cleanup-stale requires a full target (--since-hours 0)")

    settings_ollama_url: str | None = None
    if embed_model is None or ollama_url is None:
        try:
            from app.core.config import settings

            embed_model = embed_model or str(
                getattr(settings, "embed_model", "nomic-embed-text")
            )
            settings_ollama_url = str(getattr(settings, "ollama_url", "") or "")
        except Exception:
            embed_model = embed_model or "nomic-embed-text"
    embed_model = str(embed_model or "nomic-embed-text")
    ollama_url, ollama_url_source = resolve_ollama_url(
        cli_url=ollama_url,
        settings_url=settings_ollama_url,
    )

    target = build_news_projection_target(db_path, since_hours=since_hours)
    articles = list(target["articles"])
    target_points = list(target["points"])
    stats: Dict[str, Any] = {
        "articles": len(articles),
        "chunks": len(target_points),
        "upserted": 0,
        "deleted": 0,
        "dry_run": bool(dry_run),
        "qdrant_only": bool(qdrant_only),
        "ollama_url": ollama_url,
        "ollama_url_source": ollama_url_source,
    }
    if target_contract_report or dry_run or qdrant_only or cleanup_stale:
        stats["target_contract_report"] = target["report"]

    client = qdrant_client
    current_payloads: Dict[str, Dict[str, Any]] = {}
    needs_diff = dry_run or qdrant_only or cleanup_stale or target_contract_report
    if needs_diff or target_points:
        if client is None:
            try:
                from qdrant_client import QdrantClient

                client = QdrantClient(url=qdrant_url)
            except Exception as exc:
                if dry_run:
                    stats["qdrant_diff"] = _unavailable_qdrant_diff(target_points, exc)
                    stats["memo_extraction"] = _memo_skipped("dry_run", articles)
                    return stats
                raise

    if needs_diff and client is not None:
        diff, current_payloads = _build_qdrant_diff(
            client=client,
            collection=collection,
            target_points=target_points,
            allow_unavailable=dry_run,
        )
        stats["qdrant_diff"] = diff

    if dry_run:
        stats["memo_extraction"] = _memo_skipped("dry_run", articles)
        logger.info("news_chunks_sync dry run complete: %s", stats)
        return stats

    if not target_points and not cleanup_stale:
        if dispatch_memos and not qdrant_only:
            stats["memo_extraction"] = build_memo_coverage_diagnostics(
                [],
                memos_path=memo_diagnostics_path,
            )
        else:
            reason = "qdrant_only" if qdrant_only else "no_dispatch_memos"
            stats["memo_extraction"] = _memo_skipped(reason, articles)
        return stats

    if client is None:
        raise RuntimeError("Qdrant client unavailable")

    if embed_texts_fn is None:
        from app.services.ollama import ollama_embed

        def embed_texts_fn(texts: List[str]) -> List[List[float]]:
            return ollama_embed(str(ollama_url), str(embed_model), texts)

    if (
        ensure_collection_fn is None
        or upsert_points_fn is None
        or get_vector_config_fn is None
    ):
        from app.services.embeddings import (
            ensure_collection,
            get_qdrant_collection_vector_config,
            upsert_points,
        )

        ensure_collection_fn = ensure_collection_fn or ensure_collection
        upsert_points_fn = upsert_points_fn or upsert_points
        get_vector_config_fn = get_vector_config_fn or get_qdrant_collection_vector_config
    delete_points_fn = delete_points_fn or _delete_qdrant_points

    # --- Preflight: log resolved configuration before any writes ---
    logger.info(
        "news_chunks_sync preflight: collection=%s qdrant_url=%s embed_model=%s ollama_url=%s",
        collection,
        qdrant_url,
        embed_model,
        ollama_url,
    )

    # Check stored model marker — refuse to write if it conflicts with a populated collection.
    stored_model: Optional[str] = None
    if write_model_marker and NEWS_CHUNKS_MODEL_FILE.exists():
        try:
            stored_model = (
                NEWS_CHUNKS_MODEL_FILE.read_text(encoding="utf-8").strip() or None
            )
        except OSError as exc:
            logger.warning(
                "news_chunks_sync: unable to read model marker %s: %s",
                NEWS_CHUNKS_MODEL_FILE,
                exc,
            )
    if stored_model and stored_model != embed_model:
        # Only block if the collection already has vectors.
        try:
            existing_cols = [c.name for c in client.get_collections().collections]
            if collection in existing_cols:
                cfg = get_vector_config_fn(client, collection)
                existing_points = int(cfg.get("points_count") or 0)
                if existing_points > 0:
                    raise RuntimeError(
                        f"news_chunks_sync: embedding model mismatch — stored marker is '{stored_model}', "
                        f"configured model is '{embed_model}', collection '{collection}' has {existing_points} vectors. "
                        "Rebuild the collection with the correct model or update the marker file."
                    )
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(
                "news_chunks_sync: preflight model-marker check failed: %s", exc
            )

    # Determine vector dimension by embedding a probe text.
    probe_vec = embed_texts_fn(["probe"])[0]
    dim = len(probe_vec)
    logger.info("news_chunks_sync: probe_dim=%d embed_model=%s", dim, embed_model)

    # Check existing collection dimension before writing.
    try:
        existing_cols = [c.name for c in client.get_collections().collections]
        if collection in existing_cols:
            cfg = get_vector_config_fn(client, collection)
            existing_dim = cfg.get("actual_dim")
            existing_points = int(cfg.get("points_count") or 0)
            if existing_dim is not None and existing_dim != dim:
                raise RuntimeError(
                    f"news_chunks_sync: dimension mismatch — probe_dim={dim} (model='{embed_model}'), "
                    f"collection '{collection}' has dim={existing_dim} with {existing_points} existing vectors. "
                    "Rebuild the collection with the correct model before syncing."
                )
            logger.info(
                "news_chunks_sync: collection '%s' exists dim=%s points=%d — probe_dim=%d match=%s",
                collection,
                existing_dim,
                existing_points,
                dim,
                existing_dim == dim,
            )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning(
            "news_chunks_sync: preflight collection-dimension check failed: %s", exc
        )

    ensure_collection_fn(client, collection, dim)

    total_upserted = 0
    batch: List[Dict[str, Any]] = []
    points_for_upsert = target_points
    if qdrant_only:
        if not current_payloads and "qdrant_diff" not in stats:
            diff, current_payloads = _build_qdrant_diff(
                client=client,
                collection=collection,
                target_points=target_points,
                allow_unavailable=False,
            )
            stats["qdrant_diff"] = diff
        if stats.get("qdrant_diff", {}).get("status") != "available":
            raise RuntimeError("Qdrant diff is required for --qdrant-only repair")
        repair_ids = _repair_point_ids(target_points, current_payloads)
        points_for_upsert = [
            point for point in target_points if str(point["id"]) in repair_ids
        ]
        stats["repair_candidate_chunks"] = len(points_for_upsert)

    def flush_batch() -> int:
        nonlocal batch
        if not batch:
            return 0
        texts = [p["_text"] for p in batch]
        vectors = embed_texts_fn(texts)
        points = []
        for point, vec in zip(batch, vectors):
            points.append(
                {
                    "id": int(point["id"]),
                    "vector": vec,
                    "payload": point["payload"],
                }
            )
        upsert_points_fn(client, collection, points)
        n = len(points)
        batch = []
        return n

    for point in points_for_upsert:
        batch.append(point)
        if len(batch) >= batch_size:
            total_upserted += flush_batch()

    total_upserted += flush_batch()
    stats["upserted"] = total_upserted

    if cleanup_stale:
        if not current_payloads and "qdrant_diff" not in stats:
            diff, current_payloads = _build_qdrant_diff(
                client=client,
                collection=collection,
                target_points=target_points,
                allow_unavailable=False,
            )
            stats["qdrant_diff"] = diff
        if stats.get("qdrant_diff", {}).get("status") != "available":
            raise RuntimeError("Qdrant diff is required for --cleanup-stale")
        expected_ids = {str(point["id"]) for point in target_points}
        stale_ids = sorted(set(current_payloads) - expected_ids)
        for start in range(0, len(stale_ids), int(batch_size)):
            delete_points_fn(client, collection, stale_ids[start : start + int(batch_size)])
        stats["deleted"] = len(stale_ids)

    # Dispatch news memo extraction for each article (best-effort). Extraction
    # remains asynchronous by default. Explicit wait mode observes bounded task
    # completion without performing memo writes in the loader.
    if qdrant_only:
        memo_diagnostics = _memo_skipped("qdrant_only", articles)
    elif not dispatch_memos:
        memo_diagnostics = _memo_skipped("no_dispatch_memos", articles)
    else:
        if memo_dispatch_fn is not None:
            memo_diagnostics = memo_dispatch_fn(articles)
        else:
            memo_diagnostics = dispatch_news_memos(
                articles,
                memos_path=memo_diagnostics_path,
                wait_for_completion=bool(memo_wait_for_completion),
                wait_timeout_seconds=float(memo_wait_timeout_seconds),
                poll_interval_seconds=float(memo_wait_poll_interval_seconds),
                force_dispatch=bool(memo_force_dispatch),
                max_article_chars=memo_max_article_chars,
            )
    logger.info("news_chunks_sync memo diagnostics: %s", memo_diagnostics)

    # Write model marker after successful sync so future runs can verify consistency.
    if write_model_marker:
        try:
            NEWS_CHUNKS_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
            NEWS_CHUNKS_MODEL_FILE.write_text(str(embed_model), encoding="utf-8")
            logger.info(
                "news_chunks_sync: wrote model marker %s → '%s'",
                NEWS_CHUNKS_MODEL_FILE,
                embed_model,
            )
        except OSError as exc:
            logger.warning("news_chunks_sync: unable to write model marker: %s", exc)

    stats["memo_extraction"] = memo_diagnostics
    logger.info("news_chunks_sync complete: %s", stats)
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ap = argparse.ArgumentParser(description="Sync news chunks from SQLite to Qdrant.")
    ap.add_argument(
        "--db-path",
        default=str(DEFAULT_NEWS_ARTICLES_DB),
        help="news_articles SQLite path",
    )
    ap.add_argument(
        "--qdrant-url", default="http://localhost:6333", help="Qdrant service URL"
    )
    ap.add_argument(
        "--collection", default="news_chunks", help="Qdrant collection name"
    )
    ap.add_argument("--batch-size", type=int, default=64, help="Upsert batch size")
    ap.add_argument(
        "--since-hours",
        type=int,
        default=0,
        help="Only sync articles from the last N hours (0 = all)",
    )
    ap.add_argument(
        "--refresh-sqlite-fallback",
        action="store_true",
        help="Rebuild the canonical news.sqlite fallback after a successful Qdrant sync",
    )
    ap.add_argument(
        "--news-context-db",
        default=str(DEFAULT_NEWS_CONTEXT_DB),
        help="Canonical news.sqlite fallback path",
    )
    ap.add_argument(
        "--fallback-lane",
        default="high_precision",
        choices=["high_precision", "high_recall"],
        help="Lane used when rebuilding the news.sqlite fallback",
    )
    ap.add_argument(
        "--summary-json",
        default="",
        help="Optional path for a nightly sync summary JSON artifact",
    )
    ap.add_argument(
        "--ollama-url",
        default=None,
        help=(
            "Ollama base URL; overrides OLLAMA_URL, settings.ollama_url, then "
            "http://127.0.0.1:11434"
        ),
    )
    ap.add_argument(
        "--memo-diagnostics-path",
        default="",
        help=(
            "Optional host-readable news_memos.jsonl path used for memo coverage "
            "diagnostics. Does not change the Celery worker output path."
        ),
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Build target and Qdrant diff report without upserts, deletes, memos, or SQLite writes",
    )
    ap.add_argument(
        "--no-dispatch-memos",
        action="store_true",
        help="Disable asynchronous news memo extraction dispatch",
    )
    ap.add_argument(
        "--force-dispatch-memos",
        action="store_true",
        help="Dispatch memo extraction even for articles that already have persisted memos",
    )
    ap.add_argument(
        "--memo-max-article-chars",
        type=int,
        default=None,
        help=(
            "Maximum article characters sent to each memo task "
            "(default: NEWS_MEMO_MAX_ARTICLE_CHARS or 5000)"
        ),
    )
    ap.add_argument(
        "--wait-for-memos",
        action="store_true",
        help="Wait for dispatched news memo Celery tasks with a bounded timeout",
    )
    ap.add_argument(
        "--memo-wait-timeout-seconds",
        type=float,
        default=120.0,
        help="Maximum seconds to wait for memo task completion when --wait-for-memos is set",
    )
    ap.add_argument(
        "--memo-wait-poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval while waiting for memo task completion",
    )
    ap.add_argument(
        "--cleanup-stale",
        action="store_true",
        help="Delete Qdrant points outside the full eligible target set; never enabled by default",
    )
    ap.add_argument(
        "--qdrant-only",
        action="store_true",
        help="Run Qdrant projection repair only; disables memo dispatch and SQLite fallback rebuild",
    )
    ap.add_argument(
        "--target-contract-report",
        action="store_true",
        help="Include loader-eligible target counts and Qdrant diff details in the JSON output",
    )
    args = ap.parse_args()
    since = int(args.since_hours) if int(args.since_hours) > 0 else None
    if bool(args.dry_run) and bool(args.refresh_sqlite_fallback):
        ap.error("--dry-run cannot be combined with --refresh-sqlite-fallback")
    if bool(args.qdrant_only) and bool(args.refresh_sqlite_fallback):
        ap.error("--qdrant-only cannot be combined with --refresh-sqlite-fallback")
    if bool(args.cleanup_stale) and since is not None:
        ap.error("--cleanup-stale requires --since-hours 0 so the expected set is complete")
    if bool(args.wait_for_memos) and bool(args.no_dispatch_memos):
        ap.error("--wait-for-memos cannot be combined with --no-dispatch-memos")
    if bool(args.force_dispatch_memos) and bool(args.no_dispatch_memos):
        ap.error("--force-dispatch-memos cannot be combined with --no-dispatch-memos")
    if bool(args.wait_for_memos) and bool(args.qdrant_only):
        ap.error("--wait-for-memos cannot be combined with --qdrant-only")
    if bool(args.force_dispatch_memos) and bool(args.qdrant_only):
        ap.error("--force-dispatch-memos cannot be combined with --qdrant-only")
    if float(args.memo_wait_timeout_seconds) < 0:
        ap.error("--memo-wait-timeout-seconds must be >= 0")
    if float(args.memo_wait_poll_interval_seconds) <= 0:
        ap.error("--memo-wait-poll-interval-seconds must be > 0")
    try:
        memo_max_article_chars = resolve_news_memo_max_article_chars(args.memo_max_article_chars)
    except ValueError as exc:
        ap.error(str(exc))
    dispatch_memos = not bool(args.no_dispatch_memos)
    if bool(args.qdrant_only):
        dispatch_memos = False
    db_path = str(resolve_path(args.db_path))
    news_context_db = str(resolve_path(args.news_context_db))
    summary: Dict[str, Any] = {
        "generated_at_utc": now_utc_iso(),
        "paths": describe_news_artifact_paths(
            news_articles_db=Path(db_path),
            news_context_db=Path(news_context_db),
        ),
        "provider": latest_provider_run_summary(db_path),
        "qdrant_sync": {"status": "not_run"},
        "sqlite_fallback": {"status": "not_run"},
        "memo_extraction": {"status": "not_run"},
    }
    try:
        stats = sync_news_to_qdrant(
            db_path=db_path,
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            batch_size=int(args.batch_size),
            since_hours=since,
            dry_run=bool(args.dry_run),
            dispatch_memos=dispatch_memos,
            cleanup_stale=bool(args.cleanup_stale),
            qdrant_only=bool(args.qdrant_only),
            target_contract_report=bool(args.target_contract_report),
            ollama_url=args.ollama_url,
            memo_diagnostics_path=args.memo_diagnostics_path or None,
            memo_wait_for_completion=bool(args.wait_for_memos),
            memo_wait_timeout_seconds=float(args.memo_wait_timeout_seconds),
            memo_wait_poll_interval_seconds=float(args.memo_wait_poll_interval_seconds),
            memo_force_dispatch=bool(args.force_dispatch_memos),
            memo_max_article_chars=memo_max_article_chars,
        )
        sync_status = "dry_run" if bool(args.dry_run) else "success"
        summary["qdrant_sync"] = {"status": sync_status, **stats}
        summary["memo_extraction"] = stats.get("memo_extraction", {"status": "unknown"})
        provider_params = summary.get("provider", {}).get("params", {})
        window_start_utc = (
            str(provider_params.get("window_start_utc") or "")
            if isinstance(provider_params, dict)
            else ""
        )
        if bool(args.refresh_sqlite_fallback):
            summary["sqlite_fallback"] = refresh_news_sqlite_fallback(
                articles_db_path=db_path,
                context_db_path=news_context_db,
                lane=args.fallback_lane,
                window_start_utc=window_start_utc,
            )
        if args.summary_json:
            write_summary_json(args.summary_json, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        memo_status = str(summary.get("memo_extraction", {}).get("status") or "")
        if bool(args.wait_for_memos) and memo_status not in {"complete", "empty"}:
            logger.error(
                "news memo extraction wait did not complete: status=%s diagnostics=%s",
                memo_status,
                summary.get("memo_extraction", {}),
            )
            return 2
        return 0
    except Exception as exc:
        if summary.get("qdrant_sync", {}).get("status") == "not_run":
            summary["qdrant_sync"] = {"status": "error", "error": str(exc)}
        elif summary.get("sqlite_fallback", {}).get("status") == "not_run":
            summary["sqlite_fallback"] = {"status": "error", "error": str(exc)}
        else:
            summary["error"] = str(exc)
        if args.summary_json:
            write_summary_json(args.summary_json, summary)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
