"""context.py — Backend-authoritative context endpoints.

Replaces direct DbReader SQL from cockpit with proper API endpoints.
All queries use the same SQL and field names as DbReader for parity.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.providers.market_price_provider import (
    MarketPriceProvider,
    MarketPriceProviderError,
)
from app.services.source_registry import RESEARCH_MEMORY_ROOT

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
    """Run a read-only query, returning (rows, error_or_none)."""
    try:
        result = db.execute(text(sql), params)
        return [dict(row._mapping) for row in result], None
    except OperationalError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Query failed: %s", exc)
        return [], str(exc)
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Query failed: %s", exc)
        return [], str(exc)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _summarize_price_history(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    parsed_rows: list[tuple[datetime, float]] = []
    for row in history_rows:
        if not isinstance(row, dict):
            continue
        timestamp = _parse_iso_timestamp(row.get("timestamp"))
        close_value = _safe_float(row.get("close"))
        if timestamp is None or close_value is None:
            continue
        parsed_rows.append((timestamp, close_value))

    if not parsed_rows:
        return {
            "points": 0,
            "coverage_start": None,
            "coverage_end": None,
            "last_close": None,
            "first_close": None,
            "one_year_return_pct": None,
            "high_close": None,
            "low_close": None,
        }

    parsed_rows.sort(key=lambda item: item[0])
    closes = [close for _, close in parsed_rows]
    first_close = closes[0]
    last_close = closes[-1]
    one_year_return_pct = None
    if first_close != 0:
        one_year_return_pct = ((last_close / first_close) - 1.0) * 100.0

    return {
        "points": len(parsed_rows),
        "coverage_start": parsed_rows[0][0].date().isoformat(),
        "coverage_end": parsed_rows[-1][0].date().isoformat(),
        "last_close": last_close,
        "first_close": first_close,
        "one_year_return_pct": one_year_return_pct,
        "high_close": max(closes),
        "low_close": min(closes),
    }


def _load_price_context_1y(
    ticker: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str | None]:
    provider = MarketPriceProvider(
        base_url=getattr(
            settings, "market_data_base_url", "https://query1.finance.yahoo.com"
        ),
        timeout=getattr(settings, "market_data_timeout_seconds", 20.0),
    )
    try:
        payload = provider.fetch(
            ticker=ticker, exchange="ASX", range_="1y", interval="1d"
        )
        current = payload.get("current") if isinstance(payload, dict) else {}
        history = payload.get("history") if isinstance(payload, dict) else []
        if not isinstance(current, dict):
            current = {}
        if not isinstance(history, list):
            history = []
        summary = _summarize_price_history(
            [row for row in history if isinstance(row, dict)]
        )
        return current, [row for row in history if isinstance(row, dict)], summary, None
    except (MarketPriceProviderError, ValueError) as exc:
        return {}, [], _summarize_price_history([]), str(exc)
    except Exception as exc:
        logger.warning("Price context failed for %s: %s", ticker, exc)
        return {}, [], _summarize_price_history([]), str(exc)


def _load_company_memory(
    ticker: str,
    *,
    entries_limit: int,
    change_log_limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.company_memory import (
            DEFAULT_COMPANY_MEMORY_PATH,
            CompanyMemoryStore,
        )

        path = Path(DEFAULT_COMPANY_MEMORY_PATH)
    except Exception as exc:
        fallback = RESEARCH_MEMORY_ROOT / "company_memory.sqlite"
        return {
            "status": "unavailable",
            "path": str(fallback),
            "entries": [],
            "change_log": [],
            "reason": "company memory module unavailable",
        }, str(exc)

    if not path.exists():
        return {
            "status": "unavailable",
            "path": str(path),
            "entries": [],
            "change_log": [],
            "reason": "company memory store is not initialized",
        }, None

    try:
        store = CompanyMemoryStore(path)
        entries = store.list_entries(ticker)
        change_log = store.list_change_log(ticker)
        return {
            "status": "ok",
            "path": str(path),
            "entries": entries[:entries_limit],
            "change_log": change_log[:change_log_limit],
            "entries_total": len(entries),
            "change_log_total": len(change_log),
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "entries": [],
            "change_log": [],
        }, str(exc)


def _load_market_memory(
    ticker: str,
    *,
    limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.market_memory import (
            DEFAULT_MARKET_MEMORY_PATH,
            MarketMemoryStore,
        )

        path = Path(DEFAULT_MARKET_MEMORY_PATH)
    except Exception as exc:
        fallback = RESEARCH_MEMORY_ROOT / "market_memory.sqlite"
        return {
            "status": "unavailable",
            "path": str(fallback),
            "sector": None,
            "sector_items": [],
            "macro_items": [],
            "items": [],
            "reason": "market memory module unavailable",
        }, str(exc)

    if not path.exists():
        return {
            "status": "unavailable",
            "path": str(path),
            "sector": None,
            "sector_items": [],
            "macro_items": [],
            "items": [],
            "reason": "market memory store is not initialized",
        }, None

    try:
        store = MarketMemoryStore(path)
        from app.services.analysis.sector_comparison import get_sector_for_ticker

        sector = get_sector_for_ticker(ticker)
        sector_items = (
            [
                row
                for row in (store.list_sector_entries(sector, status="active") or [])
                if isinstance(row, dict)
            ]
            if sector
            else []
        )
        macro_items = [
            row
            for row in (store.list_all_macro_entries(status="active") or [])
            if isinstance(row, dict)
        ]
        items = sector_items + macro_items
        return {
            "status": "ok",
            "path": str(path),
            "sector": sector,
            "sector_items": sector_items[:limit],
            "macro_items": macro_items[:limit],
            "items": items[:limit],
            "sector_items_total": len(sector_items),
            "macro_items_total": len(macro_items),
            "items_total": len(items),
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "sector": None,
            "sector_items": [],
            "macro_items": [],
            "items": [],
        }, str(exc)


# ---------------------------------------------------------------------------
# GET /api/context/ticker
# ---------------------------------------------------------------------------


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

    # --- docs (matches DbReader.get_docs) ---
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

    # --- financials (matches DbReader.get_financials) ---
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

    # --- latest_financial_snapshot (matches DbReader.get_latest_financial_snapshot) ---
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

    # --- announcement_context (matches DbReader.get_announcement_context) ---
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

    # --- extraction_failures (matches DbReader.get_extraction_failures with ticker) ---
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

    # --- low_confidence_financials (matches DbReader.get_low_confidence_financials with ticker) ---
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


# ---------------------------------------------------------------------------
# GET /api/context/company_dump
# ---------------------------------------------------------------------------


@router.get("/company_dump")
def get_company_dump(
    ticker: str,
    docs_limit: int = Query(default=200, ge=1, le=1000),
    financials_limit: int = Query(default=100, ge=1, le=500),
    announcements_limit: int = Query(default=200, ge=1, le=1000),
    failures_limit: int = Query(default=200, ge=1, le=1000),
    low_confidence_threshold: float = Query(default=0.4, ge=0.0, le=1.0),
    low_confidence_limit: int = Query(default=200, ge=1, le=1000),
    risk_notes_limit: int = Query(default=100, ge=1, le=500),
    company_memory_entries_limit: int = Query(default=400, ge=1, le=2000),
    company_memory_change_limit: int = Query(default=400, ge=1, le=2000),
    market_memory_limit: int = Query(default=300, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ticker = _validate_ticker(ticker)

    base_context = get_ticker_context(
        ticker=ticker,
        docs_limit=docs_limit,
        financials_limit=financials_limit,
        announcements_limit=announcements_limit,
        failures_limit=failures_limit,
        low_confidence_threshold=low_confidence_threshold,
        low_confidence_limit=low_confidence_limit,
        db=db,
    )
    errors: list[str] = list(base_context.get("errors") or [])

    risk_notes, err = _run_query(
        db,
        """
        SELECT d.document_id, d.ticker, d.published_at, d.title,
               r.risk_summary, r.risk_bullets, r.guidance_summary,
               r.material_changes, r.confidence_narrative, r.updated_at
        FROM asx_risk_notes r
        JOIN documents d ON d.document_id = r.document_id
        WHERE d.ticker = :ticker
        ORDER BY d.published_at DESC
        LIMIT :limit
    """,
        {"ticker": ticker, "limit": risk_notes_limit},
    )
    if err:
        errors.append(f"risk_notes: {err}")

    price_current, price_history_1y, price_summary_1y, err = _load_price_context_1y(
        ticker
    )
    if err:
        errors.append(f"price_history_1y: {err}")

    company_memory, err = _load_company_memory(
        ticker,
        entries_limit=company_memory_entries_limit,
        change_log_limit=company_memory_change_limit,
    )
    if err:
        errors.append(f"company_memory: {err}")

    market_memory, err = _load_market_memory(ticker, limit=market_memory_limit)
    if err:
        errors.append(f"market_memory: {err}")

    docs = [row for row in (base_context.get("docs") or []) if isinstance(row, dict)]
    financials = [
        row for row in (base_context.get("financials") or []) if isinstance(row, dict)
    ]
    announcement_context = [
        row
        for row in (base_context.get("announcement_context") or [])
        if isinstance(row, dict)
    ]
    extraction_failures = [
        row
        for row in (base_context.get("extraction_failures") or [])
        if isinstance(row, dict)
    ]
    low_confidence_financials = [
        row
        for row in (base_context.get("low_confidence_financials") or [])
        if isinstance(row, dict)
    ]

    summary = {
        "doc_count": len(docs),
        "financial_period_count": len(financials),
        "announcement_context_count": len(announcement_context),
        "risk_note_count": len(risk_notes),
        "extraction_failure_count": len(extraction_failures),
        "low_confidence_financial_count": len(low_confidence_financials),
        "company_memory_entry_count": int(
            company_memory.get("entries_total", len(company_memory.get("entries") or []))
            or 0
        ),
        "company_memory_change_count": int(
            company_memory.get(
                "change_log_total",
                len(company_memory.get("change_log") or []),
            )
            or 0
        ),
        "market_memory_item_count": int(
            market_memory.get("items_total", len(market_memory.get("items") or []))
            or 0
        ),
        "price_points_1y": int(price_summary_1y.get("points") or 0),
        "last_close": price_summary_1y.get("last_close"),
        "high_close_1y": price_summary_1y.get("high_close"),
        "low_close_1y": price_summary_1y.get("low_close"),
        "one_year_return_pct": price_summary_1y.get("one_year_return_pct"),
        "price_coverage_start": price_summary_1y.get("coverage_start"),
        "price_coverage_end": price_summary_1y.get("coverage_end"),
    }

    return {
        "ticker": ticker,
        "summary": summary,
        "docs": docs,
        "financials": financials,
        "latest_financial_snapshot": base_context.get("latest_financial_snapshot"),
        "announcement_context": announcement_context,
        "risk_notes": risk_notes,
        "price": price_current,
        "price_history_1y": price_history_1y,
        "price_summary_1y": price_summary_1y,
        "extraction_failures": extraction_failures,
        "low_confidence_financials": low_confidence_financials,
        "company_memory": company_memory,
        "market_memory": market_memory,
        "backend_version": "1.1",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# GET /api/context/verification
# ---------------------------------------------------------------------------


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

    # --- extraction_failures ---
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

    # --- low_confidence_financials ---
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
