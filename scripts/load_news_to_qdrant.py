#!/usr/bin/env python3
"""Sync news chunks from SQLite to Qdrant collection `news_chunks`."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
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
NEWS_CHUNKS_MODEL_FILE = REPO_ROOT / "financial-engine_v2" / "reports" / "news_chunks_embedding_model.txt"

logger = logging.getLogger(__name__)

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB  # noqa: E402


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
            dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=int(since_hours))
        ).isoformat().replace("+00:00", "Z")
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


def _build_chunk_payload(art: Dict[str, Any], idx: int, chunk_text: str = "") -> Dict[str, Any]:
    """Build the Qdrant point payload for one chunk of a news article.

    Uses `primary_ticker` (from article_relevance) when available.
    Falls back to the single linked ticker when there is exactly one, otherwise empty.
    """
    primary_ticker = str(art.get("primary_ticker") or "").strip()
    if not primary_ticker:
        tickers = art.get("tickers") or []
        primary_ticker = tickers[0] if len(tickers) == 1 else ""
    return {
        "corpus": "news",
        "article_id": art["article_id"],
        "chunk_id": f"news:{art['article_id']}:{idx}",
        "provider": art["provider"],
        "ticker": primary_ticker,
        "published_at": art["published_at"],
        "language": art["language"],
        "title": art["title"],
        "url": art["url"],
        "source_type": "news_article",
        "text": chunk_text,
    }


def _split_chunks(text: str, max_chars: int = 1200, overlap_words: int = 60) -> List[str]:
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
        return {"articles": 0, "chunks": 0, "upserted": 0}

    client = QdrantClient(url=qdrant_url)
    embed_model = str(getattr(settings, "embed_model", "nomic-embed-text"))
    ollama_url = str(getattr(settings, "ollama_url", "http://localhost:11434"))

    # --- Preflight: log resolved configuration before any writes ---
    logger.info(
        "news_chunks_sync preflight: collection=%s qdrant_url=%s embed_model=%s ollama_url=%s",
        collection, qdrant_url, embed_model, ollama_url,
    )

    # Check stored model marker — refuse to write if it conflicts with a populated collection.
    stored_model: Optional[str] = None
    if NEWS_CHUNKS_MODEL_FILE.exists():
        try:
            stored_model = NEWS_CHUNKS_MODEL_FILE.read_text(encoding="utf-8").strip() or None
        except OSError as exc:
            logger.warning("news_chunks_sync: unable to read model marker %s: %s", NEWS_CHUNKS_MODEL_FILE, exc)
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
            logger.warning("news_chunks_sync: preflight model-marker check failed: %s", exc)

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
                collection, existing_dim, existing_points, dim, existing_dim == dim,
            )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("news_chunks_sync: preflight collection-dimension check failed: %s", exc)

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

    # Write model marker after successful sync so future runs can verify consistency.
    try:
        NEWS_CHUNKS_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        NEWS_CHUNKS_MODEL_FILE.write_text(embed_model, encoding="utf-8")
        logger.info("news_chunks_sync: wrote model marker %s → '%s'", NEWS_CHUNKS_MODEL_FILE, embed_model)
    except OSError as exc:
        logger.warning("news_chunks_sync: unable to write model marker: %s", exc)

    stats = {"articles": len(articles), "chunks": total_chunks, "upserted": total_upserted}
    logger.info("news_chunks_sync complete: %s", stats)
    return stats


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ap = argparse.ArgumentParser(description="Sync news chunks from SQLite to Qdrant.")
    ap.add_argument("--db-path", default=str(DEFAULT_NEWS_ARTICLES_DB), help="news_articles SQLite path")
    ap.add_argument("--qdrant-url", default="http://localhost:6333", help="Qdrant service URL")
    ap.add_argument("--collection", default="news_chunks", help="Qdrant collection name")
    ap.add_argument("--batch-size", type=int, default=64, help="Upsert batch size")
    ap.add_argument("--since-hours", type=int, default=0, help="Only sync articles from the last N hours (0 = all)")
    args = ap.parse_args()
    since = int(args.since_hours) if int(args.since_hours) > 0 else None
    stats = sync_news_to_qdrant(
        db_path=args.db_path,
        qdrant_url=args.qdrant_url,
        collection=args.collection,
        batch_size=int(args.batch_size),
        since_hours=since,
    )
    import json
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
