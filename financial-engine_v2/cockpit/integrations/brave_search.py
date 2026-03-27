"""Brave Search API client with DuckDuckGo fallback.

Provides structured web search results for the cockpit agent loop.
Falls back to WebFetcher (DuckDuckGo) when BRAVE_SEARCH_API_KEY is
absent or when the Brave API returns an error.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_COUNT = 5
_TIMEOUT = 15.0


class BraveSearchClient:
    """Thin wrapper around the Brave Web Search API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        web_fetcher: Any | None = None,
    ) -> None:
        self._api_key = (api_key or os.environ.get("BRAVE_SEARCH_API_KEY", "")).strip()
        self._web_fetcher = web_fetcher  # fallback to DDG via WebFetcher
        self._available = bool(self._api_key)
        if not self._available:
            logger.info("BraveSearchClient: no API key — will fall back to DuckDuckGo")

    @property
    def available(self) -> bool:
        return self._available

    def search(
        self,
        query: str,
        *,
        count: int = _DEFAULT_COUNT,
        news_only: bool = False,
    ) -> dict[str, Any]:
        """Search the web and return structured results.

        Returns:
            {"ok": bool, "results": [{"title", "url", "snippet", "age"}], "error"?: str}
        """
        if not query.strip():
            return {"ok": False, "results": [], "error": "query is empty"}

        if self._available:
            try:
                return self._brave_search(query, count=count, news_only=news_only)
            except Exception as exc:
                logger.warning("Brave search failed, falling back to DDG: %s", exc)

        # Fallback to DuckDuckGo via existing WebFetcher.
        return self._ddg_fallback(query, count=count)

    # ------------------------------------------------------------------
    # Brave API
    # ------------------------------------------------------------------

    def _brave_search(
        self,
        query: str,
        *,
        count: int = _DEFAULT_COUNT,
        news_only: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": query, "count": min(count, 20)}
        if news_only:
            params["search_type"] = "news"

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        resp = httpx.get(
            _BRAVE_API_URL,
            params=params,
            headers=headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict[str, str]] = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "age": item.get("age", ""),
            })

        return {"ok": True, "results": results[:count]}

    # ------------------------------------------------------------------
    # DuckDuckGo fallback via WebFetcher
    # ------------------------------------------------------------------

    def _ddg_fallback(self, query: str, *, count: int = _DEFAULT_COUNT) -> dict[str, Any]:
        if self._web_fetcher is None:
            return {
                "ok": False,
                "results": [],
                "error": "No Brave API key and no WebFetcher fallback configured",
            }
        try:
            raw = self._web_fetcher.search_and_fetch(query, max_results=count)
            results: list[dict[str, str]] = []
            for page in raw.get("pages", []):
                results.append({
                    "title": page.get("url", "").split("/")[-1][:80],
                    "url": page.get("url", ""),
                    "snippet": (page.get("text", "") or "")[:300],
                    "age": "",
                })
            return {"ok": raw.get("ok", True), "results": results}
        except Exception as exc:
            logger.warning("DDG fallback also failed: %s", exc)
            return {"ok": False, "results": [], "error": str(exc)[:300]}
