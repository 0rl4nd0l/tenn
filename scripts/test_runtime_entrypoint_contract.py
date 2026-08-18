#!/usr/bin/env python3
"""Tests for the runtime entrypoint contract."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import runtime_entrypoint_contract as contract


class TestRuntimeEntrypointContract(unittest.TestCase):
    def test_runtime_modes_define_distinct_entrypoints(self) -> None:
        modes = contract.runtime_modes()

        self.assertEqual(
            "financial-engine_v2/scripts/run_local_backend.sh",
            modes["agent_local_backend"].entrypoint,
        )
        self.assertEqual("scripts/cockpit", modes["full_stack_cockpit"].entrypoint)
        self.assertEqual("run.py", modes["batch_orchestrator"].entrypoint)

        self.assertEqual("canonical_for_agent_runtime_tasks", modes["agent_local_backend"].status)
        self.assertEqual("canonical_for_operator_full_stack", modes["full_stack_cockpit"].status)
        self.assertEqual("supported_not_system_bootstrap", modes["batch_orchestrator"].status)

    def test_agent_contract_matches_runtime_contract(self) -> None:
        result = contract.check_agent_contract()

        self.assertTrue(result["ok"], result["issues"])

    def test_runtime_docs_name_the_distinct_modes(self) -> None:
        result = contract.check_docs()

        self.assertTrue(result["ok"], result["issues"])

    def test_runtime_docs_require_contract_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            entrypoints = root / "entrypoints.md"
            startup = root / "startup.md"
            entrypoints.write_text(
                "Agent-Local Backend Mode\nFull-Stack Cockpit Mode\nBatch Mode\n",
                encoding="utf-8",
            )
            startup.write_text(
                "Full-Stack Cockpit Mode\nAgent-Local Backend Mode\nonly in Docker for this mode\n",
                encoding="utf-8",
            )

            result = contract.check_docs(entrypoints_doc=entrypoints, startup_doc=startup)

        self.assertFalse(result["ok"])
        self.assertIn("docs_status_agent_local_backend", result["issues"])
        self.assertIn("docs_command_full_stack_cockpit", result["issues"])

    def test_startup_docs_reject_stale_cockpit_install_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            startup = Path(tmp_dir) / "startup.md"
            startup.write_text(
                contract.STARTUP_DOC.read_text(encoding="utf-8").replace(
                    contract.STARTUP_INSTALL_COMMAND,
                    "ln -sf /home/l4nd0/tenn/scripts/cockpit ~/.local/bin/cockpit",
                ),
                encoding="utf-8",
            )

            result = contract.check_docs(
                entrypoints_doc=contract.ENTRYPOINTS_DOC,
                startup_doc=startup,
            )

        self.assertFalse(result["ok"])
        self.assertIn("startup_install_command", result["issues"])
        self.assertIn("startup_no_stale_home_tenn_symlink", result["issues"])

    def test_full_contract_validates(self) -> None:
        result = contract.validate_contract()

        self.assertTrue(result["ok"], result["issues"])


if __name__ == "__main__":
    unittest.main()
