#!/usr/bin/env python3
"""Qualitative context DB builder and query interface.

Provides:
  - build_context_db(): populate context_chunks from ingested documents
  - query_sqlite(): retrieve relevant chunks by embedding similarity
  - ticker_blob_contains(): helper for ticker matching in pipe-delimited blobs

The DB schema uses a single table ``context_chunks`` with a JSON-serialized
embedding vector per chunk.  Three embedding backends are supported:
  - hash: deterministic bag-of-characters hashing (no ML, fast, low quality)
  - ollama: Ollama /api/embed endpoint
  - sentence-transformers: HuggingFace sentence-transformers
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import struct
import sys
from pathlib import Path
from typing import Any

import httpx

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS context_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL DEFAULT '',
    corpus TEXT NOT NULL DEFAULT 'company',
    doc_type TEXT NOT NULL DEFAULT '',
    doc_date TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    ticker TEXT NOT NULL DEFAULT '',
    source_filter TEXT NOT NULL DEFAULT '',
    file TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL DEFAULT '',
    source_domain TEXT NOT NULL DEFAULT '',
    embedding_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_cc_corpus ON context_chunks(corpus);
CREATE INDEX IF NOT EXISTS idx_cc_company ON context_chunks(company);
CREATE INDEX IF NOT EXISTS idx_cc_ticker ON context_chunks(ticker);
"""


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic hash-based embedding.  Not semantic, but consistent."""
    raw = text.lower().strip().encode("utf-8", errors="replace")
    digest = hashlib.sha512(raw).digest()
    while len(digest) < dim * 8:
        digest += hashlib.sha512(digest).digest()
    vec: list[float] = []
    for i in range(dim):
        byte_val = digest[i % len(digest)]
        vec.append((byte_val / 127.5) - 1.0)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-12:
        return [0.0] * dim
    return [v / norm for v in vec]


def _ollama_embed(texts: list[str], model: str, endpoint: str) -> list[list[float]]:
    """Embed via Ollama /api/embed endpoint."""
    url = f"{endpoint.rstrip('/')}/api/embed"
    payload = {"model": model, "input": texts}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code == 404:
            url = f"{endpoint.rstrip('/')}/api/embeddings"
            results = []
            for t in texts:
                r = client.post(url, json={"model": model, "prompt": t})
                r.raise_for_status()
                results.append(r.json().get("embedding", []))
            return results
        resp.raise_for_status()
        return resp.json().get("embeddings", [])


def _embed_texts(
    texts: list[str],
    backend: str,
    model_name: str,
    ollama_endpoint: str = "http://127.0.0.1:11434",
    hash_dim: int = 384,
    st_device: str = "auto",
    st_batch_size: int = 16,
) -> list[list[float]]:
    backend = (backend or "hash").strip().lower()
    if backend == "hash":
        return [_hash_embed(t, dim=hash_dim) for t in texts]
    if backend == "ollama":
        return _ollama_embed(texts, model_name, ollama_endpoint)
    if backend == "sentence-transformers":
        from sentence_transformers import SentenceTransformer  # type: ignore
        device = None if st_device == "auto" else st_device
        model = SentenceTransformer(model_name, device=device)
        vecs = model.encode(texts, batch_size=st_batch_size, show_progress_bar=False)
        return [v.tolist() for v in vecs]
    raise ValueError(f"Unknown embed backend: {backend}")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    val = dot / (norm_a * norm_b)
    if math.isnan(val) or math.isinf(val):
        return 0.0
    return val


def ticker_blob_contains(blob: str, symbol: str) -> bool:
    """Check if a pipe-delimited ticker blob contains the symbol."""
    blob_text = str(blob or "").strip()
    token = str(symbol or "").strip().upper()
    if not token:
        return False
    return f"|{token}|" in f"|{blob_text.strip('|')}|"


def query_sqlite(
    *,
    db_path: Any,
    query: str,
    backend: str = "hash",
    model_name: str = "hash",
    ollama_endpoint: str = "http://127.0.0.1:11434",
    hash_dim: int = 384,
    st_device: str = "auto",
    st_batch_size: int = 16,
    company: str = "",
    corpus_filter: str = "",
    doc_type_filter: str = "",
    date_from: str = "",
    date_to: str = "",
    top_k: int = 8,
    ticker_filter: str = "",
    source_filter: str = "",
    exclude_corpus_filter: str = "",
) -> list[tuple[float, dict[str, Any]]]:
    """Retrieve top-k chunks by embedding similarity."""
    db_file = Path(str(db_path)).expanduser().resolve()
    if not db_file.exists():
        return []

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        sql = "SELECT * FROM context_chunks WHERE 1=1"
        params: list[Any] = []
        if company:
            sql += " AND UPPER(company) = ?"
            params.append(company.upper())
        if corpus_filter:
            sql += " AND corpus = ?"
            params.append(corpus_filter)
        if exclude_corpus_filter:
            sql += " AND corpus != ?"
            params.append(exclude_corpus_filter)
        if doc_type_filter:
            sql += " AND doc_type = ?"
            params.append(doc_type_filter)
        if date_from:
            sql += " AND doc_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND doc_date <= ?"
            params.append(date_to)
        if ticker_filter:
            sql += " AND (UPPER(ticker) LIKE ? OR UPPER(company) = ?)"
            params.append(f"%{ticker_filter.upper()}%")
            params.append(ticker_filter.upper())
        if source_filter:
            sql += " AND source_filter = ?"
            params.append(source_filter)

        rows = conn.execute(sql, params).fetchall()
        if not rows:
            return []

        query_vec = _embed_texts(
            [query],
            backend=backend,
            model_name=model_name,
            ollama_endpoint=ollama_endpoint,
            hash_dim=hash_dim,
            st_device=st_device,
            st_batch_size=st_batch_size,
        )[0]

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            row_dict = dict(row)
            emb_json = row_dict.pop("embedding_json", "[]")
            try:
                stored_vec = json.loads(emb_json)
            except Exception:
                continue
            if not isinstance(stored_vec, list) or len(stored_vec) != len(query_vec):
                continue
            sim = _cosine_similarity(query_vec, stored_vec)
            scored.append((sim, row_dict))

        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]
    finally:
        conn.close()


def _simple_chunk(text: str, max_chars: int = 800) -> list[str]:
    """Split text into chunks, respecting paragraph and sentence boundaries."""
    chunks: list[str] = []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    current = ""
    for para in paragraphs:
        if not para:
            continue
        if len(current) + len(para) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunk = para[i : i + max_chars].strip()
                    if chunk:
                        chunks.append(chunk)
                current = ""
            else:
                current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def build_context_db(
    db_path: str,
    documents: list[dict[str, Any]],
    embed_backend: str = "hash",
    embed_model: str = "hash",
    ollama_endpoint: str = "http://127.0.0.1:11434",
    hash_dim: int = 384,
    chunk_max_chars: int = 800,
) -> dict[str, int]:
    """Build or extend the qualitative context DB from document dicts.

    Each document dict should have:
      - text: str (full extracted text)
      - ticker: str
      - title: str
      - doc_date: str (YYYY-MM-DD)
      - doc_type: str (optional)
      - file: str (optional, pdf path)
      - company: str (optional, defaults to ticker)
    """
    db_file = Path(db_path).expanduser().resolve()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    conn.executescript(SCHEMA_SQL)

    total_chunks = 0
    total_docs = 0

    for doc in documents:
        text = str(doc.get("text") or "").strip()
        if not text:
            continue
        ticker = str(doc.get("ticker") or "").strip().upper()
        title = str(doc.get("title") or "").strip()
        doc_date = str(doc.get("doc_date") or "").strip()
        doc_type = str(doc.get("doc_type") or "").strip()
        file_path = str(doc.get("file") or "").strip()
        company = str(doc.get("company") or ticker).strip().upper()

        chunks = _simple_chunk(text, max_chars=chunk_max_chars)
        if not chunks:
            continue

        embeddings = _embed_texts(
            chunks,
            backend=embed_backend,
            model_name=embed_model,
            ollama_endpoint=ollama_endpoint,
            hash_dim=hash_dim,
        )

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            section = f"chunk_{i}"
            conn.execute(
                """INSERT INTO context_chunks
                   (company, corpus, doc_type, doc_date, title, text, ticker,
                    source_filter, file, section, published_at, source_domain, embedding_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    company, "company", doc_type, doc_date,
                    title, chunk_text, f"|{ticker}|" if ticker else "",
                    "", file_path, section, doc_date, "",
                    json.dumps(embedding),
                ),
            )
            total_chunks += 1
        total_docs += 1

    conn.commit()
    conn.close()
    return {"documents": total_docs, "chunks": total_chunks}


def populate_from_ingested_docs(
    db_path: str,
    database_url: str = "sqlite:///./data/fe_local.db",
    embed_backend: str = "hash",
    embed_model: str = "hash",
    ollama_endpoint: str = "http://127.0.0.1:11434",
    hash_dim: int = 384,
    chunk_max_chars: int = 800,
    limit: int = 200,
) -> dict[str, int]:
    """Read ingested documents from the backend DB and build context chunks."""
    import fitz  # PyMuPDF

    if database_url.startswith("sqlite"):
        db_file = database_url.replace("sqlite:///", "")
        if not Path(db_file).exists():
            return {"documents": 0, "chunks": 0, "error": f"DB not found: {db_file}"}
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT document_id, ticker, title, published_at, doc_class, doc_subtype, pdf_path "
            "FROM documents WHERE pdf_path IS NOT NULL AND pdf_path != '' "
            "ORDER BY published_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    else:
        return {"documents": 0, "chunks": 0, "error": "Only SQLite supported for population"}

    documents: list[dict[str, Any]] = []
    for row in rows:
        row_dict = dict(row)
        pdf_path = row_dict.get("pdf_path", "")
        if not pdf_path or not Path(pdf_path).exists():
            continue
        try:
            doc = fitz.open(pdf_path)
            text = "".join(page.get_text("text") for page in doc)
            doc.close()
        except Exception:
            continue
        if len(text.strip()) < 50:
            continue

        pub_date = str(row_dict.get("published_at") or "")[:10]
        documents.append({
            "text": text,
            "ticker": row_dict.get("ticker", ""),
            "title": row_dict.get("title", ""),
            "doc_date": pub_date,
            "doc_type": row_dict.get("doc_class", ""),
            "file": pdf_path,
            "company": row_dict.get("ticker", ""),
        })

    return build_context_db(
        db_path=db_path,
        documents=documents,
        embed_backend=embed_backend,
        embed_model=embed_model,
        ollama_endpoint=ollama_endpoint,
        hash_dim=hash_dim,
        chunk_max_chars=chunk_max_chars,
    )


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)
    sys.path.insert(0, str(repo_root / "backend"))

    db_path = str(repo_root / "reports" / "qual_context" / "company.sqlite")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")

    print(f"Building qualitative context DB: {db_path}")
    print(f"Source DB: {database_url}")

    result = populate_from_ingested_docs(
        db_path=db_path,
        database_url=database_url,
        embed_backend="hash",
        embed_model="hash",
        hash_dim=384,
        chunk_max_chars=800,
        limit=200,
    )
    print(f"Result: {result}")
