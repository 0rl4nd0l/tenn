"""context.py — Backend-authoritative context endpoints.

Replaces direct DbReader SQL from cockpit with proper API endpoints.
All queries use the same SQL and field names as DbReader for parity.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Mapping

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.routes import require_api_key
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


class CompanyMemoryAddRequest(BaseModel):
    ticker: str
    type: str
    statement: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    materiality: float = Field(default=0.7, ge=0.0, le=1.0)
    persistence: Literal["short", "medium", "long"] = "medium"
    supersedes: list[int | str] = Field(default_factory=list)
    contradicts: list[int | str] = Field(default_factory=list)
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyMemoryExpireRequest(BaseModel):
    ticker: str
    entry_id: int = Field(ge=1)
    note: str | None = None


class MarketMemoryAddRequest(BaseModel):
    scope: Literal["sector", "macro"]
    type: str
    statement: str
    ticker: str | None = None
    sector: str | None = None
    macro_topic: str | None = None
    linked_tickers: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    materiality: float = Field(default=0.7, ge=0.0, le=1.0)
    persistence: Literal["short", "medium", "long"] = "medium"
    supersedes: list[int | str] = Field(default_factory=list)
    contradicts: list[int | str] = Field(default_factory=list)
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketMemoryExpireRequest(BaseModel):
    scope: Literal["sector", "macro"]
    entry_id: int = Field(ge=1)
    note: str | None = None


class UserThesisProposalRequest(BaseModel):
    ticker: str
    proposal_type: Literal["create_thesis", "add_evidence", "invalidate"]
    statement: str
    signal: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    is_supporting: bool = True
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserThesisConfirmRequest(BaseModel):
    note: str | None = None


class UserThesisRejectRequest(BaseModel):
    note: str | None = None


class VerificationRunRequest(BaseModel):
    ticker: str | None = None
    failures_limit: int = Field(default=100, ge=1, le=500)
    low_confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    low_confidence_limit: int = Field(default=100, ge=1, le=500)


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
    db: Session,
    sql: str,
    params: dict[str, Any],
    *,
    warn_on_missing_table: bool = True,
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
        if warn_on_missing_table or not _is_missing_table_error(str(exc)):
            logger.warning("Query failed: %s", exc)
        else:
            logger.info(
                "Optional query skipped because a referenced table is unavailable"
            )
        return [], str(exc)
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Query failed: %s", exc)
        return [], str(exc)


def _is_missing_table_error(error: str | None) -> bool:
    lowered = str(error or "").lower()
    return (
        "no such table" in lowered
        or "does not exist" in lowered
        or "undefinedtable" in lowered
    )


def _build_document_announcement_context(
    docs: list[dict[str, Any]],
    *,
    limit: Any,
) -> list[dict[str, Any]]:
    """Build read-only announcement excerpts from authoritative document rows.

    Used only when the materialized cockpit_announcement_context surface is not
    present. The existing title skip policy remains the gate, so administrative
    holder/securities forms stay out of narrative context.
    """
    try:
        limit_value = int(getattr(limit, "default", limit))
    except (TypeError, ValueError):
        limit_value = 0
    if limit_value <= 0:
        return []

    try:
        from app.services.announcement_importance import (
            _extract_pdf_excerpt,
            classify_title_extraction_skip,
        )
    except Exception as exc:
        logger.warning("Announcement context fallback unavailable: %s", exc)
        return []

    context_rows: list[dict[str, Any]] = []
    for row in docs:
        if len(context_rows) >= limit_value:
            break
        if not isinstance(row, dict):
            continue

        title_skip = classify_title_extraction_skip(
            title=row.get("title"),
            doc_class=row.get("doc_class"),
            doc_subtype=row.get("doc_subtype"),
        )
        if bool(title_skip.get("skip_extraction")):
            continue

        pdf_path = str(row.get("pdf_path") or "").strip()
        pdf_sha256 = str(row.get("pdf_sha256") or "").strip().lower()
        if not pdf_path or not pdf_sha256 or pdf_sha256.startswith("blocked_"):
            continue

        try:
            excerpt = _extract_pdf_excerpt(pdf_path, max_pages=2, max_chars=3500)
        except Exception as exc:
            logger.warning(
                "Failed to extract announcement context excerpt for %s: %s",
                row.get("document_id"),
                exc,
            )
            continue

        excerpt = str(excerpt or "").strip()
        if not excerpt:
            continue

        context_rows.append(
            {
                "document_id": row.get("document_id"),
                "ticker": row.get("ticker"),
                "published_at": row.get("published_at"),
                "title": row.get("title"),
                "pdf_path": pdf_path,
                "source_url": row.get("source_url"),
                "excerpt": excerpt,
                "updated_at": None,
                "context_source": "documents_pdf_excerpt",
            }
        )

    return context_rows


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
    entry_status: str | None = "active",
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
        entries = store.list_entries(ticker, status=entry_status)
        change_log = store.list_change_log(ticker)
        return {
            "status": "ok",
            "path": str(path),
            "entry_status": entry_status or "all",
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


def _load_user_thesis_memory(
    ticker: str,
    *,
    entries_limit: int,
    proposals_limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.user_thesis_memory import (
            DEFAULT_USER_THESIS_MEMORY_PATH,
            UserThesisMemoryStore,
        )

        path = Path(DEFAULT_USER_THESIS_MEMORY_PATH)
    except Exception as exc:
        fallback = RESEARCH_MEMORY_ROOT / "user_thesis_memory.sqlite"
        return {
            "status": "unavailable",
            "path": str(fallback),
            "entries": [],
            "proposals": [],
            "reason": "user thesis memory module unavailable",
        }, str(exc)

    if not path.exists():
        return {
            "status": "unavailable",
            "path": str(path),
            "entries": [],
            "proposals": [],
            "reason": "user thesis memory store is not initialized",
        }, None

    try:
        store = UserThesisMemoryStore(path)
        entries = store.list_entries(ticker, status="active")
        proposals = store.list_proposals(ticker=ticker, limit=proposals_limit)
        return {
            "status": "ok",
            "path": str(path),
            "entries": entries[:entries_limit],
            "entries_total": len(entries),
            "proposals": proposals[:proposals_limit],
            "proposals_total": len(proposals),
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "entries": [],
            "proposals": [],
        }, str(exc)


def _safe_json_object(raw: Any) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_list(raw: Any) -> list[Any]:
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _sqlite_rows(path: Path, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with sqlite3.connect(path, timeout=5.0) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _sqlite_count(path: Path, query: str, params: tuple[Any, ...] = ()) -> int:
    with sqlite3.connect(path, timeout=5.0) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(query, params).fetchone()
    if row is None:
        return 0
    return int(row["count"] or 0)


def _load_company_memory_index(
    *,
    entries_limit: int,
    change_log_limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.company_memory import DEFAULT_COMPANY_MEMORY_PATH

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
        entries = _sqlite_rows(
            path,
            "SELECT * FROM memory_entries ORDER BY company_id ASC, entry_id ASC LIMIT ?",
            (entries_limit,),
        )
        for row in entries:
            row["metadata"] = _safe_json_object(row.pop("metadata_json", "{}"))

        change_log = _sqlite_rows(
            path,
            "SELECT * FROM change_log ORDER BY company_id ASC, change_id ASC LIMIT ?",
            (change_log_limit,),
        )
        for row in change_log:
            row["details"] = _safe_json_object(row.pop("details_json", "{}"))

        entries_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM memory_entries")
        change_log_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM change_log")
        ticker_count = _sqlite_count(
            path,
            "SELECT COUNT(DISTINCT company_id) AS count FROM memory_entries",
        )

        return {
            "status": "ok",
            "path": str(path),
            "entries": entries,
            "change_log": change_log,
            "entries_total": entries_total,
            "change_log_total": change_log_total,
            "ticker_count": ticker_count,
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "entries": [],
            "change_log": [],
        }, str(exc)


def _load_market_memory_index(
    *,
    sector_limit: int,
    macro_limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.market_memory import DEFAULT_MARKET_MEMORY_PATH

        path = Path(DEFAULT_MARKET_MEMORY_PATH)
    except Exception as exc:
        fallback = RESEARCH_MEMORY_ROOT / "market_memory.sqlite"
        return {
            "status": "unavailable",
            "path": str(fallback),
            "sector_items": [],
            "macro_items": [],
            "items": [],
            "reason": "market memory module unavailable",
        }, str(exc)

    if not path.exists():
        return {
            "status": "unavailable",
            "path": str(path),
            "sector_items": [],
            "macro_items": [],
            "items": [],
            "reason": "market memory store is not initialized",
        }, None

    try:
        sector_items = _sqlite_rows(
            path,
            "SELECT * FROM sector_states ORDER BY sector ASC, entry_id ASC LIMIT ?",
            (sector_limit,),
        )
        for row in sector_items:
            row["metadata"] = _safe_json_object(row.pop("metadata_json", "{}"))
            row["linked_tickers"] = _safe_json_list(row.pop("linked_tickers_json", "[]"))

        macro_items = _sqlite_rows(
            path,
            "SELECT * FROM macro_state ORDER BY macro_topic ASC, entry_id ASC LIMIT ?",
            (macro_limit,),
        )
        for row in macro_items:
            row["metadata"] = _safe_json_object(row.pop("metadata_json", "{}"))

        sector_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM sector_states")
        macro_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM macro_state")
        sector_count = _sqlite_count(
            path,
            "SELECT COUNT(DISTINCT sector) AS count FROM sector_states",
        )
        macro_topic_count = _sqlite_count(
            path,
            "SELECT COUNT(DISTINCT macro_topic) AS count FROM macro_state",
        )

        return {
            "status": "ok",
            "path": str(path),
            "sector_items": sector_items,
            "macro_items": macro_items,
            "items": sector_items + macro_items,
            "sector_items_total": sector_total,
            "macro_items_total": macro_total,
            "items_total": sector_total + macro_total,
            "sector_count": sector_count,
            "macro_topic_count": macro_topic_count,
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "sector_items": [],
            "macro_items": [],
            "items": [],
        }, str(exc)


def _load_user_thesis_memory_index(
    *,
    entries_limit: int,
    proposals_limit: int,
) -> tuple[dict[str, Any], str | None]:
    try:
        from app.services.user_thesis_memory import DEFAULT_USER_THESIS_MEMORY_PATH

        path = Path(DEFAULT_USER_THESIS_MEMORY_PATH)
    except Exception as exc:
        fallback = RESEARCH_MEMORY_ROOT / "user_thesis_memory.sqlite"
        return {
            "status": "unavailable",
            "path": str(fallback),
            "entries": [],
            "proposals": [],
            "reason": "user thesis memory module unavailable",
        }, str(exc)

    if not path.exists():
        return {
            "status": "unavailable",
            "path": str(path),
            "entries": [],
            "proposals": [],
            "reason": "user thesis memory store is not initialized",
        }, None

    try:
        entries = _sqlite_rows(
            path,
            "SELECT * FROM thesis_entries ORDER BY ticker ASC, entry_id ASC LIMIT ?",
            (entries_limit,),
        )
        for row in entries:
            row["metadata"] = _safe_json_object(row.pop("metadata_json", "{}"))

        proposals = _sqlite_rows(
            path,
            "SELECT * FROM thesis_proposals ORDER BY created_at DESC LIMIT ?",
            (proposals_limit,),
        )
        for row in proposals:
            row["payload"] = _safe_json_object(row.pop("payload_json", "{}"))

        entries_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM thesis_entries")
        proposals_total = _sqlite_count(path, "SELECT COUNT(*) AS count FROM thesis_proposals")
        ticker_count = _sqlite_count(
            path,
            "SELECT COUNT(DISTINCT ticker) AS count FROM thesis_entries",
        )

        return {
            "status": "ok",
            "path": str(path),
            "entries": entries,
            "proposals": proposals,
            "entries_total": entries_total,
            "proposals_total": proposals_total,
            "ticker_count": ticker_count,
        }, None
    except Exception as exc:
        return {
            "status": "error",
            "path": str(path),
            "entries": [],
            "proposals": [],
        }, str(exc)


def _memory_level_summary(
    *,
    level: str,
    label: str,
    status: str,
    scope: str,
    row_count: int | None,
    entity_count: int | None,
    source: str,
) -> dict[str, Any]:
    return {
        "level": level,
        "label": label,
        "status": status,
        "scope": scope,
        "row_count": row_count,
        "entity_count": entity_count,
        "source": source,
    }


def _build_memory_level_summaries(
    *,
    summary: dict[str, Any],
    company_memory: dict[str, Any],
    market_memory: dict[str, Any],
    user_thesis_memory: dict[str, Any],
    scoped_ticker: str | None = None,
) -> list[dict[str, Any]]:
    sector_count = market_memory.get("sector_items_total")
    if sector_count is None:
        sector_count = len(market_memory.get("sector_items") or [])

    macro_count = market_memory.get("macro_items_total")
    if macro_count is None:
        macro_count = len(market_memory.get("macro_items") or [])

    company_entries = int(summary.get("company_memory_entry_count") or 0)
    thesis_entries = int(summary.get("user_thesis_entry_count") or 0)
    thesis_proposals = int(summary.get("user_thesis_proposal_count") or 0)
    strategy_rows = thesis_entries + thesis_proposals

    return [
        _memory_level_summary(
            level="financial_truth",
            label="Financial Truth",
            status="ticker_scoped" if scoped_ticker else "load_ticker",
            scope=scoped_ticker or "ticker",
            row_count=None,
            entity_count=None,
            source="postgres",
        ),
        _memory_level_summary(
            level="company",
            label="Company Memory",
            status=str(company_memory.get("status") or "unknown"),
            scope=scoped_ticker or "all_tickers",
            row_count=company_entries,
            entity_count=(
                int(summary.get("company_memory_ticker_count") or 0)
                if not scoped_ticker
                else (1 if company_entries > 0 else 0)
            ),
            source="company_memory.sqlite",
        ),
        _memory_level_summary(
            level="sector",
            label="Sector Memory",
            status=str(market_memory.get("status") or "unknown"),
            scope=str(market_memory.get("sector") or "all_sectors"),
            row_count=int(sector_count or 0),
            entity_count=(
                int(summary.get("market_memory_sector_count") or 0)
                if not scoped_ticker
                else (1 if int(sector_count or 0) > 0 else 0)
            ),
            source="market_memory.sqlite",
        ),
        _memory_level_summary(
            level="macro",
            label="Macro Memory",
            status=str(market_memory.get("status") or "unknown"),
            scope="macro_topics",
            row_count=int(macro_count or 0),
            entity_count=int(summary.get("market_memory_macro_topic_count") or 0),
            source="market_memory.sqlite",
        ),
        _memory_level_summary(
            level="strategy",
            label="Strategy / Thesis Memory",
            status=str(user_thesis_memory.get("status") or "unknown"),
            scope=scoped_ticker or "all_tickers",
            row_count=strategy_rows,
            entity_count=(
                int(summary.get("user_thesis_ticker_count") or 0)
                if not scoped_ticker
                else (1 if strategy_rows > 0 else 0)
            ),
            source="user_thesis_memory.sqlite",
        ),
        _memory_level_summary(
            level="session",
            label="Session Memory",
            status="outside_index",
            scope="conversation_sessions",
            row_count=None,
            entity_count=None,
            source="openviking + cockpit recency",
        ),
        _memory_level_summary(
            level="operational",
            label="Operational State",
            status="outside_reasoning_memory",
            scope="jobs_alerts_feedback_workspace",
            row_count=None,
            entity_count=None,
            source="cockpit state + reports",
        ),
    ]


def _manual_memory_metadata(
    metadata: dict[str, Any],
    *,
    note: str | None,
) -> dict[str, Any]:
    payload = dict(metadata or {})
    payload.setdefault("manual", True)
    if note:
        payload["manual_note"] = str(note).strip()
    return payload


def _memory_error_status(detail: str) -> int:
    lowered = detail.lower()
    if "not found" in lowered or "no active" in lowered:
        return 404
    return 400


def _resolve_market_add_payload(request: MarketMemoryAddRequest) -> dict[str, Any]:
    ticker = _validate_ticker(request.ticker) if request.ticker else None
    linked_tickers: list[str] = []
    if ticker:
        linked_tickers.append(ticker)
    for raw in request.linked_tickers:
        candidate = _validate_ticker(raw)
        if candidate not in linked_tickers:
            linked_tickers.append(candidate)

    payload: dict[str, Any] = {
        "scope": request.scope,
        "signal_type": request.type,
        "statement": request.statement,
        "confidence": request.confidence,
        "materiality": request.materiality,
        "persistence": request.persistence,
        "supersedes": request.supersedes,
        "contradicts": request.contradicts,
        "metadata": _manual_memory_metadata(request.metadata, note=request.note),
    }

    if request.scope == "sector":
        sector = str(request.sector or "").strip()
        if not sector and ticker:
            from app.services.analysis.sector_comparison import get_sector_for_ticker

            sector = str(get_sector_for_ticker(ticker) or "").strip()
        if not sector:
            raise ValueError("sector is required for sector market memory entries")
        payload["sector"] = sector
        payload["linked_tickers"] = linked_tickers
        return payload

    macro_topic = str(request.macro_topic or "").strip()
    if not macro_topic:
        raise ValueError("macro_topic is required for macro market memory entries")
    payload["macro_topic"] = macro_topic
    return payload


def _resolve_user_thesis_proposal_payload(
    request: UserThesisProposalRequest,
) -> dict[str, Any]:
    ticker = _validate_ticker(request.ticker)
    statement = str(request.statement or "").strip()
    if not statement:
        raise ValueError("statement must not be empty")
    metadata = _manual_memory_metadata(request.metadata, note=request.note)
    metadata["is_supporting"] = bool(request.is_supporting)
    return {
        "ticker": ticker,
        "proposal_type": request.proposal_type,
        "statement": statement,
        "signal": request.signal,
        "confidence": float(request.confidence),
        "metadata": metadata,
        "requested_by": "cockpit_user",
    }


# ---------------------------------------------------------------------------
# GET /api/context/memory
# ---------------------------------------------------------------------------


@router.get("/memory")
def get_memory_context(
    ticker: str,
    company_memory_entries_limit: int = Query(default=400, ge=1, le=2000),
    company_memory_change_limit: int = Query(default=400, ge=1, le=2000),
    market_memory_limit: int = Query(default=300, ge=1, le=2000),
    user_thesis_entries_limit: int = Query(default=200, ge=1, le=2000),
    user_thesis_proposals_limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    ticker = _validate_ticker(ticker)
    errors: list[str] = []

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

    user_thesis_memory, err = _load_user_thesis_memory(
        ticker,
        entries_limit=user_thesis_entries_limit,
        proposals_limit=user_thesis_proposals_limit,
    )
    if err:
        errors.append(f"user_thesis_memory: {err}")

    summary = {
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
        "market_memory_sector": market_memory.get("sector"),
        "user_thesis_entry_count": int(
            user_thesis_memory.get(
                "entries_total", len(user_thesis_memory.get("entries") or [])
            )
            or 0
        ),
        "user_thesis_proposal_count": int(
            user_thesis_memory.get(
                "proposals_total", len(user_thesis_memory.get("proposals") or [])
            )
            or 0
        ),
    }

    return {
        "ticker": ticker,
        "summary": summary,
        "memory_levels": _build_memory_level_summaries(
            summary=summary,
            company_memory=company_memory,
            market_memory=market_memory,
            user_thesis_memory=user_thesis_memory,
            scoped_ticker=ticker,
        ),
        "company_memory": company_memory,
        "market_memory": market_memory,
        "user_thesis_memory": user_thesis_memory,
        "backend_version": "1.2",
        "errors": errors,
    }


@router.get("/memory/index")
def get_memory_index_context(
    company_memory_entries_limit: int = Query(default=5000, ge=1, le=20000),
    company_memory_change_limit: int = Query(default=2000, ge=1, le=20000),
    market_sector_limit: int = Query(default=5000, ge=1, le=20000),
    market_macro_limit: int = Query(default=5000, ge=1, le=20000),
    user_thesis_entries_limit: int = Query(default=5000, ge=1, le=20000),
    user_thesis_proposals_limit: int = Query(default=5000, ge=1, le=20000),
) -> dict[str, Any]:
    errors: list[str] = []

    company_memory, err = _load_company_memory_index(
        entries_limit=company_memory_entries_limit,
        change_log_limit=company_memory_change_limit,
    )
    if err:
        errors.append(f"company_memory: {err}")

    market_memory, err = _load_market_memory_index(
        sector_limit=market_sector_limit,
        macro_limit=market_macro_limit,
    )
    if err:
        errors.append(f"market_memory: {err}")

    user_thesis_memory, err = _load_user_thesis_memory_index(
        entries_limit=user_thesis_entries_limit,
        proposals_limit=user_thesis_proposals_limit,
    )
    if err:
        errors.append(f"user_thesis_memory: {err}")

    summary = {
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
        "company_memory_ticker_count": int(company_memory.get("ticker_count", 0) or 0),
        "market_memory_item_count": int(
            market_memory.get("items_total", len(market_memory.get("items") or []))
            or 0
        ),
        "market_memory_sector_count": int(market_memory.get("sector_count", 0) or 0),
        "market_memory_macro_topic_count": int(
            market_memory.get("macro_topic_count", 0) or 0
        ),
        "user_thesis_entry_count": int(
            user_thesis_memory.get(
                "entries_total", len(user_thesis_memory.get("entries") or [])
            )
            or 0
        ),
        "user_thesis_proposal_count": int(
            user_thesis_memory.get(
                "proposals_total", len(user_thesis_memory.get("proposals") or [])
            )
            or 0
        ),
        "user_thesis_ticker_count": int(user_thesis_memory.get("ticker_count", 0) or 0),
    }

    return {
        "ticker": None,
        "summary": summary,
        "memory_levels": _build_memory_level_summaries(
            summary=summary,
            company_memory=company_memory,
            market_memory=market_memory,
            user_thesis_memory=user_thesis_memory,
        ),
        "company_memory": company_memory,
        "market_memory": market_memory,
        "user_thesis_memory": user_thesis_memory,
        "backend_version": "1.3",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# POST /api/context/memory/*
# ---------------------------------------------------------------------------


@router.post(
    "/memory/company/add",
    dependencies=[Depends(require_api_key)],
)
def add_company_memory_note(request: CompanyMemoryAddRequest) -> dict[str, Any]:
    ticker = _validate_ticker(request.ticker)
    statement = str(request.statement or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail="statement must not be empty")

    try:
        from app.services.company_memory import add_manual_company_memory_entry

        result = add_manual_company_memory_entry(
            ticker,
            signal_type=str(request.type or "").strip().lower(),
            statement=statement,
            confidence=float(request.confidence),
            materiality=float(request.materiality),
            persistence=str(request.persistence or "medium").strip().lower(),
            supersedes=request.supersedes,
            contradicts=request.contradicts,
            metadata=_manual_memory_metadata(request.metadata, note=request.note),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("manual company memory add failed for %s", ticker)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True, "ticker": ticker, **result}


@router.post(
    "/memory/company/expire",
    dependencies=[Depends(require_api_key)],
)
def expire_company_memory_note(request: CompanyMemoryExpireRequest) -> dict[str, Any]:
    ticker = _validate_ticker(request.ticker)

    try:
        from app.services.company_memory import expire_company_memory_entry

        result = expire_company_memory_entry(
            ticker,
            int(request.entry_id),
            reason=request.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "manual company memory expiry failed for %s entry %s",
            ticker,
            request.entry_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True, "ticker": ticker, **result}


@router.post(
    "/memory/market/add",
    dependencies=[Depends(require_api_key)],
)
def add_market_memory_note(request: MarketMemoryAddRequest) -> dict[str, Any]:
    statement = str(request.statement or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail="statement must not be empty")

    try:
        from app.services.market_memory import add_manual_market_memory_entry
        result = add_manual_market_memory_entry(**_resolve_market_add_payload(request))
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("manual market memory add failed for scope %s", request.scope)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response: dict[str, Any] = {"ok": True, **result}
    if request.ticker:
        response["ticker"] = _validate_ticker(request.ticker)
    return response


@router.post(
    "/memory/market/expire",
    dependencies=[Depends(require_api_key)],
)
def expire_market_memory_note(request: MarketMemoryExpireRequest) -> dict[str, Any]:
    try:
        from app.services.market_memory import expire_market_memory_entry

        result = expire_market_memory_entry(
            scope=request.scope,
            entry_id=int(request.entry_id),
            reason=request.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "manual market memory expiry failed for %s entry %s",
            request.scope,
            request.entry_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True, **result}


# ---------------------------------------------------------------------------
# /api/context/thesis*
# ---------------------------------------------------------------------------


@router.get("/thesis")
def get_user_thesis_context(
    ticker: str,
    entries_limit: int = Query(default=200, ge=1, le=2000),
    proposals_limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    ticker = _validate_ticker(ticker)
    payload, err = _load_user_thesis_memory(
        ticker,
        entries_limit=entries_limit,
        proposals_limit=proposals_limit,
    )
    errors = [f"user_thesis_memory: {err}"] if err else []
    return {
        "ticker": ticker,
        "summary": {
            "entry_count": int(
                payload.get("entries_total", len(payload.get("entries") or [])) or 0
            ),
            "proposal_count": int(
                payload.get(
                    "proposals_total", len(payload.get("proposals") or [])
                )
                or 0
            ),
        },
        "user_thesis_memory": payload,
        "errors": errors,
    }


@router.post(
    "/thesis/proposals",
    dependencies=[Depends(require_api_key)],
)
def create_user_thesis_proposal(request: UserThesisProposalRequest) -> dict[str, Any]:
    try:
        from app.services.user_thesis_memory import UserThesisMemoryStore

        store = UserThesisMemoryStore()
        proposal = store.create_proposal(**_resolve_user_thesis_proposal_payload(request))
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("user thesis proposal creation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "proposal": proposal}


@router.post(
    "/thesis/proposals/{proposal_id}/confirm",
    dependencies=[Depends(require_api_key)],
)
def confirm_user_thesis_proposal(
    proposal_id: str,
    request: UserThesisConfirmRequest,
) -> dict[str, Any]:
    try:
        from app.services.user_thesis_memory import UserThesisMemoryStore

        store = UserThesisMemoryStore()
        proposal = store.confirm_proposal(proposal_id, note=request.note)
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("user thesis proposal confirmation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "proposal": proposal}


@router.post(
    "/thesis/proposals/{proposal_id}/reject",
    dependencies=[Depends(require_api_key)],
)
def reject_user_thesis_proposal(
    proposal_id: str,
    request: UserThesisRejectRequest,
) -> dict[str, Any]:
    try:
        from app.services.user_thesis_memory import UserThesisMemoryStore

        store = UserThesisMemoryStore()
        proposal = store.reject_proposal(proposal_id, note=request.note)
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("user thesis proposal rejection failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "proposal": proposal}


@router.post(
    "/thesis/proposals/{proposal_id}/apply",
    dependencies=[Depends(require_api_key)],
)
def apply_user_thesis_proposal(proposal_id: str) -> dict[str, Any]:
    try:
        from app.services.user_thesis_memory import UserThesisMemoryStore

        store = UserThesisMemoryStore()
        result = store.apply_confirmed_proposal(proposal_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=_memory_error_status(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("user thesis proposal apply failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, **result}


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
    announcement_context_fallback_used = False
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
        warn_on_missing_table=False,
    )
    if err:
        if _is_missing_table_error(err):
            errors.append(
                f"announcement_context: {err}; using documents_pdf_excerpt fallback"
            )
            announcement_context_fallback_used = True
            announcement_context = _build_document_announcement_context(
                docs,
                limit=announcements_limit,
            )
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
        "announcement_context_fallback_used": announcement_context_fallback_used,
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
    user_thesis_entries_limit: int = Query(default=200, ge=1, le=2000),
    user_thesis_proposals_limit: int = Query(default=200, ge=1, le=2000),
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

    user_thesis_memory, err = _load_user_thesis_memory(
        ticker,
        entries_limit=user_thesis_entries_limit,
        proposals_limit=user_thesis_proposals_limit,
    )
    if err:
        errors.append(f"user_thesis_memory: {err}")

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
        "user_thesis_entry_count": int(
            user_thesis_memory.get(
                "entries_total", len(user_thesis_memory.get("entries") or [])
            )
            or 0
        ),
        "user_thesis_proposal_count": int(
            user_thesis_memory.get(
                "proposals_total", len(user_thesis_memory.get("proposals") or [])
            )
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
        "user_thesis_memory": user_thesis_memory,
        "backend_version": "1.1",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# GET /api/context/verification
# ---------------------------------------------------------------------------


def _build_verification_context(
    db: Session,
    *,
    ticker: str | None,
    failures_limit: int,
    low_confidence_threshold: float,
    low_confidence_limit: int,
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


def _verification_outcome_summary(
    payload: Mapping[str, Any],
) -> tuple[bool, str]:
    extraction_failures = payload.get("extraction_failures")
    low_confidence_financials = payload.get("low_confidence_financials")
    errors = payload.get("errors")
    failures_count = len(extraction_failures) if isinstance(extraction_failures, list) else 0
    low_confidence_count = (
        len(low_confidence_financials) if isinstance(low_confidence_financials, list) else 0
    )
    error_count = len(errors) if isinstance(errors, list) else 0
    passed = failures_count == 0 and low_confidence_count == 0 and error_count == 0
    if passed:
        return True, "No extraction failures or low-confidence financial rows found."
    parts: list[str] = []
    if failures_count:
        parts.append(f"{failures_count} extraction failure(s)")
    if low_confidence_count:
        parts.append(f"{low_confidence_count} low-confidence financial row(s)")
    if error_count:
        parts.append(f"{error_count} backend verification error(s)")
    return False, ", ".join(parts)


@router.get("/verification")
def get_verification_context(
    ticker: str | None = Query(default=None),
    failures_limit: int = Query(default=100, ge=1, le=500),
    low_confidence_threshold: float = Query(default=0.4, ge=0.0, le=1.0),
    low_confidence_limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return _build_verification_context(
        db,
        ticker=ticker,
        failures_limit=failures_limit,
        low_confidence_threshold=low_confidence_threshold,
        low_confidence_limit=low_confidence_limit,
    )


@router.post("/verification/run", dependencies=[Depends(require_api_key)])
def run_verification_context(
    payload: VerificationRunRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    context = _build_verification_context(
        db,
        ticker=payload.ticker,
        failures_limit=payload.failures_limit,
        low_confidence_threshold=payload.low_confidence_threshold,
        low_confidence_limit=payload.low_confidence_limit,
    )
    passed, outcome_summary = _verification_outcome_summary(context)
    try:
        from app.services.cockpit_service import CockpitService

        service = CockpitService.get_instance()
        run = service.record_verification_run(
            ticker=payload.ticker or "BROAD",
            outcome_summary=outcome_summary,
            passed=passed,
        )
    except Exception as exc:
        logger.warning("record_verification_run failed: %s", exc)
        run = None
        context["errors"] = [
            *(context.get("errors") if isinstance(context.get("errors"), list) else []),
            f"verification_run_history: {exc}",
        ]

    return {"ok": True, **context, "run": run}


# ---------------------------------------------------------------------------
# GET /api/context/verification/runs
# ---------------------------------------------------------------------------


@router.get("/verification/runs")
def get_verification_runs(
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    """Return recent verification run history recorded by CockpitService."""
    try:
        from app.services.cockpit_service import CockpitService

        service = CockpitService.get_instance()
        runs = service.get_verification_runs(limit=limit)
        return {"ok": True, "runs": runs, "count": len(runs)}
    except Exception as exc:
        logger.warning("get_verification_runs failed: %s", exc)
        return {"ok": False, "runs": [], "error": str(exc)}
