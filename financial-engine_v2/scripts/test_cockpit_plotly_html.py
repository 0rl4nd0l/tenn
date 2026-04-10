#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.plotly_html import (  # noqa: E402
    build_filestats_dashboard_html,
    build_snapshot_dashboard_html,
    build_verification_dashboard_html,
)


class CockpitPlotlyHtmlTests(unittest.TestCase):
    def test_snapshot_dashboard_contains_plotly_bootstrap_and_labels(self) -> None:
        html = build_snapshot_dashboard_html(
            {
                "ticker": "BHP",
                "created_at": "2026-03-21T00:00:00Z",
                "confidence_summary": {"before": 0.4, "after": 0.8},
                "verification_summary": {
                    "checks": {"missing_pdf_files": 1, "blocked_documents": 0}
                },
                "metrics_diff": [
                    {
                        "field": "revenue",
                        "before": 100.0,
                        "after": 110.0,
                        "delta": 10.0,
                    },
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
                "checks": {
                    "missing_pdf_files": 1,
                    "blocked_documents": 2,
                    "low_confidence_financials": 3,
                },
                "samples": {
                    "extraction_failures": [
                        {
                            "ticker": "BHP",
                            "title": "BHP Interim Report",
                            "error": "parse failed",
                        }
                    ]
                },
                "remediation": ["Run resume_pending for this ticker."],
            }
        )
        self.assertIn("Plotly.newPlot('verification-counts'", html)
        self.assertIn("Sample Issues", html)
        self.assertIn("Run resume_pending for this ticker.", html)

    def test_filestats_dashboard_contains_visual_sections(self) -> None:
        html = build_filestats_dashboard_html(
            {
                "ticker": "BHP",
                "generated_at": "2026-04-09T00:00:00Z",
                "summary": {
                    "doc_count": 2,
                    "financial_period_count": 1,
                    "price_points_1y": 2,
                    "last_close": 55.2,
                    "one_year_return_pct": 12.5,
                    "risk_note_count": 1,
                    "extraction_failure_count": 0,
                },
                "docs": [
                    {
                        "document_id": "doc-1",
                        "published_at": "2026-04-01",
                        "doc_class": "quarterly",
                        "title": "Quarterly Activities",
                    },
                    {
                        "document_id": "doc-2",
                        "published_at": "2026-03-01",
                        "doc_class": "half_year",
                        "title": "Half Year Report",
                    },
                ],
                "financials": [
                    {
                        "period_end": "2025-12-31",
                        "period_type": "H",
                        "revenue": 1000,
                        "ebit": 500,
                        "np_attributable": 300,
                        "operating_cf": 200,
                        "capex": -100,
                    }
                ],
                "risk_notes": [
                    {
                        "published_at": "2026-04-01",
                        "title": "Half Year Report",
                        "risk_summary": "Input cost pressure",
                        "guidance_summary": "Guidance maintained",
                    }
                ],
                "price_history_1y": [
                    {"timestamp": "2026-04-08T00:00:00Z", "close": 54.5},
                    {"timestamp": "2026-04-09T00:00:00Z", "close": 55.2},
                ],
                "extraction_failures": [],
                "low_confidence_financials": [],
                "company_memory": {"entries": []},
                "market_memory": {"items": []},
                "cockpit_local_memory": {"agent_memory": [], "dossier_findings": []},
            }
        )
        self.assertIn("BHP Filestats Dashboard", html)
        self.assertIn("Plotly.newPlot('fs-price'", html)
        self.assertIn("Plotly.newPlot('fs-doc-class'", html)
        self.assertIn("Plotly.newPlot('fs-docs-table'", html)


if __name__ == "__main__":
    unittest.main()
