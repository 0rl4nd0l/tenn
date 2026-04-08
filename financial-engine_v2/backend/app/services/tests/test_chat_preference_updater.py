from __future__ import annotations

import pytest

from app.services.chat_preference_updater import update_preferences


def test_update_preferences_picks_better_retrieval_params():
    """Given turns with better composite metric for params A, prefer A."""
    turns = [
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.85,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.88,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 8, "commentary_weight": 0.15},
            "composite_metric": 0.72,
        },
    ]
    result = update_preferences(
        quality_turns=turns,
        current_prefs=None,
        min_sample_count=2,
    )
    pref = result["retrieval_preferences"]["rag_financial_synthesis"]
    assert pref["top_k"] == 12
    assert pref["commentary_weight"] == 0.25
    assert pref["avg_composite_metric"] > 0.85


def test_update_preferences_picks_better_router_role():
    """Given turns with better composite metric for deep_reasoning, prefer it."""
    turns = [
        {
            "financial_task_type": "valuation_analysis",
            "router_role": "deep_reasoning",
            "composite_metric": 0.90,
        },
        {
            "financial_task_type": "valuation_analysis",
            "router_role": "deep_reasoning",
            "composite_metric": 0.92,
        },
        {
            "financial_task_type": "valuation_analysis",
            "router_role": "reasoning",
            "composite_metric": 0.78,
        },
    ]
    result = update_preferences(
        quality_turns=turns,
        current_prefs=None,
        min_sample_count=2,
    )
    pref = result["router_preferences"]["valuation_analysis"]
    assert pref["preferred_role"] == "deep_reasoning"
    assert pref["avg_composite_metric"] > 0.90


def test_update_preferences_accumulates_sample_count():
    """Sample counts should accumulate across updates when enough new samples."""
    existing = {
        "schema_version": 1,
        "updated_at": "2026-04-07T00:00:00Z",
        "source_session_id": "old",
        "metric_weights": {
            "w_retrieval": 0.4,
            "w_confidence": 0.35,
            "w_coherence": 0.25,
            "sample_count": 50,
        },
        "retrieval_preferences": {
            "rag_financial_synthesis": {
                "top_k": 12,
                "commentary_weight": 0.25,
                "avg_composite_metric": 0.80,
                "sample_count": 30,
            }
        },
        "min_sample_count": 5,
    }
    turns = [
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.85,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.88,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.87,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.86,
        },
        {
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "composite_metric": 0.89,
        },
    ]
    result = update_preferences(
        quality_turns=turns,
        current_prefs=existing,
        min_sample_count=5,
    )
    pref = result["retrieval_preferences"]["rag_financial_synthesis"]
    assert pref["sample_count"] == 35  # 30 + 5


def test_update_preferences_skips_task_type_below_min_samples():
    """Task types with < min_sample_count should be skipped."""
    turns = [
        {
            "financial_task_type": "catalyst_detection",
            "retrieval_params": {"top_k": 8},
            "composite_metric": 0.85,
        },
    ]
    result = update_preferences(
        quality_turns=turns,
        current_prefs=None,
        min_sample_count=5,
    )
    assert "catalyst_detection" not in result.get("retrieval_preferences", {})
