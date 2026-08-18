#!/usr/bin/env python3
"""Validate Tenn review-board BOARD_DECISION.json artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ALLOWED_DECISIONS = {"proceed", "revise_plan", "block", "ask_owner", "supersede", "park"}
ALLOWED_EVIDENCE_GRADES = {"VERIFIED", "USER_REPORTED", "INFERRED", "UNKNOWN", "CONFLICT", "DATA_MISSING"}
ALLOWED_TASK_TIERS = {"small", "medium", "large", "critical"}
ALLOWED_FUNCTIONALITY_STATUSES = {"WORKING", "PARTIAL", "BROKEN", "DATA_MISSING", "not_applicable"}
SCHEMA_VERSION_V1 = "tenn_review_board_decision_v1"
SCHEMA_VERSION_V2 = "tenn_review_board_decision_v2"
ALLOWED_SCHEMA_VERSIONS = {SCHEMA_VERSION_V1, SCHEMA_VERSION_V2}
RUN_OUTCOME_STATUSES = {
    "ADVANCED",
    "REUSED_COMPLETE",
    "ACTIVE_DUPLICATE",
    "WAITING_ON_AUTHORIZATION",
    "DATA_MISSING",
    "EVIDENCE_CONFLICT",
    "BLOCKED_NO_NEW_INPUT",
    "LOOP_GUARD_STOP",
}
TERMINAL_NO_PROGRESS_STATUSES = RUN_OUTCOME_STATUSES - {"ADVANCED"}

REQUIRED_FIELDS = {
    "schema_version": str,
    "decision": str,
    "evidence_grade": str,
    "reason": str,
    "task_tier": str,
    "recommended_model": str,
    "actual_model": str,
    "why_this_model": str,
    "worker_model_allowed": str,
    "worker_decision_limit": str,
    "escalation_needed": str,
    "ledger_sources_checked": list,
    "duplicate_work_classification": str,
    "matching_candidates": list,
    "duplicate_work_decision": str,
    "minority_objection": str,
    "minority_objection_checks": str,
    "counter_lineage_required": bool,
    "functionality_proof_required": bool,
    "functionality_proof_status": str,
    "functionality_proof_remaining_blocker": str,
    "zoom_out_required": bool,
    "root_problem_check": str,
    "overfitting_risk": str,
    "report_only_loop_risk": str,
    "broad_system_progress": str,
    "class_based_approach_better": str,
    "production_readiness_value_next_action": str,
    "financial_extraction_breadth_provenance_confidence_regression_check": str,
    "required_changes": list,
    "owner_approval_needed": list,
    "next_goal": str,
}

LARGE_CRITICAL_FIELDS = {
    "final_decision_authority": str,
    "lower_tier_decision_insufficient": str,
}

V2_REQUIRED_FIELDS = {
    "run_outcome_status": str,
    "target_transition": str,
    "next_goal_permitted": bool,
    "next_goal_target_transition": str,
}


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


@dataclass(frozen=True)
class BoardDecisionValidationResult:
    ok: bool
    path: str
    template_mode: bool
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["issues"] = [asdict(issue) for issue in self.issues]
        return payload


def _is_missing_text(value: str) -> bool:
    stripped = value.strip()
    return not stripped or stripped in {"TODO", "TBD", "DATA_MISSING"} or "<" in stripped or ">" in stripped


def _require_fields(payload: Mapping[str, Any], fields: Mapping[str, type], issues: list[ValidationIssue]) -> None:
    for field, expected_type in fields.items():
        if field not in payload:
            issues.append(ValidationIssue(field, "missing required field"))
            continue
        if not isinstance(payload[field], expected_type):
            issues.append(ValidationIssue(field, f"must be {expected_type.__name__}"))


def _require_text(payload: Mapping[str, Any], field: str, issues: list[ValidationIssue]) -> None:
    value = payload.get(field)
    if isinstance(value, str) and _is_missing_text(value):
        issues.append(ValidationIssue(field, "must be concrete non-placeholder text"))


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_condition(value: Any) -> bool:
    if isinstance(value, str):
        return not _is_missing_text(value)
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and not _is_missing_text(item) for item in value)
    )


def validate_board_decision_payload(
    payload: Mapping[str, Any],
    *,
    path: str = "<memory>",
    template_mode: bool = False,
) -> BoardDecisionValidationResult:
    issues: list[ValidationIssue] = []
    _require_fields(payload, REQUIRED_FIELDS, issues)

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, str) and schema_version not in ALLOWED_SCHEMA_VERSIONS:
        issues.append(ValidationIssue("schema_version", f"must be one of {sorted(ALLOWED_SCHEMA_VERSIONS)}"))

    is_v2 = schema_version == SCHEMA_VERSION_V2
    if is_v2:
        _require_fields(payload, V2_REQUIRED_FIELDS, issues)
        if "resume_only_if" not in payload:
            issues.append(ValidationIssue("resume_only_if", "missing required field"))
        elif not isinstance(payload.get("resume_only_if"), (str, list)):
            issues.append(ValidationIssue("resume_only_if", "must be str or list"))
        run_outcome_status = payload.get("run_outcome_status")
        if isinstance(run_outcome_status, str) and run_outcome_status not in RUN_OUTCOME_STATUSES:
            issues.append(
                ValidationIssue("run_outcome_status", f"must be one of {sorted(RUN_OUTCOME_STATUSES)}")
            )

    decision = payload.get("decision")
    if isinstance(decision, str) and decision not in ALLOWED_DECISIONS:
        issues.append(ValidationIssue("decision", f"must be one of {sorted(ALLOWED_DECISIONS)}"))

    evidence_grade = payload.get("evidence_grade")
    if isinstance(evidence_grade, str) and evidence_grade not in ALLOWED_EVIDENCE_GRADES:
        issues.append(ValidationIssue("evidence_grade", f"must be one of {sorted(ALLOWED_EVIDENCE_GRADES)}"))

    task_tier = payload.get("task_tier")
    if isinstance(task_tier, str) and task_tier not in ALLOWED_TASK_TIERS:
        issues.append(ValidationIssue("task_tier", f"must be one of {sorted(ALLOWED_TASK_TIERS)}"))

    functionality_status = payload.get("functionality_proof_status")
    if isinstance(functionality_status, str) and functionality_status not in ALLOWED_FUNCTIONALITY_STATUSES:
        issues.append(
            ValidationIssue("functionality_proof_status", f"must be one of {sorted(ALLOWED_FUNCTIONALITY_STATUSES)}")
        )

    if template_mode:
        return BoardDecisionValidationResult(ok=not issues, path=path, template_mode=True, issues=issues)

    for field in (
        "reason",
        "why_this_model",
        "worker_model_allowed",
        "worker_decision_limit",
        "escalation_needed",
        "duplicate_work_classification",
        "duplicate_work_decision",
        "minority_objection",
    ):
        _require_text(payload, field, issues)

    if not is_v2:
        _require_text(payload, "next_goal", issues)
    else:
        _require_text(payload, "target_transition", issues)
        run_outcome_status = payload.get("run_outcome_status")
        next_goal_permitted = payload.get("next_goal_permitted")
        next_goal = payload.get("next_goal")
        next_goal_target = payload.get("next_goal_target_transition")

        if run_outcome_status in TERMINAL_NO_PROGRESS_STATUSES:
            if next_goal_permitted is not False:
                issues.append(
                    ValidationIssue(
                        "next_goal_permitted",
                        f"{run_outcome_status} must set next_goal_permitted to false",
                    )
                )
            if _has_text(next_goal):
                issues.append(
                    ValidationIssue("next_goal", f"{run_outcome_status} must not create a continuation goal")
                )
            if _has_text(next_goal_target):
                issues.append(
                    ValidationIssue(
                        "next_goal_target_transition",
                        f"{run_outcome_status} must not name a continuation transition",
                    )
                )
            if not _has_condition(payload.get("resume_only_if")):
                issues.append(
                    ValidationIssue(
                        "resume_only_if",
                        f"{run_outcome_status} requires an exact non-placeholder reopen condition",
                    )
                )
        elif run_outcome_status == "ADVANCED":
            if next_goal_permitted is True:
                _require_text(payload, "next_goal", issues)
                _require_text(payload, "next_goal_target_transition", issues)
                if (
                    _has_text(next_goal_target)
                    and _has_text(payload.get("target_transition"))
                    and str(next_goal_target).strip() == str(payload["target_transition"]).strip()
                ):
                    issues.append(
                        ValidationIssue(
                            "next_goal_target_transition",
                            "must be materially different from target_transition",
                        )
                    )
            elif next_goal_permitted is False:
                if _has_text(next_goal):
                    issues.append(
                        ValidationIssue("next_goal", "next_goal_permitted=false requires an empty next_goal")
                    )
                if _has_text(next_goal_target):
                    issues.append(
                        ValidationIssue(
                            "next_goal_target_transition",
                            "next_goal_permitted=false requires an empty next_goal_target_transition",
                        )
                    )

    ledger_sources = payload.get("ledger_sources_checked")
    if isinstance(ledger_sources, list) and not ledger_sources:
        issues.append(ValidationIssue("ledger_sources_checked", "must record at least one checked source or DATA_MISSING"))

    minority_objection = payload.get("minority_objection")
    minority_checks = payload.get("minority_objection_checks")
    if minority_objection == "none_found" and isinstance(minority_checks, str) and _is_missing_text(minority_checks):
        issues.append(
            ValidationIssue("minority_objection_checks", "must explain checks performed when no objection is credible")
        )

    if payload.get("functionality_proof_required") is True:
        if functionality_status == "not_applicable":
            issues.append(
                ValidationIssue(
                    "functionality_proof_status",
                    "cannot be not_applicable when functionality proof is required",
                )
            )
        _require_text(payload, "functionality_proof_remaining_blocker", issues)

    if payload.get("zoom_out_required") is True:
        for field in (
            "root_problem_check",
            "overfitting_risk",
            "report_only_loop_risk",
            "broad_system_progress",
            "class_based_approach_better",
            "production_readiness_value_next_action",
        ):
            _require_text(payload, field, issues)

    if task_tier in {"large", "critical"}:
        _require_fields(payload, LARGE_CRITICAL_FIELDS, issues)
        for field in LARGE_CRITICAL_FIELDS:
            _require_text(payload, field, issues)

    return BoardDecisionValidationResult(ok=not issues, path=path, template_mode=False, issues=issues)


def validate_board_decision_file(path: Path, *, template_mode: bool = False) -> BoardDecisionValidationResult:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return BoardDecisionValidationResult(
            ok=False,
            path=str(path),
            template_mode=template_mode,
            issues=[ValidationIssue("path", "file not found")],
        )
    except json.JSONDecodeError as exc:
        return BoardDecisionValidationResult(
            ok=False,
            path=str(path),
            template_mode=template_mode,
            issues=[ValidationIssue("json", f"invalid JSON: {exc}")],
        )

    if not isinstance(loaded, dict):
        return BoardDecisionValidationResult(
            ok=False,
            path=str(path),
            template_mode=template_mode,
            issues=[ValidationIssue("json", "top-level value must be an object")],
        )

    return validate_board_decision_payload(loaded, path=str(path), template_mode=template_mode)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to BOARD_DECISION.json")
    parser.add_argument(
        "--template",
        action="store_true",
        help="validate template structure without requiring concrete decision text",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_board_decision_file(args.path, template_mode=args.template)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
