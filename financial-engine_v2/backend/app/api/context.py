"""Backend-authoritative context queries preserved for later route wiring.

This file is intentionally added in first wave without router registration so the
query surface is preserved on `main` before any API contract expansion.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])

_TICKER_RE = re.compile(r"^[A-Z0-9]{1,10}$")


def _validate_ticker(raw: str) -> str:
    cleaned = (raw or "").strip().upper()
    if not cleaned:
        raise HTTPException(status_code=400, detail="ticker must not be empty")
    if not _TICKER_RE.match(cleaned):
        raise HTTPException(
            status_code=400, detail="ticker must be 1-10 alphanumeric characters"
        )
    return cleaned


def _run_query(
    db: Session, sql: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], str | None]:
    """Run a read-only query, returning rows plus an optional error string."""
    try:
        result = db.execute(text(sql), params)
        return [dict(row._mapping) for row in result], None
    except OperationalError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Context query failed: %s", exc)
        return [], str(exc)
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Context query failed: %s", exc)
        return [], str(exc)


@router.get("/ticker")
def get_ticker_context(
    ticker: str,
    docs_limit: int = Query(default=20, ge=1, le=100),
    financials_limit: int = Query(default=8, ge=1, le=50),
    announcements_limit: int = Query(default=20, ge=1, le=100),
    failures_limit: int = Query(default=50, ge=1, le=200),
    low_confidence_threshold: float = Query(default=0.4, ge=0.0, le=1.0),
    low_confidence_limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ticker = _validate_ticker(ticker)
    errors: list[str] = []

    docs, err = _run_query(
        db,
        """
        SELECT document_id, ticker, doc_class, doc_subtype, published_at,
               title, source_url, pdf_path, pdf_sha256
        FROM documents
        WHERE ticker = :ticker
        ORDER BY
            CASE
                WHEN doc_class IN ('results', 'annual_report', 'half_year_report', 'annual', 'half_year') THEN 1
                WHEN doc_class = 'guidance' THEN 2
                WHEN doc_class IN ('capital_raising', 'dividend', 'acquisition') THEN 3
                ELSE 4
            END ASC,
            published_at DESC
        LIMIT :limit
        """,
        {"ticker": ticker, "limit": docs_limit},
    )
    if err:
        errors.append(f"docs: {err}")

    financials, err = _run_query(
        db,
        """
        SELECT ticker, period_end, period_type, revenue, ebit, np_attributable,
               operating_cf, investing_cf, financing_cf, capex, cash_end, net_debt,
               shares_outstanding, confidence_metrics, source_document_id
        FROM asx_periodic_financials
        WHERE ticker = :ticker
        ORDER BY period_end DESC
        LIMIT :limit
        """,
        {"ticker": ticker, "limit": financials_limit},
    )
    if err:
        errors.append(f"financials: {err}")

    snapshot_rows, err = _run_query(
        db,
        """
        SELECT ticker, period_end, period_type, revenue, ebit, np_attributable,
               operating_cf, investing_cf, financing_cf, capex, cash_end, net_debt,
               shares_outstanding, confidence_metrics, source_document_id
        FROM asx_periodic_financials
        WHERE ticker = :ticker
        ORDER BY period_end DESC
        LIMIT 1
        """,
        {"ticker": ticker},
    )
    latest_financial_snapshot = snapshot_rows[0] if snapshot_rows else None
    if err:
        errors.append(f"latest_financial_snapshot: {err}")

    announcement_context, err = _run_query(
        db,
        """
        SELECT document_id, ticker, published_at, title, pdf_path, excerpt, updated_at
        FROM cockpit_announcement_context
        WHERE ticker = :ticker
        ORDER BY published_at DESC
        LIMIT :limit
        """,
        {"ticker": ticker, "limit": announcements_limit},
    )
    if err:
        lowered = err.lower()
        if (
            "no such table" in lowered
            or "does not exist" in lowered
            or "undefinedtable" in lowered
        ):
            announcement_context = []
        else:
            errors.append(f"announcement_context: {err}")

    extraction_failures, err = _run_query(
        db,
        """
        SELECT r.run_id, r.document_id, r.status, r.error, r.created_at,
               d.ticker, d.title
        FROM extraction_runs r
        JOIN documents d ON d.document_id = r.document_id
        WHERE r.status = 'failed' AND d.ticker = :ticker
        ORDER BY r.created_at DESC
        LIMIT :limit
        """,
        {"ticker": ticker, "limit": failures_limit},
    )
    if err:
        errors.append(f"extraction_failures: {err}")

    low_confidence_financials, err = _run_query(
        db,
        """
        SELECT ticker, period_end, period_type, confidence_metrics, source_document_id
        FROM asx_periodic_financials
        WHERE confidence_metrics IS NOT NULL AND confidence_metrics < :threshold
          AND ticker = :ticker
        ORDER BY confidence_metrics ASC
        LIMIT :limit
        """,
        {
            "ticker": ticker,
            "threshold": low_confidence_threshold,
            "limit": low_confidence_limit,
        },
    )
    if err:
        errors.append(f"low_confidence_financials: {err}")

    return {
        "ticker": ticker,
        "docs": docs,
        "financials": financials,
        "latest_financial_snapshot": latest_financial_snapshot,
        "announcement_context": announcement_context,
        "extraction_failures": extraction_failures,
        "low_confidence_financials": low_confidence_financials,
        "backend_version": "1.0",
        "errors": errors,
    }


@router.get("/verification")
def get_verification_context(
    ticker: str | None = Query(default=None),
    failures_limit: int = Query(default=100, ge=1, le=500),
    low_confidence_threshold: float = Query(default=0.4, ge=0.0, le=1.0),
    low_confidence_limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    errors: list[str] = []

    if ticker is not None:
        ticker = _validate_ticker(ticker)

    if ticker:
        failures, err = _run_query(
            db,
            """
            SELECT r.run_id, r.document_id, r.status, r.error, r.created_at,
                   d.ticker, d.title
            FROM extraction_runs r
            JOIN documents d ON d.document_id = r.document_id
            WHERE r.status = 'failed' AND d.ticker = :ticker
            ORDER BY r.created_at DESC
            LIMIT :limit
            """,
            {"ticker": ticker, "limit": failures_limit},
        )
    else:
        failures, err = _run_query(
            db,
            """
            SELECT run_id, document_id, status, error, created_at
            FROM extraction_runs
            WHERE status = 'failed'
            ORDER BY created_at DESC
            LIMIT :limit
            """,
            {"limit": failures_limit},
        )
    if err:
        errors.append(f"extraction_failures: {err}")

    if ticker:
        low_conf, err = _run_query(
            db,
            """
            SELECT ticker, period_end, period_type, confidence_metrics, source_document_id
            FROM asx_periodic_financials
            WHERE confidence_metrics IS NOT NULL AND confidence_metrics < :threshold
              AND ticker = :ticker
            ORDER BY confidence_metrics ASC
            LIMIT :limit
            """,
            {
                "ticker": ticker,
                "threshold": low_confidence_threshold,
                "limit": low_confidence_limit,
            },
        )
    else:
        low_conf, err = _run_query(
            db,
            """
            SELECT ticker, period_end, period_type, confidence_metrics, source_document_id
            FROM asx_periodic_financials
            WHERE confidence_metrics IS NOT NULL AND confidence_metrics < :threshold
            ORDER BY confidence_metrics ASC
            LIMIT :limit
            """,
            {"threshold": low_confidence_threshold, "limit": low_confidence_limit},
        )
    if err:
        errors.append(f"low_confidence_financials: {err}")

    return {
        "extraction_failures": failures,
        "low_confidence_financials": low_conf,
        "errors": errors,
    }
