#!/usr/bin/env python3
"""Tests for the pytest fallback runner."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

import python_import_contract as import_contract
import run_pytest_with_fallback as runner


class TestRunPytestWithFallback(unittest.TestCase):
    def test_normalize_pytest_args_adds_repo_config(self) -> None:
        self.assertEqual(
            ["-c", "pytest.ini", "scripts/test_example.py", "-q"],
            runner.normalize_pytest_args(["--", "scripts/test_example.py", "-q"]),
        )

    def test_normalize_pytest_args_preserves_explicit_config(self) -> None:
        self.assertEqual(
            ["-c", "financial-engine_v2/backend/pytest.ini", "financial-engine_v2/backend/tests"],
            runner.normalize_pytest_args(
                ["-c", "financial-engine_v2/backend/pytest.ini", "financial-engine_v2/backend/tests"]
            ),
        )

    def test_candidate_base_pythons_prefers_explicit_then_env(self) -> None:
        candidates = runner.candidate_base_pythons(
            "/tmp/explicit-python",
            {"TENN_PYTEST_BASE_PYTHON": "/tmp/env-python"},
        )

        self.assertEqual(Path("/tmp/explicit-python"), candidates[0])
        self.assertEqual(Path("/tmp/env-python"), candidates[1])

    def test_choose_base_python_rejects_missing_explicit_path(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit base Python is not executable"):
            runner.choose_base_python("/tmp/does-not-exist-python")

    def test_choose_base_python_preserves_venv_symlink_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "python"
            link.symlink_to(Path(os.environ.get("PYTHON", sys.executable)))

            chosen = runner.choose_base_python(str(link))

        self.assertEqual(str(link), str(chosen))

    def test_default_pythonpath_comes_from_import_contract(self) -> None:
        self.assertEqual(import_contract.import_roots(), runner.DEFAULT_PYTHONPATH)

    def test_merged_pythonpath_prepends_without_duplicates(self) -> None:
        path = runner.merged_pythonpath(
            ["/repo", "/repo/backend", "/repo"],
            os.pathsep.join(["/already", "/repo/backend"]),
        )

        self.assertEqual(
            os.pathsep.join(["/repo", "/repo/backend", "/already"]),
            path,
        )

    def test_build_direct_plan_uses_base_python(self) -> None:
        plan = runner.build_plan(
            base_python=Path("/venv/bin/python"),
            pytest_args=["--", "scripts/test_x.py", "-q"],
            pytest_available=True,
            target_site_packages=["/venv/lib/python3.11/site-packages"],
            existing_pythonpath="",
        )

        self.assertEqual("direct", plan.mode)
        self.assertEqual("/venv/bin/python", plan.runner_python)
        self.assertEqual(
            ["/venv/bin/python", "-m", "pytest", "-c", "pytest.ini", "scripts/test_x.py", "-q"],
            plan.pytest_command,
        )
        self.assertEqual([], plan.install_command)
        self.assertIn("/venv/lib/python3.11/site-packages", plan.pythonpath)

    def test_build_overlay_plan_uses_tmp_runner_and_validation_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            overlay = Path(tmp)
            plan = runner.build_plan(
                base_python=Path("/runtime/bin/python"),
                pytest_args=["scripts/test_x.py"],
                pytest_available=False,
                target_site_packages=["/runtime/lib/python3.11/site-packages"],
                overlay_dir=overlay,
                overlay_packages=("pytest==8.3.5",),
                existing_pythonpath="",
            )

        self.assertEqual("ephemeral_overlay", plan.mode)
        self.assertEqual(str(overlay / "bin" / "python"), plan.runner_python)
        self.assertEqual(
            [str(overlay / "bin" / "python"), "-m", "pip", "install", "--disable-pip-version-check", "pytest==8.3.5"],
            plan.install_command,
        )
        self.assertEqual(
            [str(overlay / "bin" / "python"), "-m", "pytest", "-c", "pytest.ini", "scripts/test_x.py"],
            plan.pytest_command,
        )
        self.assertIn("/runtime/lib/python3.11/site-packages", plan.pythonpath)


if __name__ == "__main__":
    unittest.main()
