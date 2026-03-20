#!/usr/bin/env python3
from __future__ import annotations

import unittest

from services.evaluation.fact_tuple_assembly import (
    build_fact_assembly_summary,
    enrich_row_to_fact_tuple,
)


class TestFactTupleAssembly(unittest.TestCase):
    def test_enrich_row_maps_source_and_concept(self) -> None:
        row = {
            "metric_base": "revenue",
            "value": 1234.0,
            "statement_family": "income_statement",
            "statement_scope": "group",
            "statement_period_end": "2023-12-31",
            "statement_period": "FY",
            "currency": "USD",
            "source_mode": "table_bbox",
            "page_number": 3,
            "line_no": 42,
            "line": "Revenue 1,234",
            "table_id": "doc:p1-p1:b1:t1",
            "table_page": 3,
            "block_id": "block-1",
        }
        ft = enrich_row_to_fact_tuple(row)
        self.assertEqual(ft["statement_type"], "income_statement")
        self.assertEqual(ft["concept"]["canonical"], "revenue")
        self.assertEqual(ft["scope"], "group")
        self.assertEqual(ft["period"]["period_end"], "2023-12-31")
        self.assertEqual(ft["period"]["period_type"], "FY")
        self.assertEqual(ft["sign"], "positive")
        self.assertEqual(ft["value"], 1234.0)
        self.assertEqual(ft["source"]["page"], 3)
        self.assertEqual(ft["source"]["line_no"], 42)
        self.assertEqual(ft["source"]["source_mode"], "table_bbox")
        self.assertEqual(ft["source"]["table_id"], "doc:p1-p1:b1:t1")
        self.assertEqual(ft["source"]["block_id"], "block-1")
        self.assertIn("usd", (ft.get("unit_scale_hint") or "").lower())

    def test_enrich_negative_parentheses_value(self) -> None:
        row = {
            "metric": "net_income",
            "value": "(500)",
            "statement_family": "income_statement",
        }
        ft = enrich_row_to_fact_tuple(row)
        self.assertEqual(ft["sign"], "negative")
        self.assertLess(float(ft["value"] or 0), 0)

    def test_assembly_summary_counts_and_verification(self) -> None:
        raw = """
        Consolidated income statement
        Revenue was 9,876 for the year ended 2023-12-31.
        """
        payload = {
            "canonical_rows": [
                {"metric_base": "unknown_xyz", "value": 100.0},
                {"metric_base": "revenue", "value": "not_a_number"},
                {
                    "metric_base": "revenue",
                    "value": 9876.0,
                    "statement_family": "income_statement",
                    "source_mode": "table_bbox",
                    "page_number": 1,
                },
            ]
        }
        s = build_fact_assembly_summary(payload, raw)
        self.assertEqual(s["total_candidate_rows"], 3)
        self.assertEqual(s["numeric_candidate_rows"], 2)
        self.assertEqual(s["canonical_fact_candidates"], 1)
        self.assertEqual(s["verified_facts"], 1)
        self.assertEqual(s["dropped_pre_verification"], 2)
        self.assertEqual(s["dropped_in_verification"], 0)

    def test_prefers_canonical_rows_over_primary(self) -> None:
        payload = {
            "canonical_rows": [{"metric_base": "revenue", "value": 1.0}],
            "primary_rows": [{"metric_base": "assets", "value": 2.0}],
        }
        s = build_fact_assembly_summary(payload, "Revenue 1 Assets 2")
        self.assertEqual(s["total_candidate_rows"], 1)

    def test_falls_back_to_primary_when_canonical_empty(self) -> None:
        payload = {
            "canonical_rows": [],
            "primary_rows": [{"metric_base": "revenue", "value": 50.0}],
        }
        s = build_fact_assembly_summary(payload, "Total revenue 50")
        self.assertEqual(s["total_candidate_rows"], 1)
        self.assertGreaterEqual(s["canonical_fact_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
