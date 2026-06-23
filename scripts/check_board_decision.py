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


def validate_board_decision_payload(
    payload: Mapping[str, Any],
    *,
    path: str = "<memory>",
    template_mode: bool = False,
) -> BoardDecisionValidationResult:
    issues: list[ValidationIssue] = []
    _require_fields(payload, REQUIRED_FIELDS, issues)

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
        "next_goal",
    ):
        _require_text(payload, field, issues)

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
