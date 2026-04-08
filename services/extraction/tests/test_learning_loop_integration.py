# services/extraction/tests/test_learning_loop_integration.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.extraction.preference_updater import update_preferences
from services.extraction.routing_preferences import (
    load_preferences,
    save_preferences,
    snapshot_preferences,
    restore_snapshot,
    SCHEMA_VERSION,
)
from services.extraction.skill_reviewer import (
    skill_patch,
    snapshot_skill,
    restore_skill_snapshot,
    read_skill,
)


def _make_full_assessment():
    return {
        "documents_total": 12,
        "routed_accuracy": 0.88,
        "fallback_rate": 0.15,
        "stratified": {
            "document_type": {
                "structured_financial_reports": {
                    "documents": 6, "accuracy": 0.91, "fallback_rate": 0.1, "anomaly_rate": 0.0,
                },
                "semi_structured_presentations": {
                    "documents": 4, "accuracy": 0.82, "fallback_rate": 0.2, "anomaly_rate": 0.05,
                },
                "complex_ocr_heavy": {
                    "documents": 2, "accuracy": 0.70, "fallback_rate": 0.5, "anomaly_rate": 0.0,
                },
            },
            "complexity_bucket": {},
            "extraction_method": {},
        },
    }


def _make_method_accuracies():
    return {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91, "financial_metrics_docling": 0.78,
        },
        "semi_structured_presentations": {
            "financial_metrics_pdftotext": 0.62, "financial_metrics_docling": 0.85,
        },
        "complex_ocr_heavy": {
            "financial_metrics_pdftotext": 0.55, "financial_metrics_docling": 0.70,
        },
    }


def test_full_cycle_preferences_to_routing(tmp_path):
    prefs_path = tmp_path / "routing_preferences.json"
    new_prefs = update_preferences(
        assessment_report=_make_full_assessment(),
        method_accuracies=_make_method_accuracies(),
        current_prefs=None,
        min_sample_count=2,
    )
    save_preferences(prefs_path, new_prefs)
    loaded = load_preferences(prefs_path)
    assert loaded is not None
    assert loaded["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"
    assert loaded["method_preferences"]["semi_structured_presentations"]["preferred"] == "financial_metrics_docling"
    assert loaded["method_preferences"]["complex_ocr_heavy"]["preferred"] == "financial_metrics_docling"


def test_rollback_cycle(tmp_path):
    prefs_path = tmp_path / "routing_preferences.json"
    original = {
        "schema_version": SCHEMA_VERSION, "updated_at": "2026-04-07T00:00:00Z",
        "source_run_id": "original",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_docling", "accuracy": 0.80,
                "fallback": "financial_metrics_pdftotext", "fallback_accuracy": 0.75,
                "sample_count": 5, "last_updated": "2026-04-07T00:00:00Z",
            }
        },
        "min_sample_count": 5,
    }
    save_preferences(prefs_path, original)
    snapshot_preferences(prefs_path)
    new_prefs = update_preferences(
        assessment_report=_make_full_assessment(),
        method_accuracies=_make_method_accuracies(),
        current_prefs=original,
        min_sample_count=3,
    )
    save_preferences(prefs_path, new_prefs)
    loaded = load_preferences(prefs_path)
    assert loaded["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"
    restore_snapshot(prefs_path)
    restored = load_preferences(prefs_path)
    assert restored["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_docling"


def test_skill_patch_and_rollback(tmp_path):
    skill_path = tmp_path / "extraction_skill.md"
    seed = "---\nname: test\n---\n\n## Document Type Patterns\nNo patterns learned yet.\n"
    skill_path.write_text(seed, encoding="utf-8")
    snapshot_skill(skill_path)
    skill_patch(
        skill_path=skill_path, old_string="No patterns learned yet.",
        new_string="- structured_financial_reports: prefer pdftotext (0.91 accuracy)",
    )
    assert "prefer pdftotext" in read_skill(skill_path)
    restore_skill_snapshot(skill_path)
    assert "No patterns learned yet." in read_skill(skill_path)
