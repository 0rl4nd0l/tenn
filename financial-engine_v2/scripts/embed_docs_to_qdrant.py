#!/usr/bin/env python3
"""Embed document PDFs from the database into the asx_docs Qdrant collection."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import fitz
import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "fe_local.db"
QDRANT_URL = "http://127.0.0.1:6333"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
COLLECTION = "asx_docs"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBED_BATCH = 16


def extract_text(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages).strip()
    except Exception as exc:
        print(f"  WARN: cannot extract {pdf_path}: {exc}")
        return ""


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text.strip():
        return []
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def embed_texts(texts: list[str], client: httpx.Client) -> list[list[float]]:
    if not texts:
        return []
    truncated = [t[:8000] for t in texts]
    vectors = []
    for t in truncated:
        try:
            resp = client.post(
                f"{OLLAMA_URL}/v1/embeddings",
                json={"model": EMBED_MODEL, "input": [t]},
                timeout=120.0,
            )
            resp.raise_for_status()
            vectors.append(resp.json()["data"][0]["embedding"])
        except Exception as exc:
            print(f"    embed error: {exc} (text len={len(t)}), using zero vector")
            vectors.append([0.0] * 768)
    return vectors


def main() -> None:
    db = sqlite3.connect(str(DB_PATH))
    cur = db.cursor()
    cur.execute(
        "SELECT document_id, ticker, doc_class, doc_subtype, title, pdf_path, published_at "
        "FROM documents ORDER BY published_at DESC"
    )
    docs = cur.fetchall()
    db.close()
    print(f"Found {len(docs)} documents in database")

    qclient = QdrantClient(url=QDRANT_URL, timeout=60)
    collections = {c.name for c in qclient.get_collections().collections}
    if COLLECTION not in collections:
        print(f"Creating collection {COLLECTION}")
        test_vec = embed_texts(["test"], httpx.Client(timeout=60))[0]
        qclient.create_collection(
            collection_name=COLLECTION,
            vectors_config=qmodels.VectorParams(size=len(test_vec), distance=qmodels.Distance.COSINE),
        )

    total_chunks = 0
    total_embedded = 0
    http = httpx.Client(timeout=180)

    for doc_id, ticker, doc_class, doc_subtype, title, pdf_path, published_at in docs:
        if not pdf_path or not Path(pdf_path).exists():
            print(f"  SKIP {doc_id[:8]}... no PDF: {pdf_path}")
            continue

        text = extract_text(pdf_path)
        if not text:
            print(f"  SKIP {doc_id[:8]}... empty text from {pdf_path}")
            continue

        chunks = chunk_text(text)
        if not chunks:
            continue

        print(f"  {ticker} | {title[:50]} | {len(chunks)} chunks")
        total_chunks += len(chunks)

        for batch_start in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[batch_start : batch_start + EMBED_BATCH]
            vectors = embed_texts(batch, http)

            points = []
            for i, (chunk, vector) in enumerate(zip(batch, vectors)):
                chunk_idx = batch_start + i
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}:{chunk_idx}"))
                canonical_doc_id = str(uuid.UUID(doc_id))
                points.append(
                    qmodels.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "document_id": canonical_doc_id,
                            "ticker": ticker,
                            "doc_class": doc_class or "",
                            "doc_subtype": doc_subtype or "",
                            "title": title or "",
                            "published_at": published_at or "",
                            "chunk_index": chunk_idx,
                            "text": chunk,
                        },
                    )
                )

            qclient.upsert(collection_name=COLLECTION, points=points)
            total_embedded += len(points)

    http.close()
    print(f"\nDone: {total_chunks} chunks from {len(docs)} docs, {total_embedded} points upserted to {COLLECTION}")

    info = qclient.get_collection(COLLECTION)
    print(f"Collection {COLLECTION}: {info.points_count} points")


if __name__ == "__main__":
    main()
