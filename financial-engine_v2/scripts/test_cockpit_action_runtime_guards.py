#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.action_runtime_guards import (  # noqa: E402
    conflicting_action_ids,
    evaluate_quality_gate,
    extract_report_paths,
    find_conflicting_job,
)


class ActionRuntimeGuardTests(unittest.TestCase):
    def test_conflicting_action_ids_includes_heavy_overlap(self) -> None:
        overlaps = conflicting_action_ids("asx_enrichment_sweep")
        self.assertIn("full_history", overlaps)
        self.assertIn("resume_pending", overlaps)
        self.assertIn("asx_enrichment_sweep", overlaps)
        self.assertIn("daily_announcement_ingest", overlaps)
        self.assertIn("single_ticker_announcement_backfill", overlaps)
        self.assertIn("daily_marketindex", overlaps)

    def test_daily_marketindex_conflicts_with_full_history(self) -> None:
        self.assertIn("full_history", conflicting_action_ids("daily_marketindex"))

    def test_find_conflicting_job_ignores_stale_rows(self) -> None:
        now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)
        jobs = [
            {
                "job_id": "old-running",
                "action_id": "full_history",
                "status": "running",
                "started_at": (now - timedelta(hours=48)).isoformat(),
                "ended_at": None,
            },
            {
                "job_id": "fresh-running",
                "action_id": "full_history",
                "status": "running",
                "started_at": (now - timedelta(minutes=10)).isoformat(),
                "ended_at": None,
            },
        ]
        conflict = find_conflicting_job("asx_enrichment_sweep", jobs, now_utc=now, stale_after_hours=24)
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["job_id"], "fresh-running")

    def test_extract_report_paths_reads_report_flags(self) -> None:
        command = [
            "python",
            "scripts/daily_marketindex_action.py",
            "--daily-report",
            "reports/marketindex/daily.json",
            "--download-report",
            "reports/marketindex/download.json",
        ]
        paths = extract_report_paths("daily_marketindex", command, REPO_ROOT)
        self.assertEqual(len(paths), 2)
        self.assertTrue(str(paths[0]).endswith("reports/marketindex/daily.json"))
        self.assertTrue(str(paths[1]).endswith("reports/marketindex/download.json"))

    def test_quality_gate_update_ticker_financials_fails_zero_rows(self) -> None:
        report = {
            "status": "success",
            "after": {"rows": 0},
        }
        ok, reasons = evaluate_quality_gate("update_ticker_financials", {"r.json": report})
        self.assertFalse(ok)
        self.assertTrue(any("after.rows" in reason for reason in reasons))

    def test_quality_gate_daily_marketindex_passes_with_download_gate(self) -> None:
        daily_report = {
            "status": "success",
            "settings": {"skip_download": False},
        }
        download_report = {
            "downloaded": 12,
            "quality_gate": {"passed": True, "min_download_count": 5},
        }
        ok, reasons = evaluate_quality_gate(
            "daily_marketindex",
            {"daily.json": daily_report, "download.json": download_report},
        )
        self.assertTrue(ok, msg=reasons)

    def test_quality_gate_asx_sweep_requires_completed_days(self) -> None:
        report = {
            "status": "success",
            "totals": {"days_completed": 0, "errors": 0},
        }
        ok, reasons = evaluate_quality_gate("asx_enrichment_sweep", {"r.json": report})
        self.assertFalse(ok)
        self.assertTrue(any("days_completed" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()

