from __future__ import annotations

from typing import Any

from app.services.commentary_decay import compute_recency_decay


DEFAULT_SOURCE_WEIGHTS = {
    "book": 1.0,
    "framework_pdf": 1.0,
    "investor_letter": 0.9,
    "youtube_transcript": 0.55,
    "podcast_transcript": 0.55,
    "market_commentary": 0.45,
    "news_article": 0.5,
}

DEFAULT_HALF_LIFE_DAYS = {
    "book": 3650.0,
    "framework_pdf": 3650.0,
    "investor_letter": 3650.0,
    "youtube_transcript": 14.0,
    "podcast_transcript": 14.0,
    "market_commentary": 7.0,
    "news_article": 1.0,
}


def source_weight_for_type(source_type: str) -> float:
    normalized = str(source_type or "").strip().lower()
    return float(DEFAULT_SOURCE_WEIGHTS.get(normalized, 0.5))


def half_life_for_type(source_type: str) -> float:
    normalized = str(source_type or "").strip().lower()
    return float(DEFAULT_HALF_LIFE_DAYS.get(normalized, 30.0))


def apply_source_weighting(
    *,
    relevance_score: float,
    source_type: str,
    credibility_weight: float | int | None,
    recency_decay: float,
) -> dict[str, float]:
    source_weight = source_weight_for_type(source_type)
    resolved_credibility = (
        float(credibility_weight)
        if credibility_weight not in (None, "")
        else source_weight
    )
    final_score = (
        float(relevance_score)
        * float(source_weight)
        * resolved_credibility
        * float(recency_decay)
    )
    return {
        "relevance_score": float(relevance_score),
        "source_weight": float(source_weight),
        "credibility_weight": float(resolved_credibility),
        "recency_decay": float(recency_decay),
        "final_score": float(final_score),
    }


def apply_weighting_to_chunk(chunk: dict[str, Any], *, now: Any = None) -> dict[str, Any]:
    normalized = dict(chunk)
    source_type = str(normalized.get("source_type") or "").strip().lower()
    half_life_days = normalized.get("decay_half_life")
    if half_life_days in (None, ""):
        half_life_days = normalized.get("time_decay_half_life_days")
    if half_life_days in (None, ""):
        half_life_days = half_life_for_type(source_type)

    relevance_score = normalized.get("rerank_score")
    if relevance_score in (None, ""):
        relevance_score = max(
            float(normalized.get("vector_score") or 0.0),
            float(normalized.get("keyword_score") or 0.0),
        )

    try:
        recency_decay = compute_recency_decay(
            published_at=normalized.get("published_at"),
            half_life_days=half_life_days,
            now=now,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        recency_decay = 1.0
        normalized["recency_status"] = "malformed_published_at"
        normalized["recency_warning"] = "invalid_published_at"
        normalized["published_at_parse_error"] = (
            f"{type(exc).__name__}: invalid published_at="
            f"{normalized.get('published_at')!r}: {exc}"
        )

    scoring = apply_source_weighting(
        relevance_score=float(relevance_score or 0.0),
        source_type=source_type,
        credibility_weight=normalized.get("credibility_weight"),
        recency_decay=recency_decay,
    )
    normalized["source_weight"] = scoring["source_weight"]
    normalized["credibility_weight"] = scoring["credibility_weight"]
    normalized["recency_decay"] = scoring["recency_decay"]
    normalized["relevance_score"] = scoring["relevance_score"]
    normalized["final_score"] = scoring["final_score"]
    normalized["decay_half_life"] = float(half_life_days)
    return normalized
