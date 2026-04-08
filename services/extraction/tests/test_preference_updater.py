from __future__ import annotations
import pytest
from services.extraction.preference_updater import update_preferences

def _make_report(doc_type_stratified: dict) -> dict:
    return {
        "stratified": {
            "document_type": doc_type_stratified,
            "complexity_bucket": {},
            "extraction_method": {},
        },
        "documents_total": 12,
    }

def test_update_preferences_picks_higher_accuracy_method():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10, "accuracy": 0.91, "fallback_rate": 0.1, "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91, "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report, method_accuracies=method_accuracies,
        current_prefs=None, min_sample_count=5,
    )
    pref = result["method_preferences"]["structured_financial_reports"]
    assert pref["preferred"] == "financial_metrics_pdftotext"
    assert pref["fallback"] == "financial_metrics_docling"
    assert pref["accuracy"] == 0.91
    assert pref["fallback_accuracy"] == 0.78
    assert pref["sample_count"] == 10

def test_update_preferences_accumulates_sample_count():
    existing = {
        "schema_version": 1, "updated_at": "2026-04-07T00:00:00Z", "source_run_id": "old",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_pdftotext", "accuracy": 0.85,
                "fallback": "financial_metrics_docling", "fallback_accuracy": 0.70,
                "sample_count": 20, "last_updated": "2026-04-07T00:00:00Z",
            },
        },
        "min_sample_count": 5,
    }
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10, "accuracy": 0.91, "fallback_rate": 0.1, "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91, "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report, method_accuracies=method_accuracies,
        current_prefs=existing, min_sample_count=5,
    )
    assert result["method_preferences"]["structured_financial_reports"]["sample_count"] == 30

def test_update_preferences_preserves_unaffected_doc_types():
    existing = {
        "schema_version": 1, "updated_at": "2026-04-07T00:00:00Z", "source_run_id": "old",
        "method_preferences": {
            "complex_ocr_heavy": {
                "preferred": "financial_metrics_docling", "accuracy": 0.80,
                "fallback": "financial_metrics_pdftotext", "fallback_accuracy": 0.55,
                "sample_count": 15, "last_updated": "2026-04-06T00:00:00Z",
            },
        },
        "min_sample_count": 5,
    }
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10, "accuracy": 0.91, "fallback_rate": 0.1, "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91, "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report, method_accuracies=method_accuracies,
        current_prefs=existing, min_sample_count=5,
    )
    assert "complex_ocr_heavy" in result["method_preferences"]
    assert result["method_preferences"]["complex_ocr_heavy"]["preferred"] == "financial_metrics_docling"

def test_update_preferences_skips_doc_type_below_min_samples():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 2, "accuracy": 0.91, "fallback_rate": 0.1, "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91, "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report, method_accuracies=method_accuracies,
        current_prefs=None, min_sample_count=5,
    )
    assert "structured_financial_reports" not in result["method_preferences"]

def test_update_preferences_equal_accuracy_keeps_pdftotext():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10, "accuracy": 0.85, "fallback_rate": 0.0, "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.85, "financial_metrics_docling": 0.85,
        },
    }
    result = update_preferences(
        assessment_report=report, method_accuracies=method_accuracies,
        current_prefs=None, min_sample_count=5,
    )
    pref = result["method_preferences"]["structured_financial_reports"]
    assert pref["preferred"] == "financial_metrics_pdftotext"
