from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import build_qualitative_context_db as ctx

from .db import NewsArticleStore
from .relevance import choose_primary_ticker, infer_ticker_relevance_from_text, serialize_ticker_relevance
from .utils import normalize_space

DEFAULT_PROVIDER_CORPUS_MAP = {
    "eodhd": "news_eodhd",
    "gdelt": "news_gdelt_v2",
    "rss": "news_rss_v2",
}


def _article_payload(title: str, description: str, body: str) -> str:
    return "\n\n".join(part for part in (normalize_space(title), normalize_space(description), normalize_space(body)) if part)


def _provider_to_corpus(provider: str, mapping: Mapping[str, str]) -> str:
    key = str(provider or "").strip().lower()
    if key in mapping:
        return mapping[key]
    if key:
        return f"news_{key}"
    return "news_v2"


def build_news_chunks(
    *,
    from_db: Path,
    to_db: Path,
    lane: str = "high_precision",
    provider_filter: Sequence[str] | None = None,
    from_utc: str = "",
    to_utc: str = "",
    provider_corpus_map: Mapping[str, str] | None = None,
    max_chars: int = 1200,
    overlap_words: int = 60,
    embed_backend: str = "hash",
    embed_model: str = "BAAI/bge-large-en-v1.5",
    ollama_endpoint: str = "http://127.0.0.1:11434",
    hash_dim: int = 384,
    st_device: str = "cpu",
    st_batch_size: int = 16,
) -> Dict[str, int]:
    mapping = dict(DEFAULT_PROVIDER_CORPUS_MAP)
    if provider_corpus_map:
        mapping.update({str(k).strip().lower(): str(v).strip() for k, v in provider_corpus_map.items()})

    store = NewsArticleStore(from_db)
    try:
        articles = store.get_articles_for_chunk_build(
            lane=lane,
            provider_filter=provider_filter,
            from_utc=from_utc,
            to_utc=to_utc,
        )
    finally:
        store.close()

    print(f"[chunk_builder] articles={len(articles)} embed_backend={embed_backend}", flush=True)

    # Ensure target schema exists even when we have no rows.
    ctx.store_sqlite([], [], Path(to_db).expanduser().resolve())

    # Delete existing chunks for these articles before rebuilding so stale tail chunks are removed.
    conn = sqlite3.connect(str(Path(to_db).expanduser().resolve()))
    try:
        cur = conn.cursor()
        for article in articles:
            article_id = str(article.get("article_id") or "").strip()
            if not article_id:
                continue
            cur.execute("DELETE FROM context_chunks WHERE chunk_id LIKE ?", (f"news:{article_id}:%",))
        conn.commit()
    finally:
        conn.close()

    rows_inserted = 0
    rows_skipped = 0
    article_count = 0
    batch_records: List[ctx.ChunkRecord] = []
    batch_texts: List[str] = []

    def flush() -> int:
        nonlocal batch_records, batch_texts
        if not batch_records:
            return 0
        vectors = ctx.embed_texts(
            batch_texts,
            backend=embed_backend,
            model_name=embed_model,
            ollama_endpoint=ollama_endpoint,
            hash_dim=hash_dim,
            st_device=st_device,
            st_batch_size=st_batch_size,
        )
        ctx.store_sqlite(batch_records, vectors, Path(to_db).expanduser().resolve())
        count = len(batch_records)
        batch_records = []
        batch_texts = []
        return count

    for article in articles:
        article_id = str(article.get("article_id") or "").strip()
        if not article_id:
            rows_skipped += 1
            continue
        title = str(article.get("title") or "")
        description = str(article.get("description") or "")
        body = str(article.get("body") or "")
        payload = _article_payload(title, description, body)
        if not payload:
            rows_skipped += 1
            continue

        chunks = ctx.chunk_text(payload, max_chars=max_chars, overlap_words=overlap_words)
        if not chunks:
            rows_skipped += 1
            continue
        article_count += 1
        if article_count % 50 == 0:
            print(f"[chunk_builder] progress articles={article_count} chunks_written={rows_inserted} pending_batch={len(batch_records)}", flush=True)
        provider = str(article.get("provider_best") or "").strip().lower()
        corpus = _provider_to_corpus(provider, mapping)
        linked_tickers = article.get("linked_tickers") or []
        ticker_blob = ctx.serialize_tickers(linked_tickers) if linked_tickers else ""
        ticker_relevance_json = str(article.get("ticker_relevance_json") or "")
        primary_ticker = str(article.get("primary_ticker") or "").strip()
        if linked_tickers and (not primary_ticker or not ticker_relevance_json):
            relevance_body = "\n\n".join(part for part in (description, body) if part)
            inferred_rows = infer_ticker_relevance_from_text(title=title, body=relevance_body, tickers=linked_tickers)
            if inferred_rows:
                primary_ticker = primary_ticker or choose_primary_ticker(inferred_rows, linked_tickers)
                ticker_relevance_json = ticker_relevance_json or serialize_ticker_relevance(inferred_rows)
        company = primary_ticker or (linked_tickers[0] if linked_tickers else "NEWS")
        doc_date = str(article.get("published_at_utc") or "").split("T")[0]
        source_name = str(article.get("source_name") or "")
        canonical_url = str(article.get("canonical_url") or "")

        for idx, chunk in enumerate(chunks):
            batch_records.append(
                ctx.ChunkRecord(
                    chunk_id=f"news:{article_id}:{idx}",
                    company=company,
                    file=canonical_url or f"article://{article_id}",
                    section="fulltext_context",
                    text=chunk,
                    corpus=corpus,
                    doc_type="news_article",
                    doc_date=doc_date,
                    source=source_name,
                    ticker=ticker_blob,
                    topic=provider,
                    url=canonical_url,
                    title=title,
                    published_at=str(article.get("published_at_utc") or ""),
                    ticker_relevance_json=ticker_relevance_json,
                )
            )
            batch_texts.append(chunk)
            if len(batch_records) >= 256:
                n = flush()
                rows_inserted += n
                print(f"[chunk_builder] batch flush articles_chunked={article_count} chunks_written={rows_inserted}", flush=True)

    rows_inserted += flush()
    print(f"[chunk_builder] done articles_chunked={article_count} chunks_written={rows_inserted} skipped={rows_skipped}", flush=True)
    return {
        "articles_seen": len(articles),
        "articles_chunked": article_count,
        "articles_skipped": rows_skipped,
        "chunks_written": rows_inserted,
    }
