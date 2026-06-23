#!/usr/bin/env python3
"""Tests for the repo dev/test import contract."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

import python_import_contract as contract


class TestPythonImportContract(unittest.TestCase):
    def test_import_roots_are_the_active_repo_dev_roots(self) -> None:
        repo_root = contract.REPO_ROOT

        self.assertEqual(
            (
                repo_root,
                repo_root / "financial-engine_v2",
                repo_root / "financial-engine_v2" / "backend",
                repo_root / "scripts",
            ),
            contract.import_roots(),
        )

    def test_relative_import_roots_match_pytest_ini_pythonpath(self) -> None:
        self.assertEqual(
            (".", "financial-engine_v2", "financial-engine_v2/backend", "scripts"),
            contract.relative_import_roots(),
        )

        check = contract.check_pytest_ini_pythonpath()

        self.assertTrue(check["ok"], check)
        self.assertEqual(contract.relative_import_roots(), check["expected"])
        self.assertEqual(contract.relative_import_roots(), check["actual"])

    def test_dev_pythonpath_entries_append_extras_and_existing_without_duplicates(self) -> None:
        repo_root = Path("/tmp/example-tenn")
        existing = os.pathsep.join(
            [
                "/already",
                str(repo_root / "financial-engine_v2" / "backend"),
                "",
            ]
        )

        entries = contract.dev_pythonpath_entries(
            repo_root=repo_root,
            extra_paths=[repo_root / ".venv" / "lib" / "python3.11" / "site-packages"],
            existing=existing,
        )

        self.assertEqual(str(repo_root), entries[0])
        self.assertEqual(str(repo_root / "financial-engine_v2"), entries[1])
        self.assertEqual(str(repo_root / "financial-engine_v2" / "backend"), entries[2])
        self.assertEqual(str(repo_root / "scripts"), entries[3])
        self.assertEqual(1, entries.count(str(repo_root / "financial-engine_v2" / "backend")))
        self.assertIn(str(repo_root / ".venv" / "lib" / "python3.11" / "site-packages"), entries)
        self.assertIn("/already", entries)

    def test_install_import_roots_prepends_contract_roots_in_order(self) -> None:
        repo_root = Path("/tmp/example-tenn")
        sys_path = [
            "/existing",
            str(repo_root / "scripts"),
            str(repo_root / "financial-engine_v2" / "backend"),
        ]

        updated = contract.install_import_roots(repo_root=repo_root, sys_path=sys_path)

        self.assertIs(updated, sys_path)
        self.assertEqual(
            [
                str(repo_root),
                str(repo_root / "financial-engine_v2"),
                str(repo_root / "financial-engine_v2" / "backend"),
                str(repo_root / "scripts"),
            ],
            updated[:4],
        )
        self.assertEqual(1, updated.count(str(repo_root / "scripts")))
        self.assertEqual("/existing", updated[4])


if __name__ == "__main__":
    unittest.main()
