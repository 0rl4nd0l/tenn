from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


class DbReader:
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

    def get_extraction_failures(self, limit: int = 50, ticker: str | None = None) -> list[dict[str, Any]]:
        if ticker:
            sql = text(
                """
                select r.run_id, r.document_id, r.status, r.error, r.created_at
                from extraction_runs r
                join documents d on d.document_id = r.document_id
                where r.status = 'failed' and d.ticker = :ticker
                order by r.created_at desc
                limit :limit
                """
            )
            return self._run_query(sql, {"ticker": ticker.upper(), "limit": limit})
        sql = text(
            """
            select run_id, document_id, status, error, created_at
            from extraction_runs
            where status = 'failed'
            order by created_at desc
            limit :limit
            """
        )
        return self._run_query(sql, {"limit": limit})

    def get_low_confidence_financials(self, threshold: float = 0.4, limit: int = 100, ticker: str | None = None) -> list[dict[str, Any]]:
        if ticker:
            sql = text(
                """
                select ticker, period_end, period_type, confidence_metrics, source_document_id
                from asx_periodic_financials
                where confidence_metrics is not null and confidence_metrics < :threshold
                  and ticker = :ticker
                order by confidence_metrics asc
                limit :limit
                """
            )
            return self._run_query(sql, {"threshold": threshold, "ticker": ticker.upper(), "limit": limit})
        sql = text(
            """
            select ticker, period_end, period_type, confidence_metrics, source_document_id
            from asx_periodic_financials
            where confidence_metrics is not null and confidence_metrics < :threshold
            order by confidence_metrics asc
            limit :limit
            """
        )
        return self._run_query(sql, {"threshold": threshold, "limit": limit})
