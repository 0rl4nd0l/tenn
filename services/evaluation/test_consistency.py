#!/usr/bin/env python3
from __future__ import annotations

import unittest

from services.evaluation.consistency import compute_extraction_consistency_checks


class TestExtractionConsistency(unittest.TestCase):
    def test_verified_metric_missing_from_final_flag(self) -> None:
        out = compute_extraction_consistency_checks(
            selected_payload={},
            verified_metrics={"revenue": 1.0},
            final_metrics={},
            strict_truth_mode=False,
        )
        self.assertTrue(out["has_inconsistency"])
        self.assertIn("verified_metric_missing_from_final", out["flags"])
        self.assertEqual(out["details"]["verified_metric_missing_from_final"]["metrics"], ["revenue"])

    def test_final_metric_without_verified_evidence_only_in_strict_mode(self) -> None:
        loose = compute_extraction_consistency_checks(
            selected_payload={},
            verified_metrics={"revenue": 1.0},
            final_metrics={"revenue": 1.0, "ebitda": 2.0},
            strict_truth_mode=False,
        )
        self.assertNotIn("final_metric_without_verified_evidence", loose["flags"])

        strict = compute_extraction_consistency_checks(
            selected_payload={},
            verified_metrics={"revenue": 1.0},
            final_metrics={"revenue": 1.0, "ebitda": 2.0},
            strict_truth_mode=True,
        )
        self.assertTrue(strict["has_inconsistency"])
        self.assertIn("final_metric_without_verified_evidence", strict["flags"])
        self.assertIn("ebitda", strict["details"]["final_metric_without_verified_evidence"]["metrics"])

    def test_conflict_demotion_and_primary_flags(self) -> None:
        payload = {
            "canonical_rows": [
                {
                    "line_no": 10,
                    "metric": "total_assets",
                    "value": "",
                    "raw_value": "",
                    "canonical_confidence_score": 1,
                },
            ],
            "context_rows": [
                {
                    "line_no": 20,
                    "metric": "total_assets",
                    "value": "100",
                    "raw_value": "100",
                    "context_reason": "canonical_conflict_same_period",
                    "canonical_conflict_winner_line_no": 10,
                    "canonical_confidence_score": 9,
                },
            ],
            "rejected_rows": [],
            "primary_rows": [{"line_no": 5, "metric": "revenue", "value": "", "raw_value": "n/a"}],
        }
        out = compute_extraction_consistency_checks(
            selected_payload=payload,
            verified_metrics={},
            final_metrics={},
            strict_truth_mode=False,
        )
        self.assertIn("numeric_candidate_demoted_while_label_only_selected", out["flags"])
        self.assertIn("conflict_winner_is_weaker_than_loser", out["flags"])
        self.assertIn("canonical_primary_without_numeric", out["flags"])

    def test_clean_pass_no_flags(self) -> None:
        out = compute_extraction_consistency_checks(
            selected_payload={"canonical_rows": [], "context_rows": [], "rejected_rows": [], "primary_rows": []},
            verified_metrics={"revenue": 1.0},
            final_metrics={"revenue": 1.0},
            strict_truth_mode=True,
        )
        self.assertFalse(out["has_inconsistency"])
        self.assertEqual(out["flags"], [])


if __name__ == "__main__":
    unittest.main()
