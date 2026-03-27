"""Hacker News Algolia search client.

Free, no auth required. Provides developer/tech community discussion
results for the cockpit agent loop.

API docs: https://hn.algolia.com/api
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HN_API_URL = "https://hn.algolia.com/api/v1/search"
_DEFAULT_LIMIT = 10
_TIMEOUT = 12.0


class HNSearchClient:
    """Thin wrapper around the HN Algolia search API."""

    def search(
        self,
        query: str,
        *,
        tags: str = "story",
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Search Hacker News stories/comments.

        Args:
            query: Search string.
            tags: HN Algolia tag filter (e.g. "story", "comment", "show_hn").
            limit: Maximum results to return.

        Returns:
            {"ok": bool, "stories": [{"title", "url", "points", "num_comments",
             "author", "created_at", "hn_url"}], "error"?: str}
        """
        if not query.strip():
            return {"ok": False, "stories": [], "error": "query is empty"}

        try:
            return self._fetch(query, tags=tags, limit=limit)
        except Exception as exc:
            logger.warning("HN search failed: %s", exc)
            return {"ok": False, "stories": [], "error": str(exc)[:300]}

    def _fetch(
        self,
        query: str,
        *,
        tags: str = "story",
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": query,
            "tags": tags,
            "hitsPerPage": min(limit, 50),
        }
        resp = httpx.get(_HN_API_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        stories: list[dict[str, Any]] = []
        for hit in data.get("hits", []):
            object_id = hit.get("objectID", "")
            stories.append({
                "title": hit.get("title", "") or hit.get("story_title", ""),
                "url": hit.get("url", ""),
                "points": hit.get("points", 0) or 0,
                "num_comments": hit.get("num_comments", 0) or 0,
                "author": hit.get("author", ""),
                "created_at": hit.get("created_at", ""),
                "hn_url": f"https://news.ycombinator.com/item?id={object_id}" if object_id else "",
            })

        # Sort by points descending (most relevant/discussed first).
        stories.sort(key=lambda s: s["points"], reverse=True)
        return {"ok": True, "stories": stories[:limit]}
