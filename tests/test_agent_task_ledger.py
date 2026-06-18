from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import agent_task_ledger


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "agent_task_ledger.py"


def run_ledger(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(REPO_ROOT), *args],
        cwd=REPO_ROOT,
        env=merged_env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def sample_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "task_id": "dev_flow_ledger_runtime_handoff_v1_20260617",
        "parent_task_id": None,
        "workflow": "tenn-fix",
        "status": "claimed",
        "started_at": "2026-06-17T00:00:00Z",
        "updated_at": "2026-06-17T00:00:00Z",
        "owner": "Codex",
        "session_id": "DATA_MISSING",
        "thread_id": "DATA_MISSING",
        "codex_goal_id": "DATA_MISSING",
        "source_session_ref": "DATA_MISSING",
        "issue_refs": ["78"],
        "pr_refs": ["360"],
        "branch": "control-plane/agent-ledger-runtime-handoff-v1-20260617",
        "worktree": "/home/l4nd0/tenn-agent-ledger-runtime-handoff-v1-20260617",
        "base": "origin/migration/clean-runtime-baseline-reconstruct-v1",
        "files_touched": ["scripts/agent_task_ledger.py"],
        "artifacts": ["reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/README.md"],
        "summary": "Implements task ledger runtime.",
        "validation": {"status": "not_run", "commands": []},
        "next_action": "continue",
        "owner_boundary": False,
        "supersedes": [],
        "superseded_by": [],
        "evidence_grade": "VERIFIED",
    }
    entry.update(overrides)
    return entry


def write_entry(path: Path, entry: dict[str, object]) -> None:
    path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")


def load_json(process: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert process.stderr == ""
    return json.loads(process.stdout)


class AgentTaskLedgerTests(unittest.TestCase):
    def test_resolve_path_uses_registry_root_without_literal_worktree_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            result = run_ledger("resolve-path", env={"TENN_AGENT_REGISTRY_ROOT": str(registry)})

        self.assertEqual(result.returncode, 0, result.stderr)
        resolved = Path(result.stdout.strip())
        self.assertEqual(resolved, registry / "task-ledger.jsonl")
        self.assertNotIn(".git/tenn-agent-registry/task-ledger.jsonl", resolved.as_posix())

    def test_validate_accepts_data_missing_session_and_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry_file = Path(tmp) / "entry.json"
            write_entry(entry_file, sample_entry(session_id="DATA_MISSING", thread_id="DATA_MISSING"))

            result = run_ledger("validate", "--entry-file", str(entry_file))
            payload = load_json(result)

        self.assertEqual(result.returncode, 0)
        self.assertIs(payload["ok"], True)

    def test_validate_rejects_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry = sample_entry()
            del entry["task_id"]
            entry_file = Path(tmp) / "entry.json"
            write_entry(entry_file, entry)

            result = run_ledger("validate", "--entry-file", str(entry_file))
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertTrue(any("task_id" in issue for issue in payload["issues"]))

    def test_validate_missing_entry_file_returns_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-entry.json"

            result = run_ledger("validate", "--entry-file", str(missing))
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertTrue(any("unable to read file" in issue for issue in payload["issues"]))

    def test_validate_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry_file = Path(tmp) / "entry.json"
            write_entry(entry_file, sample_entry(status="nearly_done"))

            result = run_ledger("validate", "--entry-file", str(entry_file))
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(any("status" in issue for issue in payload["issues"]))

    def test_append_writes_jsonl_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry_file = root / "entry.json"
            ledger = root / "task-ledger.jsonl"
            write_entry(entry_file, sample_entry(updated_at=""))

            result = run_ledger("append", "--entry-file", str(entry_file), "--ledger-path", str(ledger))
            payload = load_json(result)
            lines = ledger.read_text(encoding="utf-8").splitlines()
            written = json.loads(lines[0])

        self.assertEqual(result.returncode, 0)
        self.assertIs(payload["ok"], True)
        self.assertEqual(len(lines), 1)
        self.assertEqual(written["updated_at"], written["started_at"])

    def test_append_missing_entry_file_returns_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing-entry.json"
            ledger = root / "task-ledger.jsonl"

            result = run_ledger("append", "--entry-file", str(missing), "--ledger-path", str(ledger))
            payload = load_json(result)
            ledger_exists = ledger.exists()

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertFalse(ledger_exists)
        self.assertTrue(any("unable to read file" in issue for issue in payload["issues"]))

    def test_append_unwritable_ledger_path_returns_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry_file = root / "entry.json"
            stale_parent = root / "not-a-directory"
            ledger = stale_parent / "task-ledger.jsonl"
            write_entry(entry_file, sample_entry())
            stale_parent.write_text("not a directory", encoding="utf-8")

            result = run_ledger("append", "--entry-file", str(entry_file), "--ledger-path", str(ledger))
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertTrue(any("unable to open ledger for append" in issue for issue in payload["issues"]))

    def test_search_by_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "task-ledger.jsonl"
            write_entry(ledger, sample_entry(task_id="task-a"))

            result = run_ledger("search", "--ledger-path", str(ledger), "--task-id", "task-a")
            payload = load_json(result)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(payload["matches"]), 1)
        self.assertEqual(payload["duplicate_work_classification"], "ACTIVE_CONTINUE")

    def test_classification_requires_fallback_when_source_missing_even_with_matches(self) -> None:
        matches = [{"source": "committed", "line": 1, "entry": sample_entry(status="done")}]

        classification = agent_task_ledger.classify_matches(matches, ["live"])

        self.assertEqual(classification, "DATA_MISSING_FALLBACK_REQUIRED")

    def test_search_by_issue_and_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "task-ledger.jsonl"
            write_entry(ledger, sample_entry(issue_refs=["#78"], pr_refs=["360"]))

            issue_result = run_ledger("search", "--ledger-path", str(ledger), "--issue", "78")
            pr_result = run_ledger("search", "--ledger-path", str(ledger), "--pr", "#360")

        self.assertEqual(len(load_json(issue_result)["matches"]), 1)
        self.assertEqual(len(load_json(pr_result)["matches"]), 1)

    def test_search_by_session_and_thread_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "task-ledger.jsonl"
            write_entry(ledger, sample_entry(session_id="session-1", thread_id="thread-1"))

            session_result = run_ledger("search", "--ledger-path", str(ledger), "--session-id", "session-1")
            thread_result = run_ledger("search", "--ledger-path", str(ledger), "--thread-id", "thread-1")

        self.assertEqual(len(load_json(session_result)["matches"]), 1)
        self.assertEqual(len(load_json(thread_result)["matches"]), 1)

    def test_search_by_touched_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "task-ledger.jsonl"
            write_entry(ledger, sample_entry(files_touched=["scripts/agent_task_ledger.py"]))

            result = run_ledger("search", "--ledger-path", str(ledger), "--path", "agent_task_ledger.py")
            payload = load_json(result)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(payload["matches"]), 1)

    def test_search_missing_custom_ledger_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.jsonl"

            result = run_ledger("search", "--ledger-path", str(missing), "--task-id", "missing-task")
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertTrue(any("missing" in issue for issue in payload["issues"]))

    def test_summarize_groups_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "task-ledger.jsonl"
            entries = [
                sample_entry(task_id="a", status="claimed"),
                sample_entry(task_id="b", status="waiting_on_user", owner_boundary=True),
            ]
            ledger.write_text("".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries), encoding="utf-8")

            result = run_ledger("summarize", "--ledger-path", str(ledger), "--format", "json")
            payload = load_json(result)

        self.assertEqual(result.returncode, 0)
        self.assertEqual([entry["task_id"] for entry in payload["groups"]["claimed"]], ["a"])
        self.assertEqual([entry["task_id"] for entry in payload["groups"]["waiting_on_user"]], ["b"])

    def test_summarize_missing_custom_ledger_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.jsonl"

            result = run_ledger("summarize", "--ledger-path", str(missing), "--format", "json")
            payload = load_json(result)

        self.assertEqual(result.returncode, 1)
        self.assertIs(payload["ok"], False)
        self.assertTrue(any("missing" in issue for issue in payload["issues"]))

    def test_handoff_template_includes_required_sections(self) -> None:
        template = (REPO_ROOT / "docs/dev_flow/templates/HANDOFF.md").read_text(encoding="utf-8")
        required_sections = [
            "Executive summary",
            "Session ID / thread ID / goal ID",
            "Branch/worktree/base",
            "Completed work",
            "Commits",
            "PRs",
            "Issues",
            "Files changed",
            "Tests and validation",
            "Reports/task cards created",
            "Git status and dirt",
            "Ledger status",
            "Failed attempts / mistakes",
            "Open risks",
            "Owner decisions needed",
            "Next 10 milestones",
            "Short next `/goal`",
            "Do-not-touch boundaries",
            "Evidence grades",
        ]
        for section in required_sections:
            self.assertIn(f"## {section}", template)

    def test_readme_append_example_uses_supported_flags(self) -> None:
        readme = (REPO_ROOT / "docs/agent_registry/task_ledger/README.md").read_text(encoding="utf-8")

        self.assertIn("append --entry-file", readme)
        self.assertNotIn("append --task-id", readme)

    def test_skill_frontmatter_parses(self) -> None:
        paths = [
            ".agents/skills/tenn-git-guard/SKILL.md",
            ".agents/skills/tenn-issue/SKILL.md",
            ".agents/skills/tenn-fix/SKILL.md",
            ".agents/skills/tenn-worker/SKILL.md",
            ".agents/skills/tenn-explain/SKILL.md",
            ".agents/skills/tenn-handoff/SKILL.md",
        ]
        for path in paths:
            with self.subTest(path=path):
                content = (REPO_ROOT / path).read_text(encoding="utf-8")
                self.assertTrue(content.startswith("---\n"))
                _prefix, frontmatter, _body = content.split("---", 2)
                parsed = {}
                for raw_line in frontmatter.splitlines():
                    if ":" not in raw_line:
                        continue
                    key, value = raw_line.split(":", 1)
                    parsed[key.strip()] = value.strip()
                self.assertTrue(parsed["name"])
                self.assertTrue(parsed["description"])


if __name__ == "__main__":
    unittest.main()
