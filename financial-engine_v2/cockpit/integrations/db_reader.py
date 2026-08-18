"""DbReader — narrowed to diagnostics-only.

General data methods (get_docs, get_financials, get_announcement_context,
get_extraction_failures, get_low_confidence_financials) have been removed.
Authoritative data reads now flow through BackendApiClient.

The legacy methods are retained as stubs that return empty results, preserving
backward compatibility for any code that still references them when no
backend_api_client is configured.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Allowlisted diagnostic queries — names map to safe, read-only SQL.
_DIAGNOSTIC_QUERIES: dict[str, str] = {
    "tables_sqlite": (
        "SELECT name AS table_name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT :limit"
    ),
    "tables": (
        "SELECT name AS table_name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT :limit"
    ),
}


class DbReader:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.database_url = database_url
        self.last_error: str | None = None

    # ------------------------------------------------------------------
    # Legacy stubs — backward compatibility when no backend is configured.
    # These return empty results; real reads go through BackendApiClient.
    # ------------------------------------------------------------------

    def get_docs(self, ticker: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._run_read_query(
            """SELECT document_id, ticker, doc_class, doc_subtype, published_at,
                      title, source_url, pdf_path, pdf_sha256
               FROM documents WHERE ticker = :ticker
               ORDER BY published_at DESC LIMIT :limit""",
            {"ticker": (ticker or "").upper(), "limit": limit},
        )

    def get_financials(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return no rows; financial truth is available only from BackendApiClient."""
        return []

    def get_latest_financial_snapshot(self, ticker: str) -> dict[str, Any] | None:
        """Return no snapshot; financial truth is available only from BackendApiClient."""
        return None

    def get_announcement_context(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._run_read_query(
            """SELECT document_id, ticker, published_at, title, pdf_path, excerpt, updated_at
               FROM cockpit_announcement_context WHERE ticker = :ticker
               ORDER BY published_at DESC LIMIT :limit""",
            {"ticker": (ticker or "").upper(), "limit": limit},
        )
        if self.last_error and "no such table" in self.last_error.lower():
            self.last_error = None
            return []
        return rows

    def get_extraction_failures(self, limit: int = 50, ticker: str | None = None) -> list[dict[str, Any]]:
        if ticker:
            return self._run_read_query(
                """SELECT r.run_id, r.document_id, r.status, r.error, r.created_at,
                          d.ticker, d.title
                   FROM extraction_runs r JOIN documents d ON d.document_id = r.document_id
                   WHERE r.status = 'failed' AND d.ticker = :ticker
                   ORDER BY r.created_at DESC LIMIT :limit""",
                {"ticker": ticker.upper(), "limit": limit},
            )
        return self._run_read_query(
            """SELECT run_id, document_id, status, error, created_at
               FROM extraction_runs WHERE status = 'failed'
               ORDER BY created_at DESC LIMIT :limit""",
            {"limit": limit},
        )

    def get_low_confidence_financials(self, threshold: float = 0.4, limit: int = 100, ticker: str | None = None) -> list[dict[str, Any]]:
        """Return no rows; confidence diagnostics are backend-owned."""
        return []

    # ------------------------------------------------------------------
    # Shared query runner
    # ------------------------------------------------------------------

    def _run_read_query(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(sql), params).mappings().all()
            self.last_error = None
            return [dict(r) for r in rows]
        except OperationalError as exc:
            self.last_error = str(exc)
            return []
        except Exception as exc:
            self.last_error = str(exc)
            return []

    # ------------------------------------------------------------------
    # Diagnostics — the only remaining primary use case for DbReader.
    # ------------------------------------------------------------------

    def run_diagnostic_query(self, name: str, limit: int = 100) -> dict[str, Any]:
        """Run an allowlisted read-only diagnostic query by name.

        Returns {ok, columns, rows} on success, or {ok: False, error, allowed} on failure.
        """
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "query name required"}
        allowed = sorted(_DIAGNOSTIC_QUERIES.keys())
        if name not in _DIAGNOSTIC_QUERIES:
            return {"ok": False, "error": f"query '{name}' not in allowlist", "allowed": allowed}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(_DIAGNOSTIC_QUERIES[name]), {"limit": limit})
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"ok": True, "columns": columns, "rows": rows}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
