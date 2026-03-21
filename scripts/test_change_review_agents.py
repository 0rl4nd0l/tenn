from __future__ import annotations

import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.change_review_agents import (
    ChangeSummary,
    build_change_signature,
    build_consistency_findings,
    build_planner_payload,
    build_validation_findings,
    discover_test_targets,
    planner_output_is_stale,
    read_last_jsonl_record,
    render_overview,
    resolve_python_executable,
    watch,
    write_alert,
)


class ChangeReviewAgentsTest(unittest.TestCase):
    def test_consistency_flags_critical_without_tests(self) -> None:
        summary = ChangeSummary(
            branch="main",
            head_sha="a" * 40,
            timestamp_utc="2026-03-21T00:00:00Z",
            signature="abc123",
            event_id="main-abc123",
            status_lines=[" M financial-engine_v2/backend/app/services/pipeline.py"],
            tracked_files=["financial-engine_v2/backend/app/services/pipeline.py"],
            untracked_files=[],
            changed_files=["financial-engine_v2/backend/app/services/pipeline.py"],
            diff_stat="1 file changed, 2 insertions(+)",
            diff_check_output="",
            dirty=True,
        )

        findings = build_consistency_findings(summary)
        titles = [finding.title for finding in findings]
        self.assertIn("Critical runtime paths changed without test updates", titles)

    def test_discover_test_targets_finds_script_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "foo.py").write_text("print('x')\n", encoding="utf-8")
            (scripts_dir / "test_foo.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

            targets = discover_test_targets(["scripts/foo.py"], root)
            self.assertEqual(targets, ["scripts/test_foo.py"])

    def test_planner_uses_existing_role_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            event_dir = state_dir / "events" / "main-abc123"
            event_dir.mkdir(parents=True)
            (event_dir / "consistency.json").write_text(
                """{
  "findings": [
    {
      "details": "needs tests",
      "evidence": [],
      "files": ["financial-engine_v2/backend/app/services/pipeline.py"],
      "reviewer": "consistency",
      "severity": "medium",
      "title": "Critical runtime paths changed without test updates"
    }
  ]
}""",
                encoding="utf-8",
            )
            (event_dir / "validation.json").write_text(
                """{
  "findings": [
    {
      "details": "failed",
      "evidence": ["pytest"],
      "files": [],
      "reviewer": "validation",
      "severity": "high",
      "title": "pytest_targeted failed"
    }
  ],
  "results": [
    {
      "command": "python -m pytest -q scripts/test_x.py",
      "exit_code": 1,
      "label": "pytest_targeted",
      "output_excerpt": "assert 1 == 2",
      "status": "failed",
      "summary": "exited with code 1"
    }
  ]
}""",
                encoding="utf-8",
            )
            summary = ChangeSummary(
                branch="main",
                head_sha="a" * 40,
                timestamp_utc="2026-03-21T00:00:00Z",
                signature="abc123",
                event_id="main-abc123",
                status_lines=[" M financial-engine_v2/backend/app/services/pipeline.py"],
                tracked_files=["financial-engine_v2/backend/app/services/pipeline.py"],
                untracked_files=[],
                changed_files=["financial-engine_v2/backend/app/services/pipeline.py"],
                diff_stat="1 file changed, 2 insertions(+)",
                diff_check_output="",
                dirty=True,
            )

            payload = build_planner_payload(summary, event_dir)
            self.assertEqual(payload["highest_severity"], "high")
            joined_steps = " ".join(payload["priority_steps"]).lower()
            self.assertIn("reproduce and repair", joined_steps)
            self.assertIn("tests", joined_steps)

    def test_validation_findings_include_failures_and_skips(self) -> None:
        findings = build_validation_findings(
            [
                type(
                    "Result",
                    (),
                    {
                        "label": "pytest_targeted",
                        "command": "pytest -q",
                        "exit_code": 1,
                        "status": "failed",
                        "summary": "exited with code 1",
                        "output_excerpt": "failure",
                    },
                )(),
                type(
                    "Result",
                    (),
                    {
                        "label": "ruff",
                        "command": "ruff check",
                        "exit_code": None,
                        "status": "skipped",
                        "summary": "ruff missing",
                        "output_excerpt": "",
                    },
                )(),
            ]
        )
        self.assertEqual(findings[0].severity, "high")
        self.assertEqual(findings[0].title, "pytest_targeted failed")

    def test_resolve_python_executable_accepts_virtualenv_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            venv_python = root / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            venv_python.chmod(0o755)

            resolved = resolve_python_executable(root)
            self.assertEqual(resolved, str(venv_python))

    def test_planner_output_is_stale_when_dependency_is_newer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            event_dir = state_dir / "events" / "main-abc123"
            event_dir.mkdir(parents=True)
            planner_path = event_dir / "planner.json"
            planner_path.write_text("{}", encoding="utf-8")
            consistency_path = event_dir / "consistency.json"
            consistency_path.write_text("{}", encoding="utf-8")
            summary = ChangeSummary(
                branch="main",
                head_sha="a" * 40,
                timestamp_utc="2026-03-21T00:00:00Z",
                signature="abc123",
                event_id="main-abc123",
                status_lines=[" M financial-engine_v2/backend/app/services/pipeline.py"],
                tracked_files=["financial-engine_v2/backend/app/services/pipeline.py"],
                untracked_files=[],
                changed_files=["financial-engine_v2/backend/app/services/pipeline.py"],
                diff_stat="1 file changed, 2 insertions(+)",
                diff_check_output="",
                dirty=True,
            )

            stale_before = planner_output_is_stale(summary, state_dir)
            self.assertFalse(stale_before)
            time.sleep(0.02)
            consistency_path.write_text("{\"updated\": true}", encoding="utf-8")
            self.assertTrue(planner_output_is_stale(summary, state_dir))

    def test_write_alert_skips_duplicate_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            summary = ChangeSummary(
                branch="main",
                head_sha="a" * 40,
                timestamp_utc="2026-03-21T00:00:00Z",
                signature="abc123",
                event_id="main-abc123",
                status_lines=[" M scripts/change_review_agents.py"],
                tracked_files=["scripts/change_review_agents.py"],
                untracked_files=[],
                changed_files=["scripts/change_review_agents.py"],
                diff_stat="1 file changed, 2 insertions(+)",
                diff_check_output="",
                dirty=True,
            )
            payload = {
                "highest_severity": "low",
                "priority_steps": ["No blocking issues were detected; continue development and let the monitor watch for the next change."],
            }

            write_alert(summary, state_dir, payload)
            write_alert(summary, state_dir, payload)

            alerts_path = state_dir / "alerts.jsonl"
            lines = alerts_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            parsed = read_last_jsonl_record(alerts_path)
            self.assertEqual(parsed["event_id"], "main-abc123")


    def test_render_overview_links_latest_external_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            event_dir = state_dir / "events" / "main-abc123"
            latest_dir = state_dir / "latest"
            event_dir.mkdir(parents=True)
            latest_dir.mkdir(parents=True)
            (latest_dir / "external_agent_findings.md").write_text("# seeded\n", encoding="utf-8")
            summary = ChangeSummary(
                branch="main",
                head_sha="a" * 40,
                timestamp_utc="2026-03-21T00:00:00Z",
                signature="abc123",
                event_id="main-abc123",
                status_lines=[" M scripts/change_review_agents.py"],
                tracked_files=["scripts/change_review_agents.py"],
                untracked_files=[],
                changed_files=["scripts/change_review_agents.py"],
                diff_stat="1 file changed, 2 insertions(+)",
                diff_check_output="",
                dirty=True,
            )

            rendered = render_overview(summary, event_dir, state_dir)
            self.assertIn("reports/change_review_agents/latest/external_agent_findings.md", rendered)

    def test_watch_once_returns_error_on_snapshot_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            with patch("scripts.change_review_agents.snapshot_changes", side_effect=RuntimeError("boom")):
                result = watch("consistency", state_dir, state_dir, poll_seconds=1.0, once=True)
            self.assertEqual(result, 1)


    def test_build_change_signature_changes_when_untracked_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            notes = root / "notes.txt"
            notes.write_text("first\n", encoding="utf-8")
            first = build_change_signature(
                root,
                head_sha="a" * 40,
                dirty=True,
                status_lines=["?? notes.txt"],
                tracked_patch="",
                untracked_files=["notes.txt"],
            )
            notes.write_text("second\n", encoding="utf-8")
            second = build_change_signature(
                root,
                head_sha="a" * 40,
                dirty=True,
                status_lines=["?? notes.txt"],
                tracked_patch="",
                untracked_files=["notes.txt"],
            )
            self.assertNotEqual(first, second)

    def test_build_change_signature_changes_when_tracked_patch_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            first = build_change_signature(
                root,
                head_sha="a" * 40,
                dirty=True,
                status_lines=[" M scripts/change_review_agents.py"],
                tracked_patch="diff --git a/x b/x\n+one\n",
                untracked_files=[],
            )
            second = build_change_signature(
                root,
                head_sha="a" * 40,
                dirty=True,
                status_lines=[" M scripts/change_review_agents.py"],
                tracked_patch="diff --git a/x b/x\n+two\n",
                untracked_files=[],
            )
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
