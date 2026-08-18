from __future__ import annotations

import pytest

from app.services.chat_quality_scorer import (
    compute_retrieval_precision,
    compute_session_coherence,
    score_turn,
)


def test_compute_retrieval_precision_high_scores():
    chunks = [
        {"final_score": 0.9, "relevance_score": 0.85},
        {"final_score": 0.88, "relevance_score": 0.80},
        {"final_score": 0.85, "relevance_score": 0.78},
    ]
    precision = compute_retrieval_precision(chunks)
    assert precision > 0.85


def test_compute_retrieval_precision_low_scores():
    chunks = [
        {"final_score": 0.3, "relevance_score": 0.25},
        {"final_score": 0.25, "relevance_score": 0.20},
    ]
    precision = compute_retrieval_precision(chunks)
    assert precision < 0.35


def test_compute_retrieval_precision_empty_chunks():
    precision = compute_retrieval_precision([])
    assert precision == 0.0


def test_compute_retrieval_precision_treats_zero_final_score_as_real_score():
    chunks = [
        {"final_score": 0.0, "relevance_score": 0.9},
        {"final_score": 0.0, "relevance_score": 0.8},
    ]

    precision = compute_retrieval_precision(chunks)

    assert precision == 0.0


def test_compute_retrieval_precision_falls_back_when_final_score_missing():
    chunks = [
        {"relevance_score": 0.7},
        {"final_score": None, "relevance_score": 0.5},
    ]

    precision = compute_retrieval_precision(chunks)

    assert precision == pytest.approx(0.6)


def test_compute_retrieval_precision_falls_back_when_final_score_invalid():
    chunks = [
        {"final_score": "not-a-score", "relevance_score": 0.6},
        {"final_score": "", "relevance_score": 0.4},
    ]

    precision = compute_retrieval_precision(chunks)

    assert precision == pytest.approx(0.5)


def test_compute_retrieval_precision_excludes_ephemeral_and_concat_chunks():
    chunks = [
        {"final_score": 0.5, "source_kind": "primary"},
        {"final_score": 1.0, "source_kind": "ephemeral"},
        {"final_score": 1.0, "source_kind": "concat"},
        {"final_score": 0.7, "source_kind": "news"},
        {"final_score": 0.3},
    ]

    precision = compute_retrieval_precision(chunks)

    assert precision == pytest.approx(0.5)


def test_compute_session_coherence_no_prior_turns():
    coherence = compute_session_coherence(
        session_id="new-session",
        current_query="What is BHP's revenue?",
        prev_query=None,
    )
    assert coherence == 1.0  # neutral for first turn


def test_compute_session_coherence_rephrase(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.embed_texts",
        lambda _texts: [[1.0, 0.0], [1.0, 0.0]],
    )

    # Identical query = high similarity = low coherence
    coherence = compute_session_coherence(
        session_id="session-1",
        current_query="What is BHP's revenue?",
        prev_query="What is BHP's revenue?",
    )
    assert coherence < 0.2  # user is repeating = bad


def test_compute_session_coherence_negative_cosine_is_clamped(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.embed_texts",
        lambda _texts: [[1.0, 0.0], [-1.0, 0.0]],
    )

    coherence = compute_session_coherence(
        session_id="session-1",
        current_query="What is BHP's revenue?",
        prev_query="What is RIO's debt level?",
    )

    assert coherence == 1.0


def test_compute_session_coherence_new_topic(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.embed_texts",
        lambda _texts: [[1.0, 0.0], [0.5, 0.8660254]],
    )

    # Different but related queries still show some similarity
    # The threshold should be moderate (not too high)
    coherence = compute_session_coherence(
        session_id="session-1",
        current_query="What is RIO's debt level?",
        prev_query="What is BHP's revenue?",
    )
    assert (
        0.2 < coherence < 0.8
    )  # moderate coherence for related but different questions


def test_score_turn_composite_metric():
    chunks = [{"final_score": 0.85}]
    result = score_turn(
        query="What is BHP's revenue?",
        session_id="session-1",
        retrieval_hits=chunks,
        model_confidence=0.9,
        prev_query=None,
        weights={"w_retrieval": 0.4, "w_confidence": 0.35, "w_coherence": 0.25},
    )
    assert "composite_metric" in result
    assert 0.0 <= result["composite_metric"] <= 1.0
    assert result["retrieval_precision"] > 0.8
    assert result["model_confidence"] == 0.9
    assert result["session_coherence"] == 1.0  # first turn
