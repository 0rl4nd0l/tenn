from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import automation_write_executor_plan as planner


def manifest_for(action_type: str, target: dict[str, object], *, may_execute: bool = True) -> dict[str, object]:
    return {
        "read_only": True,
        "status": "eligible",
        "may_execute": may_execute,
        "action": {"type": action_type, "target": target},
        "candidate": {
            "title": "Safe automation finding",
            "evidence_path": "reports/demo.md",
            "root_cause": "candidate lacks a strict executor gate",
        },
        "blockers": [],
    }


class AutomationWriteExecutorPlanTests(unittest.TestCase):
    def test_open_issue_plan_is_dry_run_only(self) -> None:
        manifest = manifest_for(
            "open_issue",
            {
                "title": "Safe automation finding",
                "body_source": "reports/demo.md",
                "root_cause": "candidate lacks a strict executor gate",
                "lane": "reporting",
                "risk": "low",
            },
        )

        plan = planner.build_executor_plan(manifest)

        self.assertEqual("planned", plan["status"])
        self.assertTrue(plan["read_only"])
        self.assertFalse(plan["execute"])
        self.assertTrue(plan["requires_final_owner_confirmation"])
        self.assertFalse(plan["safe_to_execute_in_this_helper"])
        command = plan["commands"][0]
        self.assertFalse(command["execute"])
        self.assertEqual(["gh", "issue", "create"], command["argv"][:3])
        self.assertIn("--body-file", command["argv"])

    def test_may_execute_false_blocks_write_actions(self) -> None:
        manifest = manifest_for(
            "open_issue",
            {
                "title": "Safe automation finding",
                "body_source": "reports/demo.md",
                "root_cause": "candidate lacks a strict executor gate",
                "lane": "reporting",
                "risk": "low",
            },
            may_execute=False,
        )

        plan = planner.build_executor_plan(manifest)

        self.assertEqual("blocked", plan["status"])
        self.assertEqual([], plan["commands"])
        self.assertIn("manifest_may_execute_false", plan["blockers"])

    def test_not_read_only_manifest_blocks(self) -> None:
        manifest = manifest_for("review_only", {})
        manifest["read_only"] = False

        plan = planner.build_executor_plan(manifest)

        self.assertEqual("blocked", plan["status"])
        self.assertEqual([], plan["commands"])
        self.assertIn("manifest_not_read_only", plan["blockers"])

    def test_comment_existing_issue_and_pr_use_candidate_body_source(self) -> None:
        issue_plan = planner.build_executor_plan(manifest_for("comment_existing_issue", {"number": "291"}))
        pr_plan = planner.build_executor_plan(manifest_for("comment_existing_pr", {"number": 494}))

        self.assertEqual("planned", issue_plan["status"])
        self.assertEqual(["gh", "issue", "comment"], issue_plan["commands"][0]["argv"][:3])
        self.assertIn("<body-file-from:reports/demo.md>", issue_plan["commands"][0]["argv"])
        self.assertEqual("planned", pr_plan["status"])
        self.assertEqual(["gh", "pr", "comment"], pr_plan["commands"][0]["argv"][:3])

    def test_draft_pr_plan_requires_metadata_and_uses_draft_flag(self) -> None:
        missing = planner.build_executor_plan(manifest_for("create_draft_pr", {"branch": "control-plane/demo"}))
        self.assertEqual("blocked", missing["status"])
        self.assertIn("target_base_missing", missing["blockers"])

        plan = planner.build_executor_plan(
            manifest_for(
                "create_draft_pr",
                {
                    "branch": "control-plane/demo",
                    "base": "migration/clean-runtime-baseline-reconstruct-v1",
                    "title": "Demo draft PR",
                    "body": "Validated demo change.",
                    "validation": "python3 -m unittest scripts.test_demo",
                },
            )
        )

        self.assertEqual("planned", plan["status"])
        argv = plan["commands"][0]["argv"]
        self.assertEqual(["gh", "pr", "create"], argv[:3])
        self.assertIn("--draft", argv)
        self.assertIn("--head", argv)

    def test_high_risk_parking_plan_never_creates_worktree(self) -> None:
        plan = planner.build_executor_plan(
            manifest_for(
                "park_high_risk",
                {
                    "branch": "high-risk/automation-runtime-gate-v1",
                    "worktree": "/home/l4nd0/tenn-high-risk-automation-runtime-gate-v1",
                    "base": "control-plane/automation-strict-write-gate-layer3-v0-20260709",
                },
            )
        )

        self.assertEqual("planned", plan["status"])
        command = plan["commands"][0]
        self.assertEqual(["git", "worktree", "add"], command["argv"][:3])
        self.assertFalse(command["execute"])

    def test_unknown_action_blocks(self) -> None:
        plan = planner.build_executor_plan(manifest_for("merge_the_repo", {}))

        self.assertEqual("blocked", plan["status"])
        self.assertEqual([], plan["commands"])
        self.assertIn("unsupported_action", plan["blockers"])

    def test_review_only_has_no_write_command(self) -> None:
        manifest = {
            "read_only": True,
            "status": "owner_review_required",
            "may_execute": False,
            "action": {"type": "review_only", "target": {}},
            "blockers": ["dedupe_needs_review"],
        }

        plan = planner.build_executor_plan(manifest)

        self.assertEqual("owner_review_required", plan["status"])
        self.assertEqual([], plan["commands"])
        self.assertIn("dedupe_needs_review", plan["blockers"])

    def test_cli_reads_manifest_path(self) -> None:
        manifest = manifest_for(
            "open_issue",
            {
                "title": "Safe automation finding",
                "body_source": "reports/demo.md",
                "root_cause": "candidate lacks a strict executor gate",
                "lane": "reporting",
                "risk": "low",
            },
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/automation_write_executor_plan.py",
                    "plan",
                    "--manifest-path",
                    str(manifest_path),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, proc.returncode, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual("planned", payload["status"])
        self.assertFalse(payload["commands"][0]["execute"])


if __name__ == "__main__":
    unittest.main()
