from __future__ import annotations

import re
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


class DbReader:
    _DIAG_BLOCKED_TOKENS = re.compile(
        r"\b("
        r"insert|update|delete|drop|alter|create|grant|revoke|truncate|attach|detach|"
        r"vacuum|pragma|replace|merge|call|execute|copy|refresh|analyze|reindex"
        r")\b",
        re.IGNORECASE,
    )

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.database_url = database_url
        self.last_error: str | None = None

    def _run_query(self, sql, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(sql, params).mappings().all()
            self.last_error = None
            return [dict(r) for r in rows]
        except OperationalError as exc:
            self.last_error = str(exc)
            return []
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def get_docs(self, ticker: str, limit: int = 20) -> list[dict[str, Any]]:
        sql = text(
            """
            select document_id, ticker, doc_class, doc_subtype, published_at, title, source_url, pdf_path, pdf_sha256
            from documents
            where ticker = :ticker
            order by published_at desc
            limit :limit
            """
        )
        return self._run_query(sql, {"ticker": ticker.upper(), "limit": limit})

    def get_financials(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        sql = text(
            """
            select ticker, period_end, period_type, revenue, ebit, np_attributable,
                   operating_cf, investing_cf, financing_cf, capex, cash_end, net_debt,
                   shares_outstanding, confidence_metrics, source_document_id
            from asx_periodic_financials
            where ticker = :ticker
            order by period_end desc
            limit :limit
            """
        )
        return self._run_query(sql, {"ticker": ticker.upper(), "limit": limit})

    def get_latest_financial_snapshot(self, ticker: str) -> dict[str, Any] | None:
        rows = self.get_financials(ticker=ticker, limit=1)
        return rows[0] if rows else None

    def get_announcement_context(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        sql = text(
            """
            select document_id, ticker, published_at, title, pdf_path, excerpt, updated_at
            from cockpit_announcement_context
            where ticker = :ticker
            order by published_at desc
            limit :limit
            """
        )
        rows = self._run_query(sql, {"ticker": ticker.upper(), "limit": limit})
        # Table may not exist yet on older environments.
        if self.last_error and "no such table" in self.last_error.lower():
            self.last_error = None
            return []
        return rows

    def list_recent_doc_tickers(self, limit: int = 40) -> list[dict[str, Any]]:
        sql = text(
            """
            select ticker, count(*) as announcement_count, max(published_at) as latest_published_at
            from documents
            where ticker is not null and trim(ticker) <> ''
            group by ticker
            order by latest_published_at desc
            limit :limit
            """
        )
        return self._run_query(sql, {"limit": max(1, int(limit))})

    def list_recent_documents(self, limit: int = 20) -> list[dict[str, Any]]:
        sql = text(
            """
            select document_id, ticker, doc_class, doc_subtype, published_at, title, source_url, pdf_path
            from documents
            where ticker is not null and trim(ticker) <> ''
            order by published_at desc, document_id desc
            limit :limit
            """
        )
        return self._run_query(sql, {"limit": max(1, int(limit))})

    def get_extraction_failures(self, limit: int = 50, ticker: str | None = None) -> list[dict[str, Any]]:
        ticker_value = str(ticker or "").strip().upper()
        sql = text(
            """
            select
                er.run_id,
                er.document_id,
                er.status,
                er.error,
                er.created_at,
                d.ticker as ticker,
                d.published_at as published_at,
                d.title as title
            from extraction_runs er
            left join documents d on d.document_id = er.document_id
            where er.status = 'failed'
              and (:ticker = '' or upper(coalesce(d.ticker, '')) = :ticker)
            order by er.created_at desc
            limit :limit
            """
        )
        return self._run_query(
            sql,
            {
                "ticker": ticker_value,
                "limit": max(1, int(limit)),
            },
        )

    def get_low_confidence_financials(
        self,
        threshold: float = 0.4,
        limit: int = 100,
        ticker: str | None = None,
    ) -> list[dict[str, Any]]:
        ticker_value = str(ticker or "").strip().upper()
        sql = text(
            """
            select ticker, period_end, period_type, confidence_metrics, source_document_id
            from asx_periodic_financials
            where confidence_metrics is not null
              and confidence_metrics < :threshold
              and (:ticker = '' or upper(coalesce(ticker, '')) = :ticker)
            order by confidence_metrics asc
            limit :limit
            """
        )
        return self._run_query(
            sql,
            {
                "threshold": threshold,
                "ticker": ticker_value,
                "limit": max(1, int(limit)),
            },
        )

    def run_diagnostic_query(self, query: str, limit: int = 50) -> dict[str, Any]:
        q = str(query or "").strip()
        row_limit = max(1, min(500, int(limit)))
        if not q:
            return {"ok": False, "error": "query is required"}
        if len(q) > 4000:
            return {"ok": False, "error": "query too long"}

        q_lower = q.lower()
        if ";" in q or "--" in q or "/*" in q or "*/" in q:
            return {"ok": False, "error": "only single-statement queries without comments are allowed"}
        if not (q_lower.startswith("select ") or q_lower.startswith("with ")):
            return {"ok": False, "error": "only SELECT/CTE read queries are allowed"}
        if self._DIAG_BLOCKED_TOKENS.search(q):
            return {"ok": False, "error": "query contains blocked SQL token"}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(q))
                columns = [str(name) for name in result.keys()]
                rows = result.mappings().fetchmany(row_limit)
            payload_rows = [dict(row) for row in rows]
            self.last_error = None
            return {
                "ok": True,
                "columns": columns,
                "rows": payload_rows,
                "row_count": len(payload_rows),
                "truncated": len(payload_rows) >= row_limit,
                "limit": row_limit,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {"ok": False, "error": str(exc)}
