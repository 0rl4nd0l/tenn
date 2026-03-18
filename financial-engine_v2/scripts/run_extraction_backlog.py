#!/usr/bin/env python3
import argparse
import concurrent.futures
import datetime as dt
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
ROOT_SCRIPTS = REPO_ROOT.parent / "scripts"
if str(ROOT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ROOT_SCRIPTS))

from app.core.config import settings  # noqa: E402
from app.services.pipeline import (  # noqa: E402
    classify_extraction_failure,
    process_document,
)
from health_guard import assert_healthy, load_health_snapshot  # noqa: E402


def _sqlite_path_from_url(database_url: str) -> Path:
    text = str(database_url or "").strip()
    if not text.startswith("sqlite:///"):
        raise RuntimeError(f"Only sqlite database URLs are supported for this script: {database_url}")
    raw_path = text[len("sqlite:///") :]
    if raw_path in {"", ":memory:"}:
        raise RuntimeError("In-memory sqlite database URL is not supported for this script.")
    return Path(raw_path).expanduser().resolve()


def _parse_tickers(values: List[str] | None) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for raw in values:
        for token in str(raw or "").split(","):
            ticker = token.strip().upper()
            if ticker:
                out.append(ticker)
    deduped: List[str] = []
    seen = set()
    for ticker in out:
        if ticker in seen:
            continue
        seen.add(ticker)
        deduped.append(ticker)
    return deduped


def _load_backlog_rows(db_path: Path, *, tickers: List[str], limit: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        args: List[Any] = []
        ticker_clause = ""
        if tickers:
            placeholders = ",".join("?" for _ in tickers)
            ticker_clause = f" AND UPPER(COALESCE(d.ticker, '')) IN ({placeholders})"
            args.extend([ticker.upper() for ticker in tickers])
        query = f"""
            WITH latest AS (
                SELECT
                    er.document_id,
                    er.status,
                    er.error,
                    er.created_at,
                    ROW_NUMBER() OVER (PARTITION BY er.document_id ORDER BY er.created_at DESC) AS rn
                FROM extraction_runs er
            )
            SELECT
                d.document_id,
                d.ticker,
                d.doc_class,
                d.doc_subtype,
                d.published_at,
                d.ingested_at,
                d.title,
                d.pdf_path,
                d.pdf_sha256,
                l.status AS latest_status,
                l.error AS latest_error,
                l.created_at AS latest_extraction_created_at
            FROM documents d
            LEFT JOIN latest l
                ON l.document_id = d.document_id
               AND l.rn = 1
            WHERE COALESCE(d.pdf_sha256, '') <> ''
              AND d.pdf_sha256 NOT LIKE 'blocked_marketindex_%'
              AND LOWER(COALESCE(l.status, '')) <> 'ok'
              {ticker_clause}
            ORDER BY COALESCE(d.published_at, d.ingested_at) DESC, d.document_id DESC
            LIMIT ?
        """
        args.append(int(max(1, limit)))
        rows = conn.execute(query, tuple(args)).fetchall()
    finally:
        conn.close()

    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "document_id": str(row["document_id"] or ""),
                "ticker": str(row["ticker"] or "").upper(),
                "doc_class": str(row["doc_class"] or ""),
                "doc_subtype": str(row["doc_subtype"] or ""),
                "published_at": str(row["published_at"] or ""),
                "ingested_at": str(row["ingested_at"] or ""),
                "title": str(row["title"] or ""),
                "pdf_path": str(row["pdf_path"] or ""),
                "pdf_sha256": str(row["pdf_sha256"] or ""),
                "latest_status": str(row["latest_status"] or ""),
                "latest_error": str(row["latest_error"] or ""),
                "latest_extraction_created_at": str(row["latest_extraction_created_at"] or ""),
            }
        )
    return out


def _process_one_document(document_id: str, max_retries: int, retry_delay_seconds: float) -> Dict[str, Any]:
    attempts = max(1, int(max_retries))
    last_error = ""
    last_category = "unknown"
    for attempt in range(1, attempts + 1):
        try:
            payload = process_document(document_id)
            status = str((payload or {}).get("extraction_status") or "").strip().lower()
            if status == "ok":
                return {
                    "ok": True,
                    "document_id": document_id,
                    "attempts": attempt,
                    "extraction_status": status,
                    "error": "",
                    "failure_category": "",
                }
            last_error = f"extraction_status_{status or 'unknown'}"
            last_category = classify_extraction_failure(last_error, {})
            if attempt < attempts:
                time.sleep(max(0.0, float(retry_delay_seconds)) * attempt)
                continue
        except Exception as exc:
            last_error = str(exc)
            last_category = classify_extraction_failure(last_error, {})
            retryable = last_category in {"provider_network", "parser_timeout", "unknown"}
            if attempt < attempts and retryable:
                time.sleep(max(0.0, float(retry_delay_seconds)) * attempt)
                continue
        break
    return {
        "ok": False,
        "document_id": document_id,
        "attempts": attempts,
        "extraction_status": "failed",
        "error": last_error,
        "failure_category": last_category,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run extraction over backlog docs with retry/backoff and taxonomy reporting.")
    ap.add_argument("--database-url", default=settings.database_url, help="Database URL (sqlite:///...)")
    ap.add_argument("--ticker", action="append", help="Optional ticker filter. Repeat or pass comma-separated values.")
    ap.add_argument("--limit", type=int, default=1000, help="Maximum backlog docs to process.")
    ap.add_argument("--concurrency", type=int, default=2, help="Worker concurrency for per-document isolation.")
    ap.add_argument("--max-retries", type=int, default=2, help="Max attempts per document.")
    ap.add_argument("--retry-delay-seconds", type=float, default=2.0, help="Base delay for retries/backoff.")
    ap.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=20,
        help="Abort run when this many failures occur consecutively.",
    )
    ap.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Keep embeddings enabled while processing backlog (default disables for stability).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Report backlog only; do not process documents.")
    ap.add_argument(
        "--health-json",
        default=str(REPO_ROOT.parent / "reports" / "research_engine_health.json"),
        help="Health snapshot JSON path used for pre-run gating.",
    )
    ap.add_argument(
        "--allow-warning",
        action="store_true",
        help="Allow execution when health snapshot overall_status=warning.",
    )
    ap.add_argument(
        "--report-json",
        default=str(REPO_ROOT / "reports" / "run_extraction_backlog_report.json"),
        help="Output report JSON path.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    db_path = _sqlite_path_from_url(str(args.database_url))
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 2

    if not bool(args.dry_run):
        snapshot = load_health_snapshot(str(args.health_json))
        assert_healthy(snapshot, allow_warning=bool(args.allow_warning))

    tickers = _parse_tickers(args.ticker)
    backlog = _load_backlog_rows(db_path, tickers=tickers, limit=int(max(1, args.limit)))
    if not backlog:
        print("[backlog] no documents to process")
        return 0

    started = dt.datetime.now(dt.timezone.utc)
    report: Dict[str, Any] = {
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "database_url": str(args.database_url),
        "database_path": str(db_path),
        "tickers": tickers,
        "settings": {
            "limit": int(max(1, args.limit)),
            "concurrency": int(max(1, args.concurrency)),
            "max_retries": int(max(1, args.max_retries)),
            "retry_delay_seconds": float(max(0.0, args.retry_delay_seconds)),
            "max_consecutive_failures": int(max(1, args.max_consecutive_failures)),
            "with_embeddings": bool(args.with_embeddings),
            "dry_run": bool(args.dry_run),
        },
        "totals": {
            "backlog_selected": len(backlog),
            "processed": 0,
            "processed_ok": 0,
            "failed": 0,
            "stopped_early": False,
        },
        "failure_categories": {},
        "errors": [],
    }

    if args.dry_run:
        out_path = Path(args.report_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report["totals"]["processed"] = 0
        report["backlog_sample"] = backlog[: min(50, len(backlog))]
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[backlog] dry_run selected={len(backlog)} out={out_path}")
        return 0

    old_enable_embeddings = bool(getattr(settings, "enable_embeddings", True))
    old_enable_qdrant = bool(getattr(settings, "enable_qdrant", True))
    if not bool(args.with_embeddings):
        settings.enable_embeddings = False
        settings.enable_qdrant = False

    failure_categories: Counter[str] = Counter()
    consecutive_failures = 0
    next_index = 0
    workers = int(max(1, args.concurrency))
    max_failures = int(max(1, args.max_consecutive_failures))

    pending: Dict[concurrent.futures.Future, Dict[str, Any]] = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while next_index < len(backlog) or pending:
                while next_index < len(backlog) and len(pending) < workers and not report["totals"]["stopped_early"]:
                    row = backlog[next_index]
                    next_index += 1
                    future = pool.submit(
                        _process_one_document,
                        str(row.get("document_id") or ""),
                        int(max(1, args.max_retries)),
                        float(max(0.0, args.retry_delay_seconds)),
                    )
                    pending[future] = row

                if not pending:
                    break

                done, _ = concurrent.futures.wait(
                    pending.keys(),
                    timeout=1.0,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for fut in done:
                    row = pending.pop(fut)
                    result = fut.result()
                    report["totals"]["processed"] += 1
                    if result.get("ok"):
                        report["totals"]["processed_ok"] += 1
                        consecutive_failures = 0
                    else:
                        report["totals"]["failed"] += 1
                        consecutive_failures += 1
                        category = str(result.get("failure_category") or "unknown")
                        failure_categories[category] += 1
                        if len(report["errors"]) < 500:
                            report["errors"].append(
                                {
                                    "document_id": row.get("document_id"),
                                    "ticker": row.get("ticker"),
                                    "doc_class": row.get("doc_class"),
                                    "attempts": result.get("attempts"),
                                    "error": result.get("error"),
                                    "failure_category": category,
                                }
                            )
                    if consecutive_failures >= max_failures:
                        report["totals"]["stopped_early"] = True
                        break

                if report["totals"]["stopped_early"]:
                    break
    finally:
        settings.enable_embeddings = old_enable_embeddings
        settings.enable_qdrant = old_enable_qdrant

    report["failure_categories"] = dict(failure_categories)
    ended = dt.datetime.now(dt.timezone.utc)
    report["ended_at_utc"] = ended.isoformat().replace("+00:00", "Z")
    report["duration_seconds"] = round((ended - started).total_seconds(), 3)
    report["totals"]["remaining_unprocessed"] = max(0, len(backlog) - int(report["totals"]["processed"]))

    out_path = Path(args.report_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        "[backlog] "
        f"selected={len(backlog)} processed={report['totals']['processed']} "
        f"ok={report['totals']['processed_ok']} failed={report['totals']['failed']} "
        f"stopped_early={report['totals']['stopped_early']} out={out_path}"
    )

    if int(report["totals"]["failed"]) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
