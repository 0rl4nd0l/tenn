#!/usr/bin/env python3
"""Tests for the runtime entrypoint contract."""

from __future__ import annotations

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

    def test_full_contract_validates(self) -> None:
        result = contract.validate_contract()

        self.assertTrue(result["ok"], result["issues"])


if __name__ == "__main__":
    unittest.main()
