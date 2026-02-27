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
        ticker_query_batch_size: int = 10,
        max_ticker_batches: int = 5,
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
        out = [self.query_base]
        symbols = [str(sym or "").strip().upper() for sym in tickers if str(sym or "").strip()]
        if not symbols or self.ticker_query_batch_size <= 0 or self.max_ticker_batches <= 0:
            return out

        def _ticker_clause(symbol: str) -> str:
            # Include ASX-specific variants so symbols like CBA/WBC are discovered as .AX listings.
            return f'({symbol} OR {symbol}.AX OR "ASX:{symbol}")'

        batch: List[str] = []
        batches = 0
        for sym in symbols:
            batch.append(_ticker_clause(sym))
            if len(batch) >= self.ticker_query_batch_size:
                query = f"({self.query_base}) AND ({' OR '.join(batch)})"
                out.append(query)
                batch = []
                batches += 1
                if batches >= self.max_ticker_batches:
                    return out
        if batch and batches < self.max_ticker_batches:
            query = f"({self.query_base}) AND ({' OR '.join(batch)})"
            out.append(query)
        return out

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
        for query in self._build_query_list(tickers):
            params = dict(params_base)
            params["query"] = query
            url = f"{self.api_url.rstrip('?')}?{urllib.parse.urlencode(params)}"
            try:
                payload = self._request_json(url)
            except Exception as exc:
                last_error = exc
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
        if not rows and last_error is not None:
            raise last_error
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
