#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


def _sqlite_path_from_url(database_url: str) -> Path:
    text = str(database_url or "").strip()
    if not text.startswith("sqlite:///"):
        raise RuntimeError(f"Only sqlite database URLs are supported for this script: {database_url}")
    raw_path = text[len("sqlite:///") :]
    if raw_path in {"", ":memory:"}:
        raise RuntimeError("In-memory sqlite database URL is not supported for this script.")
    return Path(raw_path).expanduser().resolve()


def _parse_iso_datetime(value: Any) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _age_bucket(value: Any, now_utc: dt.datetime) -> str:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return "unknown"
    age_days = max(0, int((now_utc - parsed).total_seconds() // 86400))
    if age_days <= 7:
        return "0_7d"
    if age_days <= 30:
        return "8_30d"
    if age_days <= 90:
        return "31_90d"
    if age_days <= 365:
        return "91_365d"
    return "366d_plus"


def _load_rows(db_path: Path) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        query = """
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
        """
        rows = conn.execute(query).fetchall()
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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit extraction backlog and latest-failure inventory.")
    ap.add_argument("--database-url", default=settings.database_url, help="Database URL (sqlite:///...)")
    ap.add_argument("--sample-limit", type=int, default=100, help="Maximum sample rows per inventory bucket.")
    ap.add_argument(
        "--out-json",
        default=str(REPO_ROOT / "reports" / "extraction_backlog_audit.json"),
        help="Output audit JSON path.",
    )
    return ap.parse_args()


def _is_downloaded(pdf_sha256: str) -> bool:
    token = str(pdf_sha256 or "").strip()
    if not token:
        return False
    if token.startswith("blocked_marketindex_"):
        return False
    return True


def main() -> int:
    args = parse_args()
    db_path = _sqlite_path_from_url(str(args.database_url))
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 2

    rows = _load_rows(db_path)
    now_utc = dt.datetime.now(dt.timezone.utc)
    sample_limit = int(max(1, args.sample_limit))

    downloaded_not_extracted: List[Dict[str, Any]] = []
    latest_failed: List[Dict[str, Any]] = []

    counts = {
        "downloaded_not_extracted_by_ticker": Counter(),
        "downloaded_not_extracted_by_doc_class": Counter(),
        "downloaded_not_extracted_by_age_bucket": Counter(),
        "latest_failed_by_ticker": Counter(),
        "latest_failed_by_doc_class": Counter(),
        "latest_failed_by_age_bucket": Counter(),
    }

    downloaded_count = 0
    for row in rows:
        downloaded = _is_downloaded(row.get("pdf_sha256", ""))
        latest_status = str(row.get("latest_status", "")).lower()
        age_source = row.get("published_at") or row.get("ingested_at")
        age_bucket = _age_bucket(age_source, now_utc)
        ticker = str(row.get("ticker") or "UNKNOWN").upper() or "UNKNOWN"
        doc_class = str(row.get("doc_class") or "unknown")

        if downloaded:
            downloaded_count += 1

        if downloaded and not latest_status:
            counts["downloaded_not_extracted_by_ticker"][ticker] += 1
            counts["downloaded_not_extracted_by_doc_class"][doc_class] += 1
            counts["downloaded_not_extracted_by_age_bucket"][age_bucket] += 1
            if len(downloaded_not_extracted) < sample_limit:
                downloaded_not_extracted.append(
                    {
                        "document_id": row.get("document_id"),
                        "ticker": ticker,
                        "doc_class": doc_class,
                        "age_bucket": age_bucket,
                        "published_at": row.get("published_at"),
                        "title": row.get("title"),
                        "pdf_path": row.get("pdf_path"),
                    }
                )

        if latest_status == "failed":
            counts["latest_failed_by_ticker"][ticker] += 1
            counts["latest_failed_by_doc_class"][doc_class] += 1
            counts["latest_failed_by_age_bucket"][age_bucket] += 1
            if len(latest_failed) < sample_limit:
                latest_failed.append(
                    {
                        "document_id": row.get("document_id"),
                        "ticker": ticker,
                        "doc_class": doc_class,
                        "age_bucket": age_bucket,
                        "published_at": row.get("published_at"),
                        "latest_extraction_created_at": row.get("latest_extraction_created_at"),
                        "latest_error": row.get("latest_error"),
                        "title": row.get("title"),
                    }
                )

    payload = {
        "generated_at_utc": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "database_url": str(args.database_url),
        "database_path": str(db_path),
        "totals": {
            "documents": len(rows),
            "downloaded_documents": int(downloaded_count),
            "downloaded_not_extracted": int(sum(counts["downloaded_not_extracted_by_ticker"].values())),
            "latest_failed": int(sum(counts["latest_failed_by_ticker"].values())),
        },
        "breakdown": {key: dict(counter) for key, counter in counts.items()},
        "samples": {
            "downloaded_not_extracted": downloaded_not_extracted,
            "latest_failed": latest_failed,
        },
    }

    out_path = Path(args.out_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        "[audit] "
        f"docs={payload['totals']['documents']} "
        f"downloaded_not_extracted={payload['totals']['downloaded_not_extracted']} "
        f"latest_failed={payload['totals']['latest_failed']} out={out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
