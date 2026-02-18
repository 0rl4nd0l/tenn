from __future__ import annotations

from pathlib import Path
from typing import Any

from cockpit.core.types import ToolResult


class ToolRouter:
    def __init__(self, db_reader, file_indexer, web_fetcher, repo_root: Path, web_default_enabled: bool) -> None:
        self.db_reader = db_reader
        self.file_indexer = file_indexer
        self.web_fetcher = web_fetcher
        self.repo_root = Path(repo_root).resolve()
        self.web_default_enabled = web_default_enabled

    def _resolve_doc_path(self, path_value: str | None) -> Path | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.is_absolute():
            path = self.repo_root / path
        return path.resolve()

    def _extract_pdf_excerpt(self, pdf_path: Path, max_chars: int = 1500) -> str:
        try:
            import fitz  # type: ignore
        except Exception:
            return ""
        if not pdf_path.exists() or not pdf_path.is_file():
            return ""
        try:
            with fitz.open(pdf_path) as pdf:
                if pdf.page_count < 1:
                    return ""
                text = pdf[0].get_text() or ""
        except Exception:
            return ""
        return " ".join(text.split())[:max_chars]

    def gather_local_context(self, ticker: str | None, query: str) -> ToolResult:
        payload: dict[str, Any] = {
            "query": query,
            "ticker": ticker,
            "reports": self.file_indexer.list_recent_reports(limit=10),
            "matches": self.file_indexer.search_text(pattern=query, limit=20),
        }
        if ticker:
            docs = self.db_reader.get_docs(ticker, limit=10)
            payload["docs"] = docs
            context_rows = self.db_reader.get_announcement_context(ticker, limit=10)
            payload["doc_snippets_source"] = "cockpit_announcement_context" if context_rows else "live_pdf_fallback"
            if context_rows:
                payload["doc_snippets"] = context_rows[:5]
            else:
                payload["doc_snippets"] = []
                for row in docs[:5]:
                    resolved = self._resolve_doc_path(str(row.get("pdf_path", "")))
                    excerpt = self._extract_pdf_excerpt(resolved) if resolved else ""
                    payload["doc_snippets"].append(
                        {
                            "document_id": row.get("document_id"),
                            "title": row.get("title"),
                            "published_at": row.get("published_at"),
                            "pdf_path": row.get("pdf_path"),
                            "excerpt": excerpt,
                        }
                    )
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
