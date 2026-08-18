#!/usr/bin/env python3
"""
Generate a unified daily health snapshot for the local-first research engine.

Output:
  reports/research_engine_health.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_CONTEXT_DB, resolve_path  # noqa: E402

DEFAULT_OUT_PATH = REPO_ROOT / "reports" / "research_engine_health.json"
DEFAULT_NEWS_DB = DEFAULT_NEWS_CONTEXT_DB
DEFAULT_COMPANY_DB = REPO_ROOT / "reports" / "qual_context" / "company.sqlite"
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
DEFAULT_NEWS_CORPUS = "news"
DEFAULT_ALLOWLIST_PATH = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"

FAILURE_CATEGORIES: Tuple[str, ...] = (
    "provider_network",
    "llm_invalid_json",
    "ocr_or_text_unavailable",
    "parser_timeout",
    "corrupted_pdf",
    "unknown",
)


@dataclass(frozen=True)
class HealthThresholds:
    news_low_ticker_coverage_pct: float = 10.0
    news_stale_hours: float = 48.0
    company_invalid_ratio_threshold_pct: float = 1.0
    company_invalid_min_count: int = 20
    structured_min_coverage_pct: float = 40.0
    backlog_max_downloaded_not_extracted: int = 200


def _safe_pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((100.0 * float(part)) / float(total), 4)


def _iso_utc(ts: dt.datetime) -> str:
    return ts.replace(microsecond=0, tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _sqlite_path_from_url(database_url: str) -> Optional[Path]:
    text = str(database_url or "").strip()
    if not text.startswith("sqlite:///"):
        return None
    raw = text[len("sqlite:///") :]
    if raw in {"", ":memory:"}:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _parse_ticker_blob(blob: str) -> List[str]:
    raw = str(blob or "").strip()
    if not raw:
        return []
    if "|" in raw:
        parts = [p for p in raw.split("|") if p.strip()]
    else:
        parts = [p for p in raw.replace(";", ",").replace("/", ",").split(",") if p.strip()]
    out: List[str] = []
    seen = set()
    for part in parts:
        token = "".join(ch for ch in part.upper().strip() if ch.isalnum() or ch in {".", "-"})
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        for token in body.replace(",", " ").split():
            sym = "".join(ch for ch in token.upper().strip() if ch.isalnum())
            if sym:
                out.add(sym)
    return out


def _list_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row[1]) for row in rows]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _probe_gpu_status() -> Dict[str, Any]:
    unavailable = {
        "nvml_available": False,
        "gpu_count": 0,
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "driver_version": "",
        "status": "unavailable",
    }
    try:
        import pynvml  # type: ignore
    except Exception:
        return unavailable

    try:
        pynvml.nvmlInit()
    except Exception:
        return unavailable

    try:
        count = int(pynvml.nvmlDeviceGetCount())
        total_mb = 0
        used_mb = 0
        for idx in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            total_mb += int(mem.total // (1024 * 1024))
            used_mb += int(mem.used // (1024 * 1024))
        driver = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver, bytes):
            driver_text = driver.decode("utf-8", errors="ignore")
        else:
            driver_text = str(driver or "")
        return {
            "nvml_available": True,
            "gpu_count": count,
            "memory_total_mb": total_mb,
            "memory_used_mb": used_mb,
            "driver_version": driver_text,
            "status": "healthy" if count > 0 else "degraded",
        }
    except Exception:
        return {
            "nvml_available": True,
            "gpu_count": 0,
            "memory_total_mb": 0,
            "memory_used_mb": 0,
            "driver_version": "",
            "status": "degraded",
        }
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def _classify_failure(error_text: Any, structured_json: Any) -> str:
    # Prefer canonical classifier from backend pipeline if it can be imported.
    try:
        backend_root = REPO_ROOT / "financial-engine_v2" / "backend"
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from app.services.pipeline import classify_extraction_failure  # type: ignore

        bucket = str(classify_extraction_failure(error_text, structured_json) or "").strip()
        if bucket in FAILURE_CATEGORIES:
            return bucket
    except Exception:
        pass

    text = str(error_text or "").lower()
    if not text and structured_json is not None:
        try:
            text = json.dumps(structured_json, ensure_ascii=False).lower()
        except Exception:
            text = str(structured_json).lower()
    if not text:
        return "unknown"
    if any(tok in text for tok in ("connection", "network", "dns", "refused", "httpx", "ssl")):
        return "provider_network"
    if any(tok in text for tok in ("invalid json", "jsondecodeerror", "expecting value", "json parse", "malformed json")):
        return "llm_invalid_json"
    if any(tok in text for tok in ("ocr", "no text", "text unavailable", "unable to extract text")):
        return "ocr_or_text_unavailable"
    if any(tok in text for tok in ("timeout", "timed out", "deadline exceeded")):
        return "parser_timeout"
    if any(tok in text for tok in ("corrupt", "not a pdf", "invalid pdf", "trailer not found", "pdfsyntaxerror")):
        return "corrupted_pdf"
    return "unknown"


def _build_news_section(
    *,
    db_path: Path,
    corpus: str,
    now_utc: dt.datetime,
    thresholds: HealthThresholds,
    ticker_allowlist: set[str],
) -> Dict[str, Any]:
    section: Dict[str, Any] = {
        "db_path": str(db_path),
        "corpus": corpus,
        "total_chunks": 0,
        "articles_estimated": 0,
        "min_doc_date": "",
        "max_doc_date": "",
        "ticker_coverage_pct": 0.0,
        "unknown_ticker_chunk_rate_pct": 0.0,
        "doc_date_coverage_pct": 0.0,
        "drift_flags": {
            "low_ticker_coverage": False,
            "stale_news": False,
        },
    }
    if not db_path.exists() or not db_path.is_file():
        section["drift_flags"]["low_ticker_coverage"] = True
        section["drift_flags"]["stale_news"] = True
        return section

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "context_chunks"):
            section["drift_flags"]["low_ticker_coverage"] = True
            section["drift_flags"]["stale_news"] = True
            return section
        cols = set(_list_columns(conn, "context_chunks"))
        has_corpus = "corpus" in cols
        where_sql = ""
        args: List[Any] = []
        if has_corpus and corpus:
            where_sql = "WHERE corpus = ?"
            args.append(corpus)

        agg = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_chunks,
                SUM(CASE WHEN COALESCE(ticker,'') <> '' THEN 1 ELSE 0 END) AS ticker_chunks,
                SUM(CASE WHEN COALESCE(doc_date,'') <> '' THEN 1 ELSE 0 END) AS doc_date_chunks,
                MIN(NULLIF(doc_date,'')) AS min_doc_date,
                MAX(NULLIF(doc_date,'')) AS max_doc_date,
                COUNT(
                    DISTINCT CASE
                        WHEN COALESCE(url,'') <> '' THEN url
                        WHEN COALESCE(file,'') <> '' THEN file
                        ELSE chunk_id
                    END
                ) AS articles_estimated
            FROM context_chunks
            {where_sql}
            """,
            tuple(args),
        ).fetchone()

        total_chunks = int((agg["total_chunks"] or 0) if agg is not None else 0)
        ticker_chunks = int((agg["ticker_chunks"] or 0) if agg is not None else 0)
        doc_date_chunks = int((agg["doc_date_chunks"] or 0) if agg is not None else 0)
        min_doc_date = str((agg["min_doc_date"] or "") if agg is not None else "")
        max_doc_date = str((agg["max_doc_date"] or "") if agg is not None else "")
        articles_estimated = int((agg["articles_estimated"] or 0) if agg is not None else 0)

        unknown_ticker_chunks = max(0, total_chunks - ticker_chunks)
        if ticker_allowlist and total_chunks > 0:
            ticker_sql = f"SELECT ticker FROM context_chunks {where_sql} AND COALESCE(ticker,'') <> ''" if where_sql else "SELECT ticker FROM context_chunks WHERE COALESCE(ticker,'') <> ''"
            for row in conn.execute(ticker_sql, tuple(args)):
                symbols = _parse_ticker_blob(str(row["ticker"] or ""))
                if not symbols:
                    continue
                if any(sym not in ticker_allowlist for sym in symbols):
                    unknown_ticker_chunks += 1

        stale_news = True
        if max_doc_date:
            try:
                max_date = dt.date.fromisoformat(max_doc_date)
                max_dt = dt.datetime.combine(max_date, dt.time.min, tzinfo=dt.timezone.utc)
                age_hours = (now_utc - max_dt).total_seconds() / 3600.0
                stale_news = age_hours > float(thresholds.news_stale_hours)
            except Exception:
                stale_news = True

        ticker_coverage_pct = _safe_pct(ticker_chunks, total_chunks)
        section.update(
            {
                "total_chunks": total_chunks,
                "articles_estimated": articles_estimated,
                "min_doc_date": min_doc_date,
                "max_doc_date": max_doc_date,
                "ticker_coverage_pct": ticker_coverage_pct,
                "unknown_ticker_chunk_rate_pct": _safe_pct(unknown_ticker_chunks, total_chunks),
                "doc_date_coverage_pct": _safe_pct(doc_date_chunks, total_chunks),
                "drift_flags": {
                    "low_ticker_coverage": ticker_coverage_pct < float(thresholds.news_low_ticker_coverage_pct),
                    "stale_news": stale_news,
                },
            }
        )
        return section
    finally:
        conn.close()


def _build_company_rag_section(
    *,
    db_path: Path,
    thresholds: HealthThresholds,
) -> Dict[str, Any]:
    section: Dict[str, Any] = {
        "total_chunks": 0,
        "invalid_company_ratio_pct": 0.0,
        "invalid_company_count": 0,
        "drift_flags": {"invalid_company_ratio_exceeded": False},
    }
    if not db_path.exists() or not db_path.is_file():
        return section

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "context_chunks"):
            return section
        cols = set(_list_columns(conn, "context_chunks"))
        where_sql = "WHERE corpus = 'company'" if "corpus" in cols else ""
        invalid_expr = "UPPER(COALESCE(company,'')) = 'UNKNOWN'"
        if "bad_metadata_reason" in cols:
            invalid_expr = f"({invalid_expr} OR COALESCE(bad_metadata_reason,'') <> '')"

        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_chunks,
                SUM(CASE WHEN {invalid_expr} THEN 1 ELSE 0 END) AS invalid_count
            FROM context_chunks
            {where_sql}
            """
        ).fetchone()

        total_chunks = int((row["total_chunks"] or 0) if row is not None else 0)
        invalid_count = int((row["invalid_count"] or 0) if row is not None else 0)
        invalid_ratio = _safe_pct(invalid_count, total_chunks)
        invalid_exceeded = (
            invalid_ratio > float(thresholds.company_invalid_ratio_threshold_pct)
            and invalid_count > int(thresholds.company_invalid_min_count)
        )
        section.update(
            {
                "total_chunks": total_chunks,
                "invalid_company_ratio_pct": invalid_ratio,
                "invalid_company_count": invalid_count,
                "drift_flags": {"invalid_company_ratio_exceeded": bool(invalid_exceeded)},
            }
        )
        return section
    finally:
        conn.close()


def _build_structured_and_backlog_section(database_url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    structured = {
        "documents_total": 0,
        "documents_extracted_ok": 0,
        "coverage_pct": 0.0,
    }
    backlog = {
        "downloaded_not_extracted": 0,
        "latest_failed": 0,
        "failure_categories": {key: 0 for key in FAILURE_CATEGORIES},
    }

    db_path = _sqlite_path_from_url(database_url)
    if db_path is None or not db_path.exists() or not db_path.is_file():
        return structured, backlog

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "documents"):
            return structured, backlog

        has_extractions = _table_exists(conn, "extraction_runs")
        if not has_extractions:
            docs_total = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] or 0)
            structured["documents_total"] = docs_total
            structured["coverage_pct"] = 0.0
            return structured, backlog

        agg = conn.execute(
            """
            WITH latest AS (
                SELECT
                    er.document_id,
                    er.status,
                    er.error,
                    er.structured_json,
                    er.created_at,
                    ROW_NUMBER() OVER (PARTITION BY er.document_id ORDER BY er.created_at DESC) AS rn
                FROM extraction_runs er
            )
            SELECT
                (SELECT COUNT(*) FROM documents) AS docs_total,
                (SELECT COUNT(*) FROM latest WHERE rn = 1 AND LOWER(COALESCE(status,'')) = 'ok') AS docs_ok,
                (
                    SELECT COUNT(*)
                    FROM documents d
                    LEFT JOIN latest l
                      ON l.document_id = d.document_id
                     AND l.rn = 1
                    WHERE COALESCE(d.pdf_sha256,'') <> ''
                      AND d.pdf_sha256 NOT LIKE 'blocked_marketindex_%'
                      AND COALESCE(l.status,'') = ''
                ) AS downloaded_not_extracted,
                (SELECT COUNT(*) FROM latest WHERE rn = 1 AND LOWER(COALESCE(status,'')) = 'failed') AS latest_failed
            """
        ).fetchone()

        docs_total = int((agg["docs_total"] or 0) if agg is not None else 0)
        docs_ok = int((agg["docs_ok"] or 0) if agg is not None else 0)
        downloaded_not_extracted = int((agg["downloaded_not_extracted"] or 0) if agg is not None else 0)
        latest_failed = int((agg["latest_failed"] or 0) if agg is not None else 0)
        structured.update(
            {
                "documents_total": docs_total,
                "documents_extracted_ok": docs_ok,
                "coverage_pct": _safe_pct(docs_ok, docs_total),
            }
        )
        backlog["downloaded_not_extracted"] = downloaded_not_extracted
        backlog["latest_failed"] = latest_failed

        for row in conn.execute(
            """
            WITH latest AS (
                SELECT
                    er.document_id,
                    er.status,
                    er.error,
                    er.structured_json,
                    er.created_at,
                    ROW_NUMBER() OVER (PARTITION BY er.document_id ORDER BY er.created_at DESC) AS rn
                FROM extraction_runs er
            )
            SELECT error, structured_json
            FROM latest
            WHERE rn = 1 AND LOWER(COALESCE(status,'')) = 'failed'
            """
        ):
            structured_json: Any = row["structured_json"]
            if isinstance(structured_json, str):
                try:
                    structured_json = json.loads(structured_json)
                except Exception:
                    pass
            bucket = _classify_failure(row["error"], structured_json)
            if bucket not in backlog["failure_categories"]:
                bucket = "unknown"
            backlog["failure_categories"][bucket] += 1

        return structured, backlog
    finally:
        conn.close()


def build_health_snapshot(
    *,
    database_url: str,
    news_db_path: Path,
    company_db_path: Path,
    out_json: Path,
    news_corpus: str,
    thresholds: HealthThresholds,
    now_utc: Optional[dt.datetime] = None,
    gpu_probe: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    ts = now_utc or dt.datetime.now(dt.timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    ts = ts.astimezone(dt.timezone.utc)

    ticker_allowlist = _load_allowlist(DEFAULT_ALLOWLIST_PATH)
    gpu = (gpu_probe or _probe_gpu_status)()
    news = _build_news_section(
        db_path=news_db_path,
        corpus=news_corpus,
        now_utc=ts,
        thresholds=thresholds,
        ticker_allowlist=ticker_allowlist,
    )
    company_rag = _build_company_rag_section(
        db_path=company_db_path,
        thresholds=thresholds,
    )
    structured, backlog = _build_structured_and_backlog_section(database_url)

    warning_flags = []
    if bool(news["drift_flags"]["low_ticker_coverage"]):
        warning_flags.append("news.low_ticker_coverage")
    if bool(news["drift_flags"]["stale_news"]):
        warning_flags.append("news.stale_news")
    if structured["coverage_pct"] < float(thresholds.structured_min_coverage_pct):
        warning_flags.append("structured_extraction.coverage_low")
    if backlog["downloaded_not_extracted"] > int(thresholds.backlog_max_downloaded_not_extracted):
        warning_flags.append("backlog.downloaded_not_extracted_high")

    invalid_company_exceeded = bool(company_rag["drift_flags"]["invalid_company_ratio_exceeded"])
    gpu_unavailable = not bool(gpu.get("nvml_available"))

    # CPU-only hosts are common; treat missing NVML/GPU as warning, not degraded.
    if gpu_unavailable:
        warning_flags.append("gpu.unavailable")

    if invalid_company_exceeded:
        overall_status = "degraded"
    elif warning_flags:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    payload: Dict[str, Any] = {
        "generated_at_utc": _iso_utc(ts),
        "gpu": {
            "nvml_available": bool(gpu.get("nvml_available", False)),
            "gpu_count": int(gpu.get("gpu_count", 0) or 0),
            "memory_total_mb": int(gpu.get("memory_total_mb", 0) or 0),
            "memory_used_mb": int(gpu.get("memory_used_mb", 0) or 0),
            "driver_version": str(gpu.get("driver_version", "") or ""),
            "status": str(gpu.get("status", "unavailable") or "unavailable"),
        },
        "news": news,
        "company_rag": company_rag,
        "structured_extraction": structured,
        "backlog": backlog,
        "overall_status": overall_status,
    }
    return payload


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate unified research engine health snapshot JSON.")
    ap.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="Core DB URL (sqlite:///...)")
    ap.add_argument("--news-db-path", default=str(DEFAULT_NEWS_DB), help="News context sqlite path")
    ap.add_argument("--company-db-path", default=str(DEFAULT_COMPANY_DB), help="Company context sqlite path")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_PATH), help="Output JSON path")
    ap.add_argument("--news-corpus", default=DEFAULT_NEWS_CORPUS, help="News corpus label (default: news)")

    ap.add_argument("--threshold-news-low-ticker-coverage-pct", type=float, default=10.0)
    ap.add_argument("--threshold-news-stale-hours", type=float, default=48.0)
    ap.add_argument("--threshold-company-invalid-ratio-pct", type=float, default=1.0)
    ap.add_argument("--threshold-company-invalid-min-count", type=int, default=20)
    ap.add_argument("--threshold-structured-coverage-pct", type=float, default=40.0)
    ap.add_argument("--threshold-backlog-download-not-extracted", type=int, default=200)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    thresholds = HealthThresholds(
        news_low_ticker_coverage_pct=float(args.threshold_news_low_ticker_coverage_pct),
        news_stale_hours=float(args.threshold_news_stale_hours),
        company_invalid_ratio_threshold_pct=float(args.threshold_company_invalid_ratio_pct),
        company_invalid_min_count=int(args.threshold_company_invalid_min_count),
        structured_min_coverage_pct=float(args.threshold_structured_coverage_pct),
        backlog_max_downloaded_not_extracted=int(args.threshold_backlog_download_not_extracted),
    )
    payload = build_health_snapshot(
        database_url=str(args.database_url),
        news_db_path=resolve_path(str(args.news_db_path)),
        company_db_path=Path(str(args.company_db_path)).expanduser().resolve(),
        out_json=Path(str(args.out_json)).expanduser().resolve(),
        news_corpus=str(args.news_corpus or DEFAULT_NEWS_CORPUS),
        thresholds=thresholds,
    )
    out_path = Path(str(args.out_json)).expanduser().resolve()
    _atomic_write_json(out_path, payload)
    print(
        "[health] "
        f"overall_status={payload['overall_status']} "
        f"news_chunks={payload['news']['total_chunks']} "
        f"company_chunks={payload['company_rag']['total_chunks']} "
        f"docs={payload['structured_extraction']['documents_total']} "
        f"out={out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
