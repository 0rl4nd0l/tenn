from __future__ import annotations

from typing import Any

from cockpit.core.types import ToolResult


class ToolRouter:
    def __init__(self, db_reader, file_indexer, web_fetcher, web_default_enabled: bool) -> None:
        self.db_reader = db_reader
        self.file_indexer = file_indexer
        self.web_fetcher = web_fetcher
        self.web_default_enabled = web_default_enabled

    def gather_local_context(self, ticker: str | None, query: str) -> ToolResult:
        payload: dict[str, Any] = {
            "query": query,
            "ticker": ticker,
            "reports": self.file_indexer.list_recent_reports(limit=10),
            "matches": self.file_indexer.search_text(pattern=query, limit=20),
        }
        if ticker:
            payload["docs"] = self.db_reader.get_docs(ticker, limit=10)
            payload["financials"] = self.db_reader.get_financials(ticker, limit=5)
            if self.db_reader.last_error:
                payload["db_warning"] = (
                    "Database unavailable or schema not initialized for cockpit reads. "
                    f"db_url={getattr(self.db_reader, 'database_url', 'unknown')}"
                )
                payload["db_error"] = self.db_reader.last_error[:400]
        return ToolResult(ok=True, title="local_context", payload=payload)

    def fetch_web(self, url: str, enabled: bool) -> ToolResult:
        if not enabled:
            return ToolResult(ok=False, title="web_disabled", payload={"error": "Web fetch is disabled"})
        try:
            body = self.web_fetcher.fetch_text(url)
            return ToolResult(ok=True, title="web_fetch", payload={"url": url, "content": body})
        except Exception as exc:
            return ToolResult(ok=False, title="web_fetch", payload={"url": url, "error": str(exc)})
