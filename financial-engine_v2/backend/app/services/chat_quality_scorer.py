from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_EXCLUDED_RETRIEVAL_PRECISION_SOURCE_KINDS = frozenset({"concat", "ephemeral"})


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    if left_vector.shape != right_vector.shape:
        return 0.0
    denominator = float(np.linalg.norm(left_vector) * np.linalg.norm(right_vector))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left_vector, right_vector) / denominator)


def compute_retrieval_precision(chunks: list[dict[str, Any]]) -> float:
    """Average final_score of retrieved chunks (0-1 scale)."""
    scored_chunks = [
        chunk for chunk in chunks if _counts_toward_retrieval_precision(chunk)
    ]
    if not scored_chunks:
        return 0.0
    scores = [_retrieval_precision_score(chunk) for chunk in scored_chunks]
    return sum(scores) / len(scores)


def _counts_toward_retrieval_precision(chunk: dict[str, Any]) -> bool:
    source_kind = str(chunk.get("source_kind") or "").strip().casefold()
    return source_kind not in _EXCLUDED_RETRIEVAL_PRECISION_SOURCE_KINDS


def _retrieval_precision_score(chunk: dict[str, Any]) -> float:
    final_score = _coerce_score(chunk.get("final_score"))
    if final_score is not None:
        return final_score

    relevance_score = _coerce_score(chunk.get("relevance_score"))
    if relevance_score is not None:
        return relevance_score
    return 0.0


def _coerce_score(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    return score


def compute_session_coherence(
    *,
    session_id: str,
    current_query: str,
    prev_query: str | None,
) -> float:
    """
    Returns coherence score (0-1):
    - 1.0 = good (user is building on context)
    - 0.0 = bad (user is repeating/rephrasing = previous answer was inadequate)
    """
    if not prev_query:
        return 1.0  # first turn in session

    # For now: simple embedding-based similarity
    # TODO: integrate with OpenViking session_memory after base implementation
    from app.services.llm import embed_texts

    try:
        embeddings = embed_texts([current_query, prev_query])
        if len(embeddings) != 2:
            return 1.0
        similarity = _cosine_similarity(embeddings[0], embeddings[1])
        # High similarity = low coherence (user is repeating)
        # Invert: coherence = 1 - similarity
        return max(0.0, min(1.0, 1.0 - similarity))
    except Exception as exc:
        logger.warning("compute_session_coherence failed: %s", exc)
        return 1.0  # neutral on error


def score_turn(
    *,
    query: str,
    session_id: str,
    retrieval_hits: list[dict[str, Any]],
    model_confidence: float,
    prev_query: str | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Compute composite quality metric for a chat turn.

    Returns:
    {
        "composite_metric": float,
        "retrieval_precision": float,
        "model_confidence": float,
        "session_coherence": float,
        "weights": {"w_retrieval": ..., "w_confidence": ..., "w_coherence": ...},
    }
    """
    default_weights = {
        "w_retrieval": 0.4,
        "w_confidence": 0.35,
        "w_coherence": 0.25,
    }
    resolved_weights = dict(weights or default_weights)

    retrieval_precision = compute_retrieval_precision(retrieval_hits)
    session_coherence = compute_session_coherence(
        session_id=session_id,
        current_query=query,
        prev_query=prev_query,
    )

    composite_metric = (
        resolved_weights["w_retrieval"] * retrieval_precision
        + resolved_weights["w_confidence"] * float(model_confidence)
        + resolved_weights["w_coherence"] * session_coherence
    )

    return {
        "composite_metric": max(0.0, min(composite_metric, 1.0)),
        "retrieval_precision": retrieval_precision,
        "model_confidence": float(model_confidence),
        "session_coherence": session_coherence,
        "weights": resolved_weights,
    }
