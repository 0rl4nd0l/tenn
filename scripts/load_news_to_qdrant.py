#!/usr/bin/env python3
"""Sync news chunks from SQLite to Qdrant collection `news_chunks`."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Marker file records the model used to build the news_chunks collection.
# Must match on every subsequent sync to prevent dimension corruption.
NEWS_CHUNKS_MODEL_FILE = (
    REPO_ROOT / "financial-engine_v2" / "reports" / "news_chunks_embedding_model.txt"
)

logger = logging.getLogger(__name__)

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB, DEFAULT_NEWS_CONTEXT_DB  # noqa: E402
from news_pipeline.utils import now_utc_iso, parse_datetime_utc  # noqa: E402


def _source_id_for_article(art: Dict[str, Any]) -> str:
    article_id = str(art.get("article_id") or "").strip()
    return f"news:{article_id}" if article_id else ""


def _read_news_memo_source_ids(memos_path: str | Path | None = None) -> Dict[str, Any]:
    try:
        from app.services.news_memo_extractor import DEFAULT_NEWS_MEMOS_PATH
    except Exception:
        DEFAULT_NEWS_MEMOS_PATH = None  # type: ignore[assignment]

    raw_path = memos_path or DEFAULT_NEWS_MEMOS_PATH
    if raw_path is None:
        return {"path": "", "source_ids": set(), "read_errors": 0, "exists": False}
    resolved = Path(raw_path).expanduser()
    path = resolved.resolve()
    if not path.exists():
        return {"path": str(path), "source_ids": set(), "read_errors": 0, "exists": False}

    source_ids: set[str] = set()
    read_errors = 0
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            text = raw_line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                read_errors += 1
                continue
            if not isinstance(row, dict):
                read_errors += 1
                continue
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                source_ids.add(source_id)
    return {
        "path": str(path),
        "source_ids": source_ids,
        "read_errors": read_errors,
        "exists": True,
    }


def build_memo_coverage_diagnostics(
    articles: List[Dict[str, Any]],
    *,
    memos_path: str | Path | None = None,
) -> Dict[str, Any]:
    eligible_ids: list[str] = []
    skipped = 0
    for art in articles:
        source_id = _source_id_for_article(art)
        text = str(art.get("text") or "").strip()
        if not source_id or not text:
            skipped += 1
            continue
        eligible_ids.append(source_id)

    memo_state = _read_news_memo_source_ids(memos_path)
    persisted_ids = memo_state["source_ids"]
    unique_eligible = set(eligible_ids)
    missing_ids = sorted(unique_eligible - persisted_ids)
    persisted = len(unique_eligible & persisted_ids)
    read_errors = int(memo_state.get("read_errors") or 0)
    if read_errors:
        status = "degraded"
    elif not unique_eligible:
        status = "empty"
    elif not missing_ids:
        status = "complete"
    elif persisted:
        status = "partial"
    else:
        status = "none"
    return {
        "status": status,
        "eligible": len(unique_eligible),
        "skipped": skipped,
        "persisted": persisted,
        "missing": len(missing_ids),
        "missing_samples": missing_ids[:10],
        "memos_path": str(memo_state.get("path") or ""),
        "memos_file_exists": bool(memo_state.get("exists")),
        "read_errors": read_errors,
    }


def dispatch_news_memos(
    articles: List[Dict[str, Any]],
    *,
    task: Any | None = None,
    memos_path: str | Path | None = None,
) -> Dict[str, Any]:
    before = build_memo_coverage_diagnostics(articles, memos_path=memos_path)
    dispatch_task = task
    import_error = ""
    if dispatch_task is None:
        try:
            from app.tasks.news_tasks import extract_news_memo_task  # noqa: E402

            dispatch_task = extract_news_memo_task
        except Exception as exc:
            import_error = str(exc)

    dispatched = 0
    failed = 0
    failed_samples: list[dict[str, str]] = []
    if dispatch_task is not None:
        for art in articles:
            source_id = _source_id_for_article(art)
            text = str(art.get("text") or "")
            if not source_id or not text.strip():
                continue
            memo_payload = {
                "source_id": source_id,
                "article_text": text[:12000],
                "provider": str(art.get("provider") or ""),
                "published_at": str(art.get("published_at") or ""),
            }
            try:
                dispatch_task.delay(memo_payload)
                dispatched += 1
            except Exception as exc:
                failed += 1
                if len(failed_samples) < 10:
                    failed_samples.append({"source_id": source_id, "error": str(exc)})

    after = build_memo_coverage_diagnostics(articles, memos_path=memos_path)
    if import_error:
        status = "unavailable"
    elif failed:
        status = "degraded"
    elif after["missing"] == 0:
        status = "complete"
    elif dispatched:
        status = "pending"
    else:
        status = after["status"]
    return {
        "status": status,
        "eligible": before["eligible"],
        "skipped": before["skipped"],
        "dispatched": dispatched,
        "dispatch_failed": failed,
        "dispatch_failed_samples": failed_samples,
        "persisted_before_dispatch": before["persisted"],
        "persisted_after_dispatch": after["persisted"],
        "missing_after_dispatch": after["missing"],
        "missing_samples": after["missing_samples"],
        "memos_path": after["memos_path"],
        "memos_file_exists": after["memos_file_exists"],
        "read_errors": after["read_errors"],
        "import_error": import_error,
        "completion_observable": False,
    }


def latest_provider_run_summary(db_path: str | Path) -> Dict[str, Any]:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        return {"status": "missing_db", "db_path": str(db)}
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT *
              FROM provider_runs
             ORDER BY started_at DESC, run_id DESC
             LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {"status": "missing_run", "db_path": str(db)}
        payload = dict(row)
        try:
            params = json.loads(str(payload.get("params_json") or "{}"))
        except json.JSONDecodeError:
            params = {}
        payload["params"] = params
        payload.pop("params_json", None)
        errors = conn.execute(
            """
            SELECT reason, COUNT(*) AS count
              FROM rejected_items
             WHERE run_id = ?
             GROUP BY reason
             ORDER BY reason
            """,
            (str(payload.get("run_id") or ""),),
        ).fetchall()
        payload["errors_by_class"] = {
            str(item["reason"]): int(item["count"] or 0) for item in errors
        }
        return payload
    finally:
        conn.close()


def validate_news_sqlite_freshness(
    db_path: str | Path,
    *,
    window_start_utc: str = "",
) -> Dict[str, Any]:
    db = Path(db_path).expanduser().resolve()
    if not db.exists():
        return {
            "status": "degraded",
            "reason": "missing_db",
            "db_path": str(db),
            "window_start_utc": window_start_utc,
        }
    conn = sqlite3.connect(str(db))
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='context_chunks'"
        ).fetchone()
        if table is None:
            return {
                "status": "degraded",
                "reason": "missing_context_chunks",
                "db_path": str(db),
                "window_start_utc": window_start_utc,
            }
        row = conn.execute(
            "SELECT COUNT(*) AS chunks, MAX(published_at) AS newest FROM context_chunks"
        ).fetchone()
    finally:
        conn.close()

    chunks = int((row[0] if row else 0) or 0)
    newest = str((row[1] if row else "") or "")
    newest_norm = parse_datetime_utc(newest) or ""
    window_start_norm = parse_datetime_utc(window_start_utc) or ""
    stale = bool(window_start_norm and (not newest_norm or newest_norm < window_start_norm))
    return {
        "status": "degraded" if stale else "fresh",
        "reason": "stale" if stale else "",
        "db_path": str(db),
        "chunks": chunks,
        "newest_published_at": newest,
        "window_start_utc": window_start_utc,
    }


def refresh_news_sqlite_fallback(
    *,
    articles_db_path: str | Path,
    context_db_path: str | Path,
    lane: str = "high_precision",
    window_start_utc: str = "",
) -> Dict[str, Any]:
    from news_pipeline.chunk_builder import build_news_chunks

    stats = build_news_chunks(
        from_db=Path(articles_db_path),
        to_db=Path(context_db_path),
        lane=lane,
        embed_backend="hash",
    )
    freshness = validate_news_sqlite_freshness(
        context_db_path,
        window_start_utc=window_start_utc,
    )
    return {
        "status": "success" if freshness["status"] == "fresh" else "degraded",
        "build": stats,
        "freshness": freshness,
    }


def write_summary_json(path: str | Path, payload: Dict[str, Any]) -> None:
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _chunk_point_id(chunk_id: str) -> str:
    """Deterministic integer-like ID derived from chunk_id via sha1."""
    digest = hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()
    # Qdrant accepts unsigned 64-bit integers; map first 16 hex chars to int.
    return str(int(digest[:16], 16))


def _iter_chunks(
    conn: sqlite3.Connection,
    since_hours: Optional[int],
) -> List[Dict[str, Any]]:
    """Read articles + entity_links from the news articles DB."""
    where_clauses = [
        "(a.language IN ('en', '') OR a.language IS NULL)",
        "a.quality_score >= 0.3",
    ]
    params: List[Any] = []

    if since_hours is not None and int(since_hours) > 0:
        cutoff = (
            (dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=int(since_hours)))
            .isoformat()
            .replace("+00:00", "Z")
        )
        where_clauses.append("a.published_at_utc >= ?")
        params.append(cutoff)

    where_sql = " AND ".join(where_clauses)
    sql = f"""
        SELECT
            a.article_id,
            a.canonical_url,
            a.title,
            a.description,
            a.body,
            a.provider_best AS provider,
            a.language,
            a.published_at_utc
        FROM articles a
        WHERE {where_sql}
        ORDER BY a.published_at_utc DESC, a.article_id DESC
    """
    rows = conn.execute(sql, tuple(params)).fetchall()
    if not rows:
        return []

    article_ids = [str(r["article_id"]) for r in rows]
    marks = ",".join(["?"] * len(article_ids))
    link_rows = conn.execute(
        f"""
        SELECT article_id, ticker
          FROM entity_links
         WHERE article_id IN ({marks})
         GROUP BY article_id, ticker
        """,
        tuple(article_ids),
    ).fetchall()
    tickers_by_article: Dict[str, List[str]] = {}
    for lr in link_rows:
        aid = str(lr["article_id"])
        tickers_by_article.setdefault(aid, []).append(str(lr["ticker"]))

    # Resolve primary ticker from article_relevance (is_primary=1, then highest relevance_score).
    # Falls back to empty string when article_relevance has no rows for an article.
    primary_ticker_by_article: Dict[str, str] = {}
    rel_rows = conn.execute(
        f"""
        SELECT article_id, ticker
          FROM article_relevance
         WHERE article_id IN ({marks})
         ORDER BY article_id ASC, is_primary DESC, relevance_score DESC
        """,
        tuple(article_ids),
    ).fetchall()
    for rr in rel_rows:
        aid = str(rr["article_id"])
        if aid not in primary_ticker_by_article:
            primary_ticker_by_article[aid] = str(rr["ticker"])

    out = []
    for r in rows:
        article_id = str(r["article_id"])
        title = str(r["title"] or "")
        description = str(r["description"] or "")
        body = str(r["body"] or "")
        parts = [p for p in (title, description, body) if p.strip()]
        text = "\n\n".join(parts)
        if not text.strip():
            continue
        linked = sorted(set(tickers_by_article.get(article_id, [])))
        out.append(
            {
                "article_id": article_id,
                "url": str(r["canonical_url"] or ""),
                "title": title,
                "provider": str(r["provider"] or ""),
                "language": str(r["language"] or "en"),
                "published_at": str(r["published_at_utc"] or ""),
                "tickers": linked,
                "primary_ticker": primary_ticker_by_article.get(article_id, ""),
                "text": text,
            }
        )
    return out


def _build_chunk_payload(
    art: Dict[str, Any], idx: int, chunk_text: str = ""
) -> Dict[str, Any]:
    """Build the Qdrant point payload for one chunk of a news article.

    Uses `primary_ticker` (from article_relevance) when available.
    Falls back to the single linked ticker when there is exactly one, otherwise empty.
    """
    primary_ticker = str(art.get("primary_ticker") or "").strip()
    if not primary_ticker:
        tickers = art.get("tickers") or []
        primary_ticker = tickers[0] if len(tickers) == 1 else ""
    linked_tickers = list(
        dict.fromkeys(
            str(t).strip().upper() for t in (art.get("tickers") or []) if str(t).strip()
        )
    )
    return {
        "corpus": "news",
        "article_id": art["article_id"],
        "chunk_id": f"news:{art['article_id']}:{idx}",
        "provider": art["provider"],
        "ticker": primary_ticker,
        "tickers": linked_tickers,
        "primary_ticker": primary_ticker,
        "published_at": art["published_at"],
        "language": art["language"],
        "title": art["title"],
        "url": art["url"],
        "source_type": "news_article",
        "text": chunk_text,
    }


def _split_chunks(
    text: str, max_chars: int = 1200, overlap_words: int = 60
) -> List[str]:
    """Simple character-level chunker with word-boundary overlap."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for word in words:
        wl = len(word) + 1
        if current_len + wl > max_chars and current:
            chunks.append(" ".join(current))
            overlap = current[-overlap_words:] if overlap_words > 0 else []
            current = list(overlap)
            current_len = sum(len(w) + 1 for w in current)
        current.append(word)
        current_len += wl
    if current:
        chunks.append(" ".join(current))
    return chunks


def sync_news_to_qdrant(
    db_path: str,
    qdrant_url: str = "http://localhost:6333",
    collection: str = "news_chunks",
    batch_size: int = 64,
    since_hours: Optional[int] = None,
) -> Dict[str, int]:
    """
    Read news chunks from SQLite and upsert into Qdrant.

    Safe to re-run (idempotent via deterministic point IDs).
    """
    from app.services.embeddings import ensure_collection, upsert_points
    from app.services.ollama import ollama_embed
    from app.core.config import settings
    from qdrant_client import QdrantClient

    db = Path(db_path).expanduser().resolve()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        articles = _iter_chunks(conn, since_hours)
    finally:
        conn.close()

    if not articles:
        return {
            "articles": 0,
            "chunks": 0,
            "upserted": 0,
            "memo_extraction": build_memo_coverage_diagnostics([]),
        }

    client = QdrantClient(url=qdrant_url)
    embed_model = str(getattr(settings, "embed_model", "nomic-embed-text"))
    ollama_url = str(getattr(settings, "ollama_url", "http://localhost:11434"))

    # --- Preflight: log resolved configuration before any writes ---
    logger.info(
        "news_chunks_sync preflight: collection=%s qdrant_url=%s embed_model=%s ollama_url=%s",
        collection,
        qdrant_url,
        embed_model,
        ollama_url,
    )

    # Check stored model marker — refuse to write if it conflicts with a populated collection.
    stored_model: Optional[str] = None
    if NEWS_CHUNKS_MODEL_FILE.exists():
        try:
            stored_model = (
                NEWS_CHUNKS_MODEL_FILE.read_text(encoding="utf-8").strip() or None
            )
        except OSError as exc:
            logger.warning(
                "news_chunks_sync: unable to read model marker %s: %s",
                NEWS_CHUNKS_MODEL_FILE,
                exc,
            )
    if stored_model and stored_model != embed_model:
        # Only block if the collection already has vectors.
        from app.services.embeddings import get_qdrant_collection_vector_config

        try:
            existing_cols = [c.name for c in client.get_collections().collections]
            if collection in existing_cols:
                cfg = get_qdrant_collection_vector_config(client, collection)
                existing_points = int(cfg.get("points_count") or 0)
                if existing_points > 0:
                    raise RuntimeError(
                        f"news_chunks_sync: embedding model mismatch — stored marker is '{stored_model}', "
                        f"configured model is '{embed_model}', collection '{collection}' has {existing_points} vectors. "
                        "Rebuild the collection with the correct model or update the marker file."
                    )
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(
                "news_chunks_sync: preflight model-marker check failed: %s", exc
            )

    # Determine vector dimension by embedding a probe text.
    probe_vec = ollama_embed(ollama_url, embed_model, ["probe"])[0]
    dim = len(probe_vec)
    logger.info("news_chunks_sync: probe_dim=%d embed_model=%s", dim, embed_model)

    # Check existing collection dimension before writing.
    try:
        existing_cols = [c.name for c in client.get_collections().collections]
        if collection in existing_cols:
            from app.services.embeddings import get_qdrant_collection_vector_config

            cfg = get_qdrant_collection_vector_config(client, collection)
            existing_dim = cfg.get("actual_dim")
            existing_points = int(cfg.get("points_count") or 0)
            if existing_dim is not None and existing_dim != dim:
                raise RuntimeError(
                    f"news_chunks_sync: dimension mismatch — probe_dim={dim} (model='{embed_model}'), "
                    f"collection '{collection}' has dim={existing_dim} with {existing_points} existing vectors. "
                    "Rebuild the collection with the correct model before syncing."
                )
            logger.info(
                "news_chunks_sync: collection '%s' exists dim=%s points=%d — probe_dim=%d match=%s",
                collection,
                existing_dim,
                existing_points,
                dim,
                existing_dim == dim,
            )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning(
            "news_chunks_sync: preflight collection-dimension check failed: %s", exc
        )

    ensure_collection(client, collection, dim)

    total_chunks = 0
    total_upserted = 0
    batch: List[Dict[str, Any]] = []

    def flush_batch() -> int:
        nonlocal batch
        if not batch:
            return 0
        texts = [p["_text"] for p in batch]
        vectors = ollama_embed(ollama_url, embed_model, texts)
        points = []
        for point, vec in zip(batch, vectors):
            points.append(
                {
                    "id": int(point["id"]),
                    "vector": vec,
                    "payload": point["payload"],
                }
            )
        upsert_points(client, collection, points)
        n = len(points)
        batch = []
        return n

    for art in articles:
        article_id = art["article_id"]
        chunks = _split_chunks(art["text"])
        for idx, chunk_text in enumerate(chunks):
            payload = _build_chunk_payload(art, idx, chunk_text)
            point_id = _chunk_point_id(payload["chunk_id"])
            batch.append({"id": point_id, "_text": chunk_text, "payload": payload})
            total_chunks += 1
            if len(batch) >= batch_size:
                total_upserted += flush_batch()

    total_upserted += flush_batch()

    # Dispatch news memo extraction for each article (best-effort). Extraction
    # completes asynchronously, so diagnostics report dispatch and current
    # persisted coverage instead of pretending completion is observable here.
    memo_diagnostics = dispatch_news_memos(articles)
    logger.info("news_chunks_sync memo diagnostics: %s", memo_diagnostics)

    # Write model marker after successful sync so future runs can verify consistency.
    try:
        NEWS_CHUNKS_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        NEWS_CHUNKS_MODEL_FILE.write_text(embed_model, encoding="utf-8")
        logger.info(
            "news_chunks_sync: wrote model marker %s → '%s'",
            NEWS_CHUNKS_MODEL_FILE,
            embed_model,
        )
    except OSError as exc:
        logger.warning("news_chunks_sync: unable to write model marker: %s", exc)

    stats = {
        "articles": len(articles),
        "chunks": total_chunks,
        "upserted": total_upserted,
        "memo_extraction": memo_diagnostics,
    }
    logger.info("news_chunks_sync complete: %s", stats)
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ap = argparse.ArgumentParser(description="Sync news chunks from SQLite to Qdrant.")
    ap.add_argument(
        "--db-path",
        default=str(DEFAULT_NEWS_ARTICLES_DB),
        help="news_articles SQLite path",
    )
    ap.add_argument(
        "--qdrant-url", default="http://localhost:6333", help="Qdrant service URL"
    )
    ap.add_argument(
        "--collection", default="news_chunks", help="Qdrant collection name"
    )
    ap.add_argument("--batch-size", type=int, default=64, help="Upsert batch size")
    ap.add_argument(
        "--since-hours",
        type=int,
        default=0,
        help="Only sync articles from the last N hours (0 = all)",
    )
    ap.add_argument(
        "--refresh-sqlite-fallback",
        action="store_true",
        help="Rebuild the canonical news.sqlite fallback after a successful Qdrant sync",
    )
    ap.add_argument(
        "--news-context-db",
        default=str(DEFAULT_NEWS_CONTEXT_DB),
        help="Canonical news.sqlite fallback path",
    )
    ap.add_argument(
        "--fallback-lane",
        default="high_precision",
        choices=["high_precision", "high_recall"],
        help="Lane used when rebuilding the news.sqlite fallback",
    )
    ap.add_argument(
        "--summary-json",
        default="",
        help="Optional path for a nightly sync summary JSON artifact",
    )
    args = ap.parse_args()
    since = int(args.since_hours) if int(args.since_hours) > 0 else None
    summary: Dict[str, Any] = {
        "generated_at_utc": now_utc_iso(),
        "provider": latest_provider_run_summary(args.db_path),
        "qdrant_sync": {"status": "not_run"},
        "sqlite_fallback": {"status": "not_run"},
        "memo_extraction": {"status": "not_run"},
    }
    try:
        stats = sync_news_to_qdrant(
            db_path=args.db_path,
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            batch_size=int(args.batch_size),
            since_hours=since,
        )
        summary["qdrant_sync"] = {"status": "success", **stats}
        summary["memo_extraction"] = stats.get("memo_extraction", {"status": "unknown"})
        provider_params = summary.get("provider", {}).get("params", {})
        window_start_utc = (
            str(provider_params.get("window_start_utc") or "")
            if isinstance(provider_params, dict)
            else ""
        )
        if bool(args.refresh_sqlite_fallback):
            summary["sqlite_fallback"] = refresh_news_sqlite_fallback(
                articles_db_path=args.db_path,
                context_db_path=args.news_context_db,
                lane=args.fallback_lane,
                window_start_utc=window_start_utc,
            )
        if args.summary_json:
            write_summary_json(args.summary_json, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        if summary.get("qdrant_sync", {}).get("status") == "not_run":
            summary["qdrant_sync"] = {"status": "error", "error": str(exc)}
        elif summary.get("sqlite_fallback", {}).get("status") == "not_run":
            summary["sqlite_fallback"] = {"status": "error", "error": str(exc)}
        else:
            summary["error"] = str(exc)
        if args.summary_json:
            write_summary_json(args.summary_json, summary)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
