from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import system_brief as sb


def labels(*names: str) -> list[dict[str, str]]:
    return [{"name": name} for name in names]


def marker_payload(job_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "job_id": job_id,
        "review_status": "OWNER_DECISION_REQUIRED",
        "reviewed_at": "2026-07-09T00:00:00Z",
        "reviewed_by": "Codex",
        "review_evidence": ["Owner decision needed before mutation."],
        "source_report_paths": ["README.md"],
        "summary": "Owner must choose whether to proceed.",
        "next_action": "ask_owner",
        "runtime_functionality_proven": False,
        "github_state_checked": True,
    }
    payload.update(overrides)
    return payload


class FakeRunner:
    def __init__(self, *, issue_payload: object | None = None, pr_payload: object | None = None, fail_gh: bool = False):
        self.issue_payload = [] if issue_payload is None else issue_payload
        self.pr_payload = [] if pr_payload is None else pr_payload
        self.fail_gh = fail_gh

    def __call__(self, command: list[str], cwd: Path | None = None) -> sb.CommandResult:
        if command[:3] == ["git", "branch", "--show-current"]:
            return sb.CommandResult(0, "main\n", "")
        if command[:3] == ["git", "rev-parse", "--short"]:
            return sb.CommandResult(0, "abc123\n", "")
        if command[:3] == ["git", "status", "--short"]:
            return sb.CommandResult(0, "", "")
        if command[:3] == ["git", "branch", "--list"]:
            return sb.CommandResult(0, "", "")
        if command[:3] == ["gh", "issue", "list"]:
            if self.fail_gh:
                return sb.CommandResult(1, "", "network unavailable")
            return sb.CommandResult(0, json.dumps(self.issue_payload), "")
        if command[:3] == ["gh", "pr", "list"]:
            if self.fail_gh:
                return sb.CommandResult(1, "", "network unavailable")
            return sb.CommandResult(0, json.dumps(self.pr_payload), "")
        return sb.CommandResult(1, "", f"unexpected command: {' '.join(command)}")


class SystemBriefTests(unittest.TestCase):
    def test_ready_issue_filter_allows_only_safe_labels(self) -> None:
        safe_issue = {
            "labels": labels("state:ready", "risk:low", "mode:safe-extension", "lane:evaluation"),
        }
        runtime_issue = {
            "labels": labels(
                "state:ready",
                "risk:low",
                "mode:safe-extension",
                "lane:evaluation",
                "lane:runtime",
            ),
        }
        missing_mode = {
            "labels": labels("state:ready", "risk:low", "lane:evaluation"),
        }
        extra_lane = {
            "labels": labels("state:ready", "risk:low", "mode:audit", "lane:reporting", "lane:cockpit"),
        }

        self.assertTrue(sb.is_eligible_ready_issue(safe_issue))
        self.assertFalse(sb.is_eligible_ready_issue(runtime_issue))
        self.assertFalse(sb.is_eligible_ready_issue(missing_mode))
        self.assertFalse(sb.is_eligible_ready_issue(extra_lane))

    def test_failed_validation_candidate_sorts_before_ready_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = root / "repo"
            automation_root = root / "automation"
            (repo_root / "reports" / "agent_jobs").mkdir(parents=True)
            (automation_root / "state").mkdir(parents=True)
            (automation_root / "reports").mkdir(parents=True)
            (automation_root / "logs").mkdir(parents=True)
            (automation_root / "state" / "candidates.jsonl").write_text(
                json.dumps(
                    {
                        "status": "failed_validation",
                        "title": "Validation failed for automation fix",
                        "detail": "Focused test failed.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            issue_payload = [
                {
                    "number": 12,
                    "title": "Safe ready issue",
                    "labels": labels("state:ready", "risk:low", "mode:audit", "lane:reporting"),
                    "url": "https://example.test/issues/12",
                }
            ]

            brief = sb.build_brief(
                repo_root=repo_root,
                automation_root=automation_root,
                repo="owner/repo",
                issue_limit=10,
                pr_limit=10,
                recent_report_limit=5,
                log_limit=5,
                runner=FakeRunner(issue_payload=issue_payload),
            )

        self.assertEqual("failed_validation", brief.items[0].status)
        self.assertEqual("candidate_state", brief.items[0].source)
        self.assertTrue(any(item.status == "state_ready_issue" for item in brief.items))

    def test_missing_github_becomes_data_missing_item(self) -> None:
        items, status = sb.collect_github_issue_items("owner/repo", 10, runner=FakeRunner(fail_gh=True))

        self.assertEqual("DATA_MISSING", status)
        self.assertEqual("data_missing", items[0].status)
        self.assertEqual("github_issues", items[0].source)

    def test_owner_decision_marker_creates_queue_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            report_dir = repo_root / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            (report_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
            (report_dir / "REPORT_REVIEW_STATUS.json").write_text(
                json.dumps(marker_payload("demo_report")),
                encoding="utf-8",
            )

            items, status = sb.collect_report_marker_items(repo_root, recent_report_limit=5)

        self.assertEqual("ok", status)
        self.assertEqual("owner_decision_required", items[0].status)
        self.assertIn("demo_report", items[0].title)

    def test_format_brief_includes_recommended_command(self) -> None:
        state = sb.RepoState(repo_root="/tmp/repo", branch="main", head="abc123", dirty=False, status_lines=[])
        item = sb.BriefItem(
            priority=10,
            status="failed_validation",
            source="candidate_state",
            title="Validation failed",
            detail="A focused test failed.",
            owner_action="review this",
            risk="medium",
            evidence="candidates.jsonl:1",
            recommended_command="python3 -m unittest scripts.test_system_brief",
        )
        output = sb.format_brief(sb.Brief(repo_state=state, items=[item], sources={}), max_items=3)

        self.assertIn("Recommended first", output)
        self.assertIn("python3 -m unittest scripts.test_system_brief", output)
        self.assertIn("No writes were performed.", output)

    def test_direct_report_marker_sorts_before_broad_automation_report(self) -> None:
        direct = sb.BriefItem(
            priority=20,
            status="owner_decision_required",
            source="report_markers",
            title="Direct marker",
            detail="Direct marker detail.",
            owner_action="review this",
            risk="low",
            evidence="reports/agent_jobs/demo/REPORT_REVIEW_STATUS.json",
            recommended_command="python3 scripts/report_review_status.py validate reports/agent_jobs/demo",
        )
        broad = sb.BriefItem(
            priority=20,
            status="owner_decision_required",
            source="automation_reports",
            title="Broad report mention",
            detail="Broad report mention.",
            owner_action="review this",
            risk="low",
            evidence="/tmp/report.md",
            recommended_command="sed -n '1,180p' /tmp/report.md",
        )
        items = [broad, direct]
        items.sort(key=lambda item: (item.priority, sb.SOURCE_PRIORITY.get(item.source, 50), item.title))

        self.assertEqual("report_markers", items[0].source)


if __name__ == "__main__":
    unittest.main()
