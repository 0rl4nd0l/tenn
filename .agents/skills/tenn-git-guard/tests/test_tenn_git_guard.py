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


def make_repo_with_remote_default(
    base: Path,
    *,
    remote_name: str = "origin",
    default_branch: str = "master",
) -> Path:
    remote = base / f"greyhound-{remote_name}.git"
    remote.mkdir()
    run(["git", "init", "--bare"], cwd=remote)

    repo = base / "greyhound-repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    run(["git", "config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("greyhound\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repo)
    run(["git", "commit", "-m", "initial"], cwd=repo)
    run(["git", "branch", "-M", default_branch], cwd=repo)
    run(["git", "remote", "add", remote_name, str(remote)], cwd=repo)
    run(["git", "push", "-u", remote_name, default_branch], cwd=repo)
    run(["git", "symbolic-ref", "HEAD", f"refs/heads/{default_branch}"], cwd=remote)
    run(
        [
            "git",
            "symbolic-ref",
            f"refs/remotes/{remote_name}/HEAD",
            f"refs/remotes/{remote_name}/{default_branch}",
        ],
        cwd=repo,
    )
    return repo


def make_repo_with_origin_master(base: Path) -> Path:
    return make_repo_with_remote_default(base)


def make_fake_control_plane(
    base: Path,
    *,
    ledger_search_payload: dict[str, object] | None = None,
    contract_payload: dict[str, object] | None = None,
    registry_active_jobs: list[dict[str, object]] | None = None,
    registry_warnings: list[dict[str, object]] | None = None,
    decision_validate_payload: dict[str, object] | None = None,
    decision_search_payload: dict[str, object] | None = None,
) -> Path:
    root = base / "control-plane"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    search_payload = ledger_search_payload or {"ok": True, "matches": []}
    contract_result = contract_payload or {"ok": True, "metadata": {}, "issues": [], "warnings": []}
    active_jobs = registry_active_jobs or []
    active_warnings = registry_warnings or []
    decision_validate = decision_validate_payload or {
        "ok": True,
        "data_missing": [],
        "issues": [],
        "entry_count": 0,
    }
    decision_search = decision_search_payload or {
        "ok": True,
        "data_missing": [],
        "issues": [],
        "matches": [],
    }
    (scripts / "agent_job_contract.py").write_text(
        "\n".join(
            [
                "import json",
                f"PAYLOAD = {json.dumps(contract_result, sort_keys=True)!r}",
                "payload = json.loads(PAYLOAD)",
                "print(json.dumps(payload))",
                "raise SystemExit(0 if payload.get('ok') else 1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (scripts / "agent_job_registry.py").write_text(
        "\n".join(
            [
                "import json, os",
                "print(json.dumps({",
                "  'ok': True,",
                "  'read_only': True,",
                "  'lock_acquired': False,",
                f"  'active_jobs': json.loads({json.dumps(active_jobs, sort_keys=True)!r}),",
                f"  'warnings': json.loads({json.dumps(active_warnings, sort_keys=True)!r}),",
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
    (scripts / "agent_decision_ledger.py").write_text(
        "\n".join(
            [
                "import json, os, sys",
                f"VALIDATE = {json.dumps(decision_validate, sort_keys=True)!r}",
                f"SEARCH = {json.dumps(decision_search, sort_keys=True)!r}",
                "cmd = sys.argv[1] if len(sys.argv) > 1 else ''",
                "if cmd == 'resolve-path':",
                "    print(os.path.join(os.environ.get('TENN_AGENT_REGISTRY_ROOT', ''), 'decision-ledger.jsonl'))",
                "elif cmd == 'validate':",
                "    payload = json.loads(VALIDATE)",
                "    print(json.dumps(payload))",
                "    raise SystemExit(0 if payload.get('ok') else 1)",
                "elif cmd == 'search':",
                "    payload = json.loads(SEARCH)",
                "    print(json.dumps(payload))",
                "    raise SystemExit(0 if payload.get('ok') else 1)",
                "else:",
                "    raise SystemExit(2)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (scripts / "agent_job_hook.py").write_text(
        "import json, sys\n"
        "sys.stdin.read()\n"
        "print(json.dumps({'systemMessage': 'v2 hook dispatched'}))\n",
        encoding="utf-8",
    )
    return root


def v2_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "job_id": "new-v2-job",
        "control_contract_version": 2,
        "computed_scope_fingerprint": "f" * 64,
        "project_id": "greyhound",
        "claim_id": "historical_market_floor",
        "hypothesis_id": "thedogs_floor_v1",
        "program_track": "offline_development",
        "source_class": "thedogs_published_market_history",
        "dataset_version": "snapshot-663-v1",
        "evidence_hash": "sha256:" + "a" * 64,
        "target_transition": "floor_verified",
    }
    metadata.update(overrides)
    return metadata


def write_task_card(repo: Path) -> Path:
    path = repo / "task.md"
    path.write_text("---\ncontrol_contract_version: 2\n---\n", encoding="utf-8")
    return path


def decision_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "decision_id": "decision-1",
        "scope_fingerprint": "f" * 64,
        "task_id": "old-task",
        "run_id": "old-run",
        "project_id": "greyhound",
        "claim_id": "historical_market_floor",
        "hypothesis_id": "thedogs_floor_v1",
        "program_track": "offline_development",
        "source_class": "thedogs_published_market_history",
        "dataset_version": "snapshot-663-v1",
        "evidence_hash": "sha256:" + "a" * 64,
        "target_transition": "floor_verified",
        "phase_before": "floor_unverified",
        "phase_after": "floor_verified",
        "decision": "PASS",
        "outcome_status": "ADVANCED",
        "decision_delta": "The immutable 663-race snapshot clears the floor.",
        "evidence_refs": ["artifact.json"],
        "blocks": [],
        "does_not_block": [],
        "validated_at": "2026-07-13T00:00:00Z",
        "invalidation_conditions": ["evidence hash changes"],
        "reopen_conditions": ["dataset version changes"],
    }
    entry.update(overrides)
    return entry


def v2_active_job(metadata: dict[str, object], **overrides: object) -> dict[str, object]:
    active = {
        "job_id": "other-active-job",
        "control_contract_version": 2,
        **{
            field: metadata[field]
            for field in guard.V2_ACTIVE_SEMANTIC_FIELDS
        },
        "scope_fingerprint": metadata["computed_scope_fingerprint"],
        "status": "active",
        "stale": False,
    }
    active.update(overrides)
    return active


class TennGitGuardTest(unittest.TestCase):
    def test_stable_v2_canonical_root_precedes_and_falls_through_to_glob(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            home = base / "home"
            home.mkdir()
            stable_source = make_fake_control_plane(base / "stable-source")
            stable = home / "tenn-semantic-anti-loop-v2-canonical"
            stable_source.rename(stable)
            arbitrary_source = make_fake_control_plane(base / "arbitrary-source")
            arbitrary = home / "tenn-aaa-stale-worktree"
            arbitrary_source.rename(arbitrary)

            with mock.patch.object(
                guard.Path,
                "home",
                return_value=home,
            ), mock.patch.object(guard, "git_config_global", return_value=None):
                selected, _ = guard.discover_control_plane_root({}, require_v2=True)
                stable.rename(base / "stable-absent")
                fallback, checked = guard.discover_control_plane_root({}, require_v2=True)

            self.assertEqual(selected, stable.resolve())
            self.assertEqual(fallback, arbitrary.resolve())
            self.assertIn(str(stable.resolve()), checked)

    def test_portable_hook_skips_stale_root_and_dispatches_v2_capable_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            stale = make_fake_control_plane(base / "stale")
            (stale / "scripts/agent_decision_ledger.py").unlink()
            (stale / "scripts/agent_job_hook.py").unlink()
            capable = make_fake_control_plane(base / "capable")

            with mock.patch.object(
                guard,
                "git_config_global",
                return_value=str(capable),
            ):
                payload = guard.portable_hook(
                    repo_root=repo,
                    platform="codex",
                    event="Stop",
                    stdin_text=json.dumps({"hook_event_name": "Stop"}),
                    env={"TENN_CONTROL_PLANE_ROOT": str(stale)},
                )
                selected, checked = guard.discover_control_plane_root(
                    {"TENN_CONTROL_PLANE_ROOT": str(stale)},
                    require_v2=True,
                )

            self.assertEqual(payload, {"systemMessage": "v2 hook dispatched"})
            self.assertEqual(selected, capable.resolve())
            self.assertIn(str(stale.resolve()), checked)

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

    def test_target_repo_local_registry_root_is_honored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            registry_root = base / "repo-configured-registry"
            run(["git", "config", "--local", "tenn.agentRegistryRoot", str(registry_root)], cwd=repo)

            payload = guard.preflight(
                repo_root=repo,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["registry_root"], str(registry_root.resolve()))
            self.assertEqual(payload["registry_source"], "git_local:tenn.agentRegistryRoot")

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

    def test_summary_fallback_caps_branch_and_worktree_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            for index in range(4):
                run(["git", "branch", f"topic-branch-{index}"], cwd=repo)
                run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        f"topic-worktree-{index}",
                        str(base / f"worktree-{index}"),
                        "HEAD",
                    ],
                    cwd=repo,
                )

            payload = guard.preflight(
                repo_root=repo,
                topic="topic",
                fallback_sample_limit=2,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            fallback = payload["fallback_sources_checked"]
            self.assertEqual(fallback["detail"], "summary")
            branches = fallback["local_and_remote_branches"]
            worktrees = fallback["worktrees"]
            self.assertIsInstance(branches, dict)
            self.assertIsInstance(worktrees, dict)
            self.assertGreater(branches["count"], 2)
            self.assertGreater(worktrees["count"], 2)
            self.assertLessEqual(len(branches["sample"]), 2)
            self.assertLessEqual(len(worktrees["sample"]), 2)
            self.assertTrue(branches["truncated"])
            self.assertTrue(worktrees["truncated"])
            self.assertIn("dirty_status_rows", fallback)

    def test_full_fallback_detail_preserves_branch_and_worktree_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)

            payload = guard.preflight(
                repo_root=repo,
                topic="topic",
                fallback_detail="full",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            fallback = payload["fallback_sources_checked"]
            self.assertEqual(fallback["detail"], "full")
            self.assertIsInstance(fallback["local_and_remote_branches"], list)
            self.assertIsInstance(fallback["worktrees"], list)

    def test_cross_repo_origin_master_owns_canonical_identity_and_path_classification(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo_with_origin_master(base)
            control_plane = make_fake_control_plane(base)
            canonical_head = subprocess.check_output(
                ["git", "rev-parse", "origin/master"],
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

            canonical_payload = guard.preflight(
                repo_root=repo,
                topic="cross repo canonical ownership",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(canonical_payload["base"], "origin/master")
            self.assertEqual(canonical_payload["upstream"], "origin/master")
            self.assertEqual(canonical_payload["canonical_branch"], "origin/master")
            self.assertEqual(
                canonical_payload["canonical_branch_ref"],
                "refs/remotes/origin/master",
            )
            self.assertEqual(canonical_payload["canonical_head"], canonical_head)
            self.assertEqual(
                canonical_payload["path_ownership"]["classification"],
                "VALID_CANONICAL_WORKTREE",
            )

            run(["git", "checkout", "-b", "greyhound-pilot"], cwd=repo)
            (repo / "pilot.txt").write_text("pilot\n", encoding="utf-8")
            run(["git", "add", "pilot.txt"], cwd=repo)
            run(["git", "commit", "-m", "pilot"], cwd=repo)
            run(["git", "branch", "--set-upstream-to", "origin/master"], cwd=repo)

            task_payload = guard.preflight(
                repo_root=repo,
                topic="cross repo canonical ownership",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(task_payload["canonical_branch"], "origin/master")
            self.assertEqual(task_payload["canonical_head"], canonical_head)
            self.assertEqual(task_payload["merge_base"], canonical_head)
            self.assertEqual(
                task_payload["path_ownership"]["classification"],
                "VALID_TASK_WORKTREE",
            )

    def test_no_upstream_retains_tenn_canonical_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
            ).strip()
            run(
                [
                    "git",
                    "update-ref",
                    "refs/remotes/origin/migration/clean-runtime-baseline-reconstruct-v1",
                    head,
                ],
                cwd=repo,
            )

            payload = guard.preflight(
                repo_root=repo,
                topic="fallback canonical ownership",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["base"], guard.DEFAULT_FALLBACK_BASE)
            self.assertIsNone(payload["upstream"])
            self.assertEqual(payload["canonical_branch"], guard.DEFAULT_FALLBACK_BASE)
            self.assertEqual(payload["canonical_branch_ref"], guard.CANONICAL_BRANCH_REF)
            self.assertEqual(payload["canonical_head"], head)

    def test_published_feature_upstream_does_not_override_tenn_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo_with_origin_master(base)
            control_plane = make_fake_control_plane(base)
            canonical_head = git_head = subprocess.check_output(
                ["git", "rev-parse", "origin/master"],
                cwd=repo,
                text=True,
            ).strip()
            run(
                ["git", "update-ref", f"refs/remotes/origin/{guard.DEFAULT_FALLBACK_BASE.removeprefix('origin/')}", canonical_head],
                cwd=repo,
            )
            run(["git", "checkout", "-b", "published-feature"], cwd=repo)
            (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
            run(["git", "add", "feature.txt"], cwd=repo)
            run(["git", "commit", "-m", "feature"], cwd=repo)
            run(["git", "push", "-u", "origin", "published-feature"], cwd=repo)
            self.assertNotEqual(git_head, subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip())

            payload = guard.preflight(
                repo_root=repo,
                topic="published feature canonical safety",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["base"], guard.DEFAULT_FALLBACK_BASE)
            self.assertEqual(payload["canonical_head"], canonical_head)
            self.assertNotEqual(payload["base"], "origin/published-feature")

    def test_published_feature_uses_remote_default_without_tenn_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo_with_origin_master(base)
            control_plane = make_fake_control_plane(base)
            canonical_head = subprocess.check_output(
                ["git", "rev-parse", "origin/master"], cwd=repo, text=True
            ).strip()
            run(["git", "checkout", "-b", "published-feature"], cwd=repo)
            (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
            run(["git", "add", "feature.txt"], cwd=repo)
            run(["git", "commit", "-m", "feature"], cwd=repo)
            run(["git", "push", "-u", "origin", "published-feature"], cwd=repo)

            payload = guard.preflight(
                repo_root=repo,
                topic="published feature canonical safety",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["base"], "origin/master")
            self.assertEqual(payload["canonical_head"], canonical_head)
            self.assertEqual(
                payload["path_ownership"]["classification"],
                "VALID_TASK_WORKTREE",
            )

    def test_non_origin_remote_symbolic_default_owns_canonical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo_with_remote_default(
                base,
                remote_name="upstream",
                default_branch="main",
            )
            control_plane = make_fake_control_plane(base)
            canonical_head = subprocess.check_output(
                ["git", "rev-parse", "upstream/main"], cwd=repo, text=True
            ).strip()
            run(["git", "checkout", "-b", "published-feature"], cwd=repo)
            (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
            run(["git", "add", "feature.txt"], cwd=repo)
            run(["git", "commit", "-m", "feature"], cwd=repo)
            run(["git", "push", "-u", "upstream", "published-feature"], cwd=repo)

            payload = guard.preflight(
                repo_root=repo,
                topic="non origin canonical safety",
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["base"], "upstream/main")
            self.assertEqual(
                payload["canonical_branch_ref"],
                "refs/remotes/upstream/main",
            )
            self.assertEqual(payload["canonical_head"], canonical_head)
            self.assertEqual(
                payload["path_ownership"]["classification"],
                "VALID_TASK_WORKTREE",
            )

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

    def test_local_canonical_branch_behind_remote_blocks_as_stale_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            control_plane = make_fake_control_plane(base)

            run(["git", "checkout", "-b", "migration/clean-runtime-baseline-reconstruct-v1"], cwd=repo)
            local_canonical_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
            ).strip()
            current_tree = subprocess.check_output(
                ["git", "rev-parse", f"{local_canonical_head}^{{tree}}"],
                cwd=repo,
                text=True,
            ).strip()
            remote_canonical_head = subprocess.check_output(
                ["git", "commit-tree", current_tree, "-m", "remote canonical"],
                cwd=repo,
                text=True,
            ).strip()
            run(
                [
                    "git",
                    "update-ref",
                    "refs/remotes/origin/migration/clean-runtime-baseline-reconstruct-v1",
                    remote_canonical_head,
                ],
                cwd=repo,
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo,
                    text=True,
                ).strip(),
                local_canonical_head,
            )
            self.assertNotEqual(
                subprocess.run(
                    [
                        "git",
                        "merge-base",
                        "HEAD",
                        "origin/migration/clean-runtime-baseline-reconstruct-v1",
                    ],
                    cwd=repo,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                ).returncode,
                0,
            )

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

    def test_v2_missing_decision_ledger_hard_stops_data_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_validate_payload={
                    "ok": False,
                    "data_missing": ["live"],
                    "issues": [],
                    "entry_count": 0,
                },
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "DATA_MISSING")
            self.assertEqual(payload["decision_ledger_status"], "DATA_MISSING")
            self.assertFalse(payload["substantive_work_permitted"])
            self.assertEqual(payload["final_decision"], "block")

    def test_exact_resolved_v2_scope_reuses_complete_without_report_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            entry = decision_entry()
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_search_payload={
                    "ok": True,
                    "data_missing": [],
                    "issues": [],
                    "matches": [{"entry": entry, "has_decision_delta": True, "is_no_delta": False}],
                },
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "REUSED_COMPLETE")
            self.assertFalse(payload["substantive_work_permitted"])
            self.assertFalse(payload["report_write_permitted"])
            self.assertEqual(payload["final_decision"], "block")

    def test_latest_exact_conflict_outranks_older_resolved_decision(self) -> None:
        older = decision_entry(decision_id="older-pass")
        latest = decision_entry(
            decision_id="latest-conflict",
            decision="CONFLICT",
            outcome_status="EVIDENCE_CONFLICT",
            decision_delta="New evidence conflicts with the earlier pass.",
        )

        result = guard.classify_v2_scope(
            v2_metadata(),
            active_jobs=[],
            decision_matches=[{"entry": older}, {"entry": latest}],
        )

        self.assertEqual(result["status"], "EVIDENCE_CONFLICT")
        self.assertEqual(result["matching_decision_ids"], ["latest-conflict"])

    def test_matching_active_v2_fingerprint_stops_as_active_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            metadata = v2_metadata()
            metadata["computed_scope_fingerprint"] = guard._compute_scope_fingerprint(metadata)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": metadata, "issues": [], "warnings": []},
                registry_active_jobs=[v2_active_job(metadata)],
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "ACTIVE_DUPLICATE")
            self.assertFalse(payload["substantive_work_permitted"])
            self.assertEqual(payload["final_decision"], "block")

    def test_third_unchanged_no_delta_continuation_stops_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            entries = []
            for index in range(2):
                entry = decision_entry(
                    decision_id=f"no-delta-{index}",
                    scope_fingerprint=str(index) * 64,
                    target_transition=f"related-transition-{index}",
                    phase_after="floor_unverified",
                    decision="DATA_MISSING",
                    outcome_status="BLOCKED_NO_NEW_INPUT",
                    decision_delta="NO_CHANGE",
                )
                entries.append({"entry": entry, "has_decision_delta": False, "is_no_delta": True})
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_search_payload={"ok": True, "data_missing": [], "issues": [], "matches": entries},
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "LOOP_GUARD_STOP")
            self.assertEqual(payload["no_delta_outcomes"], 2)
            self.assertFalse(payload["substantive_work_permitted"])

    def test_changed_evidence_hash_admits_related_v2_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            old_entry = decision_entry(
                scope_fingerprint="0" * 64,
                evidence_hash="sha256:" + "b" * 64,
                phase_after="floor_unverified",
                decision="DATA_MISSING",
                outcome_status="BLOCKED_NO_NEW_INPUT",
                decision_delta="NO_CHANGE",
            )
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_search_payload={
                    "ok": True,
                    "data_missing": [],
                    "issues": [],
                    "matches": [
                        {"entry": old_entry, "has_decision_delta": False, "is_no_delta": True},
                        {"entry": {**old_entry, "decision_id": "old-2"}, "is_no_delta": True},
                    ],
                },
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "ALLOW_CHANGED_EVIDENCE")
            self.assertTrue(payload["semantic_scope_admitted"])

    def test_new_dataset_evidence_pair_is_not_collapsed_across_old_entries(self) -> None:
        current = v2_metadata(
            dataset_version="dataset-b",
            evidence_hash="sha256:" + "b" * 64,
            computed_scope_fingerprint="1" * 64,
        )
        matches = [
            {
                "entry": decision_entry(
                    decision_id="dataset-a-evidence-b",
                    dataset_version="dataset-a",
                    evidence_hash="sha256:" + "b" * 64,
                    scope_fingerprint="2" * 64,
                )
            },
            {
                "entry": decision_entry(
                    decision_id="dataset-b-evidence-a",
                    dataset_version="dataset-b",
                    evidence_hash="sha256:" + "a" * 64,
                    scope_fingerprint="3" * 64,
                )
            },
        ]

        result = guard.classify_v2_scope(
            current,
            active_jobs=[],
            decision_matches=matches,
        )

        self.assertEqual(result["status"], "ALLOW_CHANGED_EVIDENCE")
        self.assertTrue(result["scope_admitted"])

    def test_genuinely_new_hypothesis_admits_related_v2_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            old_entry = decision_entry(hypothesis_id="old-hypothesis", scope_fingerprint="0" * 64)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_search_payload={
                    "ok": True,
                    "data_missing": [],
                    "issues": [],
                    "matches": [{"entry": old_entry, "is_no_delta": True}],
                },
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["semantic_control_status"], "ALLOW_NEW_HYPOTHESIS")
            self.assertTrue(payload["semantic_scope_admitted"])

    def test_prospective_missing_evidence_blocks_promotion_but_not_offline_fit(self) -> None:
        entry = decision_entry(
            scope_fingerprint="0" * 64,
            claim_id="strict_sportsbet_same_floor",
            program_track="prospective_readiness",
            decision="DATA_MISSING",
            outcome_status="DATA_MISSING",
            decision_delta="NO_CHANGE",
            blocks=["strict_same_floor_comparison", "promote_model"],
            does_not_block=["fit_offline_challenger"],
        )
        active_jobs: list[dict[str, object]] = []

        promotion = guard.classify_v2_scope(
            v2_metadata(
                claim_id="strict_sportsbet_same_floor",
                target_transition="promote_model",
                program_track="prospective_readiness",
                computed_scope_fingerprint="1" * 64,
            ),
            active_jobs=active_jobs,
            decision_matches=[{"entry": entry, "is_no_delta": True}],
        )
        offline = guard.classify_v2_scope(
            v2_metadata(
                claim_id="strict_sportsbet_same_floor",
                target_transition="fit_offline_challenger",
                program_track="offline_development",
                hypothesis_id="offline-fit-v1",
                computed_scope_fingerprint="2" * 64,
            ),
            active_jobs=active_jobs,
            decision_matches=[{"entry": entry, "is_no_delta": True}],
        )

        self.assertEqual(promotion["status"], "DATA_MISSING")
        self.assertFalse(promotion["scope_admitted"])
        self.assertTrue(offline["scope_admitted"])

    def test_prospective_no_delta_does_not_consume_offline_loop_allowance(self) -> None:
        matches = [
            {
                "entry": decision_entry(
                    decision_id=f"prospective-{index}",
                    scope_fingerprint=str(index) * 64,
                    program_track="prospective_readiness",
                    decision="DATA_MISSING",
                    outcome_status="BLOCKED_NO_NEW_INPUT",
                    decision_delta="NO_DELTA",
                    target_transition=f"capture-{index}",
                ),
                "is_no_delta": True,
            }
            for index in range(2)
        ]

        result = guard.classify_v2_scope(
            v2_metadata(program_track="offline_development"),
            active_jobs=[],
            decision_matches=matches,
        )

        self.assertEqual(result["status"], "ALLOW_NEW_SCOPE")
        self.assertEqual(result["no_delta_outcomes"], 0)

    def test_prospective_entry_blocks_offline_only_for_named_transition(self) -> None:
        blocker = decision_entry(
            program_track="prospective_readiness",
            decision="DATA_MISSING",
            outcome_status="DATA_MISSING",
            decision_delta="NO_DELTA",
            blocks=["offline_fit_with_prospective_dependency"],
        )

        blocked = guard.classify_v2_scope(
            v2_metadata(
                program_track="offline_development",
                target_transition="offline_fit_with_prospective_dependency",
                computed_scope_fingerprint="1" * 64,
            ),
            active_jobs=[],
            decision_matches=[{"entry": blocker, "is_no_delta": True}],
        )
        unrelated = guard.classify_v2_scope(
            v2_metadata(
                program_track="offline_development",
                target_transition="ordinary_offline_fit",
                computed_scope_fingerprint="2" * 64,
            ),
            active_jobs=[],
            decision_matches=[{"entry": blocker, "is_no_delta": True}],
        )

        self.assertEqual(blocked["status"], "DATA_MISSING")
        self.assertFalse(blocked["scope_admitted"])
        self.assertEqual(unrelated["status"], "ALLOW_NEW_SCOPE")
        self.assertTrue(unrelated["scope_admitted"])

    def test_obsolete_evidence_controls_do_not_affect_current_pair(self) -> None:
        old_pair = {
            "dataset_version": "old-dataset",
            "evidence_hash": "sha256:" + "b" * 64,
            "scope_fingerprint": "1" * 64,
        }
        obsolete_blocker = decision_entry(
            decision_id="obsolete-blocker",
            decision="DATA_MISSING",
            outcome_status="DATA_MISSING",
            decision_delta="NO_DELTA",
            blocks=["floor_verified"],
            **old_pair,
        )
        obsolete_allowance = decision_entry(
            decision_id="obsolete-allowance",
            does_not_block=["floor_verified"],
            **old_pair,
        )
        obsolete_same_hypothesis = decision_entry(
            decision_id="obsolete-hypothesis",
            hypothesis_id="current-hypothesis",
            **old_pair,
        )
        current_other_hypothesis = decision_entry(
            decision_id="current-other-hypothesis",
            hypothesis_id="other-hypothesis",
            scope_fingerprint="2" * 64,
        )

        result = guard.classify_v2_scope(
            v2_metadata(
                hypothesis_id="current-hypothesis",
                computed_scope_fingerprint="3" * 64,
            ),
            active_jobs=[],
            decision_matches=[
                {"entry": obsolete_blocker, "is_no_delta": True},
                {"entry": obsolete_allowance},
                {"entry": obsolete_same_hypothesis, "is_no_delta": True},
                {"entry": current_other_hypothesis},
            ],
        )

        self.assertEqual(result["status"], "ALLOW_NEW_HYPOTHESIS")
        self.assertTrue(result["scope_admitted"])

    def test_obsolete_no_delta_entries_do_not_trigger_current_pair_loop(self) -> None:
        old = decision_entry(
            decision_id="old-no-delta",
            dataset_version="old-dataset",
            evidence_hash="sha256:" + "b" * 64,
            scope_fingerprint="1" * 64,
            decision="DATA_MISSING",
            outcome_status="BLOCKED_NO_NEW_INPUT",
            decision_delta="NO_DELTA",
        )
        current = decision_entry(
            decision_id="current-no-delta",
            scope_fingerprint="2" * 64,
            target_transition="related-current-transition",
            decision="DATA_MISSING",
            outcome_status="BLOCKED_NO_NEW_INPUT",
            decision_delta="NO_DELTA",
        )

        result = guard.classify_v2_scope(
            v2_metadata(),
            active_jobs=[],
            decision_matches=[
                {"entry": old, "is_no_delta": True},
                {"entry": current, "is_no_delta": True},
            ],
        )

        self.assertEqual(result["status"], "ALLOW_RELATED_SCOPE")
        self.assertEqual(result["no_delta_outcomes"], 1)

    def test_v2_invalid_registry_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                registry_active_jobs="not-a-list",  # type: ignore[arg-type]
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["registry_status"], "DATA_MISSING")
            self.assertEqual(payload["semantic_control_status"], "DATA_MISSING")
            self.assertEqual(payload["final_decision"], "block")

    def test_v2_unreadable_active_record_warning_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                registry_warnings=[
                    {"field": "active_jobs", "message": "active/broken.json is invalid JSON"}
                ],
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["registry_status"], "DATA_MISSING")
            self.assertIn("registry_v2_active_records", payload["data_missing_sources"])
            self.assertEqual(payload["final_decision"], "block")

    def test_v2_semantically_invalid_active_record_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                registry_active_jobs=[
                    {
                        "job_id": "broken-v2",
                        "control_contract_version": 2,
                        "scope_fingerprint": "f" * 64,
                        "status": "active",
                        "stale": False,
                    }
                ],
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["registry_status"], "DATA_MISSING")
            self.assertEqual(payload["semantic_control_status"], "DATA_MISSING")
            self.assertEqual(payload["final_decision"], "block")

    def test_new_hypothesis_does_not_bypass_unchanged_promotion_blocker(self) -> None:
        entry = decision_entry(
            hypothesis_id="old-hypothesis",
            scope_fingerprint="0" * 64,
            program_track="prospective_readiness",
            decision="DATA_MISSING",
            outcome_status="DATA_MISSING",
            decision_delta="NO_CHANGE",
            blocks=["promote_model"],
        )

        result = guard.classify_v2_scope(
            v2_metadata(
                hypothesis_id="new-hypothesis",
                program_track="prospective_readiness",
                target_transition="promote_model",
                computed_scope_fingerprint="1" * 64,
            ),
            active_jobs=[],
            decision_matches=[{"entry": entry, "is_no_delta": True}],
        )

        self.assertEqual(result["status"], "DATA_MISSING")
        self.assertFalse(result["scope_admitted"])

    def test_explicit_blocker_wins_over_other_not_blocked_entry(self) -> None:
        blocker = decision_entry(
            decision_id="prospective-blocker",
            decision="DATA_MISSING",
            outcome_status="DATA_MISSING",
            decision_delta="NO_CHANGE",
            blocks=["promote_model"],
        )
        unrelated_allowance = decision_entry(
            decision_id="offline-allowance",
            scope_fingerprint="1" * 64,
            does_not_block=["promote_model"],
        )

        result = guard.classify_v2_scope(
            v2_metadata(
                target_transition="promote_model",
                computed_scope_fingerprint="2" * 64,
            ),
            active_jobs=[],
            decision_matches=[{"entry": blocker}, {"entry": unrelated_allowance}],
        )

        self.assertEqual(result["status"], "DATA_MISSING")
        self.assertFalse(result["scope_admitted"])

    def test_v1_task_card_keeps_working_when_decision_ledger_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={
                    "ok": True,
                    "metadata": {"job_id": "legacy-v1"},
                    "issues": [],
                    "warnings": [
                        {
                            "field": "control_contract_version",
                            "message": "legacy v1 task card",
                        }
                    ],
                },
                decision_validate_payload={"ok": False, "data_missing": ["live"], "issues": []},
            )

            payload = guard.preflight(
                repo_root=repo,
                task_card=card,
                env={**os.environ, "TENN_CONTROL_PLANE_ROOT": str(control_plane)},
            )

            self.assertEqual(payload["control_contract_status"], "V1_WARNING")
            self.assertEqual(payload["semantic_control_status"], "V1_NOT_APPLICABLE")
            self.assertNotEqual(payload["final_decision"], "block")

    def test_cli_returns_nonzero_for_v2_hard_block_but_preserves_v1_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            control_plane = make_fake_control_plane(
                base,
                contract_payload={"ok": True, "metadata": v2_metadata(), "issues": [], "warnings": []},
                decision_search_payload={
                    "ok": True,
                    "data_missing": [],
                    "issues": [],
                    "matches": [{"entry": decision_entry()}],
                },
            )
            env = {
                **os.environ,
                "TENN_CONTROL_PLANE_ROOT": str(control_plane),
                "GIT_CONFIG_GLOBAL": os.devnull,
            }
            v2 = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "preflight",
                    "--repo-root",
                    str(repo),
                    "--task-card",
                    str(card),
                    "--json",
                ],
                cwd=repo,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            control_plane = make_fake_control_plane(
                base / "legacy",
                contract_payload={"ok": True, "metadata": {"job_id": "legacy"}, "issues": [], "warnings": []},
            )
            env["TENN_CONTROL_PLANE_ROOT"] = str(control_plane)
            v1 = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "preflight",
                    "--repo-root",
                    str(repo),
                    "--task-card",
                    str(card),
                    "--json",
                ],
                cwd=repo,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(v2.returncode, 3)
            self.assertEqual(v1.returncode, 0)

    def test_cli_returns_nonzero_for_missing_or_explicit_null_task_card(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = make_repo(base)
            card = write_task_card(repo)
            card.write_text("---\ncontrol_contract_version: ~\n---\n", encoding="utf-8")
            control_plane = make_fake_control_plane(
                base,
                contract_payload={
                    "ok": False,
                    "metadata": {"control_contract_version": None},
                    "issues": [
                        {
                            "field": "control_contract_version",
                            "message": "must be the integer 1 or 2 when provided",
                        }
                    ],
                    "warnings": [],
                },
            )
            env = {
                **os.environ,
                "TENN_CONTROL_PLANE_ROOT": str(control_plane),
                "GIT_CONFIG_GLOBAL": os.devnull,
            }

            invalid = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "preflight",
                    "--repo-root",
                    str(repo),
                    "--task-card",
                    str(card),
                    "--json",
                ],
                cwd=repo,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            missing = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "preflight",
                    "--repo-root",
                    str(repo),
                    "--task-card",
                    str(repo / "missing-task-card.md"),
                    "--json",
                ],
                cwd=repo,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(json.loads(invalid.stdout)["control_contract_status"], "V2_INVALID")
            self.assertEqual(missing.returncode, 2)
            self.assertEqual(json.loads(missing.stdout)["control_contract_status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
