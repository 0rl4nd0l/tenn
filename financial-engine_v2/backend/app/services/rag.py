from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.services.embeddings import (
    ensure_collection,
    log_invalid_asx_docs_payload,
    validate_asx_docs_payload,
)
from app.services.llm import embed_texts, get_routing_decision
from app.services.research_context_builder import ResearchContextBuilder
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from shared.ticker_inference import detect_unique_ticker

logger = logging.getLogger(__name__)
_TICKER_STOPWORDS = {
    "ASX",
    "PDF",
    "THE",
    "AND",
    "FOR",
    "APPENDIX",
    "NOTICE",
    "ANNUAL",
    "HALF",
}
_FINANCIAL_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cash_flow": ("cash flow", "cashflow"),
    "revenue": ("revenue",),
    "earnings": ("earnings", "profit"),
    "ebitda": ("ebitda",),
}
_FINANCIAL_TITLE_MARKERS = ("appendix", "results", "financial")
_ASX_DOCS_COLLECTION = "asx_docs"
_NEWS_ROUNDUP_TITLE_MARKERS = (
    "market news",
    "market update",
    "morning wrap",
    "lunch wrap",
    "closing bell",
    "evening wrap",
    "rise and shine",
    "scan lists",
    "broker moves",
    "asx 200",
    "latest nasdaq news",
    "financial, business & stock market news",
)


def _build_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        timeout=int(getattr(settings, "qdrant_timeout_seconds", 60) or 60),
    )


def _build_query_filter(ticker: Optional[str]) -> Optional[qmodels.Filter]:
    symbol = (ticker or "").strip().upper()
    if not symbol:
        return None
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="ticker",
                match=qmodels.MatchValue(value=symbol),
            )
        ]
    )


def _supports_ticker_filter(collection_name: str) -> bool:
    return str(collection_name or "").strip() == _ASX_DOCS_COLLECTION


def _build_news_ticker_filter(ticker: Optional[str]) -> Optional[qmodels.Filter]:
    symbol = (ticker or "").strip().upper()
    if not symbol:
        return None
    return qmodels.Filter(
        should=[
            qmodels.FieldCondition(
                key="ticker",
                match=qmodels.MatchValue(value=symbol),
            ),
            qmodels.FieldCondition(
                key="primary_ticker",
                match=qmodels.MatchValue(value=symbol),
            ),
            qmodels.FieldCondition(
                key="tickers",
                match=qmodels.MatchValue(value=symbol),
            ),
        ]
    )


def _title_mentions_ticker(title: str, ticker: str) -> bool:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return False
    return bool(re.search(rf"\b{re.escape(symbol)}\b", str(title or ""), re.IGNORECASE))


def _is_roundup_title(title: str) -> bool:
    lower = str(title or "").strip().lower()
    return any(marker in lower for marker in _NEWS_ROUNDUP_TITLE_MARKERS)


def _parse_news_published_at(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _payload_tickers(payload: dict[str, Any]) -> list[str]:
    values = payload.get("tickers")
    if isinstance(values, list):
        return [str(value).strip().upper() for value in values if str(value).strip()]
    if isinstance(values, str):
        return [part.strip().upper() for part in values.split(",") if part.strip()]
    return []


def _news_ticker_match_bonus(payload: dict[str, Any], ticker: str) -> float:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return 0.0

    bonus = 0.0
    primary = str(payload.get("primary_ticker") or "").strip().upper()
    stored_ticker = str(payload.get("ticker") or "").strip().upper()
    linked_tickers = _payload_tickers(payload)
    title = str(payload.get("title") or "")

    if primary == symbol:
        bonus += 0.25
    elif stored_ticker == symbol:
        bonus += 0.21
    elif symbol in linked_tickers:
        bonus += 0.08

    if _title_mentions_ticker(title, symbol):
        bonus += 0.28

    if _is_roundup_title(title):
        bonus -= 0.16
    if len(linked_tickers) >= 30:
        bonus -= 0.12
    elif len(linked_tickers) >= 12:
        bonus -= 0.06
    return bonus


def _news_recency_bonus(
    published_at: datetime | None,
    *,
    newest_published_at: datetime | None,
) -> float:
    if published_at is None or newest_published_at is None:
        return 0.0
    age_days = max(
        0.0,
        (newest_published_at - published_at).total_seconds() / 86400.0,
    )
    if age_days <= 1:
        return 0.14
    if age_days <= 7:
        return 0.12
    if age_days <= 30:
        return 0.09
    if age_days <= 90:
        return 0.04
    if age_days >= 180:
        return -0.14
    if age_days >= 90:
        return -0.08
    return 0.0


def _normalize_news_results(
    hits: list[Any],
    *,
    ticker: Optional[str],
    top_k: int,
) -> list[dict[str, Any]]:
    by_article: dict[str, dict[str, Any]] = {}
    normalized_ticker = (ticker or "").strip().upper()
    newest_published_at = max(
        (
            parsed
            for parsed in (
                _parse_news_published_at(
                    (dict(getattr(hit, "payload", None) or {})).get("published_at")
                )
                for hit in hits
            )
            if parsed is not None
        ),
        default=None,
    )

    for hit in hits:
        payload = dict(getattr(hit, "payload", None) or {})
        score = float(getattr(hit, "score", 0.0) or 0.0)
        article_id = str(payload.get("article_id") or payload.get("chunk_id") or "")
        rank_score = score
        published_dt = _parse_news_published_at(payload.get("published_at"))
        if normalized_ticker:
            rank_score += _news_ticker_match_bonus(payload, normalized_ticker)
            rank_score += _news_recency_bonus(
                published_dt,
                newest_published_at=newest_published_at,
            )

        candidate = {"score": score, "payload": payload}
        published_at = str(payload.get("published_at") or "")
        existing = by_article.get(article_id)
        if existing is None:
            by_article[article_id] = {
                "result": candidate,
                "rank_score": rank_score,
                "published_at": published_at,
            }
            continue
        if rank_score > existing["rank_score"] or (
            math.isclose(rank_score, existing["rank_score"])
            and published_at > existing["published_at"]
        ):
            by_article[article_id] = {
                "result": candidate,
                "rank_score": rank_score,
                "published_at": published_at,
            }

    ranked = sorted(
        by_article.values(),
        key=lambda row: (row["rank_score"], row["published_at"]),
        reverse=True,
    )
    return [row["result"] for row in ranked[: int(max(1, top_k))]]


def extract_ticker(query: str) -> str | None:
    return detect_unique_ticker(query, stopwords=_TICKER_STOPWORDS)


def _effective_ticker(query: str, ticker: Optional[str]) -> str | None:
    symbol = str(ticker or "").strip().upper()
    if symbol:
        return symbol
    return extract_ticker(query)


def _detect_financial_intents(query: str) -> list[str]:
    normalized_query = str(query or "").strip().lower()
    return [
        intent
        for intent, keywords in _FINANCIAL_INTENT_KEYWORDS.items()
        if any(keyword in normalized_query for keyword in keywords)
    ]


def _search_points(
    client: QdrantClient,
    *,
    query_vector: list[float],
    limit: int,
    ticker: str | None,
) -> tuple[list[Any], bool]:
    search_kwargs: Dict[str, Any] = {
        "collection_name": settings.qdrant_collection,
        "query_vector": query_vector,
        "limit": limit,
    }
    query_filter = (
        _build_query_filter(ticker)
        if _supports_ticker_filter(settings.qdrant_collection)
        else None
    )
    if query_filter is not None:
        search_kwargs["query_filter"] = query_filter

    points = client.search(**search_kwargs)
    used_ticker_fallback = False
    if not points and query_filter is not None:
        used_ticker_fallback = True
        logger.info(
            "No documents found — ingestion missing",
            extra={
                "ticker": ticker,
                "qdrant_collection": settings.qdrant_collection,
                "filter_applied": True,
                "fallback_used": True,
            },
        )
        points = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=limit,
        )
        if not points:
            logger.info(
                "No documents found — ingestion missing",
                extra={
                    "ticker": ticker,
                    "qdrant_collection": settings.qdrant_collection,
                    "filter_applied": False,
                    "fallback_used": True,
                },
            )
    return list(points), used_ticker_fallback


def _score_hit(
    score: float,
    *,
    payload: dict[str, Any],
    expected_ticker: str | None,
    financial_intents: list[str],
) -> float:
    boosted_score = float(score)
    normalized_hit_ticker = str(payload.get("ticker") or "").strip().upper()
    if expected_ticker and normalized_hit_ticker == expected_ticker:
        boosted_score *= 1.25
    if financial_intents:
        doc_class = str(payload.get("doc_class") or "").strip().lower()
        title = str(payload.get("title") or "").strip().lower()
        if "financial" in doc_class:
            boosted_score *= 1.15
        if any(marker in title for marker in _FINANCIAL_TITLE_MARKERS):
            boosted_score *= 1.10
    return boosted_score


def _build_research_context(
    query: str,
    evidence_hits: list[dict[str, Any]],
    ticker: str | None = None,
    financial_intents: list[str] | None = None,
) -> dict[str, Any]:
    resolved_ticker = str(ticker or "").strip().upper() or _effective_ticker(
        query, None
    )
    resolved_financial_intents = (
        list(financial_intents)
        if financial_intents is not None
        else _detect_financial_intents(query)
    )
    orchestrator = RetrievalOrchestrator()
    retrieval = orchestrator.retrieve(
        query,
        ticker=resolved_ticker,
        financial_intents=resolved_financial_intents,
    )
    builder = ResearchContextBuilder(commentary_weight_max=0.25)
    return builder.build(
        frameworks=retrieval.get("frameworks") or [],
        methodology_chunks=retrieval.get("methodology_chunks")
        or retrieval.get("chunks")
        or [],
        evidence_chunks=evidence_hits,
        commentary_chunks=retrieval.get("commentary_chunks") or [],
        commentary_memos=retrieval.get("commentary_memos") or [],
    )


def query_news_chunks(
    *,
    query: str,
    ticker: Optional[str] = None,
    provider: Optional[str] = None,
    language: Optional[str] = "en",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    top_k: int = 10,
) -> Dict[str, Any]:
    """Vector search over news chunks stored in Qdrant.

    Uses the same embedding pipeline (embed_texts via model router) as query_rag()
    to ensure cross-source consistency.
    """
    q = (query or "").strip()
    if not q:
        raise ValueError("query is required")
    if not settings.enable_qdrant:
        raise RuntimeError("RAG backend is disabled (qdrant disabled)")

    embed_metadata = {
        "task_type": "embedding",
        "component": "rag.query_news_chunks",
        "operation": "rag_query",
    }
    vectors = embed_texts([q], metadata=embed_metadata)
    if not vectors:
        return {"results": []}
    vec = vectors[0]

    must_filters: list[Any] = []
    if language:
        must_filters.append(
            qmodels.FieldCondition(
                key="language", match=qmodels.MatchValue(value=language)
            )
        )
    if provider:
        must_filters.append(
            qmodels.FieldCondition(
                key="provider", match=qmodels.MatchValue(value=provider)
            )
        )
    news_ticker_filter = _build_news_ticker_filter(ticker)
    if news_ticker_filter is not None:
        must_filters.append(news_ticker_filter)
    if date_from:
        must_filters.append(
            qmodels.FieldCondition(
                key="published_at", range=qmodels.Range(gte=date_from)
            )
        )
    if date_to:
        must_filters.append(
            qmodels.FieldCondition(key="published_at", range=qmodels.Range(lte=date_to))
        )

    query_filter = qmodels.Filter(must=must_filters) if must_filters else None

    client = _build_qdrant_client()
    candidate_limit = int(max(1, top_k))
    if ticker:
        candidate_limit = 200
    hits = client.search(
        collection_name="news_chunks",
        query_vector=vec,
        limit=candidate_limit,
        query_filter=query_filter,
        with_payload=True,
    )

    results = _normalize_news_results(hits, ticker=ticker, top_k=top_k)
    return {"results": results}


def query_rag(
    *,
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 8,
    debug: bool = False,
) -> Dict[str, Any]:
    """Vector search over announcement chunks stored in Qdrant."""
    q = (query or "").strip()
    limit = int(max(1, top_k))

    if not q:
        raise ValueError("query is required")

    if not settings.enable_embeddings:
        raise RuntimeError("RAG backend is disabled (embeddings disabled)")
    if not settings.enable_qdrant:
        raise RuntimeError("RAG backend is disabled (qdrant disabled)")

    embed_metadata = {
        "task_type": "embedding",
        "component": "rag.query_rag",
        "operation": "rag_query",
    }
    resolved_ticker = _effective_ticker(q, ticker)
    financial_intents = _detect_financial_intents(q)
    intent_detected = financial_intents[0] if financial_intents else None
    filter_applied = bool(
        resolved_ticker and _supports_ticker_filter(settings.qdrant_collection)
    )
    embed_decision = get_routing_decision(q, embed_metadata)
    vectors = embed_texts(
        [q],
        metadata=embed_metadata,
    )
    if not vectors:
        logger.info(
            "query_rag",
            extra={
                "query_length": len(q),
                "ticker": ticker,
                "top_k": limit,
                "embedding_model": embed_decision.model_name,
                "embedding_dim": 0,
                "qdrant_collection": settings.qdrant_collection,
                "candidate_count": 0,
                "filtered_count": 0,
                "average_score": 0.0,
            },
        )
        out: Dict[str, Any] = {
            "ok": True,
            "hits": [],
            "retrieved": 0,
            "candidate_count": 0,
            "filtered_count": 0,
        }
        if debug:
            out["debug"] = {
                "embedding_norm": 0.0,
                "score_distribution": {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0},
                "hit_ticker_distribution": {},
                "detected_ticker": resolved_ticker,
                "intent_detected": intent_detected,
                "filter_applied": filter_applied,
                "fallback_used": False,
                "skipped_invalid_payloads": 0,
                "top_payload_keys": [],
                "collection_dimension": 0,
            }
        return out

    query_vector = vectors[0]

    client = _build_qdrant_client()
    ensure_collection(client, settings.qdrant_collection, len(query_vector))
    points, used_ticker_fallback = _search_points(
        client,
        query_vector=query_vector,
        limit=limit,
        ticker=resolved_ticker,
    )

    hits: List[Dict[str, Any]] = []
    skipped_invalid_payloads = 0
    logged_invalid_payloads: set[tuple[str, str, str, str]] = set()
    for point in points:
        payload = dict(point.payload or {})
        point_id = getattr(point, "id", None)
        is_valid, reason = validate_asx_docs_payload(payload, mode="read")
        if not is_valid:
            skipped_invalid_payloads += 1
            log_key = (
                str(point_id or ""),
                str(payload.get("ticker") or ""),
                str(payload.get("title") or ""),
                str(reason or "payload validation failed"),
            )
            if log_key not in logged_invalid_payloads:
                logged_invalid_payloads.add(log_key)
                log_invalid_asx_docs_payload(
                    reason or "payload validation failed",
                    payload=payload,
                    collection=settings.qdrant_collection,
                    point_id=point_id,
                    action="skipped_read",
                )
            continue
        raw_score = float(point.score or 0.0)
        hit_ticker = str(payload.get("ticker") or "")
        adjusted_score = _score_hit(
            raw_score,
            payload=payload,
            expected_ticker=resolved_ticker,
            financial_intents=financial_intents,
        )
        hit: dict[str, Any] = {
            "score": raw_score,
            "_adjusted_score": adjusted_score,
            "ticker": hit_ticker,
            "title": str(payload.get("title") or ""),
            "document_id": str(payload.get("document_id") or ""),
            "doc_class": payload.get("doc_class"),
            "doc_subtype": payload.get("doc_subtype"),
            "chunk_index": payload.get("chunk_index"),
        }
        text_value = str(payload.get("text") or "").strip()
        if text_value:
            hit["text"] = text_value
        published_at_value = str(payload.get("published_at") or "").strip()
        if published_at_value:
            hit["published_at"] = published_at_value
        hits.append(hit)

    hits.sort(key=lambda hit: float(hit.get("_adjusted_score") or 0.0), reverse=True)
    for hit in hits:
        hit.pop("_adjusted_score", None)

    candidate_count = len(points)
    filtered_count = len(hits)
    average_score = (
        sum(float(p.score or 0.0) for p in points) / candidate_count
        if candidate_count
        else 0.0
    )
    logger.info(
        "query_rag",
        extra={
            "query_length": len(q),
            "ticker": resolved_ticker,
            "financial_intents": financial_intents,
            "intent_detected": intent_detected,
            "top_k": limit,
            "embedding_model": embed_decision.model_name,
            "embedding_dim": len(query_vector),
            "qdrant_collection": settings.qdrant_collection,
            "ticker_filter_applied": filter_applied,
            "filter_applied": filter_applied,
            "candidate_count": candidate_count,
            "filtered_count": filtered_count,
            "skipped_invalid_payloads": skipped_invalid_payloads,
            "average_score": average_score,
            "used_ticker_fallback": used_ticker_fallback,
            "fallback_used": used_ticker_fallback,
        },
    )
    result: Dict[str, Any] = {
        "ok": True,
        "hits": hits,
        "retrieved": len(hits),
        "candidate_count": candidate_count,
        "filtered_count": filtered_count,
        "research_context": _build_research_context(q, hits),
    }
    if debug:
        scores = [float(p.score or 0.0) for p in points]
        n = len(scores)
        mean_s = sum(scores) / n if n else 0.0
        variance = sum((s - mean_s) ** 2 for s in scores) / n if n else 0.0
        result["debug"] = {
            "embedding_norm": math.sqrt(sum(x * x for x in query_vector)),
            "score_distribution": {
                "min": min(scores) if scores else 0.0,
                "max": max(scores) if scores else 0.0,
                "mean": mean_s,
                "std": math.sqrt(variance),
            },
            "hit_ticker_distribution": dict(Counter(h["ticker"] for h in hits)),
            "detected_ticker": resolved_ticker,
            "intent_detected": intent_detected,
            "filter_applied": filter_applied,
            "fallback_used": used_ticker_fallback,
            "skipped_invalid_payloads": skipped_invalid_payloads,
            "top_payload_keys": sorted(
                set(key for p in points for key in (p.payload or {}).keys())
            ),
            "collection_dimension": len(query_vector),
        }
    return result
