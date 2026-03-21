#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.plotly_html import build_snapshot_dashboard_html, build_verification_dashboard_html  # noqa: E402


class CockpitPlotlyHtmlTests(unittest.TestCase):
    def test_snapshot_dashboard_contains_plotly_bootstrap_and_labels(self) -> None:
        html = build_snapshot_dashboard_html(
            {
                "ticker": "BHP",
                "created_at": "2026-03-21T00:00:00Z",
                "confidence_summary": {"before": 0.4, "after": 0.8},
                "verification_summary": {"checks": {"missing_pdf_files": 1, "blocked_documents": 0}},
                "metrics_diff": [
                    {"field": "revenue", "before": 100.0, "after": 110.0, "delta": 10.0},
                    {"field": "ebit", "before": 50.0, "after": 55.0, "delta": 5.0},
                ],
            }
        )
        self.assertIn("Plotly.newPlot('snapshot-comparison'", html)
        self.assertIn("BHP Snapshot Dashboard", html)
        self.assertIn("Verification Counts", html)

    def test_verification_dashboard_contains_tables_and_counts(self) -> None:
        html = build_verification_dashboard_html(
            {
                "ticker": "BHP",
                "checks": {"missing_pdf_files": 1, "blocked_documents": 2, "low_confidence_financials": 3},
                "samples": {
                    "extraction_failures": [
                        {"ticker": "BHP", "title": "BHP Interim Report", "error": "parse failed"}
                    ]
                },
                "remediation": ["Run resume_pending for this ticker."],
            }
        )
        self.assertIn("Plotly.newPlot('verification-counts'", html)
        self.assertIn("Sample Issues", html)
        self.assertIn("Run resume_pending for this ticker.", html)


if __name__ == "__main__":
    unittest.main()
