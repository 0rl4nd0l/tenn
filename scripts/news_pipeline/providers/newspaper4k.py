"""Newspaper4k provider — full article scraping via collect_au_finance_news."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from ..models import ArticleCandidate
from ..utils import canonicalize_url, normalize_space, parse_datetime_utc, sha1_hex
from .base import ParseResult, ProviderClient

INTEGRATION_DIR = Path(__file__).resolve().parents[3] / "integrations" / "newspaper4k_au"
NEWSPAPER4K_SOURCE_PROFILES = {
    "daily": INTEGRATION_DIR / "sources_au_finance_rss_only.txt",
    "broad": INTEGRATION_DIR / "sources_all_au_finance.txt",
}
DEFAULT_SOURCE_PROFILE = "daily"
DEFAULT_SOURCES_FILE = NEWSPAPER4K_SOURCE_PROFILES[DEFAULT_SOURCE_PROFILE]

# Domains whose URL shapes don't match the generic article-URL heuristics
# (e.g. 2-segment paths like /news/slug) but are known article publishers.
# Exempted from the looks_like_article_url() gate in collect_au_finance_news.
ARTICLE_GATE_EXEMPT_DOMAINS = [
    "stockhead.com.au",
    "stockhead.com",
    "capitalbrief.com",
    "finance.yahoo.com",
    "au.finance.yahoo.com",
    "kalkinemedia.com",
    "kalkinemedia.com.au",
    "benzinga.com",
    "livewiremarkets.com",
    "marketindex.com.au",
    "skynews.com.au",
    "theaustralian.com.au",
]

# Domains that require JS rendering for article discovery and/or extraction.
DEFAULT_PLAYWRIGHT_DOMAINS = [
    "stockhead.com.au",
    "skynews.com.au",
    "capitalbrief.com",
    "finance.yahoo.com",
    "benzinga.com",
    "marketindex.com.au",
    "livewiremarkets.com",
]

# Lazy-import to avoid hard dependency when other providers are used.
_collector = None


def resolve_sources_file(
    *, source_profile: str = DEFAULT_SOURCE_PROFILE, sources_file: Path | None = None
) -> Path:
    if sources_file is not None:
        return Path(sources_file).expanduser().resolve()
    profile = str(source_profile or DEFAULT_SOURCE_PROFILE).strip().lower()
    try:
        return NEWSPAPER4K_SOURCE_PROFILES[profile].expanduser().resolve()
    except KeyError as exc:
        choices = ", ".join(sorted(NEWSPAPER4K_SOURCE_PROFILES))
        raise ValueError(
            f"Unsupported newspaper4k source profile {source_profile!r}; "
            f"expected one of: {choices}"
        ) from exc


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
        source_profile: str = DEFAULT_SOURCE_PROFILE,
        sources_file: Path | None = None,
        max_articles_per_source: int = 15,
        max_total_articles: int = 60,
        min_text_chars: int = 200,
        min_keyword_hits: int = 0,
        request_timeout_seconds: int = 10,
        sleep_seconds: float = 0.5,
        finance_url_gate: bool = False,
        raw_html_dir: Path | None = None,
        http_cookie: str = "",
        playwright_domains: Sequence[str] | None = DEFAULT_PLAYWRIGHT_DOMAINS,
        no_playwright: bool | None = None,
    ) -> None:
        self.source_profile = (
            str(source_profile or DEFAULT_SOURCE_PROFILE).strip().lower()
        )
        self.sources_file = resolve_sources_file(
            source_profile=self.source_profile, sources_file=sources_file
        )
        self.max_articles_per_source = int(max(1, max_articles_per_source))
        self.max_total_articles = int(max(1, max_total_articles))
        self.min_text_chars = int(max(1, min_text_chars))
        self.min_keyword_hits = int(max(0, min_keyword_hits))
        self.request_timeout_seconds = int(max(1, request_timeout_seconds))
        self.sleep_seconds = float(max(0, sleep_seconds))
        self.finance_url_gate = bool(finance_url_gate)
        self.raw_html_dir = Path(raw_html_dir).expanduser().resolve() if raw_html_dir else None
        self.http_cookie = str(http_cookie or "")
        self.no_playwright = (
            self.source_profile == DEFAULT_SOURCE_PROFILE and sources_file is None
            if no_playwright is None
            else bool(no_playwright)
        )
        if self.no_playwright:
            self.playwright_domains: list[str] | None = None
        else:
            self.playwright_domains = list(playwright_domains) if playwright_domains else None
        setattr(
            self,
            "_tenn_provider_settings",
            {
                "provider": self.name,
                "source_profile": self.source_profile,
                "sources_file": str(self.sources_file),
                "max_articles_per_source": int(self.max_articles_per_source),
                "max_total_articles": int(self.max_total_articles),
                "request_timeout_seconds": int(self.request_timeout_seconds),
                "sleep_seconds": float(self.sleep_seconds),
                "no_playwright": bool(self.no_playwright),
            },
        )

    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for batch in self.fetch_window_batches(
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            tickers=tickers,
        ):
            rows.extend(batch)
        return rows

    def fetch_window_batches(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> Iterable[List[Dict[str, Any]]]:
        import time

        collector = _import_collector()
        sources = collector.parse_sources(self.sources_file)
        if not sources:
            return

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

        total_rows = 0
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
                    article_url_gate_exempt_domains=ARTICLE_GATE_EXEMPT_DOMAINS,
                    keywords=keywords,
                    recent_cutoff=recent_cutoff,
                    raw_html_dir=self.raw_html_dir,
                    http_cookie=self.http_cookie,
                    playwright_domains=self.playwright_domains,
                )
            except Exception as exc:
                print(f"[newspaper4k] source {spec.url} error: {exc}", flush=True)
                continue

            source_rows: List[Dict[str, Any]] = []
            kept = 0
            for article in articles:
                source_rows.append(
                    {
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
                    }
                )
                kept += 1
                total_rows += 1
                if total_rows >= self.max_total_articles:
                    break

            print(
                f"[newspaper4k] {spec.url} seen={stats.get('source_articles_seen', 0)} "
                f"kept={kept} errors={stats.get('download_errors', 0)}",
                flush=True,
            )
            if source_rows:
                yield source_rows
            if total_rows >= self.max_total_articles:
                break
            if index < len(sources) - 1 and self.sleep_seconds > 0:
                time.sleep(self.sleep_seconds)

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
