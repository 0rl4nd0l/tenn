#!/usr/bin/env python3
"""Focused tests for the Codex automation runner contract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codex_automation_runner as runner


class CodexAutomationRunnerTest(unittest.TestCase):
    def test_expected_jobs_are_registered(self) -> None:
        expected_jobs = {
            "automation-health",
            "bug-regression",
            "daily-closeout",
            "doc-drift",
            "extraction-regression",
            "future-opportunities",
            "memory-drift",
            "repo-hygiene",
        }

        self.assertEqual(expected_jobs, set(runner.JOBS))

    def test_daily_closeout_prompt_is_audit_only(self) -> None:
        prompt = runner.JOBS["daily-closeout"].prompt_builder()

        required_fragments = (
            "Daily Closeout / Lock-Up Audit",
            "Closeout status:",
            "Open P0/P1 blockers:",
            "Dirty or collision risks:",
            "Automation health:",
            "PR / issue queue:",
            "Next recommended prompt:",
            "Do not:",
            "edit files",
            "create, update, comment on, close, or reopen GitHub issues or PRs",
            "install, enable, start, stop, restart, reload, or edit live systemd units",
            "write DBs, Qdrant, Redis, news stores",
            "run broad extraction, backfill, ingestion, migration, or dependency-install commands",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, prompt)

    def test_health_expectations_cover_registered_jobs(self) -> None:
        expected = {expectation.name for expectation in runner.HEALTH_EXPECTATIONS}

        self.assertEqual(set(runner.JOBS), expected)

    def test_list_jobs_returns_success(self) -> None:
        self.assertEqual(0, runner.list_jobs())

    def test_failed_child_process_writes_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            timestamp = "20260629T120000+1000"
            command = [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('transport down\\n'); sys.exit(7)",
            ]

            with (
                mock.patch.object(runner, "OUTPUT_ROOT", output_root),
                mock.patch.object(runner, "_timestamp", return_value=timestamp),
                mock.patch.object(runner, "_command", return_value=command),
            ):
                self.assertEqual(7, runner.run_job("memory-drift"))

            report_path = output_root / "reports" / f"{timestamp}-memory-drift.md"
            log_path = output_root / "logs" / f"{timestamp}-memory-drift.jsonl"

            self.assertTrue(report_path.exists())
            self.assertTrue(log_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Status: BROKEN", report)
            self.assertIn("transport down", report)
            self.assertIn("result: WORKING / PARTIAL / BROKEN / DATA_MISSING | BROKEN", report)

    def test_health_rows_classify_broken_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            report_dir = output_root / "reports"
            log_dir = output_root / "logs"
            report_dir.mkdir()
            log_dir.mkdir()
            (report_dir / "20260629T120000+1000-memory-drift.md").write_text(
                "# Failure\n\nStatus: BROKEN\n",
                encoding="utf-8",
            )
            (log_dir / "20260629T120000+1000-memory-drift.jsonl").write_text(
                "transport down\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "OUTPUT_ROOT", output_root):
                _rows, issues, records = runner._health_rows(datetime.now().astimezone())

            memory_record = next(record for record in records if record["name"] == "memory-drift")
            self.assertEqual("BROKEN_REPORT", memory_record["status"])
            self.assertIn("memory-drift: BROKEN_REPORT", issues)


if __name__ == "__main__":
    unittest.main()
