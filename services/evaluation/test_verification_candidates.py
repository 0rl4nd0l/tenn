#!/usr/bin/env python3
from __future__ import annotations

import unittest

from services.evaluation.verification_candidates import (
    build_verification_candidates,
    build_verification_candidates_with_stats,
)


class VerificationCandidatesTests(unittest.TestCase):
    def test_uncertain_period_scope_survive_to_verification_candidates(self) -> None:
        payload = {
            "canonical_metrics": {"revenue": 100.0},
            "primary_rows": [
                {"metric": "ebit", "value": 20.0, "period": "", "statement_scope": "unknown"},
            ],
        }
        out = build_verification_candidates(
            payload,
            strict_period_filter=True,
            strict_scope_filter=True,
            strict_evidence=True,
        )
        self.assertIn("revenue", out)
        self.assertIn("ebit", out)

    def test_strict_period_scope_record_drop_counters(self) -> None:
        payload = {
            "canonical_metrics": {"revenue": 100.0},
            "primary_rows": [
                {"metric": "ebit", "value": 20.0, "period": "", "statement_scope": "unknown"},
            ],
        }
        _, stats = build_verification_candidates_with_stats(
            payload,
            strict_period_filter=True,
            strict_scope_filter=True,
            strict_evidence=True,
        )
        self.assertEqual(stats["dropped_period"], 1)
        self.assertEqual(stats["dropped_scope"], 1)

    def test_relaxed_flags_include_noncanonical_row_candidates(self) -> None:
        payload = {
            "canonical_metrics": {"revenue": 100.0},
            "primary_rows": [
                {"metric": "trade_and_other_receivables", "value": 33.0, "period": "", "statement_scope": "other"},
                {"metric": "ebit", "value": 20.0, "period": "2024-12-31", "statement_scope": "income_statement"},
            ],
        }
        out = build_verification_candidates(
            payload,
            strict_period_filter=False,
            strict_scope_filter=False,
            strict_evidence=False,
        )
        self.assertIn("revenue", out)
        self.assertIn("trade_and_other_receivables", out)
        self.assertIn("ebit", out)

    def test_noncanonical_numeric_candidate_excluded_when_explicit_noise(self) -> None:
        payload = {
            "canonical_metrics": {"revenue": 100.0},
            "primary_rows": [
                {
                    "metric": "abc_xyz",
                    "value": 12.0,
                    "period": "",
                    "statement_scope": "unknown",
                    "row_label": "drill assay update",
                    "line": "ore g/t au result",
                }
            ],
        }
        out, stats = build_verification_candidates_with_stats(
            payload,
            strict_period_filter=False,
            strict_scope_filter=False,
            strict_evidence=True,
        )
        self.assertNotIn("abc_xyz", out)
        self.assertEqual(stats["dropped_noncanonical"], 1)


if __name__ == "__main__":
    unittest.main()
