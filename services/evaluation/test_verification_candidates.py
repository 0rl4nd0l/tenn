#!/usr/bin/env python3
from __future__ import annotations

import unittest

from services.evaluation.verification_candidates import build_verification_candidates


class VerificationCandidatesTests(unittest.TestCase):
    def test_strict_flags_return_canonical_only(self) -> None:
        payload = {
            "canonical_metrics": {"revenue": 100.0},
            "primary_rows": [{"metric": "ebit", "value": 20.0, "period": "2024-12-31", "statement_scope": "income_statement"}],
        }
        out = build_verification_candidates(
            payload,
            strict_period_filter=True,
            strict_scope_filter=True,
            strict_evidence=True,
        )
        self.assertEqual(out, {"revenue": 100.0})

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


if __name__ == "__main__":
    unittest.main()
