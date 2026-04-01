"""analysis_rag_adapter.py — Thin adapter between analysis modules and Qdrant.

Provides a ``rag_fn`` compatible with ``TickerContextLoader(rag_fn=...)``
that embeds a query and searches the specified Qdrant collection.

Signature: ``(query: str, collection: str, top_k: int) -> list[dict]``
Each dict has keys: text, score, document_id, title.
"""
from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient

from app.core.config import settings
from app.services.embeddings import ensure_collection
from app.services.llm import embed_texts

logger = logging.getLogger(__name__)


def _build_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        timeout=int(getattr(settings, "qdrant_timeout_seconds", 60) or 60),
    )


def analysis_rag_query(
    query: str, collection: str, top_k: int,
) -> list[dict[str, Any]]:
    """Embed *query* and search *collection* in Qdrant.

    Returns a list of dicts with keys expected by ``TickerContextLoader._rag``:
    ``text``, ``score``, ``document_id``, ``title``.
    """
    if not settings.enable_qdrant:
        logger.debug("Qdrant disabled — skipping RAG query for collection %s", collection)
        return []

    embed_metadata = {
        "task_type": "embedding",
        "component": "analysis_rag_adapter",
        "operation": "rag_query",
    }
    vectors = embed_texts([query], metadata=embed_metadata)
    if not vectors:
        logger.warning("Empty embedding for analysis RAG query on %s", collection)
        return []

    query_vector = vectors[0]
    client = _build_client()

    try:
        ensure_collection(client, collection, len(query_vector))
    except Exception:
        logger.warning("Collection %s not available — skipping", collection)
        return []

    hits = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=max(1, top_k),
        with_payload=True,
    )

    results: list[dict[str, Any]] = []
    for h in hits:
        payload = h.payload or {}
        results.append({
            "text": str(payload.get("text") or payload.get("chunk_text") or ""),
            "score": float(h.score),
            "document_id": str(payload.get("document_id") or payload.get("source_id") or ""),
            "title": str(payload.get("title") or payload.get("source_name") or ""),
        })
    return results
