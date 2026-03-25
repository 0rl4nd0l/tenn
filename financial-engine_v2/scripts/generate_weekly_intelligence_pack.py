#!/usr/bin/env python3
"""
Generate a weekly intelligence pack from the last 7 days of documents.

Read-only: no DB or Qdrant modifications.
- Aggregates documents by ticker (counts, risk flags, high-risk docs).
- Identifies new tickers with >3 mentions.
- Runs RAG summary query and includes results.
- Writes structured JSON to reports/weekly/<timestamp>.json.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _normalize_database_url(repo_root: Path, database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        value = "sqlite:///./data/fe_local.db"
    if value.startswith("sqlite:///"):
        path_part = value[len("sqlite:///") :]
        if path_part.startswith("./") or not path_part.startswith("/"):
            return f"sqlite:///{(repo_root / path_part).resolve()}"
    return value


def _count_risk_flags(risk_summary: Any, risk_bullets: Any) -> int:
    """Count risk flags: one per risk_bullet; if only risk_summary, count 1."""
    bullets = risk_bullets if isinstance(risk_bullets, list) else []
    summary = (risk_summary or "").strip() if isinstance(risk_summary, str) else ""
    if bullets:
        return len(bullets)
    if summary:
        return 1
    return 0


def _is_high_risk(risk_summary: Any, risk_bullets: Any) -> bool:
    """Treat as high-risk if there is a risk summary or any risk bullets."""
    bullets = risk_bullets if isinstance(risk_bullets, list) else []
    summary = (risk_summary or "").strip() if isinstance(risk_summary, str) else ""
    return bool(summary or bullets)


def fetch_weekly_documents(
    database_url: str,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Read documents from the last N days with risk notes. Read-only."""
    from sqlalchemy import create_engine, text

    db_url = _normalize_database_url(REPO_ROOT, database_url)
    engine = create_engine(db_url, pool_pre_ping=True)
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    since_iso = since.isoformat()

    sql = text(
        """
        SELECT
            d.document_id,
            d.ticker,
            d.doc_class,
            d.published_at,
            d.ingested_at,
            r.risk_summary,
            r.risk_bullets
        FROM documents d
        LEFT JOIN asx_risk_notes r ON r.document_id = d.document_id
        WHERE d.ticker IS NOT NULL AND TRIM(d.ticker) <> ''
          AND (
            (d.published_at IS NOT NULL AND d.published_at >= :since_iso)
            OR (d.published_at IS NULL AND d.ingested_at >= :since_iso)
          )
        ORDER BY COALESCE(d.published_at, d.ingested_at) DESC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"since_iso": since_iso}).mappings().all()
    return [dict(r) for r in rows]


def aggregate_by_ticker(
    documents: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    int,
    int,
    list[str],
]:
    """
    Aggregate by ticker: doc count, risk_flags count, high_risk doc count.
    Returns (by_ticker, total_risk_flags, total_high_risk_docs, new_tickers_over_3_mentions).
    """
    by_ticker: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "document_count": 0,
            "risk_flags_count": 0,
            "high_risk_document_count": 0,
        }
    )
    total_risk_flags = 0
    total_high_risk_docs = 0

    for doc in documents:
        ticker = str(doc.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        risk_summary = doc.get("risk_summary")
        risk_bullets = doc.get("risk_bullets")
        flags = _count_risk_flags(risk_summary, risk_bullets)
        high = _is_high_risk(risk_summary, risk_bullets)

        by_ticker[ticker]["document_count"] += 1
        by_ticker[ticker]["risk_flags_count"] += flags
        if high:
            by_ticker[ticker]["high_risk_document_count"] += 1
        total_risk_flags += flags
        if high:
            total_high_risk_docs += 1

    new_tickers = [
        t
        for t, agg in by_ticker.items()
        if agg["document_count"] > 3
    ]
    new_tickers.sort()

    return dict(by_ticker), total_risk_flags, total_high_risk_docs, new_tickers


def run_rag_summary(api_base_url: str, query: str, top_k: int = 12) -> dict[str, Any]:
    """Call backend /rag/query (read-only). Returns payload or error stub."""
    from cockpit.integrations.backend_api import BackendApiClient

    client = BackendApiClient(api_base_url)
    result = client.rag_query(q=query, top_k=top_k, timeout=30.0)
    if result.get("ok"):
        return {"ok": True, "query": query, "rag_response": result.get("payload")}
    return {
        "ok": False,
        "query": query,
        "error": result.get("error", "RAG request failed"),
    }


def build_report(
    *,
    database_url: str,
    api_base_url: str,
    days: int = 7,
    rag_query: str = "Summarise key risks and catalysts this week",
    rag_top_k: int = 12,
) -> dict[str, Any]:
    """Build the weekly intelligence pack. Read-only."""
    documents = fetch_weekly_documents(database_url, days=days)
    by_ticker, total_risk_flags, total_high_risk_docs, new_tickers = aggregate_by_ticker(
        documents
    )

    rag_result = run_rag_summary(api_base_url, query=rag_query, top_k=rag_top_k)

    since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "window_since_utc": since.isoformat(),
        "document_count": len(documents),
        "ticker_count": len(by_ticker),
        "total_risk_flags": total_risk_flags,
        "total_high_risk_documents": total_high_risk_docs,
        "by_ticker": {k: dict(v) for k, v in sorted(by_ticker.items())},
        "new_tickers_over_3_mentions": new_tickers,
        "rag_summary": rag_result,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate weekly intelligence pack (read-only; no DB/Qdrant writes).",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db"),
        help="Database URL (read-only queries)",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("COCKPIT_BACKEND_API_URL", "http://localhost:8000"),
        help="Backend API base URL for /rag/query",
    )
    parser.add_argument("--days", type=int, default=7, help="Number of days in window")
    parser.add_argument(
        "--output-dir",
        default="reports/weekly",
        help="Output directory for JSON report",
    )
    parser.add_argument(
        "--rag-query",
        default="Summarise key risks and catalysts this week",
        help="RAG summary query text",
    )
    parser.add_argument("--rag-top-k", type=int, default=12, help="RAG top_k")
    args = parser.parse_args()

    report = build_report(
        database_url=args.database_url,
        api_base_url=args.api_base_url,
        days=max(1, args.days),
        rag_query=args.rag_query,
        rag_top_k=max(1, args.rag_top_k),
    )

    out_dir = REPO_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
