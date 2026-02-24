#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.actions import ActionRegistry  # noqa: E402


class ActionRegistryDoctorTests(unittest.TestCase):
    def test_extract_control_args_dry_run_aliases(self) -> None:
        clean, control = ActionRegistry.extract_control_args(
            {"ticker": "BHP", "dry_run": "true", "preview-only": "false"},
        )
        self.assertEqual(clean, {"ticker": "BHP"})
        self.assertTrue(control["dry_run"])

    def test_doctor_quick_single_action_does_not_crash(self) -> None:
        reg = ActionRegistry(repo_root=REPO_ROOT, confirm_required=True)
        report = reg.doctor(check_help=False, action_id="update_ticker_financials")

        self.assertIn("preflight", report)
        self.assertIn("checks", report)
        self.assertEqual(report["counts"]["total"], 1)
        self.assertEqual(report["counts"]["failed"], 0)
        self.assertTrue(report["checks"][0]["python_exists"])
        self.assertTrue(report["checks"][0]["script_exists"])

    def test_mutating_actions_advertise_dry_run_flag(self) -> None:
        reg = ActionRegistry(repo_root=REPO_ROOT, confirm_required=True)
        for spec in reg.list_actions():
            if not spec.is_mutating:
                continue
            self.assertGreaterEqual(len(spec.command_template), 2)
            script_rel = str(spec.command_template[1])
            script_path = (REPO_ROOT / script_rel).resolve()
            self.assertTrue(script_path.exists(), msg=f"Missing script for action {spec.id}: {script_path}")
            text = script_path.read_text(encoding="utf-8")
            self.assertIn("--dry-run", text, msg=f"Action {spec.id} script missing --dry-run: {script_rel}")


if __name__ == "__main__":
    unittest.main()

