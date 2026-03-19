#!/usr/bin/env python3
"""Unit tests for run_extract_broad_tickers validation and logical-doc grouping."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Import after path fix (module lives in scripts/)
import run_extract_broad_tickers as RUNNER


class TestLogicalDoc(unittest.TestCase):
    def test_strips_uuid_suffix(self):
        path = "/data/docs/29M/financial_performance/2022-02-23_fy2021-appendix-4e_68d6b280-a7e2-4e10-8139-a6ee3a91f87f.pdf"
        out = RUNNER._logical_doc(path)
        self.assertIn("2022-02-23_fy2021-appendix-4e.pdf", out)
        self.assertNotIn("68d6b280", out)

    def test_empty_returns_empty(self):
        self.assertEqual(RUNNER._logical_doc(""), "")
        self.assertEqual(RUNNER._logical_doc(None), None)

    def test_no_uuid_unchanged(self):
        path = "/data/report.pdf"
        self.assertEqual(RUNNER._logical_doc(path), path)


class TestValidateCanonicalLogic(unittest.TestCase):
    def test_same_logical_doc_different_values_one_conflict(self):
        """Duplicate PDFs (same report, two UUIDs) with different extractions → one conflict by logical_doc."""
        base = "/docs/29M/financial_performance/2022-02-23_fy2021-appendix-4e-annual-financial-report"
        rows = [
            {"file": base + "_68d6b280-a7e2-4e10-8139-a6ee3a91f87f.pdf", "statement_period_end": "2021-07-02", "metric": "npat", "value": 121013.0},
            {"file": base + "_79c2cf8d-43d7-4e15-b7ab-df32004d37cb.pdf", "statement_period_end": "2021-07-02", "metric": "npat", "value": 55796000.0},
        ]
        v = RUNNER.validate_canonical_logic(rows)
        self.assertFalse(v["valid"])
        self.assertEqual(v["conflicts"], 1)
        self.assertEqual(len([i for i in v["issues"] if "Conflicting" in i]), 1)
        self.assertIn("doc=", v["issues"][-1])
        self.assertIn("2022-02-23_fy2021-appendix-4e", v["issues"][-1])

    def test_same_logical_doc_same_value_no_conflict(self):
        """Duplicate PDFs with same value → no conflict."""
        base = "/docs/ACF/2024-02-20_half-yearly-report"
        rows = [
            {"file": base + "_abb2848e-4b7e-4a80-b607-a375720e2c52.pdf", "statement_period_end": "2023-12-31", "metric": "revenue", "value": 101041125.0},
            {"file": base + "_d80e7ec5-2f56-4d71-a507-c7b9f01354a2.pdf", "statement_period_end": "2023-12-31", "metric": "revenue", "value": 101041125.0},
        ]
        v = RUNNER.validate_canonical_logic(rows)
        self.assertTrue(v["valid"])
        self.assertEqual(v["conflicts"], 0)

    def test_iso_period_ok(self):
        rows = [{"file": "/a.pdf", "statement_period_end": "2024-12-31", "metric": "revenue", "value": 100.0}]
        v = RUNNER.validate_canonical_logic(rows)
        self.assertEqual(v["period_ok"], 1)
        self.assertEqual(v["period_bad"], 0)


if __name__ == "__main__":
    unittest.main()
