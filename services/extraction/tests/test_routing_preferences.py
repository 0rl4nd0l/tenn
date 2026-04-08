from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from services.extraction.routing_preferences import (
    load_preferences,
    snapshot_preferences,
    restore_snapshot,
    SCHEMA_VERSION,
)


def test_load_preferences_returns_none_when_file_missing():
    result = load_preferences(Path("/nonexistent/routing_preferences.json"))
    assert result is None


def test_load_preferences_returns_none_when_file_malformed(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text("not json", encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_none_when_schema_version_wrong(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text(
        json.dumps({"schema_version": 999, "method_preferences": {}}),
        encoding="utf-8",
    )
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_valid_prefs(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    data = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": "2026-04-08T14:30:00Z",
        "source_run_id": "run-1",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_pdftotext",
                "accuracy": 0.91,
                "fallback": "financial_metrics_docling",
                "fallback_accuracy": 0.78,
                "sample_count": 10,
                "last_updated": "2026-04-08T14:30:00Z",
            }
        },
        "min_sample_count": 5,
    }
    prefs_file.write_text(json.dumps(data), encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is not None
    assert result["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"


def test_snapshot_creates_prev_file(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text('{"schema_version": 1}', encoding="utf-8")
    prev_path = snapshot_preferences(prefs_file)
    assert prev_path.exists()
    assert prev_path.name == "routing_preferences.prev.json"
    assert prev_path.read_text(encoding="utf-8") == '{"schema_version": 1}'


def test_snapshot_returns_none_when_file_missing(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    result = snapshot_preferences(prefs_file)
    assert result is None


def test_restore_snapshot_overwrites_current(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prev_file = tmp_path / "routing_preferences.prev.json"
    prefs_file.write_text('{"new": true}', encoding="utf-8")
    prev_file.write_text('{"old": true}', encoding="utf-8")
    restore_snapshot(prefs_file)
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"old": True}
    assert not prev_file.exists()


def test_restore_snapshot_noop_when_no_prev(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text('{"current": true}', encoding="utf-8")
    restore_snapshot(prefs_file)
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"current": True}
