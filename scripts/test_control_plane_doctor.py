from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import control_plane_doctor as doctor


class ControlPlaneDoctorTests(unittest.TestCase):
    def test_summarize_exit_codes(self) -> None:
        healthy = [doctor.result("a", doctor.PASS, "ok")]
        warning = healthy + [doctor.result("b", doctor.WARN, "drift")]
        failing = warning + [doctor.result("c", doctor.FAIL, "broken")]

        self.assertEqual(doctor.summarize(healthy)["exit_code"], 0)
        self.assertEqual(doctor.summarize(warning)["exit_code"], 1)
        self.assertEqual(doctor.summarize(failing)["exit_code"], 2)

    def test_file_hash_parity_reports_missing_and_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = root / "expected"
            actual = root / "actual"
            expected.mkdir()
            actual.mkdir()
            (expected / "same.txt").write_text("same", encoding="utf-8")
            (actual / "same.txt").write_text("same", encoding="utf-8")
            (expected / "changed.txt").write_text("old", encoding="utf-8")
            (actual / "changed.txt").write_text("new", encoding="utf-8")
            (expected / "missing.txt").write_text("missing", encoding="utf-8")

            check = doctor.check_hash_tree(
                "templates",
                expected,
                actual,
                ["*.txt"],
            )

        self.assertEqual(check["status"], doctor.WARN)
        self.assertEqual(check["evidence"]["mismatched"], ["changed.txt"])
        self.assertEqual(check["evidence"]["missing"], ["missing.txt"])

    def test_hook_targets_are_extracted_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            present = root / "present.py"
            present.write_text("pass\n", encoding="utf-8")
            hooks = root / "hooks.json"
            hooks.write_text(
                json.dumps(
                    {
                        "hooks": [
                            {"command": f"python3 {present}"},
                            {"command": f"python3 {root / 'missing.py'} || true"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            check = doctor.check_hook_targets(hooks)

        self.assertEqual(check["status"], doctor.WARN)
        self.assertEqual(check["evidence"]["missing"], [str(root / "missing.py")])

    def test_candidate_state_validates_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "candidates.jsonl"
            state.write_text('{"fingerprint":"a"}\nnot-json\n', encoding="utf-8")
            invalid = doctor.check_candidate_state(state)
            state.write_text('{"fingerprint":"a"}\n', encoding="utf-8")
            valid = doctor.check_candidate_state(state)

        self.assertEqual(invalid["status"], doctor.FAIL)
        self.assertEqual(invalid["evidence"]["invalid_lines"], [2])
        self.assertEqual(valid["status"], doctor.PASS)

    def test_marker_semantics_flags_optional_missing_marker_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "report_review_status.py"
            brief = root / "system_brief.py"
            marker.write_text("marker_exists=False\nreview_status=DATA_MISSING\n", encoding="utf-8")
            brief.write_text("reason='stale_report'\n", encoding="utf-8")

            check = doctor.check_marker_semantics(marker, brief)

        self.assertEqual(check["status"], doctor.WARN)
        self.assertTrue(check["evidence"]["optional_missing_marker"])
        self.assertTrue(check["evidence"]["brief_stale_report_path"])

    def test_cli_warns_when_cached_canonical_ref_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            self._init_repo(repo)
            branch = self._git(repo, "branch", "--show-current")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "fetch", "origin", branch)
            cached_sha = self._git(repo, "rev-parse", f"origin/{branch}")
            (repo / "newer").write_text("remote truth", encoding="utf-8")
            self._git(repo, "add", "newer")
            self._git(repo, "commit", "-m", "advance remote truth")
            remote_sha = self._git(repo, "rev-parse", "HEAD")

            completed = subprocess.run(
                [
                    "python3",
                    str(Path(doctor.__file__)),
                    "--repo-root",
                    str(repo),
                    "--canonical-ref",
                    f"origin/{branch}",
                    "--deployed-root",
                    str(repo),
                    "--host-skills-root",
                    str(root / "host-skills"),
                    "--hooks-file",
                    str(root / "hooks.json"),
                    "--installed-units-root",
                    str(root / "units"),
                    "--candidate-state",
                    str(root / "candidates.jsonl"),
                    "--json",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            payload = json.loads(completed.stdout)
            parity = next(check for check in payload["checks"] if check["id"] == "git_sha_parity")

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(parity["status"], doctor.WARN)
        self.assertEqual(parity["evidence"]["canonical_sha"], cached_sha)
        self.assertEqual(parity["evidence"]["remote_canonical_sha"], remote_sha)
        self.assertFalse(parity["evidence"]["canonical_ref_fresh"])

    def test_cli_returns_hard_error_for_unresolvable_canonical_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            self._init_repo(repo)
            completed = subprocess.run(
                [
                    "python3",
                    str(Path(doctor.__file__)),
                    "--repo-root",
                    str(repo),
                    "--canonical-ref",
                    "origin/does-not-exist",
                    "--deployed-root",
                    str(repo),
                    "--host-skills-root",
                    str(root / "host-skills"),
                    "--hooks-file",
                    str(root / "hooks.json"),
                    "--installed-units-root",
                    str(root / "units"),
                    "--candidate-state",
                    str(root / "candidates.jsonl"),
                    "--json",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            payload = json.loads(completed.stdout)
            parity = next(check for check in payload["checks"] if check["id"] == "git_sha_parity")

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(payload["summary"]["status"], doctor.FAIL)
        self.assertEqual(parity["status"], doctor.FAIL)
        self.assertIn("canonical", parity["summary"])

    def test_cli_healthy_fixture_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            deployed = root / "deployed"
            host_skills = root / "host-skills"
            installed_units = root / "units"
            state = root / "state"
            for path in (repo, deployed, host_skills, installed_units, state):
                path.mkdir(parents=True)

            self._init_repo(repo)
            self._init_repo(deployed)
            repo_sha = self._git(repo, "rev-parse", "HEAD")
            deployed_sha = self._git(deployed, "rev-parse", "HEAD")
            self.assertEqual(repo_sha, deployed_sha)
            branch = self._git(repo, "branch", "--show-current")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "fetch", "origin", branch)

            scripts = repo / "scripts"
            scripts.mkdir()
            runner = scripts / "codex_automation_runner.py"
            runner.write_text(
                "import json\nprint(json.dumps({'daily-closeout': {'model_policy': 'small', "
                "'model_selection': {'model': 'mini', 'reasoning_effort': 'medium'}}}))\n",
                encoding="utf-8",
            )
            deployed_scripts = deployed / "scripts"
            deployed_scripts.mkdir()
            (deployed_scripts / runner.name).write_text(runner.read_text(encoding="utf-8"), encoding="utf-8")

            repo_units = repo / "systemd" / "user"
            repo_units.mkdir(parents=True)
            (repo_units / "tenn-codex-demo.timer").write_text("timer", encoding="utf-8")
            (installed_units / "tenn-codex-demo.timer").write_text("timer", encoding="utf-8")

            repo_skill = repo / ".agents" / "skills" / "demo"
            host_skill = host_skills / "demo"
            repo_skill.mkdir(parents=True)
            host_skill.mkdir(parents=True)
            (repo_skill / "SKILL.md").write_text("same", encoding="utf-8")
            (host_skill / "SKILL.md").write_text("same", encoding="utf-8")

            hook_target = root / "hook.py"
            hook_target.write_text("pass\n", encoding="utf-8")
            hooks = root / "hooks.json"
            hooks.write_text(json.dumps({"command": f"python3 {hook_target}"}), encoding="utf-8")
            (state / "candidates.jsonl").write_text('{"fingerprint":"a"}\n', encoding="utf-8")
            marker = scripts / "report_review_status.py"
            marker.write_text("marker_exists=False\n", encoding="utf-8")
            brief = scripts / "system_brief.py"
            brief.write_text("queue=[]\n", encoding="utf-8")
            docs = repo / "docs" / "dev_flow"
            docs.mkdir(parents=True)
            freshness = docs / "FRESH.md"
            freshness.write_text(f"last_verified_commit: {repo_sha}\nstale_if_files:\n- scripts/never.py\n", encoding="utf-8")

            before = self._snapshot(root)
            completed = subprocess.run(
                [
                    "python3",
                    str(Path(doctor.__file__)),
                    "--repo-root",
                    str(repo),
                    "--canonical-ref",
                    f"origin/{branch}",
                    "--deployed-root",
                    str(deployed),
                    "--host-skills-root",
                    str(host_skills),
                    "--hooks-file",
                    str(hooks),
                    "--installed-units-root",
                    str(installed_units),
                    "--candidate-state",
                    str(state / "candidates.jsonl"),
                    "--doc",
                    str(freshness),
                    "--json",
                ],
                check=False,
                text=True,
                capture_output=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            payload = json.loads(completed.stdout)
            parity = next(check for check in payload["checks"] if check["id"] == "git_sha_parity")
            after = self._snapshot(root)

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(payload["schema_version"], doctor.SCHEMA_VERSION)
        self.assertEqual(payload["summary"]["status"], doctor.PASS)
        self.assertTrue(parity["evidence"]["canonical_ref_fresh"])
        self.assertEqual(parity["evidence"]["remote_canonical_sha"], repo_sha)
        self.assertEqual(before, after)

    @staticmethod
    def _git(repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()

    def _init_repo(self, repo: Path) -> None:
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "doctor@example.invalid")
        self._git(repo, "config", "user.name", "Doctor Test")
        (repo / "seed").write_text("same", encoding="utf-8")
        self._git(repo, "add", "seed")
        self._git(repo, "commit", "-m", "seed")

    @staticmethod
    def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
        return {
            str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in root.rglob("*")
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
