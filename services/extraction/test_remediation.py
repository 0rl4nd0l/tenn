#!/usr/bin/env python3
from __future__ import annotations

from services.extraction.remediation import (
    assess_non_financial_explicit_drop,
    build_candidate_profile,
    financial_like_table_signals,
    label_only_or_empty_numeric_candidates,
    should_escalate_docling_after_probe,
    should_suppress_docling_for_explicit_non_financial,
)


def test_build_candidate_profile_counts_numeric_canonical() -> None:
    profile = build_candidate_profile(
        {
            "status": "ok",
            "completeness": {"row_count": 3, "rows_with_numeric_value": 1},
            "canonical_metrics": {"revenue": "100", "ebitda": None},
        }
    )
    assert profile["row_count"] == 3
    assert profile["rows_with_numeric_value"] == 1
    assert profile["canonical_numeric_metric_count"] == 1


def test_non_financial_explicit_drop_when_classifier_and_profile_agree() -> None:
    classifier = {
        "is_financial": False,
        "table_density": 0.02,
        "features": {"context_rows": 5, "pdftotext_row_count": 0, "tsr_tables_processed": 0},
    }
    profile = {
        "row_count": 0,
        "rows_with_numeric_value": 0,
        "canonical_numeric_metric_count": 0,
        "method_status": "ok",
    }
    out = assess_non_financial_explicit_drop(classifier, profile)
    assert out["applied"] is True
    assert out["reason"] == "non_financial_classifier_no_extractable_numeric_signal"


def test_non_financial_drop_not_applied_when_label_only_rows() -> None:
    classifier = {"is_financial": False, "features": {}, "table_density": 0.0}
    profile = {
        "row_count": 4,
        "rows_with_numeric_value": 0,
        "canonical_numeric_metric_count": 0,
        "method_status": "ok",
    }
    out = assess_non_financial_explicit_drop(classifier, profile)
    assert out["applied"] is False
    assert out["detail"] == "label_only_rows_need_escalation"


def test_financial_like_table_signal_overrides_non_financial_classifier() -> None:
    classifier = {
        "is_financial": False,
        "table_density": 0.12,
        "complexity_score": 0.5,
        "features": {"context_rows": 50, "pdftotext_row_count": 0, "tsr_tables_processed": 0},
    }
    profile = {
        "row_count": 0,
        "rows_with_numeric_value": 0,
        "canonical_numeric_metric_count": 0,
        "method_status": "ok",
    }
    out = assess_non_financial_explicit_drop(classifier, profile)
    assert out["applied"] is False
    assert out["detail"] == "strong_table_signal_overrides_non_financial_classifier"


def test_escalation_when_label_only_and_financial_classifier() -> None:
    classifier = {
        "is_financial": True,
        "features": {"context_rows": 10, "pdftotext_row_count": 2, "tsr_tables_processed": 0},
        "table_density": 0.04,
    }
    profile = {
        "row_count": 6,
        "rows_with_numeric_value": 0,
        "canonical_numeric_metric_count": 0,
        "method_status": "ok",
    }
    ok, reason = should_escalate_docling_after_probe(
        classifier=classifier,
        profile=profile,
        fallback_reasons=[],
        explicit_non_financial_drop=False,
    )
    assert ok is True
    assert "label_only_or_empty_numeric" in reason


def test_no_escalation_when_fallback_reasons_nonempty() -> None:
    classifier = {"is_financial": True, "features": {}}
    profile = {"row_count": 0, "rows_with_numeric_value": 0, "canonical_numeric_metric_count": 0, "method_status": "ok"}
    ok, reason = should_escalate_docling_after_probe(
        classifier=classifier,
        profile=profile,
        fallback_reasons=["low_confidence"],
        explicit_non_financial_drop=False,
    )
    assert ok is False
    assert "already_trigger" in reason


def test_suppress_docling_for_explicit_non_financial_unless_anomaly() -> None:
    assessment = {"applied": True, "reason": "non_financial_classifier_no_extractable_numeric_signal"}
    assert should_suppress_docling_for_explicit_non_financial(assessment, []) is True
    assert should_suppress_docling_for_explicit_non_financial(assessment, ["financial_anomaly"]) is False


def test_label_only_or_empty_numeric_candidates() -> None:
    assert (
        label_only_or_empty_numeric_candidates(
            {"row_count": 2, "rows_with_numeric_value": 0, "canonical_numeric_metric_count": 0, "method_status": "ok"}
        )
        is True
    )
    assert (
        label_only_or_empty_numeric_candidates(
            {"row_count": 0, "rows_with_numeric_value": 0, "canonical_numeric_metric_count": 0, "method_status": "ok"}
        )
        is True
    )
    assert (
        label_only_or_empty_numeric_candidates(
            {"row_count": 2, "rows_with_numeric_value": 1, "canonical_numeric_metric_count": 0, "method_status": "ok"}
        )
        is False
    )


def test_financial_like_table_signals_threshold() -> None:
    weak = financial_like_table_signals(
        {"features": {"context_rows": 5, "pdftotext_row_count": 1, "tsr_tables_processed": 0}, "table_density": 0.01, "complexity_score": 0.1}
    )
    assert weak["strong_financial_table_signal"] is False
    strong = financial_like_table_signals(
        {"features": {"context_rows": 50, "pdftotext_row_count": 0, "tsr_tables_processed": 3}, "table_density": 0.2, "complexity_score": 0.5}
    )
    assert strong["strong_financial_table_signal"] is True
