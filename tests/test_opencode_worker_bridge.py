from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "opencode_worker_bridge.py"
spec = importlib.util.spec_from_file_location("opencode_worker_bridge", SCRIPT_PATH)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)


VALID_RESULT = """\
worker_id: scout-1
task_tier: small
model: deepseek/deepseek-chat
decision_limit: evidence_only
summary: Checked the bridge script and tests.
findings:
- The script exists and is scoped to control-plane tooling.
evidence_paths:
- scripts/opencode_worker_bridge.py
confidence: medium
risks:
- Codex still needs to review the result.
recommended_next_action: Codex review
stop_condition_hit: no
"""


def result_with_stop_condition_hit(value: str) -> str:
    return VALID_RESULT.replace("stop_condition_hit: no", f"stop_condition_hit: {value}")


class OpenCodeWorkerBridgeTests(unittest.TestCase):
    def test_probe_output_shape_when_opencode_missing(self) -> None:
        with mock.patch.object(bridge.shutil, "which", return_value=None):
            result = bridge.probe_opencode(command="definitely-missing-opencode")
        self.assertFalse(result["available"])
        self.assertEqual(result["command"], "definitely-missing-opencode")
        self.assertIn("version", result["checks"])
        self.assertFalse(result["deepseek_available"])

    def test_worker_directory_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_file = root / "task.md"
            task_file.write_text("Inspect scripts/opencode_worker_bridge.py only.\n", encoding="utf-8")
            opencode = root / "opencode"
            opencode.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "if sys.argv[1:3] == ['debug', 'config']:\n"
                "    print(os.environ['OPENCODE_CONFIG_CONTENT'])\n"
                "    raise SystemExit(0)\n"
                "print('''" + VALID_RESULT.replace("'", "\\'") + "''')\n",
                encoding="utf-8",
            )
            opencode.chmod(0o755)

            with mock.patch.dict(bridge.os.environ, {"OPENCODE_SERVER_URL": ""}, clear=False), mock.patch(
                "builtins.print"
            ):
                rc = bridge.main(
                    [
                        "run",
                        "--job-dir",
                        str(root / "job"),
                        "--worker-id",
                        "scout-1",
                        "--agent",
                        "evidence-scout",
                        "--model",
                        "deepseek/deepseek-chat",
                        "--task-file",
                        str(task_file),
                        "--workdir",
                        str(root),
                        "--decision-limit",
                        "evidence_only",
                        "--timeout-seconds",
                        "5",
                        "--opencode-command",
                        str(opencode),
                    ]
                )

            worker_dir = root / "job" / "scout-1"
            self.assertEqual(rc, 0)
            self.assertTrue((worker_dir / "WORKER_TASK.md").is_file())
            self.assertTrue((worker_dir / "WORKER_RESULT.md").is_file())
            self.assertTrue((worker_dir / "WORKER_META.json").is_file())
            self.assertTrue((worker_dir / "raw_output.txt").is_file())
            meta = json.loads((worker_dir / "WORKER_META.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"], "completed")
            self.assertEqual(meta["permission_enforcement"]["profile"], "readonly")
            self.assertEqual(meta["permission_enforcement"]["method"], "OPENCODE_CONFIG_CONTENT")
            self.assertTrue(meta["permission_enforcement"]["verified"])
            self.assertFalse(meta["attach_mode_requested"])
            self.assertFalse(meta["attach_mode_allowed"])
            self.assertFalse(meta["remote_permission_verified"])

    def test_result_validation_success(self) -> None:
        result = bridge.validate_result_text(VALID_RESULT)
        self.assertTrue(result["ok"])
        self.assertEqual(result["fields"]["worker_id"], "scout-1")

    def test_result_validation_accepts_stop_condition_hit_yes(self) -> None:
        result = bridge.validate_result_text(result_with_stop_condition_hit("yes"))
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_stop_condition_hit_no(self) -> None:
        result = bridge.validate_result_text(result_with_stop_condition_hit("no"))
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_stop_condition_hit_data_missing(self) -> None:
        result = bridge.validate_result_text(result_with_stop_condition_hit("DATA_MISSING"))
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_fenced_worker_result(self) -> None:
        result = bridge.validate_result_text("```markdown\n" + VALID_RESULT + "```\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["fields"]["stop_condition_hit"], "no")

    def test_result_validation_accepts_spaced_fence_info_string(self) -> None:
        result = bridge.validate_result_text("``` markdown\n" + VALID_RESULT + "```\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["fields"]["stop_condition_hit"], "no")

    def test_result_validation_accepts_longer_fenced_worker_result(self) -> None:
        result = bridge.validate_result_text("````markdown\n" + VALID_RESULT + "````\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["fields"]["stop_condition_hit"], "no")

    def test_result_validation_ignores_field_like_lines_inside_internal_fences(self) -> None:
        invalid = VALID_RESULT.replace("stop_condition_hit: no\n", "")
        invalid = invalid.replace(
            "- The script exists and is scoped to control-plane tooling.",
            "- Example contract snippet:\n```markdown\nstop_condition_hit: no\n```",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("stop_condition_hit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_invalid_stop_condition_inside_fence(self) -> None:
        result = bridge.validate_result_text("```markdown\n" + result_with_stop_condition_hit("maybe") + "```\n")
        self.assertFalse(result["ok"])
        self.assertIn("stop_condition_hit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_ignores_following_stop_condition_impact_field(self) -> None:
        result = bridge.validate_result_text(VALID_RESULT + "stop_condition_impact: none\n")
        self.assertTrue(result["ok"])

    def test_result_validation_rejects_missing_evidence_paths(self) -> None:
        invalid = VALID_RESULT.replace("- scripts/opencode_worker_bridge.py", "- DATA_MISSING")
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("evidence_paths", {issue["field"] for issue in result["issues"]})

    def test_result_validation_accepts_terminal_claim_phrases_inside_evidence_paths(self) -> None:
        for path in (
            "docs/dev_flow/merge-ready-checklist.md",
            "docs/dev_flow/ready-for-merge.md",
            "reports/agent_jobs/approved-to-merge.txt",
        ):
            with self.subTest(path=path):
                advisory = VALID_RESULT.replace("- scripts/opencode_worker_bridge.py", f"- {path}")
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_accepts_quoted_terminal_claim_phrases_in_evidence(self) -> None:
        for sentence in (
            'The docs list "ready for merge" as a phrase workers must not use.',
            "The test fixture cites `merge-approved` as invalid worker language.",
        ):
            with self.subTest(sentence=sentence):
                advisory = VALID_RESULT.replace("- The script exists and is scoped to control-plane tooling.", f"- {sentence}")
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_rejects_missing_stop_condition_hit(self) -> None:
        invalid = VALID_RESULT.replace("stop_condition_hit: no\n", "")
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("stop_condition_hit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_invalid_stop_condition_hit_values(self) -> None:
        for value in ("maybe", "unknown", "n/a", "", "yes please"):
            with self.subTest(value=value):
                result = bridge.validate_result_text(result_with_stop_condition_hit(value))
                self.assertFalse(result["ok"])
                self.assertIn("stop_condition_hit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_final_authority_under_evidence_only(self) -> None:
        invalid = VALID_RESULT.replace("Codex review", "final decision: ready to merge")
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_merge_readiness_next_to_boundary(self) -> None:
        for sentence in (
            "Codex has final authority; this is ready for merge.",
            "Codex has final authority; this is ready-for-merge.",
            "Codex has final authority; merge approved.",
            "Codex has final authority; merge-approved.",
            "Codex has final authority; approved-to-merge.",
            "Codex has final authority; approved-for-merge.",
            "Codex has final authority; this is merge-ready.",
        ):
            with self.subTest(sentence=sentence):
                invalid = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_quoted_terminal_claims_in_decision_fields(self) -> None:
        for invalid in (
            VALID_RESULT.replace("recommended_next_action: Codex review", 'recommended_next_action: "ready for merge"'),
            VALID_RESULT.replace("summary: Checked the bridge script and tests.", 'summary: "ship it"'),
        ):
            with self.subTest(invalid=invalid):
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_accepts_negated_merge_readiness_report(self) -> None:
        for sentence in (
            "This is not ready for merge because validation failed.",
            "This is not currently ready for merge because validation failed.",
            "This should not be considered ready for merge because validation failed.",
            "Do not mark this ready for merge because validation failed.",
            "This should not be approved for merge because validation failed.",
            "This should not be merge-approved because validation failed.",
        ):
            with self.subTest(sentence=sentence):
                advisory = VALID_RESULT.replace(
                    "- The script exists and is scoped to control-plane tooling.",
                    f"- {sentence}",
                )
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_accepts_parent_final_decision_boundary(self) -> None:
        for sentence in (
            "Codex parent session owns the final decision; worker output is evidence only.",
            "The parent agent owns the final decision; worker output is evidence only.",
        ):
            with self.subTest(sentence=sentence):
                advisory = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_accepts_no_final_decisions_by_workers_boundary(self) -> None:
        advisory = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Bridge policy says evidence-only workers make no final decisions.",
        )
        result = bridge.validate_result_text(advisory)
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_parent_denies_worker_final_decisions(self) -> None:
        for sentence in (
            "Codex does not allow workers to make final decisions.",
            "Workers are not allowed to make final decisions.",
        ):
            with self.subTest(sentence=sentence):
                advisory = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_rejects_worker_final_decision_claim(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "The worker should make the final decision for this lane.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_authority_claim_with_codex_mention(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex should accept the worker's final decision for this lane.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_codex_reviewing_worker_final_decision(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex must review the worker's final decision before acting.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_final_decision_after_codex_mention(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex should accept that the worker makes the final decision for this lane.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_self_final_decision_after_codex_mention(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex should accept that I make the final decision for this lane.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_mixed_boundary_and_self_authority_line(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex must make the final decision; final authority is mine.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_comma_mixed_boundary_and_self_authority_line(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex must make the final decision, final authority is mine.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_joined_boundary_and_self_authority_line(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex must make the final decision and final authority is mine.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_negation_that_still_claims_authority(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Workers are not evidence only; final authority is mine.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_cannot_be_denied_authority(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Workers cannot be denied final authority.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_should_not_have_less_than_authority(self) -> None:
        for sentence in (
            "Workers should not have less than final authority.",
            "Workers are not allowed to have less than final authority.",
        ):
            with self.subTest(sentence=sentence):
                invalid = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_appositive_shared_authority_qualifier(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex, not workers, has final authority alongside workers.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_exception_qualified_worker_denial(self) -> None:
        for sentence in (
            "Workers have no final authority except me.",
            "Workers have no final authority unless I approve.",
            "Workers have no final authority apart from scout-1.",
            "Workers have no final authority other than scout-1.",
            "Workers have no final authority, but the model has final authority.",
            "Workers have no final authority, but OpenCode has final authority.",
            "Workers have no final authority, but the agent has final authority.",
        ):
            with self.subTest(sentence=sentence):
                invalid = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_denial_with_later_authority_claim(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "No final decisions are made by workers, final authority is elsewhere.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_negated_parent_final_authority_boundary(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "The final authority does not remain with Codex.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_parent_final_authority_outside_codex(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "The final authority should remain outside Codex.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_first_person_final_decision_boundary(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex is responsible for reviewing my final decision.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_alias_final_decision_boundary(self) -> None:
        for sentence in (
            "Codex is responsible for reviewing OpenCode's final decision.",
            "Codex is responsible for reviewing the model's final decision.",
            "Codex is responsible for reviewing the agent's final decision.",
            "Codex is responsible for reviewing the scout's final decision.",
            "Codex is responsible for reviewing the evidence scout's final decision.",
            "Codex is responsible for reviewing the delegate's final decision.",
            "Codex is responsible for reviewing the subagent's final decision.",
            "Codex is responsible for reviewing an external reviewer's final decision.",
            "Codex is responsible for reviewing the AI final decision.",
            "Codex is responsible for reviewing the assistant final decision.",
            "Codex is responsible for reviewing the external reviewer final decision.",
        ):
            with self.subTest(sentence=sentence):
                invalid = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_worker_id_final_decision_boundary(self) -> None:
        invalid = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex is responsible for reviewing scout-1's final decision.",
        )
        result = bridge.validate_result_text(invalid)
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_rejects_trailing_worker_authority_qualifier(self) -> None:
        for sentence in (
            "Codex is responsible for reviewing this final decision of mine.",
            "Codex has final authority alongside workers.",
            "Codex has final authority with the delegate.",
            "Codex has final authority alongside the subagent.",
            "Codex has final authority except for merge readiness.",
            "Codex has final authority unless merge readiness is involved.",
            "Codex has final authority apart from merge readiness.",
            "Codex has final authority other than merge readiness.",
            "Codex has final authority and the delegate has final authority.",
            "Codex has final authority, and the subagent has final authority.",
            "If I approve, Codex has final authority.",
            "Once the worker approves, Codex has final authority.",
        ):
            with self.subTest(sentence=sentence):
                invalid = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(invalid)
                self.assertFalse(result["ok"])
                self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_result_validation_accepts_final_decision_remains_with_codex(self) -> None:
        advisory = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "The final decision remains with Codex; worker output is evidence only.",
        )
        result = bridge.validate_result_text(advisory)
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_codex_must_make_final_decision_boundary(self) -> None:
        advisory = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex must make the final decision; worker output is evidence only.",
        )
        result = bridge.validate_result_text(advisory)
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_codex_is_final_authority_boundary(self) -> None:
        for sentence in (
            "Codex remains final authority; worker output is evidence only.",
            "Codex is final authority; worker output is evidence only.",
            "Codex is the final authority; worker output is evidence only.",
            "Codex has final authority; worker output is evidence only.",
            "Codex has the final authority; worker output is evidence only.",
            "Codex has sole final authority; worker output is evidence only.",
            "Codex has exclusive final authority; worker output is evidence only.",
            "Codex is the sole final authority; worker output is evidence only.",
            "Codex has final authority, not workers.",
        ):
            with self.subTest(sentence=sentence):
                advisory = VALID_RESULT.replace("Codex still needs to review the result.", sentence)
                result = bridge.validate_result_text(advisory)
                self.assertTrue(result["ok"])

    def test_result_validation_accepts_codex_not_workers_final_authority_boundary(self) -> None:
        advisory = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "Codex, not workers, has final authority.",
        )
        result = bridge.validate_result_text(advisory)
        self.assertTrue(result["ok"])

    def test_result_validation_accepts_no_final_decision_by_workers_boundary(self) -> None:
        advisory = VALID_RESULT.replace(
            "Codex still needs to review the result.",
            "No final decisions are made by evidence-only workers.",
        )
        result = bridge.validate_result_text(advisory)
        self.assertTrue(result["ok"])

    def test_requested_decision_limit_mismatch_rejects_result(self) -> None:
        invalid = VALID_RESULT.replace("decision_limit: evidence_only", "decision_limit: recommendation_only")
        result = bridge.validate_result_text(invalid, expected_decision_limit="evidence_only")
        self.assertFalse(result["ok"])
        self.assertIn("decision_limit", {issue["field"] for issue in result["issues"]})

    def test_worker_supplied_decision_limit_cannot_bypass_evidence_only_metadata_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "WORKER_RESULT.md"
            result_path.write_text(
                VALID_RESULT.replace("decision_limit: evidence_only", "decision_limit: recommendation_only").replace(
                    "Codex review", "ready to merge"
                ),
                encoding="utf-8",
            )
            (Path(tmp) / "WORKER_META.json").write_text(
                json.dumps({"decision_limit": "evidence_only"}),
                encoding="utf-8",
            )
            result = bridge.validate_result_file(result_path)
        self.assertFalse(result["ok"])
        issue_fields = {issue["field"] for issue in result["issues"]}
        self.assertIn("decision_limit", issue_fields)
        self.assertIn("permission_enforcement", issue_fields)

    def test_result_file_validation_rejects_missing_permission_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "WORKER_RESULT.md"
            result_path.write_text(VALID_RESULT, encoding="utf-8")
            result = bridge.validate_result_file(result_path)
        self.assertFalse(result["ok"])
        self.assertIn("permission_enforcement", {issue["field"] for issue in result["issues"]})

    def test_result_file_validation_rejects_unverified_permission_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "WORKER_RESULT.md"
            result_path.write_text(VALID_RESULT, encoding="utf-8")
            (Path(tmp) / "WORKER_META.json").write_text(
                json.dumps({"permission_enforcement": {"profile": "readonly", "verified": False}}),
                encoding="utf-8",
            )
            result = bridge.validate_result_file(result_path)
        self.assertFalse(result["ok"])
        self.assertIn("permission_enforcement", {issue["field"] for issue in result["issues"]})

    def test_result_file_validation_uses_trusted_worker_id_for_authority_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worker_dir = Path(tmp) / "job" / "scout-1"
            worker_dir.mkdir(parents=True)
            result_path = worker_dir / "WORKER_RESULT.md"
            result_path.write_text(
                VALID_RESULT.replace("worker_id: scout-1", "worker_id: other-worker").replace(
                    "Codex still needs to review the result.",
                    "Codex is responsible for reviewing scout-1's final decision.",
                ),
                encoding="utf-8",
            )
            (worker_dir / "WORKER_META.json").write_text(
                json.dumps(
                    {
                        "worker_id": "scout-1",
                        "decision_limit": "evidence_only",
                        "permission_enforcement": {
                            "profile": "readonly",
                            "verified": True,
                            "method": "OPENCODE_CONFIG_CONTENT",
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = bridge.validate_result_file(result_path)
        self.assertFalse(result["ok"])
        issue_fields = {issue["field"] for issue in result["issues"]}
        self.assertIn("worker_id", issue_fields)
        self.assertIn("decision_limit", issue_fields)

    def test_generated_readonly_permission_config_denies_edit(self) -> None:
        config = bridge.build_readonly_opencode_config("evidence-scout")
        self.assertEqual(config["permission"]["edit"], "deny")
        self.assertEqual(config["agent"]["evidence-scout"]["permission"]["edit"], "deny")
        self.assertFalse(bridge.validate_readonly_permission_config(config, "evidence-scout"))

    def test_generated_readonly_permission_config_denies_dangerous_bash(self) -> None:
        bash = bridge.build_readonly_opencode_config("evidence-scout")["permission"]["bash"]
        self.assertEqual(bash["*"], "deny")
        self.assertEqual(bash["git commit*"], "deny")
        self.assertEqual(bash["git push*"], "deny")
        self.assertEqual(bash["git reset*"], "deny")
        self.assertEqual(bash["git clean*"], "deny")
        self.assertEqual(bash["rm *"], "deny")
        self.assertEqual(bash["cat *"], "deny")
        self.assertEqual(bash["rg *"], "deny")
        self.assertEqual(bash["grep *"], "deny")
        self.assertEqual(bash["git status"], "allow")
        self.assertEqual(bash["git diff --stat"], "allow")

    def test_evidence_only_permission_enforcement_sets_inline_config_env(self) -> None:
        with mock.patch.object(
            bridge,
            "verify_readonly_permission_enforcement",
            return_value={"ok": True, "method": "opencode_config_content_debug_config"},
        ):
            meta, env = bridge.build_permission_enforcement(
                decision_limit="evidence_only",
                permission_profile="readonly",
                agent="evidence-scout",
                opencode_path="/usr/bin/opencode",
                timeout_seconds=5,
            )
        self.assertEqual(meta["profile"], "readonly")
        self.assertEqual(meta["method"], "OPENCODE_CONFIG_CONTENT")
        self.assertTrue(meta["verified"])
        self.assertIn("OPENCODE_CONFIG_CONTENT", env)
        injected = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(injected["permission"]["edit"], "deny")

    def test_permission_verification_uses_pure_debug_config(self) -> None:
        config = bridge.build_readonly_opencode_config("evidence-scout")
        with mock.patch.object(
            bridge,
            "run_command",
            return_value=bridge.CommandResult(
                command=[],
                exit_code=0,
                stdout=json.dumps(config),
                stderr="",
                timed_out=False,
            ),
        ) as run_command:
            result = bridge.verify_readonly_permission_enforcement(
                "/usr/bin/opencode",
                agent="evidence-scout",
                config_content=json.dumps(config),
                timeout_seconds=5,
            )
        self.assertTrue(result["ok"])
        self.assertEqual(run_command.call_args.args[0], ["/usr/bin/opencode", "debug", "config", "--pure"])
        self.assertIn("OPENCODE_CONFIG_CONTENT", run_command.call_args.kwargs["env"])

    def test_evidence_only_fails_closed_when_permission_enforcement_unproven(self) -> None:
        with mock.patch.object(
            bridge,
            "verify_readonly_permission_enforcement",
            return_value={"ok": False, "reason": "debug_config_failed"},
        ):
            with self.assertRaises(bridge.BridgeError):
                bridge.build_permission_enforcement(
                    decision_limit="evidence_only",
                    permission_profile="readonly",
                    agent="evidence-scout",
                    opencode_path="/usr/bin/opencode",
                    timeout_seconds=5,
                )

    def test_evidence_only_rejects_non_readonly_permission_profile(self) -> None:
        with self.assertRaises(bridge.BridgeError):
            bridge.build_permission_enforcement(
                decision_limit="evidence_only",
                permission_profile="none",
                agent="evidence-scout",
                opencode_path="/usr/bin/opencode",
                timeout_seconds=5,
            )

    def test_evidence_only_fails_closed_when_opencode_server_url_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_file = root / "task.md"
            task_file.write_text("Inspect scripts/opencode_worker_bridge.py only.\n", encoding="utf-8")
            opencode = root / "opencode"
            opencode.write_text("#!/usr/bin/env python3\nraise SystemExit('opencode should not run')\n", encoding="utf-8")
            opencode.chmod(0o755)

            with mock.patch.dict(bridge.os.environ, {"OPENCODE_SERVER_URL": "http://127.0.0.1:4096"}, clear=False):
                with mock.patch("builtins.print"):
                    rc = bridge.main(
                        [
                            "run",
                            "--job-dir",
                            str(root / "job"),
                            "--worker-id",
                            "scout-1",
                            "--agent",
                            "evidence-scout",
                            "--model",
                            "deepseek/deepseek-chat",
                            "--task-file",
                            str(task_file),
                            "--workdir",
                            str(root),
                            "--decision-limit",
                            "evidence_only",
                            "--timeout-seconds",
                            "5",
                            "--opencode-command",
                            str(opencode),
                        ]
                    )

            meta = json.loads((root / "job" / "scout-1" / "WORKER_META.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 2)
        self.assertEqual(meta["failure"], "remote_permission_enforcement_failed")
        self.assertTrue(meta["attach_mode_requested"])
        self.assertFalse(meta["attach_mode_allowed"])
        self.assertFalse(meta["remote_permission_verified"])

    def test_non_evidence_attach_policy_is_not_blocked(self) -> None:
        server_url, meta = bridge.resolve_attach_mode(
            decision_limit="recommendation_only",
            server_url="http://127.0.0.1:4096",
        )
        self.assertEqual(server_url, "http://127.0.0.1:4096")
        self.assertTrue(meta["attach_mode_requested"])
        self.assertTrue(meta["attach_mode_allowed"])
        self.assertFalse(meta["remote_permission_verified"])

    def test_ledger_entry_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worker_dir = Path(tmp) / "job" / "scout-1"
            worker_dir.mkdir(parents=True)
            (worker_dir / "WORKER_META.json").write_text(
                json.dumps(
                    {
                        "worker_id": "scout-1",
                        "agent": "evidence-scout",
                        "model": "deepseek/deepseek-chat",
                        "task_tier": "small",
                        "decision_limit": "evidence_only",
                        "workdir": "/tmp/work",
                        "result_path": str(worker_dir / "WORKER_RESULT.md"),
                        "status": "completed",
                    }
                ),
                encoding="utf-8",
            )
            parser = bridge.build_parser()
            args = parser.parse_args(["ledger-entry", "--job-dir", str(Path(tmp) / "job"), "--worker-id", "scout-1"])
            with mock.patch("builtins.print") as printed:
                rc = bridge.command_ledger_entry(args)
            self.assertEqual(rc, 0)
            payload = json.loads(printed.call_args.args[0])
            self.assertEqual(payload["runtime"], "opencode")
            self.assertEqual(payload["worker_id"], "scout-1")
            self.assertIn("session_id", payload)
            self.assertIn("agent_task_ledger_available", payload)

    def test_denylist_rejects_secret_looking_paths(self) -> None:
        self.assertTrue(bridge.is_denied_path(".env"))
        self.assertTrue(bridge.is_denied_path("config/credentials.json"))
        self.assertTrue(bridge.is_denied_path("data/raw/company.sqlite"))
        denied = bridge.find_denied_references("Please inspect config/.env and data/raw/company.sqlite")
        self.assertIn("config/.env", denied)

    def test_command_construction_does_not_include_dangerous_permission_flags(self) -> None:
        command = bridge.build_opencode_command(
            "/usr/bin/opencode",
            agent="evidence-scout",
            model="deepseek/deepseek-chat",
            workdir=Path("/tmp/work"),
            prompt="hello",
        )
        self.assertEqual(command[:2], ["/usr/bin/opencode", "run"])
        self.assertIn("--pure", command)
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertNotIn("--permission-mode", command)
        self.assertIn("--agent", command)
        self.assertIn("--model", command)


if __name__ == "__main__":
    unittest.main()
