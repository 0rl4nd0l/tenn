from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from services.extraction.router import select_extractor_with_reason

def _make_prefs(doc_type: str, preferred: str, sample_count: int = 10) -> dict:
    return {
        "schema_version": 1, "updated_at": "2026-04-08T00:00:00Z", "source_run_id": "test",
        "method_preferences": {
            doc_type: {
                "preferred": preferred, "accuracy": 0.90,
                "fallback": "financial_metrics_docling", "fallback_accuracy": 0.70,
                "sample_count": sample_count, "last_updated": "2026-04-08T00:00:00Z",
            }
        },
        "min_sample_count": 5,
    }

def _mock_classifier(doc_type: str = "structured_financial_reports"):
    return {"document_type": doc_type, "complexity_score": 0.5, "table_density": 0.1}

@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.router.classify_pdf", return_value=_mock_classifier())
def test_rule0_uses_learned_preference(mock_classify, mock_load):
    mock_load.return_value = _make_prefs("structured_financial_reports", "financial_metrics_docling")
    result = select_extractor_with_reason(document_diagnostics={"rejected_rows": 0}, method_results={})
    assert result["selected_extractor"] == "financial_metrics_docling"
    assert result["reason"] == "learned_preference_structured_financial_reports"

@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.router.classify_pdf", return_value=_mock_classifier())
def test_rule0_falls_through_insufficient_samples(mock_classify, mock_load):
    mock_load.return_value = _make_prefs("structured_financial_reports", "financial_metrics_docling", sample_count=2)
    result = select_extractor_with_reason(document_diagnostics={"rejected_rows": 0}, method_results={})
    assert result["reason"] != "learned_preference_structured_financial_reports"

@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.router.classify_pdf", return_value=_mock_classifier())
def test_rule0_falls_through_when_no_prefs(mock_classify, mock_load):
    mock_load.return_value = None
    result = select_extractor_with_reason(document_diagnostics={"rejected_rows": 0}, method_results={})
    assert result["reason"] != "learned_preference_structured_financial_reports"

@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.router.classify_pdf", return_value=_mock_classifier("unknown_type"))
def test_rule0_falls_through_when_doc_type_not_in_prefs(mock_classify, mock_load):
    mock_load.return_value = _make_prefs("structured_financial_reports", "financial_metrics_docling")
    result = select_extractor_with_reason(document_diagnostics={"rejected_rows": 0}, method_results={})
    assert "learned_preference" not in result["reason"]
