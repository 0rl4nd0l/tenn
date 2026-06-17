from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "opencode_worker_bridge.py"
spec = importlib.util.spec_from_file_location("opencode_worker_bridge", SCRIPT_PATH)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)


VALID_RESULT = """\
worker_id: scout-1
task_tier: small
model: deepseek/deepseek-chat
decision_limit: evidence_only
summary: Checked the bridge script and tests.
findings:
- The script exists and is scoped to control-plane tooling.
evidence_paths:
- scripts/opencode_worker_bridge.py
confidence: medium
risks:
- Codex still needs to review the result.
recommended_next_action: Codex review
"""


class OpenCodeWorkerBridgeTests(unittest.TestCase):
    def test_probe_output_shape_when_opencode_missing(self) -> None:
        with mock.patch.object(bridge.shutil, "which", return_value=None):
            result = bridge.probe_opencode(command="definitely-missing-opencode")
        self.assertFalse(result["available"])
        self.assertEqual(result["command"], "definitely-missing-opencode")
        self.assertIn("version", result["checks"])
        self.assertFalse(result["deepseek_available"])

    def test_worker_directory_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_file = root / "task.md"
            task_file.write_text("Inspect scripts/opencode_worker_bridge.py only.\n", encoding="utf-8")
            opencode = root / "opencode"
            opencode.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('''" + VALID_RESULT.replace("'", "\\'") + "''')\n",
                encoding="utf-8",
            )
            opencode.chmod(0o755)

            with mock.patch("builtins.print"):
                rc = bridge.main(
                    [
                        "run",
                        "--job-dir",
                        str(root / "job"),
                        "--worker-id",
                        "scout-1",
                        "--agent",
                        "evidence-scout",
                        "--model",
                        "deepseek/deepseek-chat",
                        "--task-file",
                        str(task_file),
                        "--workdir",
                        str(root),
                        "--decision-limit",
                        "evidence_only",
                        "--timeout-seconds",
                        "5",
                        "--opencode-command",
                        str(opencode),
                    ]
                )

            worker_dir = root / "job" / "scout-1"
            self.assertEqual(rc, 0)
            self.assertTrue((worker_dir / "WORKER_TASK.md").is_file())
            self.assertTrue((worker_dir / "WORKER_RESULT.md").is_file())
            self.assertTrue((worker_dir / "WORKER_META.json").is_file())
            self.assertTrue((worker_dir / "raw_output.txt").is_file())
            meta = json.loads((worker_dir / "WORKER_META.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"], "completed")

    def test_result_validation_success(self) -> None:
        result = bridge.validate_result_text(VALID_RESULT)
        self.assertTrue(result["ok"])
        self.assertEqual(result["fields"]["worker_id"], "scout-1")

    def test_result_validation_rejects_missing_evidence_paths(self) -> None:
        invalid = VALID_RESULT.replace("- scripts/opencode_worker_bridge.py", "- DATA_MISSING")
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("evidence_paths", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_final_authority_under_evidence_only(self) -> None:
        invalid = VALID_RESULT.replace("Codex review", "final decision: ready to merge")
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_ledger_entry_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worker_dir = Path(tmp) / "job" / "scout-1"
            worker_dir.mkdir(parents=True)
            (worker_dir / "WORKER_META.json").write_text(
                json.dumps(
                    {
                        "worker_id": "scout-1",
                        "agent": "evidence-scout",
                        "model": "deepseek/deepseek-chat",
                        "task_tier": "small",
                        "decision_limit": "evidence_only",
                        "workdir": "/tmp/work",
                        "result_path": str(worker_dir / "WORKER_RESULT.md"),
                        "status": "completed",
                    }
                ),
                encoding="utf-8",
            )
            parser = bridge.build_parser()
            args = parser.parse_args(["ledger-entry", "--job-dir", str(Path(tmp) / "job"), "--worker-id", "scout-1"])
            with mock.patch("builtins.print") as printed:
                rc = bridge.command_ledger_entry(args)
            self.assertEqual(rc, 0)
            payload = json.loads(printed.call_args.args[0])
            self.assertEqual(payload["runtime"], "opencode")
            self.assertEqual(payload["worker_id"], "scout-1")
            self.assertIn("session_id", payload)
            self.assertIn("agent_task_ledger_available", payload)

    def test_denylist_rejects_secret_looking_paths(self) -> None:
        self.assertTrue(bridge.is_denied_path(".env"))
        self.assertTrue(bridge.is_denied_path("config/credentials.json"))
        self.assertTrue(bridge.is_denied_path("data/raw/company.sqlite"))
        denied = bridge.find_denied_references("Please inspect config/.env and data/raw/company.sqlite")
        self.assertIn("config/.env", denied)

    def test_command_construction_does_not_include_dangerous_permission_flags(self) -> None:
        command = bridge.build_opencode_command(
            "/usr/bin/opencode",
            agent="evidence-scout",
            model="deepseek/deepseek-chat",
            workdir=Path("/tmp/work"),
            prompt="hello",
        )
        self.assertEqual(command[:2], ["/usr/bin/opencode", "run"])
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertNotIn("--permission-mode", command)
        self.assertIn("--agent", command)
        self.assertIn("--model", command)


if __name__ == "__main__":
    unittest.main()
