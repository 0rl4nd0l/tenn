from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.services.hybrid_retriever import HybridRetriever
from app.services.llm import generate_json
from app.services.rag import query_rag
from app.services.source_weighting import apply_weighting_to_chunk
from app.services.strategy_controller import get_active_strategy_state


logger = logging.getLogger(__name__)


def _apply_chat_strategy(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = get_active_strategy_state()
    source_weights = {
        str(key).strip().casefold(): float(value)
        for key, value in dict(state.get("source_weights") or {}).items()
        if str(key).strip()
    }
    decay_rules = {
        str(key).strip().casefold(): float(value)
        for key, value in dict(state.get("decay_rules") or {}).items()
        if str(key).strip()
    }
    filter_rules = dict(state.get("filter_rules") or {})
    allow = {
        str(item or "").strip().casefold()
        for item in list(filter_rules.get("allow") or [])
        if str(item or "").strip()
    }
    deny = {
        str(item or "").strip().casefold()
        for item in list(filter_rules.get("deny") or [])
        if str(item or "").strip()
    }

    ranked: list[dict[str, Any]] = []
    for raw_chunk in results:
        chunk = apply_weighting_to_chunk(raw_chunk)
        source_name = str(chunk.get("source_name") or chunk.get("source_file") or "").strip()
        source_key = source_name.casefold()

        if allow and source_key not in allow:
            continue
        if source_key in deny:
            continue

        if source_key in source_weights:
            chunk["credibility_weight"] = float(source_weights[source_key])
            chunk = apply_weighting_to_chunk(chunk)
        if source_key in decay_rules:
            chunk["decay_half_life"] = max(
                0.1,
                float(chunk.get("decay_half_life") or chunk.get("time_decay_half_life_days") or 1.0)
                * float(decay_rules[source_key]),
            )
            chunk = apply_weighting_to_chunk(chunk)

        ranked.append(chunk)

    ranked.sort(
        key=lambda item: (
            -float(item.get("final_score") or 0.0),
            -float(item.get("relevance_score") or 0.0),
            str(item.get("chunk_id") or ""),
        )
    )
    return ranked[:10]


def _normalize_news_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """Map news payload fields to the shape expected by _apply_chat_strategy."""
    normalized = dict(chunk)
    if not normalized.get("source_name"):
        normalized["source_name"] = str(
            normalized.get("title") or normalized.get("provider") or "news"
        ).strip()
    if not normalized.get("source_type"):
        normalized["source_type"] = "news_article"
    return normalized


def _context_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        rows.append(
            {
                "text": str(chunk.get("text") or "").strip(),
                "source_name": str(chunk.get("source_name") or chunk.get("source_file") or "").strip(),
                "relevance_score": float(chunk.get("relevance_score") or 0.0),
                "recency_decay": float(chunk.get("recency_decay") or 1.0),
                "final_score": float(chunk.get("final_score") or 0.0),
                "source_type": str(chunk.get("source_type") or "").strip(),
                "published_at": str(chunk.get("published_at") or "").strip(),
                "retrieval_strategies": list(chunk.get("retrieval_strategies") or []),
            }
        )
    return rows


def _build_prompt(query: str, context_rows: list[dict[str, Any]]) -> str:
    context_json = json.dumps(context_rows, ensure_ascii=False, indent=2)
    return (
        "You are Tenn, a financial research assistant.\n\n"
        "Use ONLY the provided context.\n"
        "Answer the question clearly.\n\n"
        "Then provide:\n"
        "- Key insights\n"
        "- Supporting evidence\n"
        "- Confidence level (0-1)\n\n"
        "Return only valid JSON with this schema:\n"
        '{"answer":"","insights":[],"supporting_evidence":[],"confidence":0.0}\n\n'
        f"Question:\n{query.strip()}\n\n"
        f"Context:\n{context_json}\n"
    )


def _degraded_chat_payload(message: str, *, error: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "answer": message,
        "insights": [],
        "supporting_evidence": [],
        "confidence": 0.0,
        "sources": [],
        "system_status": "degraded",
    }
    detail = str(error or "").strip()
    if detail:
        payload["error"] = detail
    return payload


def chat_with_tenn(query: str) -> dict[str, Any]:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise ValueError("query is required")

    if not bool(getattr(settings, "enable_embeddings", True)) or not bool(
        getattr(settings, "enable_qdrant", True)
    ):
        return _degraded_chat_payload(
            (
                "Chat analysis requires embeddings and Qdrant to be enabled. "
                "Set ENABLE_EMBEDDINGS=true and ENABLE_QDRANT=true and restart the backend."
            )
        )

    try:
        rag_result = query_rag(query=normalized_query, top_k=10)
        rag_hits = rag_result.get("hits") or []
        evidence = rag_result.get("research_context", {}).get("evidence_chunks") or rag_hits

        retriever = HybridRetriever(collection_name="commentary_chunks")
        try:
            retrieval = retriever.retrieve(
                query=normalized_query,
                framework_families=None,
                top_k_vector=10,
                top_k_keyword=10,
            )
            commentary_chunks = list(retrieval.get("chunks") or [])
        except Exception:
            commentary_chunks = []

        news_retriever = HybridRetriever(collection_name="news_chunks")
        try:
            news_retrieval = news_retriever.retrieve(
                query=normalized_query,
                framework_families=None,
                top_k_vector=10,
                top_k_keyword=10,
            )
            news_chunks = [
                _normalize_news_chunk(c)
                for c in list(news_retrieval.get("chunks") or [])
            ]
        except Exception:
            news_chunks = []

        ranked_chunks = _apply_chat_strategy(commentary_chunks + news_chunks)
        context_rows = _context_rows(ranked_chunks)

        if not context_rows and evidence:
            context_rows = [
                {
                    "text": str(hit.get("text") or hit.get("title") or "").strip(),
                    "source_name": str(hit.get("title") or hit.get("document_id") or "").strip(),
                    "relevance_score": float(hit.get("score") or 0.0),
                    "recency_decay": 1.0,
                    "final_score": float(hit.get("score") or 0.0),
                    "source_type": str(hit.get("doc_class") or "").strip(),
                    "published_at": str(hit.get("published_at") or "").strip(),
                    "retrieval_strategies": ["rag_vector"],
                }
                for hit in evidence[:10]
                if str(hit.get("text") or hit.get("title") or "").strip()
            ]

        if not context_rows:
            return _degraded_chat_payload("I do not have enough retrieved context to answer safely.")

        llm_payload = generate_json(
            _build_prompt(normalized_query, context_rows),
            metadata={
                "task_type": "reasoning",
                "component": "tenn_chat",
                "operation": "chat_with_tenn",
            },
        )
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        logger.exception("chat_with_tenn degraded query=%s error=%s", normalized_query[:120], detail)
        return _degraded_chat_payload(
            (
                "Chat analysis is unavailable because the local retrieval stack is not ready. "
                "For API smoke tests, start the backend with isolated defaults. "
                "For full chat analysis, run Qdrant plus a llama.cpp server with embeddings enabled "
                "and matching LLM_API_KEY or EMBEDDING_API_KEY."
            ),
            error=detail,
        )

    answer = str(llm_payload.get("answer") or "").strip()
    insights = [str(item).strip() for item in list(llm_payload.get("insights") or []) if str(item).strip()]
    confidence = max(0.0, min(1.0, float(llm_payload.get("confidence") or 0.0)))
    sources = [
        {
            "source_name": row["source_name"],
            "relevance_score": row["relevance_score"],
            "recency_decay": row["recency_decay"],
            "final_score": row["final_score"],
            "source_type": row["source_type"],
            "published_at": row["published_at"],
        }
        for row in context_rows
    ]

    return {
        "answer": answer,
        "insights": insights,
        "supporting_evidence": llm_payload.get("supporting_evidence") or [],
        "confidence": confidence,
        "sources": sources,
    }
