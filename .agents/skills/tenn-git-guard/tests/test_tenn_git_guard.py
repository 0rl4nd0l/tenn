from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/tenn_git_guard.py"
SPEC = importlib.util.spec_from_file_location("tenn_git_guard", SCRIPT_PATH)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(guard)


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_repo(base: Path) -> Path:
    repo = base / "runtime-repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    run(["git", "config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repo)
    run(["git", "commit", "-m", "initial"], cwd=repo)
    return repo


def make_fake_control_plane(base: Path, *, ledger_search_payload: dict[str, object] | None = None) -> Path:
    root = base / "control-plane"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    search_payload = ledger_search_payload or {"ok": True, "matches": []}
    (scripts / "agent_job_contract.py").write_text("# fake contract\n", encoding="utf-8")
    (scripts / "agent_job_registry.py").write_text(
        "\n".join(
            [
                "import json, os",
                "print(json.dumps({",
                "  'ok': True,",
                "  'read_only': True,",
                "  'lock_acquired': False,",
                "  'active_jobs': [],",
                "  'registry_root': os.environ.get('TENN_AGENT_REGISTRY_ROOT'),",
                "}))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (scripts / "agent_task_ledger.py").write_text(
        "\n".join(
            [
                "import json, os, sys",
                f"SEARCH_PAYLOAD = {json.dumps(search_payload, sort_keys=True)!r}",
                "cmd = sys.argv[1] if len(sys.argv) > 1 else ''",
                "if cmd == 'resolve-path':",
                "    print(os.path.join("
                "os.environ.get('TENN_AGENT_REGISTRY_ROOT', ''), "
                "'task-ledger.jsonl'))",
                "elif cmd == 'validate':",
                "    print(json.dumps({'ok': True, 'data_missing': [], 'entry_count': 0}))",
                "elif cmd == 'search':",
                "    print(json.dumps(json.loads(SEARCH_PAYLOAD)))",
                "else:",
                "    raise SystemExit(2)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return root


class TennGitGuardTest(unittest.TestCase):
    def test_global_control_plane_supports_runtime_repo_without_local_guard_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            registry_root = base / "registry"

            payload = guard.preflight(
                repo_root=repo,
                topic="score-live output guard",
                env={
                    **os.environ,
                    "TENN_CONTROL_PLANE_ROOT": str(control_plane),
                    "TENN_AGENT_REGISTRY_ROOT": str(registry_root),
                },
            )

            self.assertEqual(payload["guard_support_status"], "PASS")
            self.assertEqual(payload["control_plane_root"], str(control_plane.resolve()))
            self.assertEqual(payload["registry_root"], str(registry_root.resolve()))
            self.assertEqual(payload["registry_status"], "PASS")
            self.assertEqual(payload["ledger_status"], "PASS")
            self.assertFalse((repo / "scripts/agent_task_ledger.py").exists())

    def test_missing_control_plane_is_explicit_data_missing_not_repo_script_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            isolated_home = base / "home"
            isolated_home.mkdir()

            with mock.patch.object(
                guard.Path,
                "home",
                return_value=isolated_home,
            ), mock.patch.object(guard, "git_config_global", return_value=None):
                payload = guard.preflight(repo_root=repo, env={})

            self.assertEqual(payload["guard_support_status"], "DATA_MISSING")
            self.assertIn("control_plane_root", payload["data_missing_sources"])
            self.assertEqual(payload["final_decision"], "warning")

    def test_registry_root_env_overrides_git_common_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            registry_root = base / "configured-registry"

            payload = guard.preflight(
                repo_root=repo,
                env={
                    **os.environ,
                    "TENN_CONTROL_PLANE_ROOT": str(control_plane),
                    "TENN_AGENT_REGISTRY_ROOT": str(registry_root),
                },
            )

            self.assertEqual(payload["registry_root"], str(registry_root.resolve()))
            self.assertEqual(payload["registry_source"], "env:TENN_AGENT_REGISTRY_ROOT")

    def test_linked_worktree_uses_common_git_dir_registry_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            worktree = base / "runtime-linked"
            run(["git", "worktree", "add", "-b", "linked-test", str(worktree)], cwd=repo)
            control_plane = make_fake_control_plane(base)

            payload = guard.preflight(
                repo_root=worktree,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            expected = repo / ".git/tenn-agent-registry"
            self.assertEqual(payload["registry_root"], str(expected.resolve()))
            self.assertEqual(payload["registry_source"], "git_common_dir")

    def test_dirty_status_rows_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

            payload = guard.preflight(
                repo_root=repo,
                topic="dirty",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertTrue(any("dirty.txt" in row for row in payload["dirty_status"]))
            self.assertEqual(payload["path_ownership"]["classification"], "DIRTY_RELATED_WORKTREE")
            self.assertTrue(payload["path_ownership_blocks_implementation"])
            self.assertTrue(payload["stop_reimplementation"])
            self.assertEqual(payload["final_decision"], "block")

    def test_branch_not_based_on_current_canonical_blocks_as_stale_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)

            run(["git", "checkout", "-b", "canonical"], cwd=repo)
            (repo / "canonical.txt").write_text("canonical\n", encoding="utf-8")
            run(["git", "add", "canonical.txt"], cwd=repo)
            run(["git", "commit", "-m", "canonical"], cwd=repo)
            canonical_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
            ).strip()
            run(
                [
                    "git",
                    "update-ref",
                    "refs/remotes/origin/migration/clean-runtime-baseline-reconstruct-v1",
                    canonical_head,
                ],
                cwd=repo,
            )

            run(["git", "checkout", "master"], cwd=repo)
            run(["git", "checkout", "-b", "stale-task"], cwd=repo)
            (repo / "task.txt").write_text("task\n", encoding="utf-8")
            run(["git", "add", "task.txt"], cwd=repo)
            run(["git", "commit", "-m", "task"], cwd=repo)

            payload = guard.preflight(
                repo_root=repo,
                topic="repo path ownership",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["path_ownership"]["classification"], "STALE_PATH")
            self.assertTrue(payload["path_ownership_blocks_implementation"])
            self.assertTrue(payload["stop_reimplementation"])
            self.assertEqual(payload["final_decision"], "block")

    def test_not_git_repo_blocks_with_path_ownership_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "not-git"
            path.mkdir()

            payload = guard.preflight(repo_root=path, topic="repo path ownership")

            self.assertEqual(payload["final_decision"], "block")
            self.assertEqual(payload["errors"], ["repo_root_is_not_a_git_repository"])
            self.assertEqual(payload["path_ownership"]["classification"], "NOT_GIT_REPO")
            self.assertTrue(payload["path_ownership_blocks_implementation"])
            self.assertTrue(payload["stop_reimplementation"])

    def test_ledger_proven_open_pr_blocks_duplicate_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(
                base,
                ledger_search_payload={
                    "ok": True,
                    "data_missing": [],
                    "issues": [],
                    "duplicate_work_classification": "OPEN_PR_WAIT",
                    "matches": [
                        {
                            "source": "live",
                            "path": "ledger.jsonl",
                            "line": 1,
                            "entry": {"task_id": "existing", "status": "pr_opened"},
                        }
                    ],
                },
            )

            payload = guard.preflight(
                repo_root=repo,
                topic="repo path ownership",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["duplicate_work_classification"], "OPEN_PR_WAIT")
            self.assertEqual(payload["duplicate_work_status"], "DUPLICATE")
            self.assertTrue(payload["stop_reimplementation"])
            self.assertEqual(payload["final_decision"], "block")


if __name__ == "__main__":
    unittest.main()
