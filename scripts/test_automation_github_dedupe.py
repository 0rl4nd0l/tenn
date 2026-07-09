from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from typing import Sequence

from scripts import automation_candidate_store as store
from scripts import automation_github_dedupe as dedupe


NOW = datetime(2026, 7, 9, 7, 0, tzinfo=timezone.utc)


class FakeRunner:
    def __init__(
        self,
        *,
        issues: list[dict[str, object]] | None = None,
        prs: list[dict[str, object]] | None = None,
        fail_kind: str | None = None,
    ) -> None:
        self.issues = issues or []
        self.prs = prs or []
        self.fail_kind = fail_kind
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> dedupe.CommandResult:
        self.commands.append(command)
        if command[:3] == ["gh", "issue", "list"]:
            if self.fail_kind == "issue":
                return dedupe.CommandResult(1, "", "issue read failed")
            return dedupe.CommandResult(0, json.dumps(self.issues), "")
        if command[:3] == ["gh", "pr", "list"]:
            if self.fail_kind == "pr":
                return dedupe.CommandResult(1, "", "pr read failed")
            return dedupe.CommandResult(0, json.dumps(self.prs), "")
        return dedupe.CommandResult(2, "", f"unexpected command: {' '.join(command)}")


def assert_read_only_commands(testcase: unittest.TestCase, commands: Sequence[Sequence[str]]) -> None:
    for command in commands:
        testcase.assertTrue(dedupe.is_read_only_gh_command(command), command)


class AutomationGithubDedupeTests(unittest.TestCase):
    def test_related_issue_exact_classifies_duplicate_issue(self) -> None:
        runner = FakeRunner(
            issues=[
                {
                    "number": 291,
                    "title": "Automation write gate",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/issues/291",
                    "labels": [{"name": "state:ready"}],
                }
            ]
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Write gate",
            root_cause="duplicate should not create another issue",
            related_issue="291",
            runner=runner,
        )

        self.assertEqual("duplicate_issue", result.status)
        self.assertEqual("issue", result.best_match.kind if result.best_match else None)
        self.assertEqual(["related_issue_exact"], result.best_match.reasons if result.best_match else [])
        assert_read_only_commands(self, runner.commands)

    def test_exact_pr_title_classifies_duplicate_pr(self) -> None:
        runner = FakeRunner(
            prs=[
                {
                    "number": 492,
                    "title": "Add automation candidate store layer",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/pull/492",
                    "headRefName": "control-plane/automation-candidate-store-layer1-v0-20260709",
                    "labels": [],
                }
            ]
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Add automation candidate store layer",
            root_cause="candidate state suppression",
            runner=runner,
        )

        self.assertEqual("duplicate_pr", result.status)
        self.assertEqual("title_exact", result.best_match.reasons[0] if result.best_match else None)
        assert_read_only_commands(self, runner.commands)

    def test_partial_github_failure_fails_closed_as_data_missing(self) -> None:
        runner = FakeRunner(
            prs=[
                {
                    "number": 492,
                    "title": "Add automation candidate store layer",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/pull/492",
                }
            ],
            fail_kind="issue",
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Add automation candidate store layer",
            root_cause="candidate state suppression",
            runner=runner,
        )

        self.assertEqual("data_missing", result.status)
        self.assertIsNone(result.best_match)
        self.assertEqual(1, len(result.errors))
        assert_read_only_commands(self, runner.commands)

    def test_fuzzy_overlap_requires_review_not_duplicate(self) -> None:
        runner = FakeRunner(
            issues=[
                {
                    "number": 300,
                    "title": "Automation candidate state review queue",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/issues/300",
                }
            ]
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Automation candidate state",
            root_cause="suppression status review",
            runner=runner,
        )

        self.assertEqual("needs_review", result.status)
        self.assertEqual("medium", result.best_match.confidence if result.best_match else None)

    def test_short_root_cause_does_not_create_high_confidence_duplicate(self) -> None:
        runner = FakeRunner(
            issues=[
                {
                    "number": 301,
                    "title": "Automation write gate",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/issues/301",
                }
            ]
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Timer backlog",
            root_cause="automation",
            runner=runner,
        )

        self.assertNotIn(result.status, {"duplicate_issue", "duplicate_pr"})

    def test_unrelated_successful_reads_classify_new(self) -> None:
        runner = FakeRunner(
            issues=[
                {
                    "number": 1,
                    "title": "Cockpit UI copy issue",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/issues/1",
                }
            ],
            prs=[
                {
                    "number": 2,
                    "title": "Extraction parser patch",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/pull/2",
                }
            ],
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Automation strict write gate",
            root_cause="dedupe missing before write",
            runner=runner,
        )

        self.assertEqual("new", result.status)
        self.assertIsNone(result.best_match)

    def test_labels_do_not_filter_search_query(self) -> None:
        runner = FakeRunner(
            prs=[
                {
                    "number": 492,
                    "title": "Add automation candidate store layer",
                    "state": "OPEN",
                    "url": "https://github.com/0rl4nd0l/tenn/pull/492",
                    "headRefName": "control-plane/automation-candidate-store-layer1-v0-20260709",
                    "labels": [],
                }
            ]
        )

        result = dedupe.check_candidate(
            repo="0rl4nd0l/tenn",
            title="Add automation candidate store layer",
            root_cause="candidate state suppression",
            labels=["state:ready"],
            runner=runner,
        )

        self.assertEqual("duplicate_pr", result.status)
        self.assertTrue(all("label:" not in " ".join(command) for command in runner.commands))

    def test_candidate_store_duplicate_record_preserves_fingerprint(self) -> None:
        candidate = store.build_record(
            job="automation",
            lane="reporting",
            evidence_path="reports/demo.md",
            root_cause="write gate duplicate",
            status="needs_review",
            title="Write gate duplicate",
            now=NOW,
        )
        dedupe_result = {
            "status": "duplicate_issue",
            "best_match": {
                "kind": "issue",
                "number": "#291",
                "title": "Write gate duplicate",
                "url": "https://github.com/0rl4nd0l/tenn/issues/291",
            },
        }

        duplicate = store.duplicate_record_from_dedupe(candidate, dedupe_result, now=NOW)

        self.assertIsNotNone(duplicate)
        assert duplicate is not None
        self.assertEqual("duplicate", duplicate["status"])
        self.assertEqual(candidate["fingerprint"], duplicate["fingerprint"])
        self.assertEqual("291", duplicate["related_issue"])
        self.assertEqual("gh issue view 291 --repo 0rl4nd0l/tenn", duplicate["recommended_command"])


if __name__ == "__main__":
    unittest.main()
