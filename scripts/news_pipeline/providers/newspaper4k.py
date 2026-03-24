"""Newspaper4k provider — full article scraping via collect_au_finance_news."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..models import ArticleCandidate
from ..utils import canonicalize_url, normalize_space, parse_datetime_utc, sha1_hex
from .base import ParseResult, ProviderClient

INTEGRATION_DIR = Path(__file__).resolve().parents[3] / "integrations" / "newspaper4k_au"
DEFAULT_SOURCES_FILE = INTEGRATION_DIR / "sources_au_finance.txt"

# Lazy-import to avoid hard dependency when other providers are used.
_collector = None


def _import_collector():
    global _collector
    if _collector is not None:
        return _collector
    integration_path = str(INTEGRATION_DIR)
    if integration_path not in sys.path:
        sys.path.insert(0, integration_path)
    import collect_au_finance_news as mod
    _collector = mod
    return mod


class Newspaper4kProvider(ProviderClient):
    name = "newspaper4k"

    def __init__(
        self,
        *,
        sources_file: Path | None = None,
        max_articles_per_source: int = 30,
        max_total_articles: int = 300,
        min_text_chars: int = 200,
        min_keyword_hits: int = 0,
        request_timeout_seconds: int = 20,
        sleep_seconds: float = 0.5,
        finance_url_gate: bool = False,
        raw_html_dir: Path | None = None,
        http_cookie: str = "",
    ) -> None:
        self.sources_file = Path(sources_file or DEFAULT_SOURCES_FILE).expanduser().resolve()
        self.max_articles_per_source = int(max(1, max_articles_per_source))
        self.max_total_articles = int(max(1, max_total_articles))
        self.min_text_chars = int(max(1, min_text_chars))
        self.min_keyword_hits = int(max(0, min_keyword_hits))
        self.request_timeout_seconds = int(max(1, request_timeout_seconds))
        self.sleep_seconds = float(max(0, sleep_seconds))
        self.finance_url_gate = bool(finance_url_gate)
        self.raw_html_dir = Path(raw_html_dir).expanduser().resolve() if raw_html_dir else None
        self.http_cookie = str(http_cookie or "")

    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        import time

        collector = _import_collector()
        sources = collector.parse_sources(self.sources_file)
        if not sources:
            return []

        start_ts = parse_datetime_utc(window_start_utc)
        if start_ts:
            recent_cutoff = dt.datetime.fromisoformat(
                start_ts.replace("Z", "+00:00")
            ).astimezone(dt.timezone.utc)
        else:
            recent_cutoff = dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=96)

        keywords = collector.parse_keywords(None, "")
        finance_include = list(collector.DEFAULT_FINANCE_URL_INCLUDE_TOKENS)
        finance_exclude = list(collector.DEFAULT_FINANCE_URL_EXCLUDE_TOKENS)

        rows: List[Dict[str, Any]] = []
        for index, spec in enumerate(sources):
            try:
                articles, stats = collector.extract_from_source(
                    source=spec,
                    max_articles=self.max_articles_per_source,
                    min_text_chars=self.min_text_chars,
                    min_keyword_hits=self.min_keyword_hits,
                    request_timeout_seconds=self.request_timeout_seconds,
                    finance_url_gate=self.finance_url_gate,
                    finance_url_include_tokens=finance_include,
                    finance_url_exclude_tokens=finance_exclude,
                    finance_url_gate_exempt_domains=[],
                    article_url_gate_exempt_domains=[],
                    keywords=keywords,
                    recent_cutoff=recent_cutoff,
                    raw_html_dir=self.raw_html_dir,
                    http_cookie=self.http_cookie,
                )
            except Exception as exc:
                print(f"[newspaper4k] source {spec.url} error: {exc}", flush=True)
                continue

            kept = 0
            for article in articles:
                rows.append({
                    "url": article.article_url,
                    "title": article.title,
                    "body": article.body,
                    "source_name": article.source_name,
                    "language": article.language or "en",
                    "published_at": (
                        collector.iso_utc(article.published_at) if article.published_at else ""
                    ),
                    "authors": article.authors,
                    "keyword_hits": article.keyword_hits,
                    "body_source": article.body_source,
                    "body_lengths": article.body_lengths,
                    "source_url": article.source_url,
                })
                kept += 1
                if len(rows) >= self.max_total_articles:
                    break

            print(
                f"[newspaper4k] {spec.url} seen={stats.get('source_articles_seen', 0)} "
                f"kept={kept} errors={stats.get('download_errors', 0)}",
                flush=True,
            )
            if len(rows) >= self.max_total_articles:
                break
            if index < len(sources) - 1 and self.sleep_seconds > 0:
                time.sleep(self.sleep_seconds)

        return rows

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        title = normalize_space(item.get("title"))
        canonical_url = canonicalize_url(normalize_space(item.get("url")))
        if not title and not canonical_url:
            return ParseResult(candidate=None, reject_reason="missing_identity")

        body = normalize_space(item.get("body") or "")
        if not body:
            return ParseResult(candidate=None, reject_reason="missing_text")

        published_raw = normalize_space(item.get("published_at") or "")
        published_at_utc = parse_datetime_utc(published_raw) if published_raw else ""
        if not published_at_utc:
            # Use fetched_at as fallback if no publish date available.
            published_at_utc = parse_datetime_utc(fetched_at_utc) or ""
        if not published_at_utc:
            return ParseResult(
                candidate=None,
                reject_reason="missing_published_at",
                diagnostics={"title": title, "url": canonical_url},
            )

        source_name = normalize_space(item.get("source_name") or "newspaper4k")
        language = normalize_space(item.get("language") or "en")
        provider_item_id = "n4k_" + sha1_hex(f"{canonical_url}|{title}|{published_at_utc}")[:24]

        candidate = ArticleCandidate(
            provider=self.name,
            provider_item_id=provider_item_id,
            canonical_url=canonical_url,
            title=title,
            description=normalize_space(item.get("description") or body[:300]),
            body=body,
            source_name=source_name,
            language=language,
            published_at_utc=published_at_utc,
            fetched_at_utc=parse_datetime_utc(fetched_at_utc) or "",
            provider_published_at_raw=published_raw,
            raw_payload=item,
        )
        return ParseResult(candidate=candidate)
