"""Tests for _build_action_env PYTHONPATH assembly.

Validates that action subprocesses can import modules from parent scripts/,
repo scripts/, and the COCKPIT_SHARED_SCRIPTS_ROOT env var — the fix for the
health_guard ModuleNotFoundError that blocked backfill actions in Docker.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import _build_action_env


class TestBuildActionEnvPythonPath:
    def test_includes_backend_dir(self, tmp_path: Path) -> None:
        env = _build_action_env(tmp_path)
        assert str((tmp_path / "backend").resolve()) in env["PYTHONPATH"].split(":")

    def test_includes_cockpit_dir(self, tmp_path: Path) -> None:
        env = _build_action_env(tmp_path)
        assert str((tmp_path / "cockpit").resolve()) in env["PYTHONPATH"].split(":")

    def test_includes_parent_scripts_dir(self, tmp_path: Path) -> None:
        env = _build_action_env(tmp_path)
        assert str((tmp_path.parent / "scripts").resolve()) in env["PYTHONPATH"].split(
            ":"
        )

    def test_includes_repo_scripts_dir(self, tmp_path: Path) -> None:
        env = _build_action_env(tmp_path)
        assert str((tmp_path / "scripts").resolve()) in env["PYTHONPATH"].split(":")

    def test_includes_workspace_scripts_hardcoded(self, tmp_path: Path) -> None:
        env = _build_action_env(tmp_path)
        assert "/workspace/scripts" in env["PYTHONPATH"].split(":")

    def test_includes_cockpit_shared_scripts_root(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("COCKPIT_SHARED_SCRIPTS_ROOT", "/custom/scripts")
        env = _build_action_env(tmp_path)
        assert "/custom/scripts" in env["PYTHONPATH"].split(":")

    def test_empty_shared_scripts_root_excluded(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("COCKPIT_SHARED_SCRIPTS_ROOT", "")
        env = _build_action_env(tmp_path)
        paths = env["PYTHONPATH"].split(":")
        assert "" not in paths

    def test_preserves_existing_pythonpath(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("PYTHONPATH", "/existing/path")
        env = _build_action_env(tmp_path)
        assert "/existing/path" in env["PYTHONPATH"].split(":")

    def test_no_shared_scripts_root_env_var(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.delenv("COCKPIT_SHARED_SCRIPTS_ROOT", raising=False)
        env = _build_action_env(tmp_path)
        # Should not crash; empty string excluded from paths
        paths = env["PYTHONPATH"].split(":")
        assert "" not in paths
