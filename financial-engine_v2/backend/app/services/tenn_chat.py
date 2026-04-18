from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.hybrid_retriever import HybridRetriever
from app.services.llm import generate_json
from app.services.rag import query_rag
from app.services.session_memory import (
    _build_turn_payload,
    get_session_context,
    record_turn,
)
from app.services.source_weighting import apply_weighting_to_chunk
from app.services.strategy_controller import get_active_strategy_state


logger = logging.getLogger(__name__)
_CHAT_LLM_TIMEOUT_SECONDS = 90.0
_SMALL_TALK_RE = re.compile(
    r"^(hi|hello|hey|yo|sup|thanks|thank you|good (morning|afternoon|evening)|how are you)[\s!,.?]*$",
    re.IGNORECASE,
)
_UNVERIFIED_ANSWER_RE = re.compile(
    r"\b(?:cannot|can't|can not|do not|don't)\s+(?:verify|confirm|substantiate)\b|"
    r"\bnot enough (?:evidence|context|information)\b|"
    r"\bunable to verify\b",
    re.IGNORECASE,
)


def _json_safe_value(value: Any) -> Any:
    """Recursively coerce values into JSON-safe primitives."""
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe_value(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def _safe_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _is_small_talk_query(query: str) -> bool:
    return bool(_SMALL_TALK_RE.match(str(query or "").strip()))


def _today_iso_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _filter_news_by_ticker(chunks: list[dict[str, Any]], ticker: str | None) -> list[dict[str, Any]]:
    normalized_ticker = str(ticker or "").strip().upper()
    if not normalized_ticker:
        return chunks
    filtered = [
        chunk
        for chunk in chunks
        if str(chunk.get("ticker") or "").strip().upper() == normalized_ticker
    ]
    if filtered:
        return filtered
    # If nothing is tagged with ticker, do not silently fall back to unrelated news.
    return []


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
                "url": str(chunk.get("url") or "").strip(),
                "relevance_score": _safe_float(chunk.get("relevance_score"), 0.0),
                "recency_decay": _safe_float(chunk.get("recency_decay"), 1.0),
                "final_score": _safe_float(chunk.get("final_score"), 0.0),
                "source_type": str(chunk.get("source_type") or "").strip(),
                "published_at": str(chunk.get("published_at") or "").strip(),
                "retrieval_strategies": list(chunk.get("retrieval_strategies") or []),
            }
        )
    return rows


def _evidence_context_rows(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize RAG evidence hits into the same row shape used by _context_rows.

    This is specifically used when vector retrieval yields zero chunks, but
    query_rag still provides "evidence_chunks" for grounding.
    """
    rows: list[dict[str, Any]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue

        # Some RAG evidence hits only have `title` (no `text`), so fall back to
        # title to avoid sending empty context to the model.
        text = str(hit.get("text") or hit.get("title") or "").strip()
        title = str(hit.get("title") or "").strip()
        if not text and not title:
            continue

        source_name = title or text
        url = str(hit.get("url") or hit.get("source_url") or "").strip()
        relevance_score = _safe_float(hit.get("score"), 0.0)

        rows.append(
            {
                "text": text,
                "source_name": source_name,
                "url": url,
                "relevance_score": relevance_score,
                "recency_decay": 1.0,
                "final_score": relevance_score,
                "source_type": str(hit.get("doc_class") or "").strip(),
                "published_at": str(hit.get("published_at") or "").strip(),
                "retrieval_strategies": ["rag_vector"],
            }
        )

    return rows


def _normalize_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0

    if math.isnan(parsed) or math.isinf(parsed):
        return 0.0
    return max(0.0, min(1.0, parsed))


def _normalize_insights(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_supporting_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    # Ensure nested non-finite floats (NaN/Inf) become JSON-safe nulls.
    return [_json_safe_value(item) for item in value if isinstance(item, dict)]


def _format_session_context_block(prior_turns: list[dict[str, Any]]) -> str:
    lines: list[str] = ["Relevant prior session context (use as background only):"]
    for turn in prior_turns:
        q = str(turn.get("query") or "").strip()
        a = str(turn.get("answer") or "").strip()
        ticker = str(turn.get("ticker") or "").strip()
        conf = turn.get("confidence")
        parts: list[str] = []
        if ticker:
            parts.append(f"ticker={ticker}")
        if conf is not None:
            parts.append(f"confidence={conf:.2f}")
        meta = f" ({', '.join(parts)})" if parts else ""
        if q:
            lines.append(f"  Q: {q[:200]}{meta}")
        if a:
            lines.append(f"  A: {a[:300]}")
    return "\n".join(lines)


def _build_prompt(
    query: str,
    context_rows: list[dict[str, Any]],
    *,
    prior_turns: list[dict[str, Any]] | None = None,
) -> str:
    today_iso = _today_iso_utc()
    context_json = json.dumps(context_rows, ensure_ascii=False, indent=2)
    session_block = ""
    if prior_turns:
        session_block = _format_session_context_block(prior_turns) + "\n\n"
    return (
        "You are Tenn, a financial research assistant.\n\n"
        "Use ONLY the provided context. Do not rely on prior knowledge or assumptions.\n\n"
        f"Today's date is {today_iso}. Treat any dates in retrieved content as historical context.\n\n"
        "Temporal and uncertainty rules — follow strictly:\n"
        "- Prefer evidence from more recent sources. Use `published_at` to judge recency.\n"
        "- If sources conflict or contradict, acknowledge the conflict explicitly in your answer.\n"
        "- If the most relevant article is more than 7 days old, note the staleness and reduce confidence.\n"
        "- Do not extrapolate from incomplete or partial evidence. State what is unknown.\n"
        "- Every factual claim in `answer` or `insights` must be backed by the provided context.\n"
        "- If a claim cannot be verified from the provided context, say you cannot verify it.\n"
        "- Uncertainty is correct. Set `confidence` to reflect actual evidence quality, not to appear helpful.\n"
        "  A confidence of 0.2 is a valid, honest answer when evidence is sparse or stale.\n\n"
        f"{session_block}"
        "Answer the question based on the context.\n"
        "Then provide:\n"
        "- Key insights (each must be directly supported by a specific context item)\n"
        "- Supporting evidence (cite `source_name` and `published_at` for each item)\n"
        "- Do not include any claim unless it can be tied to a supporting evidence item\n"
        "- Confidence (0-1): reflect evidence quality, recency, and completeness\n\n"
        "Return ONLY valid JSON — no prose before or after:\n"
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


def chat_with_tenn(
    query: str,
    *,
    ticker: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise ValueError("query is required")
    normalized_ticker = str(ticker or "").strip().upper() or None
    normalized_session_id = str(session_id or "").strip() or None

    if _is_small_talk_query(normalized_query):
        return {
            "answer": "Hello. Ask me about a company, ticker, or financial topic and I will pull relevant evidence.",
            "insights": [],
            "supporting_evidence": [],
            "confidence": 0.0,
            "sources": [],
        }

    session_memory_enabled = (
        bool(getattr(settings, "enable_session_memory", True))
        and normalized_session_id is not None
    )

    if not bool(getattr(settings, "enable_embeddings", True)) or not bool(
        getattr(settings, "enable_qdrant", True)
    ):
        return _degraded_chat_payload(
            (
                "Chat analysis requires embeddings and Qdrant to be enabled. "
                "Set ENABLE_EMBEDDINGS=true and ENABLE_QDRANT=true and restart the backend."
            )
        )

    prior_turns: list[dict[str, Any]] = []
    if session_memory_enabled:
        prior_turns = get_session_context(
            normalized_session_id,  # type: ignore[arg-type]
            normalized_query,
            semantic_limit=3,
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
        except Exception as exc:
            logger.warning(
                "commentary_retrieval_failed",
                extra={
                    "component": "tenn_chat",
                    "collection": "commentary_chunks",
                    "operation": "retrieve",
                    "error": type(exc).__name__,
                    "detail": str(exc)[:200],
                },
            )
            commentary_chunks = []

        news_retriever = HybridRetriever(collection_name="news_chunks")
        try:
            news_retrieval = news_retriever.retrieve(
                query=normalized_query,
                framework_families=None,
                ticker=normalized_ticker,
                top_k_vector=10,
                top_k_keyword=10,
            )
            news_chunks = [
                _normalize_news_chunk(c)
                for c in list(news_retrieval.get("chunks") or [])
            ]
            news_chunks = _filter_news_by_ticker(news_chunks, normalized_ticker)
        except Exception as exc:
            logger.warning(
                "news_retrieval_failed",
                extra={
                    "component": "tenn_chat",
                    "collection": "news_chunks",
                    "operation": "retrieve",
                    "error": type(exc).__name__,
                    "detail": str(exc)[:200],
                },
            )
            news_chunks = []

        ranked_chunks = _apply_chat_strategy(commentary_chunks + news_chunks)
        context_rows = _context_rows(ranked_chunks)

        if not context_rows and evidence:
            if isinstance(evidence, list):
                context_rows = _evidence_context_rows(evidence[:10])

        if not context_rows:
            return _degraded_chat_payload("I do not have enough retrieved context to answer safely.")

        llm_payload = generate_json(
            _build_prompt(normalized_query, context_rows, prior_turns=prior_turns or None),
            metadata={
                "task_type": "reasoning",
                "component": "tenn_chat",
                "operation": "chat_with_tenn",
                # Force local llama.cpp path for cockpit chat; prevents
                # slow external fallback after local timeout.
                "requested_base_url": settings.llamacpp_url,
            },
            timeout=_CHAT_LLM_TIMEOUT_SECONDS,
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
    insights = _normalize_insights(llm_payload.get("insights"))
    confidence = _normalize_confidence(llm_payload.get("confidence"))
    sources = [
        {
            "source_name": row["source_name"],
            "url": row.get("url") or "",
            "relevance_score": row["relevance_score"],
            "recency_decay": row["recency_decay"],
            "final_score": row["final_score"],
            "source_type": row["source_type"],
            "published_at": row["published_at"],
        }
        for row in context_rows
    ]
    if answer and not sources and not _UNVERIFIED_ANSWER_RE.search(answer):
        logger.warning(
            "chat_missing_sources_guard query=%s",
            normalized_query[:120],
        )
        answer = (
            "I cannot verify that from the current retrieved evidence, so I will not make "
            "factual claims without supporting sources."
        )
        confidence = 0.0
    if not answer:
        logger.warning(
            "chat_empty_answer_fallback query=%s sources=%d",
            normalized_query[:120],
            len(sources),
        )
        answer = (
            "I found supporting sources but could not generate a narrative answer this turn. "
            "Please retry, or ask a narrower question (for example: 'summarize today's BHP headlines')."
        )
        confidence = 0.0

    supporting_evidence = _normalize_supporting_evidence(llm_payload.get("supporting_evidence"))

    result: dict[str, Any] = {
        "answer": answer,
        "insights": insights,
        "supporting_evidence": supporting_evidence,
        "confidence": confidence,
        "sources": sources,
    }

    if session_memory_enabled:
        retrieved_chunk_ids = [
            str(row.get("chunk_id") or "")
            for row in context_rows
            if str(row.get("chunk_id") or "").strip()
        ]
        # Build the turn payload now but do NOT record it yet.
        # The route layer will score quality first, then call record_turn() with
        # the metrics included.  This is surfaced via the private "_pending_turn"
        # key so that no call site outside routes/chat.py depends on it.
        result["_pending_turn"] = {
            "session_id": normalized_session_id,
            "payload": _build_turn_payload(
                session_id=normalized_session_id,  # type: ignore[arg-type]
                query=normalized_query,
                answer=answer,
                ticker=normalized_ticker,
                confidence=confidence,
                sources=sources,
                retrieved_chunk_ids=retrieved_chunk_ids or None,
            ),
        }

    return result
