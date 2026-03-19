#!/usr/bin/env python3
from __future__ import annotations

import unittest

from services.evaluation.failure_analysis import build_failure_analysis
from services.extraction.router import REJECTED_ROWS_THRESHOLD


def _base_probe() -> dict:
    return {
        "status": "ok",
        "canonical_metrics": {},
        "completeness": {"row_count": 0},
        "normalized_metrics": [],
    }


class FailureAnalysisTests(unittest.TestCase):
    def test_extractor_runtime_failure(self) -> None:
        out = build_failure_analysis(
            selected_payload={"status": "failed", "canonical_metrics": {}, "completeness": {}, "normalized_metrics": []},
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 0.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="unknown",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "extractor_runtime_failure")
        self.assertFalse(out["stage_signals"]["extractor_status_ok"])

    def test_no_metric_candidates(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {},
                "completeness": {"row_count": 0},
                "normalized_metrics": [],
            },
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 1.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "no_metric_candidates")

    def test_non_canonical_only(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {},
                "completeness": {"row_count": 2, "rows_with_numeric_value": 0},
                "normalized_metrics": [{"metric": "custom_obscure_metric_xyz", "value": 1.0}],
                "document_diagnostics": [{}],
            },
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 1.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "non_canonical_only")

    def test_label_only_candidates(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {},
                "completeness": {"row_count": 3, "rows_with_numeric_value": 0},
                "normalized_metrics": [{"metric": "revenue", "value": None}],
                "document_diagnostics": [{}],
            },
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 1.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "label_only_candidates")

    def test_numeric_unverified(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {"revenue": 100.0},
                "completeness": {"row_count": 1, "rows_with_numeric_value": 1},
                "normalized_metrics": [],
                "document_diagnostics": [{}],
            },
            verification={
                "verified": {},
                "rejected": {"revenue": {"value": 100.0, "numeric_match": False, "context_match": False}},
                "verified_count": 0,
                "rejected_count": 1,
                "verification_ratio": 0.0,
            },
            strict_truth_mode=True,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "numeric_unverified")
        self.assertIn("strict_truth_mode_drops_unverified_metrics", out["failure_reasons"])

    def test_ambiguity_conflict_rejected_rows_threshold(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {},
                "completeness": {"row_count": 0},
                "normalized_metrics": [],
                "document_diagnostics": [
                    {
                        "rejected_rows": REJECTED_ROWS_THRESHOLD,
                        "consistency_failures": 0,
                        "identity_resolution_conflicts": 0,
                        "rejection_reasons": {},
                    }
                ],
            },
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 1.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "ambiguity_conflict")
        self.assertIn("rejected_rows_high", out["failure_reasons"])

    def test_success_full_verification(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {"revenue": 100.0},
                "completeness": {"row_count": 1, "rows_with_numeric_value": 1},
                "normalized_metrics": [],
                "document_diagnostics": [{}],
            },
            verification={
                "verified": {"revenue": 100.0},
                "rejected": {},
                "verified_count": 1,
                "rejected_count": 0,
                "verification_ratio": 1.0,
            },
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="annual_report",
            is_financial=True,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "success")
        self.assertEqual(out["stage_signals"]["verification_ratio"], 1.0)

    def test_likely_non_financial(self) -> None:
        out = build_failure_analysis(
            selected_payload={
                "status": "ok",
                "canonical_metrics": {},
                "completeness": {"row_count": 0},
                "normalized_metrics": [],
                "document_diagnostics": [{}],
            },
            verification={"verified": {}, "rejected": {}, "verified_count": 0, "rejected_count": 0, "verification_ratio": 1.0},
            strict_truth_mode=False,
            fallback_triggered=False,
            docling_executed=False,
            selected_method="financial_metrics_pdftotext",
            document_type="unknown",
            is_financial=False,
            probe_method_payload=_base_probe(),
            probe_coverage=0.0,
        )
        self.assertEqual(out["failure_class"], "likely_non_financial")


if __name__ == "__main__":
    unittest.main()
