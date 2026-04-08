from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.chat_preference_updater import update_preferences
from app.services.chat_preferences import (
    SCHEMA_VERSION,
    load_preferences,
    restore_snapshot,
    save_preferences,
    snapshot_preferences,
)
from app.services.chat_skill_reviewer import (
    read_skill,
    restore_skill_snapshot,
    skill_patch,
    snapshot_skill,
)


def _make_quality_turns():
    return [
        {
            "session_id": "sess-1",
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "router_role": "deep_reasoning",
            "composite_metric": 0.88,
        },
        {
            "session_id": "sess-1",
            "financial_task_type": "rag_financial_synthesis",
            "retrieval_params": {"top_k": 12, "commentary_weight": 0.25},
            "router_role": "deep_reasoning",
            "composite_metric": 0.85,
        },
        {
            "session_id": "sess-2",
            "financial_task_type": "valuation_analysis",
            "retrieval_params": {"top_k": 8, "commentary_weight": 0.15},
            "router_role": "deep_reasoning",
            "composite_metric": 0.92,
        },
    ]


def test_full_cycle_quality_turns_to_preferences(tmp_path):
    """End-to-end: quality turns -> preferences -> correct params selected."""
    prefs_path = tmp_path / "chat_preferences.json"

    new_prefs = update_preferences(
        quality_turns=_make_quality_turns(),
        current_prefs=None,
        min_sample_count=2,
    )
    save_preferences(prefs_path, new_prefs)

    loaded = load_preferences(prefs_path)
    assert loaded is not None
    assert loaded["retrieval_preferences"]["rag_financial_synthesis"]["top_k"] == 12
    assert (
        loaded["router_preferences"]["rag_financial_synthesis"]["preferred_role"]
        == "deep_reasoning"
    )


def test_rollback_cycle(tmp_path):
    """Snapshot -> update -> rollback restores original."""
    prefs_path = tmp_path / "chat_preferences.json"

    original = {
        "schema_version": SCHEMA_VERSION,
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
                "top_k": 8,
                "commentary_weight": 0.15,
                "avg_composite_metric": 0.75,
                "sample_count": 10,
            }
        },
        "min_sample_count": 10,
    }
    save_preferences(prefs_path, original)
    snapshot_preferences(prefs_path)

    new_prefs = update_preferences(
        quality_turns=_make_quality_turns(),
        current_prefs=original,
        min_sample_count=2,
    )
    save_preferences(prefs_path, new_prefs)

    loaded = load_preferences(prefs_path)
    assert loaded["retrieval_preferences"]["rag_financial_synthesis"]["top_k"] == 12

    restore_snapshot(prefs_path)
    restored = load_preferences(prefs_path)
    assert restored["retrieval_preferences"]["rag_financial_synthesis"]["top_k"] == 8


def test_skill_patch_and_rollback(tmp_path):
    """Skill file: patch -> rollback restores original."""
    skill_path = tmp_path / "chat_skill.md"
    seed = (
        "---\nname: test\n---\n\n## RAG Retrieval Patterns\nNo patterns learned yet.\n"
    )
    skill_path.write_text(seed, encoding="utf-8")

    snapshot_skill(skill_path)

    skill_patch(
        skill_path=skill_path,
        old_string="No patterns learned yet.",
        new_string="- rag_financial_synthesis: prefer top_k=12 (avg 0.88)",
    )
    assert "prefer top_k=12" in read_skill(skill_path)

    restore_skill_snapshot(skill_path)
    assert "No patterns learned yet." in read_skill(skill_path)
