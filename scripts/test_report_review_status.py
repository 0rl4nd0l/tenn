from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import report_review_status as rrs


def runtime_proof_report(proof_result: str = "WORKING") -> str:
    return "\n".join(
        [
            "State: DONE",
            "",
            "## Runtime Functionality Proof",
            "- intended output: rows in live output",
            "- live output location: `sqlite:///tmp/proof.db`",
            "- pre-run max timestamp or count: 10",
            "- post-run max timestamp or count: 11",
            "- rows/files inserted or updated after run start: 1",
            "- readiness/gate status: gate passed",
            "- exact command/query used: `select count(*) from output`",
            f"- result: {proof_result}",
            "- remaining blocker: none",
            "",
        ]
    )


def marker_payload(job_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "job_id": job_id,
        "review_status": "PENDING_REVIEW",
        "reviewed_at": "DATA_MISSING",
        "reviewed_by": "DATA_MISSING",
        "review_evidence": ["DATA_MISSING"],
        "source_report_paths": ["README.md"],
        "summary": "Marker exists but has not been reviewed.",
        "next_action": "collect_more_evidence",
        "runtime_functionality_proven": False,
        "github_state_checked": "DATA_MISSING",
    }
    payload.update(overrides)
    return payload


class ReportReviewStatusTests(unittest.TestCase):
    def test_missing_marker_is_data_missing_not_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)

            result = rrs.load_report_review_status(report_dir)

        self.assertTrue(result.ok)
        self.assertFalse(result.marker_exists)
        self.assertEqual("DATA_MISSING", result.review_status)
        self.assertEqual([], result.issues)

    def test_valid_marker_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            (report_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
            (report_dir / rrs.MARKER_FILENAME).write_text(
                json.dumps(marker_payload("demo_report")),
                encoding="utf-8",
            )

            result = rrs.load_report_review_status(report_dir, require_existing_source_paths=True)

        self.assertTrue(result.ok)
        self.assertTrue(result.marker_exists)
        self.assertEqual("PENDING_REVIEW", result.review_status)

    def test_invalid_review_status_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", review_status="APPROVED"),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("review_status", {issue.field for issue in result.issues})

    def test_non_string_review_status_fails_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", review_status=["PENDING_REVIEW"]),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("review_status", {issue.field for issue in result.issues})

    def test_boolean_like_integers_do_not_satisfy_boolean_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload(
                    "demo_report",
                    runtime_functionality_proven=1,
                    github_state_checked=0,
                ),
                report_dir=report_dir,
            )

        fields = {issue.field for issue in result.issues}
        self.assertFalse(result.ok)
        self.assertIn("runtime_functionality_proven", fields)
        self.assertIn("github_state_checked", fields)

    def test_schema_version_rejects_boolean_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", schema_version=True),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("schema_version", {issue.field for issue in result.issues})

    def test_job_id_must_match_containing_report_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("other_report"),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("job_id", {issue.field for issue in result.issues})

    def test_runtime_true_requires_working_runtime_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            (report_dir / "README.md").write_text("# No runtime proof\n", encoding="utf-8")

            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", runtime_functionality_proven=True),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("runtime_functionality_proven", {issue.field for issue in result.issues})

    def test_runtime_true_accepts_working_runtime_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            (report_dir / "README.md").write_text(runtime_proof_report(), encoding="utf-8")

            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", runtime_functionality_proven=True),
                report_dir=report_dir,
            )

        self.assertTrue(result.ok)

    def test_source_paths_must_stay_inside_report_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", source_report_paths=["reports/agent_jobs/other/README.md"]),
                report_dir=report_dir,
                repo_root=Path(temp_dir),
            )

        self.assertFalse(result.ok)
        self.assertIn("source_report_paths", {issue.field for issue in result.issues})

    def test_non_data_missing_status_requires_concrete_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "reports" / "agent_jobs" / "demo_report"
            report_dir.mkdir(parents=True)
            result = rrs.validate_report_review_status_payload(
                marker_payload("demo_report", source_report_paths=["DATA_MISSING"]),
                report_dir=report_dir,
            )

        self.assertFalse(result.ok)
        self.assertIn("source_report_paths", {issue.field for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
