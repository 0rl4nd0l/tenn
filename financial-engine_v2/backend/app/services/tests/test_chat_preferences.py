from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.chat_preferences import (
    SCHEMA_VERSION,
    load_preferences,
    restore_snapshot,
    snapshot_preferences,
)


def test_load_preferences_returns_none_when_file_missing():
    result = load_preferences(Path("/nonexistent/chat_preferences.json"))
    assert result is None


def test_load_preferences_returns_none_when_file_malformed(tmp_path):
    prefs_file = tmp_path / "chat_preferences.json"
    prefs_file.write_text("not json", encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_none_when_schema_version_wrong(tmp_path):
    prefs_file = tmp_path / "chat_preferences.json"
    prefs_file.write_text(
        json.dumps({"schema_version": 999, "retrieval_preferences": {}}),
        encoding="utf-8",
    )
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_valid_prefs(tmp_path):
    prefs_file = tmp_path / "chat_preferences.json"
    data = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": "2026-04-08T14:30:00Z",
        "source_session_id": "session-1",
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
                "avg_composite_metric": 0.82,
                "sample_count": 45,
            }
        },
        "min_sample_count": 10,
    }
    prefs_file.write_text(json.dumps(data), encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is not None
    assert result["retrieval_preferences"]["rag_financial_synthesis"]["top_k"] == 12


def test_snapshot_creates_prev_file(tmp_path):
    prefs_file = tmp_path / "chat_preferences.json"
    prefs_file.write_text('{"schema_version": 1}', encoding="utf-8")
    prev_path = snapshot_preferences(prefs_file)
    assert prev_path.exists()
    assert prev_path.name == "chat_preferences.prev.json"


def test_restore_snapshot_overwrites_current(tmp_path):
    prefs_file = tmp_path / "chat_preferences.json"
    prev_file = tmp_path / "chat_preferences.prev.json"
    prefs_file.write_text('{"new": true}', encoding="utf-8")
    prev_file.write_text('{"old": true}', encoding="utf-8")
    restore_snapshot(prefs_file)
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"old": True}
    assert not prev_file.exists()
