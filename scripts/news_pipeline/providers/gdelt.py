from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Sequence

from ..models import ArticleCandidate
from ..utils import (
    canonicalize_url,
    normalize_space,
    now_utc_iso,
    parse_datetime_utc,
    parse_extra_fields,
    sha1_hex,
)
from .base import ParseResult, ProviderClient

DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _compact_utc(value: str) -> str:
    ts = parse_datetime_utc(value)
    if not ts:
        raise ValueError(f"invalid UTC timestamp: {value}")
    parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return parsed.strftime("%Y%m%d%H%M%S")


def _first_non_empty(*values: Any) -> str:
    for value in values:
        txt = normalize_space(value)
        if txt:
            return txt
    return ""


class GdeltProvider(ProviderClient):
    name = "gdelt"

    def __init__(
        self,
        *,
        api_url: str = DOC_API_URL,
        max_records: int = 250,
        request_timeout: float = 60.0,
        user_agent: str = "tenn-gdelt-ingest-v2/1.0",
        query_base: str = '("Australian Securities Exchange" OR ASX OR ".AX" OR "Australian shares" OR "Australian stocks" OR "ASX listed")',
        ticker_query_batch_size: int = 5,
        max_ticker_batches: int = 3,
        request_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
        max_retry_sleep_seconds: float = 120.0,
    ) -> None:
        self.api_url = str(api_url or DOC_API_URL).strip()
        self.max_records = int(max(1, min(250, int(max_records))))
        self.request_timeout = float(max(1.0, request_timeout))
        self.user_agent = str(user_agent or "tenn-gdelt-ingest-v2/1.0")
        self.query_base = str(query_base or "(ASX)").strip()
        self.ticker_query_batch_size = int(max(0, ticker_query_batch_size))
        self.max_ticker_batches = int(max(0, max_ticker_batches))
        self.request_retries = int(max(0, request_retries))
        self.retry_backoff_seconds = float(max(0.1, retry_backoff_seconds))
        self.max_retry_sleep_seconds = float(max(1.0, max_retry_sleep_seconds))
        self.last_fetch_diagnostics: Dict[str, Any] = {}

    @staticmethod
    def _is_query_length_error(exc: Exception) -> bool:
        if isinstance(exc, urllib.error.HTTPError) and int(getattr(exc, "code", 0) or 0) in (400, 414):
            return True
        msg = str(exc or "").strip().lower()
        return ("too short or too long" in msg) or ("query" in msg and "too long" in msg)

    @staticmethod
    def _ticker_clause(symbol: str) -> str:
        # Include ASX-specific variants so symbols like CBA/WBC are discovered as .AX listings.
        return f'({symbol} OR {symbol}.AX OR "ASX:{symbol}")'

    def _build_ticker_query(self, symbols: Sequence[str], *, include_query_base: bool = True) -> str:
        clean_symbols = [str(sym or "").strip().upper() for sym in symbols if str(sym or "").strip()]
        if not clean_symbols:
            return self.query_base if include_query_base else "(ASX)"
        clauses = [self._ticker_clause(sym) for sym in clean_symbols]
        joined = " OR ".join(clauses)
        if include_query_base:
            return f"({self.query_base}) AND ({joined})"
        return f"({joined})"

    def _build_query_plan(self, tickers: Sequence[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = [{"query": self.query_base, "symbols": [], "uses_base": True, "kind": "base"}]
        symbols = [str(sym or "").strip().upper() for sym in tickers if str(sym or "").strip()]
        if not symbols or self.ticker_query_batch_size <= 0 or self.max_ticker_batches <= 0:
            return out
        batch: List[str] = []
        batches = 0
        for sym in symbols:
            batch.append(sym)
            if len(batch) >= self.ticker_query_batch_size:
                out.append(
                    {
                        "query": self._build_ticker_query(batch, include_query_base=True),
                        "symbols": list(batch),
                        "uses_base": True,
                        "kind": "ticker_batch",
                    }
                )
                batch = []
                batches += 1
                if batches >= self.max_ticker_batches:
                    return out
        if batch and batches < self.max_ticker_batches:
            out.append(
                {
                    "query": self._build_ticker_query(batch, include_query_base=True),
                    "symbols": list(batch),
                    "uses_base": True,
                    "kind": "ticker_batch",
                }
            )
        return out

    def _request_json(self, url: str) -> Dict[str, Any]:
        max_attempts = self.request_retries + 1
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                method="GET",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                    raw_text = resp.read().decode("utf-8", errors="replace")
                raw_preview = normalize_space(raw_text)[:240]
                payload = json.loads(raw_text)
                if not isinstance(payload, dict):
                    return {}
                return payload
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code != 429 or attempt >= max_attempts - 1:
                    raise
                retry_after_raw = str(exc.headers.get("Retry-After", "")).strip() if exc.headers else ""
                try:
                    retry_after = float(retry_after_raw)
                except Exception:
                    retry_after = 0.0
                # Respect explicit server retry hints; otherwise use bounded exponential backoff.
                if retry_after > 0:
                    sleep_seconds = retry_after
                else:
                    sleep_seconds = min(self.retry_backoff_seconds * (2**attempt), self.max_retry_sleep_seconds)
                time.sleep(max(0.1, sleep_seconds))
                continue
            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    message = f"GDELT returned non-JSON payload: {exc}"
                    if raw_preview:
                        message += f" | preview={raw_preview!r}"
                    raise RuntimeError(message) from exc
                time.sleep(max(0.1, min(self.retry_backoff_seconds * (2**attempt), self.max_retry_sleep_seconds)))
                continue
            except Exception as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    raise
                time.sleep(max(0.1, min(self.retry_backoff_seconds * (2**attempt), self.max_retry_sleep_seconds)))
        if last_error is not None:
            raise last_error
        return {}

    def _build_query_list(self, tickers: Sequence[str]) -> List[str]:
        return [str(row.get("query") or "").strip() for row in self._build_query_plan(tickers) if str(row.get("query") or "").strip()]

    def fetch_window(self, *, window_start_utc: str, window_end_utc: str, tickers: Sequence[str]) -> List[Dict[str, Any]]:
        params_base = {
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(self.max_records),
            "sort": "datedesc",
            "startdatetime": _compact_utc(window_start_utc),
            "enddatetime": _compact_utc(window_end_utc),
        }
        rows: List[Dict[str, Any]] = []
        dedupe = set()
        last_error: Exception | None = None
        query_plan = self._build_query_plan(tickers)
        pending_queries: List[Dict[str, Any]] = [dict(row) for row in query_plan]
        query_errors: List[Dict[str, str]] = []
        ticker_query_errors = 0
        seen_queries: set[str] = set()
        queries_attempted = 0
        queries_succeeded = 0
        fallback_splits = 0
        fallback_single_symbol = 0
        fallback_base_simple = 0
        while pending_queries:
            row = pending_queries.pop(0)
            query = str(row.get("query") or "").strip()
            if not query or query in seen_queries:
                continue
            seen_queries.add(query)
            symbols = [str(sym or "").strip().upper() for sym in (row.get("symbols") or []) if str(sym or "").strip()]
            params = dict(params_base)
            params["query"] = query
            url = f"{self.api_url.rstrip('?')}?{urllib.parse.urlencode(params)}"
            queries_attempted += 1
            try:
                payload = self._request_json(url)
                queries_succeeded += 1
            except Exception as exc:
                last_error = exc
                query_errors.append({"query": query[:280], "error": str(exc)})
                if symbols:
                    ticker_query_errors += 1
                if self._is_query_length_error(exc):
                    if len(symbols) > 1:
                        midpoint = max(1, len(symbols) // 2)
                        left = symbols[:midpoint]
                        right = symbols[midpoint:]
                        for subset in (left, right):
                            if not subset:
                                continue
                            pending_queries.append(
                                {
                                    "query": self._build_ticker_query(subset, include_query_base=True),
                                    "symbols": subset,
                                    "uses_base": True,
                                    "kind": "ticker_batch_split",
                                }
                            )
                        fallback_splits += 1
                        continue
                    if len(symbols) == 1 and bool(row.get("uses_base", True)):
                        pending_queries.append(
                            {
                                "query": self._build_ticker_query(symbols, include_query_base=False),
                                "symbols": symbols,
                                "uses_base": False,
                                "kind": "ticker_single_symbol_fallback",
                            }
                        )
                        fallback_single_symbol += 1
                        continue
                    if not symbols and query != '(ASX OR "Australian Securities Exchange")':
                        pending_queries.append(
                            {
                                "query": '(ASX OR "Australian Securities Exchange")',
                                "symbols": [],
                                "uses_base": False,
                                "kind": "base_query_fallback",
                            }
                        )
                        fallback_base_simple += 1
                        continue
                continue
            articles = payload.get("articles")
            if not isinstance(articles, list):
                continue
            for item in articles:
                if not isinstance(item, dict):
                    continue
                signature = (
                    str(item.get("url") or "").strip(),
                    str(item.get("title") or "").strip().lower(),
                    str(item.get("seendate") or item.get("date") or "").strip(),
                )
                if signature in dedupe:
                    continue
                dedupe.add(signature)
                enriched = dict(item)
                enriched["_gdelt_query"] = query
                rows.append(enriched)
        self.last_fetch_diagnostics = {
            "query_plan_size": len(query_plan),
            "queries_attempted": int(queries_attempted),
            "queries_succeeded": int(queries_succeeded),
            "query_errors": int(len(query_errors)),
            "ticker_query_errors": int(ticker_query_errors),
            "fallback_splits": int(fallback_splits),
            "fallback_single_symbol": int(fallback_single_symbol),
            "fallback_base_simple": int(fallback_base_simple),
            "rows_returned": int(len(rows)),
        }
        if query_errors:
            self.last_fetch_diagnostics["query_error_samples"] = query_errors[:5]
        if not rows and last_error is not None and (queries_succeeded <= 0 or ticker_query_errors > 0):
            message = (
                "GDELT fetch failed after "
                f"{queries_attempted} query attempts ({len(query_errors)} errors, {queries_succeeded} successes): "
                f"{last_error}"
            )
            raise RuntimeError(message) from last_error
        return rows

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        extra = parse_extra_fields(item.get("extra_fields"))
        title = _first_non_empty(item.get("title"), item.get("headline"), extra.get("title"), extra.get("headline"))
        canonical_url = canonicalize_url(
            _first_non_empty(
                item.get("url"),
                item.get("link"),
                extra.get("url"),
                extra.get("link"),
                extra.get("article_url"),
            )
        )
        if not title and not canonical_url:
            return ParseResult(candidate=None, reject_reason="missing_identity")

        description = _first_non_empty(
            item.get("snippet"),
            item.get("context"),
            item.get("description"),
            item.get("summary"),
            extra.get("description"),
        )
        body = _first_non_empty(
            item.get("text"),
            item.get("content"),
            item.get("body"),
            extra.get("text"),
            extra.get("content"),
            description,
        )
        source_name = _first_non_empty(
            item.get("domain"),
            item.get("source"),
            item.get("source_name"),
            item.get("publisher"),
            extra.get("domain"),
            extra.get("source"),
        )
        if not source_name and canonical_url:
            parsed = urllib.parse.urlsplit(canonical_url)
            source_name = str(parsed.hostname or "").lower()
            if source_name.startswith("www."):
                source_name = source_name[4:]

        language = _first_non_empty(item.get("language"), extra.get("language"))
        published_raw = _first_non_empty(
            item.get("published_at"),
            item.get("seendate"),
            item.get("date"),
            extra.get("published_at"),
            extra.get("seendate_raw"),
            extra.get("seendate"),
            extra.get("date"),
        )
        if not published_raw:
            return ParseResult(
                candidate=None,
                reject_reason="missing_published_at",
                diagnostics={"provider_published_at_raw": "", "title": title, "url": canonical_url},
            )
        published_at_utc = parse_datetime_utc(published_raw)
        if not published_at_utc:
            return ParseResult(
                candidate=None,
                reject_reason="invalid_published_at",
                diagnostics={"provider_published_at_raw": published_raw, "title": title, "url": canonical_url},
            )
        provider_item_id = _first_non_empty(
            item.get("id"),
            item.get("guid"),
            item.get("article_id"),
            extra.get("id"),
            extra.get("guid"),
        )
        if not provider_item_id:
            provider_item_id = "gdelt_" + sha1_hex(f"{canonical_url}|{title}|{published_at_utc}")[:24]

        candidate = ArticleCandidate(
            provider=self.name,
            provider_item_id=provider_item_id,
            canonical_url=canonical_url,
            title=title,
            description=description,
            body=body,
            source_name=source_name or "gdelt",
            language=language,
            published_at_utc=published_at_utc,
            fetched_at_utc=parse_datetime_utc(fetched_at_utc) or now_utc_iso(),
            provider_published_at_raw=published_raw,
            raw_payload=item,
        )
        return ParseResult(candidate=candidate)
