#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.pipeline import (  # noqa: E402
    EXTRACTION_FAILURE_TAXONOMY,
    classify_extraction_failure,
)


def _sqlite_path_from_url(database_url: str) -> Path:
    text = str(database_url or "").strip()
    if not text.startswith("sqlite:///"):
        raise RuntimeError(f"Only sqlite database URLs are supported for this script: {database_url}")
    raw_path = text[len("sqlite:///") :]
    if raw_path in {"", ":memory:"}:
        raise RuntimeError("In-memory sqlite database URL is not supported for this script.")
    return Path(raw_path).expanduser().resolve()


def _load_failure_rows(
    db_path: Path,
    *,
    latest_only: bool,
    limit: int,
    tickers: List[str],
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        ticker_clause = ""
        args: List[Any] = []
        if tickers:
            placeholders = ",".join("?" for _ in tickers)
            ticker_clause = f" AND UPPER(COALESCE(d.ticker, '')) IN ({placeholders})"
            args.extend([t.upper() for t in tickers])

        base_select = """
            SELECT
                er.document_id,
                er.status,
                er.error,
                er.structured_json,
                er.created_at,
                d.ticker,
                d.doc_class,
                d.doc_subtype,
                d.published_at,
                d.title,
                d.pdf_path
            FROM {source} er
            LEFT JOIN documents d ON d.document_id = er.document_id
            WHERE er.status = 'failed'
        """
        if latest_only:
            source = """
                (
                    SELECT
                        run_id,
                        document_id,
                        status,
                        error,
                        structured_json,
                        created_at,
                        ROW_NUMBER() OVER (PARTITION BY document_id ORDER BY created_at DESC) AS rn
                    FROM extraction_runs
                )
            """
            query = base_select.format(source=source) + " AND er.rn = 1" + ticker_clause + " ORDER BY er.created_at DESC LIMIT ?"
        else:
            source = "extraction_runs"
            query = base_select.format(source=source) + ticker_clause + " ORDER BY er.created_at DESC LIMIT ?"
        args.append(int(max(1, limit)))
        rows = cur.execute(query, tuple(args)).fetchall()
    finally:
        conn.close()

    out: List[Dict[str, Any]] = []
    for row in rows:
        structured = row["structured_json"]
        if isinstance(structured, str):
            try:
                structured = json.loads(structured)
            except Exception:
                structured = {"_raw": structured}
        elif structured is None:
            structured = {}
        out.append(
            {
                "document_id": str(row["document_id"] or ""),
                "status": str(row["status"] or ""),
                "error": str(row["error"] or ""),
                "structured_json": structured if isinstance(structured, dict) else {},
                "created_at": str(row["created_at"] or ""),
                "ticker": str(row["ticker"] or ""),
                "doc_class": str(row["doc_class"] or ""),
                "doc_subtype": str(row["doc_subtype"] or ""),
                "published_at": str(row["published_at"] or ""),
                "title": str(row["title"] or ""),
                "pdf_path": str(row["pdf_path"] or ""),
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Classify extraction failures into deterministic taxonomy buckets.")
    ap.add_argument("--database-url", default=settings.database_url, help="Database URL (sqlite:///...)")
    ap.add_argument("--all-runs", action="store_true", help="Include all failed runs instead of latest run per document.")
    ap.add_argument("--limit", type=int, default=4000, help="Maximum failed rows to classify.")
    ap.add_argument("--sample-per-class", type=int, default=5, help="Sample rows to keep per class.")
    ap.add_argument("--ticker", action="append", help="Optional ticker filter. Repeat or pass comma-separated values.")
    ap.add_argument(
        "--out-json",
        default=str(REPO_ROOT / "reports" / "extraction_failure_taxonomy.json"),
        help="Output report JSON path.",
    )
    return ap.parse_args()


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


def main() -> int:
    args = parse_args()
    db_path = _sqlite_path_from_url(str(args.database_url))
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 2

    tickers = _parse_tickers(args.ticker)
    rows = _load_failure_rows(
        db_path,
        latest_only=not bool(args.all_runs),
        limit=int(max(1, args.limit)),
        tickers=tickers,
    )

    counts: Dict[str, int] = {key: 0 for key in EXTRACTION_FAILURE_TAXONOMY}
    samples: Dict[str, List[Dict[str, Any]]] = {key: [] for key in EXTRACTION_FAILURE_TAXONOMY}
    for row in rows:
        bucket = classify_extraction_failure(row.get("error"), row.get("structured_json"))
        counts[bucket] = int(counts.get(bucket, 0)) + 1
        if len(samples.get(bucket, [])) < int(max(1, args.sample_per_class)):
            sample = {
                "document_id": row.get("document_id"),
                "ticker": row.get("ticker"),
                "doc_class": row.get("doc_class"),
                "created_at": row.get("created_at"),
                "error": row.get("error"),
                "title": row.get("title"),
            }
            samples.setdefault(bucket, []).append(sample)

    payload = {
        "generated_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "database_url": str(args.database_url),
        "database_path": str(db_path),
        "latest_only": not bool(args.all_runs),
        "limit": int(max(1, args.limit)),
        "tickers": tickers,
        "totals": {
            "rows_classified": len(rows),
            "categories_present": len([k for k, v in counts.items() if int(v) > 0]),
        },
        "counts_by_category": counts,
        "samples_by_category": {k: v for k, v in samples.items() if v},
    }

    out_path = Path(args.out_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[classify] rows={len(rows)} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
