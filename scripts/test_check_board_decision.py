from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import check_board_decision


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_board_decision.py"


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "tenn_review_board_decision_v1",
        "decision": "revise_plan",
        "evidence_grade": "VERIFIED",
        "reason": "Use one narrow control-plane hardening slice.",
        "task_tier": "large",
        "recommended_model": "high_reasoning",
        "actual_model": "GPT-5 Codex",
        "why_this_model": "The decision crosses repo policy, templates, and validation gates.",
        "worker_model_allowed": "read_only_evidence_scouts_only",
        "worker_decision_limit": "evidence_only",
        "escalation_needed": "Owner approval is needed for host-global mutation.",
        "final_decision_authority": "Codex chair for the report; Orlando for owner-boundary actions.",
        "lower_tier_decision_insufficient": "A simple grep check cannot evaluate the cross-surface workflow.",
        "ledger_sources_checked": [{"kind": "live", "path": "DATA_MISSING", "status": "DATA_MISSING"}],
        "duplicate_work_classification": "NO_MATCHING_ACTIVE_WORK_FOUND",
        "matching_candidates": [],
        "duplicate_work_decision": "proceed_as_new_work",
        "minority_objection": "none_found",
        "minority_objection_checks": "Checked templates, skills, and status docs for credible objections.",
        "counter_lineage_required": False,
        "functionality_proof_required": False,
        "functionality_proof_status": "not_applicable",
        "functionality_proof_remaining_blocker": "none",
        "zoom_out_required": True,
        "root_problem_check": "The root problem is incomplete machine validation.",
        "overfitting_risk": "Avoid only editing prose.",
        "report_only_loop_risk": "The next action is an implementation slice.",
        "broad_system_progress": "A validator improves future board reliability.",
        "class_based_approach_better": "Workflow-class validation is better than one-off board cleanup.",
        "production_readiness_value_next_action": "Add the validator and focused tests.",
        "financial_extraction_breadth_provenance_confidence_regression_check": "not_applicable",
        "required_changes": ["Add validator"],
        "owner_approval_needed": [],
        "next_goal": "Run tenn-fix on the validator task card.",
    }
    payload.update(overrides)
    return payload


def valid_v2_payload(**overrides: object) -> dict[str, object]:
    payload = valid_payload(
        schema_version="tenn_review_board_decision_v2",
        run_outcome_status="ADVANCED",
        target_transition="validated_v2_control",
        next_goal_permitted=True,
        next_goal_target_transition="pilot_v2_control",
        resume_only_if="",
        next_goal="Pilot the validated control on a newly authorized repository.",
    )
    payload.update(overrides)
    return payload


def issue_fields(result: check_board_decision.BoardDecisionValidationResult) -> set[str]:
    return {issue.field for issue in result.issues}


def test_valid_large_zoom_out_decision_passes() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_payload())

    assert result.ok
    assert result.issues == []


def test_v1_decision_still_requires_next_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_payload(next_goal=""))

    assert not result.ok
    assert "next_goal" in issue_fields(result)


def test_v2_terminal_outcome_accepts_reopen_condition_without_next_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(
            run_outcome_status="LOOP_GUARD_STOP",
            next_goal_permitted=False,
            next_goal_target_transition="",
            resume_only_if="The dataset version, evidence hash, or hypothesis ID changes.",
            next_goal="",
        )
    )

    assert result.ok
    assert result.issues == []


def test_v2_terminal_outcome_accepts_list_reopen_conditions() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(
            run_outcome_status="LOOP_GUARD_STOP",
            next_goal_permitted=False,
            next_goal_target_transition="",
            resume_only_if=[
                "The dataset version changes.",
                "The evidence hash changes.",
            ],
            next_goal="",
        )
    )

    assert result.ok
    assert result.issues == []


def test_v2_terminal_outcome_rejects_continuation_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(
            run_outcome_status="DATA_MISSING",
            next_goal_permitted=False,
            next_goal_target_transition="collect_the_same_report",
            resume_only_if="The named prospective evidence becomes available.",
        )
    )

    assert not result.ok
    assert "next_goal" in issue_fields(result)
    assert "next_goal_target_transition" in issue_fields(result)


def test_v2_terminal_outcome_requires_exact_resume_condition() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(
            run_outcome_status="BLOCKED_NO_NEW_INPUT",
            next_goal_permitted=False,
            next_goal_target_transition="",
            resume_only_if="DATA_MISSING",
            next_goal="",
        )
    )

    assert not result.ok
    assert "resume_only_if" in issue_fields(result)


def test_v2_advanced_outcome_permits_materially_different_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_v2_payload())

    assert result.ok
    assert result.issues == []


def test_v2_advanced_outcome_rejects_same_transition_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(next_goal_target_transition="validated_v2_control")
    )

    assert not result.ok
    assert "next_goal_target_transition" in issue_fields(result)


def test_v2_advanced_outcome_can_finish_without_next_goal() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_v2_payload(
            next_goal_permitted=False,
            next_goal_target_transition="",
            next_goal="",
        )
    )

    assert result.ok
    assert result.issues == []


def test_invalid_decision_value_fails() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_payload(decision="approve"))

    assert not result.ok
    assert "decision" in issue_fields(result)


def test_missing_required_field_fails() -> None:
    payload = valid_payload()
    del payload["duplicate_work_decision"]

    result = check_board_decision.validate_board_decision_payload(payload)

    assert not result.ok
    assert "duplicate_work_decision" in issue_fields(result)


def test_none_found_minority_objection_requires_checks() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_payload(minority_objection_checks=""))

    assert not result.ok
    assert "minority_objection_checks" in issue_fields(result)


def test_runtime_proof_required_rejects_not_applicable() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_payload(
            functionality_proof_required=True,
            functionality_proof_status="not_applicable",
            functionality_proof_remaining_blocker="",
        )
    )

    assert not result.ok
    assert "functionality_proof_status" in issue_fields(result)
    assert "functionality_proof_remaining_blocker" in issue_fields(result)


def test_zoom_out_required_rejects_missing_root_problem() -> None:
    result = check_board_decision.validate_board_decision_payload(valid_payload(root_problem_check=""))

    assert not result.ok
    assert "root_problem_check" in issue_fields(result)


def test_large_decision_requires_final_authority_fields() -> None:
    payload = valid_payload()
    del payload["final_decision_authority"]

    result = check_board_decision.validate_board_decision_payload(payload)

    assert not result.ok
    assert "final_decision_authority" in issue_fields(result)


def test_template_mode_allows_placeholders_but_checks_structure() -> None:
    result = check_board_decision.validate_board_decision_payload(
        valid_payload(
            reason="",
            minority_objection="none_found",
            minority_objection_checks="",
            ledger_sources_checked=[],
            root_problem_check="",
            next_goal="",
        ),
        template_mode=True,
    )

    assert result.ok


def test_cli_outputs_json_and_nonzero_for_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "BOARD_DECISION.json"
    path.write_text(json.dumps(valid_payload(decision="approve")), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["ok"] is False
    assert payload["issues"]
    assert completed.stderr == ""


def test_cli_template_mode_accepts_template_placeholders(tmp_path: Path) -> None:
    path = tmp_path / "BOARD_DECISION.json"
    path.write_text(json.dumps(valid_payload(reason="", next_goal="")), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--template"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["template_mode"] is True
