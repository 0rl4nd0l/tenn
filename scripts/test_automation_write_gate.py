from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import automation_write_gate as gate


SAFE_CANDIDATE = {
    "title": "Safe automation finding",
    "root_cause": "candidate lacks a strict write gate",
    "evidence_path": "reports/demo.md",
    "lane": "reporting",
    "risk": "low",
}


class AutomationWriteGateTests(unittest.TestCase):
    def test_new_safe_candidate_requires_exact_open_issue_approval(self) -> None:
        manifest = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "new", "errors": []},
            requested_action="open_issue",
        )

        self.assertEqual("eligible", manifest["status"])
        self.assertEqual("open_issue", manifest["action"]["type"])
        self.assertEqual("open issue", manifest["required_approval_phrase"])
        self.assertEqual("missing", manifest["approval"]["status"])
        self.assertFalse(manifest["may_execute"])

        approved = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "new", "errors": []},
            requested_action="open_issue",
            approval_phrase="open issue",
        )
        self.assertEqual("matched", approved["approval"]["status"])
        self.assertTrue(approved["may_execute"])

    def test_duplicate_issue_routes_to_existing_comment_not_new_issue(self) -> None:
        dedupe = {
            "status": "duplicate_issue",
            "errors": [],
            "best_match": {
                "kind": "issue",
                "number": 291,
                "title": "Existing automation gate",
                "url": "https://github.com/0rl4nd0l/tenn/issues/291",
            },
        }

        manifest = gate.build_manifest(SAFE_CANDIDATE, dedupe, requested_action="auto")

        self.assertEqual("eligible", manifest["status"])
        self.assertEqual("comment_existing_issue", manifest["action"]["type"])
        self.assertEqual("291", manifest["action"]["target"]["number"])
        self.assertEqual("comment on existing issue", manifest["required_approval_phrase"])
        self.assertIn("duplicate_issue", manifest["reasons"])

    def test_fuzzy_needs_review_dedupe_blocks_writes(self) -> None:
        manifest = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "needs_review", "errors": [], "best_match": {"kind": "pr", "number": 493}},
            requested_action="open_issue",
            approval_phrase="open issue",
        )

        self.assertEqual("owner_review_required", manifest["status"])
        self.assertEqual("review_only", manifest["action"]["type"])
        self.assertFalse(manifest["may_execute"])
        self.assertIn("dedupe_needs_review", manifest["blockers"])

    def test_data_missing_fails_closed(self) -> None:
        manifest = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "data_missing", "errors": ["gh unavailable"]},
            requested_action="open_issue",
            approval_phrase="open issue",
        )

        self.assertEqual("data_missing", manifest["status"])
        self.assertFalse(manifest["may_execute"])
        self.assertIn("dedupe_data_missing", manifest["blockers"])

    def test_unknown_dedupe_status_fails_closed(self) -> None:
        manifest = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "maybe", "errors": []},
            requested_action="open_issue",
            approval_phrase="open issue",
        )

        self.assertEqual("data_missing", manifest["status"])
        self.assertFalse(manifest["may_execute"])
        self.assertEqual("review_only", manifest["action"]["type"])
        self.assertIn("dedupe_data_missing", manifest["blockers"])

    def test_high_risk_requires_isolation_for_parking(self) -> None:
        candidate = dict(SAFE_CANDIDATE, risk="high", lane="runtime")
        missing = gate.build_manifest(candidate, {"status": "new", "errors": []}, requested_action="park_high_risk")
        self.assertEqual("blocked", missing["status"])
        self.assertIn("isolation_missing", missing["blockers"])

        isolated = dict(
            candidate,
            isolation={
                "branch": "high-risk/automation-runtime-gate-v1",
                "worktree": "/home/l4nd0/tenn-high-risk-automation-runtime-gate-v1",
                "base": "control-plane/automation-strict-write-gate-layer3-v0-20260709",
            },
        )
        manifest = gate.build_manifest(
            isolated,
            {"status": "new", "errors": []},
            requested_action="park_high_risk",
            approval_phrase="start high-risk experiment",
        )

        self.assertEqual("eligible", manifest["status"])
        self.assertEqual("park_high_risk", manifest["action"]["type"])
        self.assertTrue(manifest["may_execute"])
        self.assertEqual("high-risk/automation-runtime-gate-v1", manifest["action"]["target"]["branch"])

    def test_draft_pr_requires_branch_metadata_and_exact_approval(self) -> None:
        missing = gate.build_manifest(
            SAFE_CANDIDATE,
            {"status": "new", "errors": []},
            requested_action="create_draft_pr",
            approval_phrase="create draft PR",
        )
        self.assertEqual("blocked", missing["status"])
        self.assertIn("draft_pr_metadata_missing", missing["blockers"])

        candidate = dict(
            SAFE_CANDIDATE,
            draft_pr={
                "branch": "control-plane/demo",
                "base": "migration/clean-runtime-baseline-reconstruct-v1",
                "title": "Demo draft PR",
                "body": "Validated demo change.",
                "validation": "python3 -m unittest scripts.test_demo",
            },
        )
        manifest = gate.build_manifest(
            candidate,
            {"status": "new", "errors": []},
            requested_action="create_draft_pr",
            approval_phrase="create draft PR",
        )
        self.assertEqual("eligible", manifest["status"])
        self.assertTrue(manifest["may_execute"])
        self.assertEqual("control-plane/demo", manifest["action"]["target"]["branch"])

    def test_cli_accepts_inline_json_and_file_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dedupe_path = Path(temp_dir) / "dedupe.json"
            dedupe_path.write_text(json.dumps({"status": "new", "errors": []}), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/automation_write_gate.py",
                    "manifest",
                    "--candidate-json",
                    json.dumps(SAFE_CANDIDATE),
                    "--dedupe-path",
                    str(dedupe_path),
                    "--requested-action",
                    "open_issue",
                    "--approval-phrase",
                    "open issue",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, proc.returncode, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["may_execute"])
        self.assertTrue(payload["read_only"])


if __name__ == "__main__":
    unittest.main()
