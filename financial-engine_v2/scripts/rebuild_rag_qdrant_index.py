#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.services.pipeline import process_document  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wipe and rebuild Qdrant RAG index from existing local documents."
    )
    parser.add_argument(
        "--ticker",
        default="",
        help="Optional ticker symbol to restrict rebuild (e.g. BHP). Default: all tickers.",
    )
    parser.add_argument(
        "--since",
        default="",
        help="Only consider docs with published_at >= this ISO date (e.g. 2024-01-01).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max documents to process (0 = all selected).",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "rebuild_rag_qdrant_index_report.json"),
        help="Output report path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing Qdrant or DB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ticker_filter = args.ticker.strip().upper()
    if args.limit < 0:
        raise SystemExit("--limit must be >= 0")

    since_dt = _parse_dt(args.since)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "started_at": _utc_now(),
        "settings": {
            "ticker": ticker_filter or None,
            "since": args.since or None,
            "limit": args.limit,
        },
        "selected_count": 0,
        "processed_count": 0,
        "error_count": 0,
        "total_chunks": 0,
        "qdrant_count": None,
        "items": [],
    }

    db = SessionLocal()
    try:
        q = db.query(Document)
        if ticker_filter:
            q = q.filter(Document.ticker == ticker_filter)
        q = q.order_by(Document.published_at.desc().nullslast())
        rows = q.all()
        if since_dt:
            rows = [r for r in rows if r.published_at and r.published_at >= since_dt]
        if args.limit > 0:
            rows = rows[: args.limit]
        summary["selected_count"] = len(rows)

        if args.dry_run:
            plan = {
                "dry_run": True,
                "script": "rebuild_rag_qdrant_index",
                "settings": summary["settings"],
                "estimates": {
                    "docs_selected": len(rows),
                    "note": "Exact chunk/vector counts depend on PDF content and chunking at runtime.",
                },
            }
            print(json.dumps(plan, indent=2, default=str))
            return

        # Ensure embeddings/Qdrant are enabled; disable extraction for faster, RAG-only rebuild.
        settings.enable_embeddings = True
        settings.enable_qdrant = True
        settings.enable_extraction = False

        client = QdrantClient(url=settings.qdrant_url)
        # Wipe existing collection if present.
        try:
            client.delete_collection(collection_name=settings.qdrant_collection)
        except Exception:
            # If collection does not exist yet, ignore.
            pass

        for row in rows:
            item: dict[str, object] = {
                "document_id": str(row.document_id),
                "ticker": row.ticker,
                "published_at": str(row.published_at) if row.published_at else None,
                "title": row.title,
                "chunks": 0,
                "status": None,
                "error": None,
            }
            try:
                result = process_document(str(row.document_id))
                chunks = int(result.get("chunks", 0))
                item["chunks"] = chunks
                item["status"] = result.get("extraction_status", "unknown")
                summary["processed_count"] = int(summary["processed_count"]) + 1
                summary["total_chunks"] = int(summary["total_chunks"]) + chunks
            except Exception as exc:
                item["status"] = "error"
                item["error"] = str(exc)
                summary["error_count"] = int(summary["error_count"]) + 1
            summary["items"].append(item)

        # Verify Qdrant count after rebuild.
        try:
            count_result = client.count(
                collection_name=settings.qdrant_collection,
                exact=True,
            )
            summary["qdrant_count"] = int(getattr(count_result, "count", 0))
        except Exception as exc:
            summary["qdrant_count"] = f"error: {exc}"
            summary["error_count"] = int(summary["error_count"]) + 1
    finally:
        db.close()

    summary["ended_at"] = _utc_now()
    summary["status"] = "success" if int(summary["error_count"]) == 0 else "partial_failure"
    report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # Save vector baseline for verify_vector_baseline.py (only when we have a numeric count).
    qdrant_count = summary.get("qdrant_count")
    if isinstance(qdrant_count, int):
        baseline_path = REPO_ROOT / "reports" / "vector_baseline.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(
                {
                    "vector_count": qdrant_count,
                    "updated_at": _utc_now(),
                    "source": "rebuild_rag_qdrant_index",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[rebuild_rag_qdrant_index] baseline written to {baseline_path}", flush=True)

    print(
        f"[rebuild_rag_qdrant_index] ticker={ticker_filter or 'ALL'} "
        f"selected={summary['selected_count']} processed={summary['processed_count']} "
        f"chunks={summary['total_chunks']} qdrant_count={summary['qdrant_count']} "
        f"errors={summary['error_count']} report={report_path}",
        flush=True,
    )
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

