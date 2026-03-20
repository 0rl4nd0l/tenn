from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path
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


def _first_non_empty(*values: Any) -> str:
    for value in values:
        txt = normalize_space(value)
        if txt:
            return txt
    return ""


_LANG_NAME_TO_ISO: Dict[str, str] = {
    "english": "en",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "dutch": "nl",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "arabic": "ar",
    "russian": "ru",
}


def _normalize_language(raw: str) -> str:
    """Normalize language tag to ISO 639-1 lowercase (e.g. 'English' -> 'en', 'EN' -> 'en')."""
    txt = str(raw or "").strip().lower()
    if not txt:
        return ""
    if txt in _LANG_NAME_TO_ISO:
        return _LANG_NAME_TO_ISO[txt]
    # Already looks like a valid 2-char code.
    if len(txt) == 2 and txt.isalpha():
        return txt
    # Try stripping region suffix (e.g. 'en-US' -> 'en').
    if "-" in txt:
        prefix = txt.split("-", 1)[0]
        if len(prefix) == 2 and prefix.isalpha():
            return prefix
    return txt


def _utc_date(value: str) -> str:
    ts = parse_datetime_utc(value)
    if not ts:
        raise ValueError(f"invalid UTC timestamp: {value}")
    return ts.split("T", 1)[0]


class EodhdProvider(ProviderClient):
    name = "eodhd"
    max_limit = 1000

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "https://eodhd.com/api/news",
        request_timeout: float = 30.0,
        user_agent: str = "tenn-eodhd-ingest-v2/1.0",
        capture_dir: Path | None = None,
        require_capture_contract: bool = True,
        allow_live_without_captures: bool = False,
        market_limit: int = 1000,
        symbol_limit: int = 1000,
        symbol_suffix: str = ".AU",
        symbols_only: bool = False,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url or "").strip().rstrip("?")
        self.request_timeout = float(max(1.0, request_timeout))
        self.user_agent = str(user_agent or "tenn-eodhd-ingest-v2/1.0")
        self.capture_dir = Path(capture_dir).expanduser().resolve() if capture_dir is not None else None
        self.require_capture_contract = bool(require_capture_contract)
        self.allow_live_without_captures = bool(allow_live_without_captures)
        self.market_limit = int(max(1, market_limit))
        self.symbol_limit = int(max(1, symbol_limit))
        self.symbol_suffix = str(symbol_suffix or ".AU")
        self.symbols_only = bool(symbols_only)

    def _request_json(self, url: str) -> Any:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def _load_capture_file(self, path: Path) -> List[Dict[str, Any]]:
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            out: List[Dict[str, Any]] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if not text:
                    continue
                try:
                    parsed = json.loads(text)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    out.append(parsed)
            return out
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("items", "news", "data", "articles", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    def _capture_patterns(self, kind: str, ticker: str) -> List[str]:
        if kind == "market":
            return [
                "market_news*.json",
                "market-news*.json",
                "market_news*.jsonl",
                "market-news*.jsonl",
            ]
        symbol = str(ticker or "").strip().upper()
        return [
            f"symbol_{symbol}*.json",
            f"symbol_{symbol}*.jsonl",
            f"symbol-news-{symbol}*.json",
            f"symbol-news-{symbol}*.jsonl",
        ]

    def _load_captures(
        self,
        *,
        kind: str,
        ticker: str,
        window_start_utc: str,
        window_end_utc: str,
    ) -> List[Dict[str, Any]]:
        if self.capture_dir is None or not self.capture_dir.exists() or not self.capture_dir.is_dir():
            return []
        start = parse_datetime_utc(window_start_utc)
        end = parse_datetime_utc(window_end_utc)
        if not start or not end:
            return []
        start_dt = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = dt.datetime.fromisoformat(end.replace("Z", "+00:00"))

        files = []
        for pattern in self._capture_patterns(kind, ticker):
            files.extend(sorted(self.capture_dir.glob(pattern)))
        out: List[Dict[str, Any]] = []
        for file_path in files:
            for item in self._load_capture_file(file_path):
                published_raw = _first_non_empty(
                    item.get("published_at"),
                    item.get("published"),
                    item.get("date"),
                    item.get("timestamp"),
                    item.get("datetime"),
                )
                published = parse_datetime_utc(published_raw)
                if published:
                    ts = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if ts < start_dt or ts > end_dt:
                        continue
                enriched = dict(item)
                enriched["_eodhd_capture_file"] = str(file_path)
                enriched["_eodhd_kind"] = kind
                if ticker:
                    enriched["_eodhd_ticker"] = ticker
                out.append(enriched)
        return out

    def _build_live_url(
        self,
        *,
        ticker: str,
        window_start_utc: str,
        window_end_utc: str,
        limit: int,
        offset: int = 0,
    ) -> str:
        params = {
            "api_token": self.api_key,
            "fmt": "json",
            "limit": str(int(max(1, min(limit, self.max_limit)))),
            "from": _utc_date(window_start_utc),
            "to": _utc_date(window_end_utc),
        }
        if int(offset) > 0:
            params["offset"] = str(int(offset))
        if ticker:
            symbol = str(ticker).upper()
            params["s"] = symbol if symbol.endswith(self.symbol_suffix) else f"{symbol}{self.symbol_suffix}"
        return f"{self.base_url}?{urllib.parse.urlencode(params)}"

    def _parse_payload_rows(self, payload: Any, *, ticker: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]]
        if isinstance(payload, list):
            rows = [row for row in payload if isinstance(row, dict)]
        elif isinstance(payload, dict):
            rows = []
            for key in ("items", "news", "data", "articles", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    rows = [row for row in value if isinstance(row, dict)]
                    break
            if not rows:
                rows = [payload]
        else:
            rows = []
        for row in rows:
            row["_eodhd_kind"] = "symbol" if ticker else "market"
            if ticker:
                row["_eodhd_ticker"] = ticker
        return rows

    def _fetch_live(self, *, ticker: str, window_start_utc: str, window_end_utc: str, limit: int) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("EODHD API key is missing (expected env EODHD_API_KEY).")
        page_limit = int(max(1, min(limit, self.max_limit)))
        offset = 0
        seen = set()
        all_rows: List[Dict[str, Any]] = []
        while True:
            url = self._build_live_url(
                ticker=ticker,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                limit=page_limit,
                offset=offset,
            )
            payload = self._request_json(url)
            rows = self._parse_payload_rows(payload, ticker=ticker)
            fresh_rows = []
            for row in rows:
                signature = (
                    str(row.get("id") or row.get("news_id") or "").strip(),
                    str(row.get("url") or row.get("link") or "").strip(),
                    str(row.get("title") or row.get("headline") or "").strip().lower(),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                fresh_rows.append(row)
            all_rows.extend(fresh_rows)
            if len(rows) < page_limit or not fresh_rows:
                break
            offset += page_limit
        return all_rows

    def fetch_market_window(self, *, window_start_utc: str, window_end_utc: str) -> List[Dict[str, Any]]:
        rows = self._load_captures(
            kind="market",
            ticker="",
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
        )
        if rows:
            return rows
        if self.require_capture_contract and not self.allow_live_without_captures:
            capture_path = str(self.capture_dir) if self.capture_dir is not None else "<missing>"
            raise RuntimeError(
                "EODHD capture contract not found. Add JSON/JSONL captures under "
                f"{capture_path} or use --allow-missing-eodhd-captures."
            )
        return self._fetch_live(
            ticker="",
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            limit=self.market_limit,
        )

    def fetch_symbol_window(self, *, ticker: str, window_start_utc: str, window_end_utc: str) -> List[Dict[str, Any]]:
        rows = self._load_captures(
            kind="symbol",
            ticker=str(ticker),
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
        )
        if rows:
            return rows
        if self.require_capture_contract and not self.allow_live_without_captures:
            capture_path = str(self.capture_dir) if self.capture_dir is not None else "<missing>"
            raise RuntimeError(
                "EODHD capture contract not found. Add JSON/JSONL captures under "
                f"{capture_path} or use --allow-missing-eodhd-captures."
            )
        return self._fetch_live(
            ticker=str(ticker),
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            limit=self.symbol_limit,
        )

    def fetch_window(self, *, window_start_utc: str, window_end_utc: str, tickers: Sequence[str]) -> List[Dict[str, Any]]:
        all_rows: List[Dict[str, Any]] = []
        if not self.symbols_only:
            all_rows.extend(self.fetch_market_window(window_start_utc=window_start_utc, window_end_utc=window_end_utc))
        for ticker in tickers:
            all_rows.extend(
                self.fetch_symbol_window(
                    ticker=str(ticker),
                    window_start_utc=window_start_utc,
                    window_end_utc=window_end_utc,
                )
            )
        dedupe = set()
        unique_rows: List[Dict[str, Any]] = []
        for row in all_rows:
            signature = (
                str(row.get("id") or row.get("news_id") or "").strip(),
                str(row.get("url") or row.get("link") or "").strip(),
                str(row.get("title") or row.get("headline") or "").strip().lower(),
            )
            if signature in dedupe:
                continue
            dedupe.add(signature)
            unique_rows.append(row)
        return unique_rows

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        extra = parse_extra_fields(item.get("extra_fields"))
        canonical_url = canonicalize_url(
            _first_non_empty(
                item.get("link"),
                item.get("url"),
                item.get("news_url"),
                extra.get("link"),
                extra.get("url"),
            )
        )
        title = _first_non_empty(item.get("title"), item.get("headline"), item.get("name"), extra.get("title"))
        if not canonical_url and not title:
            return ParseResult(candidate=None, reject_reason="missing_identity")

        description = _first_non_empty(
            item.get("description"),
            item.get("snippet"),
            item.get("summary"),
            extra.get("description"),
        )
        body = _first_non_empty(
            item.get("content"),
            item.get("text"),
            item.get("body"),
            extra.get("content"),
            extra.get("text"),
            description,
        )
        source_name = _first_non_empty(
            item.get("source"),
            item.get("source_name"),
            item.get("site"),
            item.get("publisher"),
            extra.get("source"),
            extra.get("site"),
        )
        language = _normalize_language(_first_non_empty(item.get("language"), item.get("lang"), extra.get("language")))

        published_raw = _first_non_empty(
            item.get("published_at"),
            item.get("published"),
            item.get("date"),
            item.get("datetime"),
            item.get("timestamp"),
            extra.get("published_at"),
            extra.get("published"),
            extra.get("date"),
            extra.get("timestamp"),
        )
        if not published_raw:
            return ParseResult(
                candidate=None,
                reject_reason="missing_published_at",
                diagnostics={"title": title, "url": canonical_url},
            )
        published_at_utc = parse_datetime_utc(published_raw)
        if not published_at_utc:
            return ParseResult(
                candidate=None,
                reject_reason="invalid_published_at",
                diagnostics={"title": title, "url": canonical_url, "provider_published_at_raw": published_raw},
            )

        provider_item_id = _first_non_empty(item.get("id"), item.get("news_id"), item.get("uid"), extra.get("id"))
        if not provider_item_id:
            provider_item_id = "eodhd_" + sha1_hex(f"{canonical_url}|{title}|{published_at_utc}")[:24]

        candidate = ArticleCandidate(
            provider=self.name,
            provider_item_id=provider_item_id,
            canonical_url=canonical_url,
            title=title,
            description=description,
            body=body,
            source_name=source_name or "eodhd",
            language=language,
            published_at_utc=published_at_utc,
            fetched_at_utc=parse_datetime_utc(fetched_at_utc) or now_utc_iso(),
            provider_published_at_raw=published_raw,
            raw_payload=item,
        )
        return ParseResult(candidate=candidate)
