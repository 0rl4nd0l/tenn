from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.services.router_optimizer import _preferred_role_name


@pytest.fixture
def temp_prefs_file():
    """Create a temporary chat_preferences.json file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


def test_preferred_role_name_uses_learned_preference(temp_prefs_file, monkeypatch):
    """Rule 0: _preferred_role_name should use learned router preference."""
    prefs = {
        "schema_version": 1,
        "updated_at": "2026-04-07T12:00:00Z",
        "source_session_id": "test_session",
        "metric_weights": {
            "w_retrieval": 0.4,
            "w_confidence": 0.35,
            "w_coherence": 0.25,
            "sample_count": 20,
        },
        "retrieval_preferences": {},
        "router_preferences": {
            "valuation_analysis": {
                "preferred_role": "deep_reasoning",
                "avg_composite_metric": 0.92,
                "sample_count": 15,
            }
        },
    }
    temp_prefs_file.write_text(json.dumps(prefs), encoding="utf-8")

    # Patch the _CHAT_PREFERENCES_PATH constant
    import app.services.router_optimizer as ro_module

    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", temp_prefs_file)

    # Call with valuation_analysis - normally would choose "reasoning" based on config
    # but learned preference should override to "deep_reasoning"
    config = {
        "valuation_force_deep_reasoning": False,  # Normally would return "reasoning"
        "deep_prompt_chars": 3000,
        "short_prompt_chars": 300,
    }
    result = _preferred_role_name(
        task_type="reasoning",
        financial_task_type="valuation_analysis",
        prompt="What is BHP's valuation?",
        prompt_length=100,
        deep_reasoning_requested=False,
        metadata={"financial_task_type": "valuation_analysis"},
        complexity="medium",
        config=config,
    )
    # Should use learned preference
    assert result == "deep_reasoning"


def test_preferred_role_name_ignores_invalid_learned_role(temp_prefs_file, monkeypatch):
    """Rule 0: invalid learned roles should be ignored."""
    prefs = {
        "schema_version": 1,
        "updated_at": "2026-04-07T12:00:00Z",
        "source_session_id": "test_session",
        "metric_weights": {
            "w_retrieval": 0.4,
            "w_confidence": 0.35,
            "w_coherence": 0.25,
            "sample_count": 20,
        },
        "retrieval_preferences": {},
        "router_preferences": {
            "filing_summary": {
                "preferred_role": "invalid_role",  # Invalid
                "avg_composite_metric": 0.85,
                "sample_count": 12,
            }
        },
    }
    temp_prefs_file.write_text(json.dumps(prefs), encoding="utf-8")

    import app.services.router_optimizer as ro_module

    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", temp_prefs_file)

    config = {
        "financial_short_summary_chars": 400,
        "financial_deep_analysis_chars": 2500,
        "deep_prompt_chars": 3000,
        "short_prompt_chars": 300,
    }
    result = _preferred_role_name(
        task_type="reasoning",
        financial_task_type="filing_summary",
        prompt="Short summary of BHP filing",
        prompt_length=150,
        deep_reasoning_requested=False,
        metadata={"financial_task_type": "filing_summary"},
        complexity="low",
        config=config,
    )
    # Should fall back to hardcoded logic (router for short summary)
    assert result == "router"


def test_preferred_role_name_uses_hardcoded_when_no_prefs(monkeypatch):
    """When chat_preferences.json doesn't exist, use hardcoded logic."""
    import app.services.router_optimizer as ro_module

    nonexistent_path = Path("/tmp/nonexistent_router_prefs.json")
    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", nonexistent_path)

    config = {
        "valuation_force_deep_reasoning": True,
        "deep_prompt_chars": 3000,
        "short_prompt_chars": 300,
    }
    result = _preferred_role_name(
        task_type="reasoning",
        financial_task_type="valuation_analysis",
        prompt="What is RIO's valuation?",
        prompt_length=100,
        deep_reasoning_requested=False,
        metadata={"financial_task_type": "valuation_analysis"},
        complexity="medium",
        config=config,
    )
    # Should use hardcoded logic (deep_reasoning because valuation_force_deep_reasoning=True)
    assert result == "deep_reasoning"


def test_preferred_role_name_skips_learned_prefs_for_non_financial_tasks(
    temp_prefs_file, monkeypatch
):
    """Rule 0 only applies to financial task types."""
    prefs = {
        "schema_version": 1,
        "updated_at": "2026-04-07T12:00:00Z",
        "source_session_id": "test_session",
        "metric_weights": {
            "w_retrieval": 0.4,
            "w_confidence": 0.35,
            "w_coherence": 0.25,
            "sample_count": 20,
        },
        "retrieval_preferences": {},
        "router_preferences": {
            "valuation_analysis": {
                "preferred_role": "deep_reasoning",
                "avg_composite_metric": 0.92,
                "sample_count": 15,
            }
        },
    }
    temp_prefs_file.write_text(json.dumps(prefs), encoding="utf-8")

    import app.services.router_optimizer as ro_module

    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", temp_prefs_file)

    config = {
        "deep_prompt_chars": 3000,
        "short_prompt_chars": 300,
    }
    # Call without financial_task_type
    result = _preferred_role_name(
        task_type="reasoning",
        financial_task_type=None,  # No financial task type
        prompt="What is the capital of Australia?",
        prompt_length=100,
        deep_reasoning_requested=False,
        metadata={},
        complexity="low",
        config=config,
    )
    # Should use hardcoded logic (router for low complexity)
    assert result == "router"
