#!/usr/bin/env python3
"""Re-embed all extracted BHP documents into Qdrant.

Reads documents from SQLite, re-chunks from PDF via extract_structured(),
embeds via Ollama, and upserts to Qdrant. Skips documents whose PDFs are
missing. Does NOT re-run extraction — only chunking + embedding.

Run in tmux with .env.local sourced.
"""
import logging
import os
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
for name in ["httpx", "httpcore", "urllib3"]:
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger("re_embed_docs")

from qdrant_client import QdrantClient
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.docling_extract import extract_structured
from app.services.embeddings import (
    delete_points_for_document,
    ensure_collection,
    upsert_points,
    validate_payload,
    log_rejected_payload,
)
from app.services.pipeline import _embed_chunks, _resolve_pdf_path
from app.services.structured_chunking import chunk_prose_sections


def main() -> None:
    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.ticker == "BHP")
            .filter(Document.pdf_sha256.isnot(None))
            .order_by(Document.published_at.desc())
            .all()
        )
    finally:
        db.close()

    total = len(docs)
    print(f"\n{'='*60}", flush=True)
    print(f"Re-embed: {total} BHP documents", flush=True)
    print(f"Qdrant: {settings.qdrant_url} collection={settings.qdrant_collection}", flush=True)
    print(f"Embedding: {settings.embed_model} via {os.getenv('EMBEDDING_URL', settings.ollama_url)}", flush=True)
    print(f"Batch size: {settings.embedding_batch_size}", flush=True)
    print(f"{'='*60}\n", flush=True)

    qc = QdrantClient(url=settings.qdrant_url, timeout=settings.qdrant_timeout_seconds)
    ok = skip = fail = total_points = 0
    t0 = time.time()

    for i, doc in enumerate(docs):
        doc_id = str(doc.document_id).lower()
        label = f"[{i+1}/{total}] {doc_id[:8]}.. {doc.title[:50] if doc.title else '<no title>'}"

        # Resolve PDF path
        pdf_path = _resolve_pdf_path(doc.pdf_path)
        if not pdf_path or not Path(pdf_path).exists():
            skip += 1
            print(f"  SKIP {label} (PDF missing: {pdf_path})", flush=True)
            continue

        try:
            # Extract structure from PDF
            structured_doc = extract_structured(pdf_path)
            chunks = chunk_prose_sections(structured_doc)
            if not chunks:
                skip += 1
                print(f"  SKIP {label} (0 chunks)", flush=True)
                continue

            # Embed
            vectors = _embed_chunks(chunks)
            if len(vectors) != len(chunks):
                logger.warning(
                    "Vector/chunk mismatch for %s: %d chunks, %d vectors",
                    doc_id, len(chunks), len(vectors),
                )

            if not vectors:
                skip += 1
                print(f"  SKIP {label} (0 vectors)", flush=True)
                continue

            # Build points
            usable = vectors[: len(chunks)]
            ensure_collection(qc, settings.qdrant_collection, len(usable[0]))

            points = []
            for idx, vec in enumerate(usable):
                payload = {
                    "document_id": doc_id,
                    "ticker": doc.ticker,
                    "doc_class": doc.doc_class,
                    "doc_subtype": doc.doc_subtype,
                    "chunk_index": idx,
                    "title": doc.title,
                }
                is_valid, reason = validate_payload(payload)
                if not is_valid:
                    log_rejected_payload(
                        reason or "payload validation failed",
                        payload=payload,
                        collection=settings.qdrant_collection,
                        point_id=f"{doc_id}:{idx}",
                    )
                    continue
                points.append({
                    "id": f"{doc_id}:{idx}",
                    "vector": vec,
                    "payload": payload,
                })

            if points:
                delete_points_for_document(qc, settings.qdrant_collection, doc_id)
                result = dict(upsert_points(qc, settings.qdrant_collection, points) or {})
                written = int(result.get("written_points", 0))
                total_points += written
                ok += 1
                elapsed = time.time() - t0
                avg = elapsed / (i + 1)
                print(f"  OK   {label} chunks={len(chunks)} points={written} [{avg:.1f}s/doc]", flush=True)
            else:
                skip += 1
                print(f"  SKIP {label} (all payloads rejected)", flush=True)

        except Exception as e:
            fail += 1
            print(f"  FAIL {label} {str(e)[:100]}", flush=True)
            logger.exception("Failed to re-embed %s", doc_id)

    elapsed = time.time() - t0
    print(f"\n{'='*60}", flush=True)
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)
    print(f"ok={ok} skip={skip} fail={fail} total_points={total_points}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
