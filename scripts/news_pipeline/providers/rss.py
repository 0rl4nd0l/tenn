"""RSS provider wrapping the existing ingest_asx_rss_headlines implementation."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..models import ArticleCandidate
from ..utils import canonicalize_url, normalize_space, now_utc_iso, parse_datetime_utc, sha1_hex
from .base import ParseResult, ProviderClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DEFAULT_FEEDS_FILE = (
    REPO_ROOT / "integrations" / "newspaper4k_au" / "sources_au_finance_rss_only.txt"
)
DEFAULT_ASX_TICKERS = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_IDENTITY_MAP = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"


class RssProvider(ProviderClient):
    name = "rss"

    def __init__(
        self,
        *,
        feeds_file: Path | None = None,
        asx_tickers_file: Path | None = None,
        identity_map_path: Path | None = None,
        request_timeout: float = 15.0,
        http_retries: int = 2,
        user_agent: str = "tenn-asx-rss-ingest/1.0",
    ) -> None:
        self.feeds_file = Path(feeds_file).expanduser().resolve() if feeds_file else DEFAULT_FEEDS_FILE
        self.asx_tickers_file = (
            Path(asx_tickers_file).expanduser().resolve() if asx_tickers_file else DEFAULT_ASX_TICKERS
        )
        self.identity_map_path = (
            Path(identity_map_path).expanduser().resolve() if identity_map_path else DEFAULT_IDENTITY_MAP
        )
        self.request_timeout = float(max(1.0, request_timeout))
        self.http_retries = int(max(0, http_retries))
        self.user_agent = str(user_agent or "tenn-asx-rss-ingest/1.0")

    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        """Fetch RSS feeds and return raw row dicts compatible with parse_item."""
        import ingest_asx_rss_headlines as rss_ingest  # noqa: F401

        feed_targets = rss_ingest.load_feed_targets(
            feed_urls=[],
            feeds_file=self.feeds_file if self.feeds_file.exists() else None,
        )
        if not feed_targets:
            return []

        rows, _stats = rss_ingest.build_rss_rows(
            feed_targets=feed_targets,
            asx_tickers_file=self.asx_tickers_file,
            identity_map_path=self.identity_map_path,
            ticker_token_keywords=None,
            collision_phrase_map={},
            corpus="news_rss_v2",
            topic="asx_rss_headline",
            request_timeout=self.request_timeout,
            http_retries=self.http_retries,
            user_agent=self.user_agent,
        )
        return rows

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        title = normalize_space(item.get("title") or item.get("headline"))
        canonical_url = canonicalize_url(normalize_space(item.get("url") or item.get("link")))
        if not title and not canonical_url:
            return ParseResult(candidate=None, reject_reason="missing_identity")

        published_raw = normalize_space(item.get("published_at") or item.get("date") or "")
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

        description = normalize_space(item.get("summary") or item.get("description") or "")
        body = normalize_space(item.get("text") or item.get("body") or description or title)
        source_name = normalize_space(item.get("source") or item.get("source_domain") or "rss")

        provider_item_id = normalize_space(item.get("id") or item.get("guid") or "")
        if not provider_item_id:
            provider_item_id = "rss_" + sha1_hex(f"{canonical_url}|{title}|{published_at_utc}")[:24]

        candidate = ArticleCandidate(
            provider=self.name,
            provider_item_id=provider_item_id,
            canonical_url=canonical_url,
            title=title,
            description=description,
            body=body,
            source_name=source_name,
            language="en",
            published_at_utc=published_at_utc,
            fetched_at_utc=parse_datetime_utc(fetched_at_utc) or now_utc_iso(),
            provider_published_at_raw=published_raw,
            raw_payload=item,
        )
        return ParseResult(candidate=candidate)
