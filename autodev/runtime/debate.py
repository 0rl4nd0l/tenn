"""Deterministic debate layer with proposer, skeptic, and auditor roles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DebateContext:
    phase: str
    task_id: str
    task_slug: str
    task_description: str
    milestone_dod: str
    branch_name: str
    repo_root: Path
    allowed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    changed_files: list[str]
    changed_lines: int
    changed_file_count: int
    max_changed_lines_per_attempt: int
    max_changed_files_per_attempt: int
    allow_network: bool
    strictness: str
    require_3_failure_modes: bool
    gate_names: list[str]


@dataclass(frozen=True)
class DebateOutput:
    role: str
    passed: bool
    veto: bool
    reasons: list[str]
    required_changes: list[str]
    risk_level: str
    stop_retries: bool
    plan_summary: str = ""
    failure_modes: list[str] | None = None


def _any_outside_allowed(changed_files: list[str], allowed_paths: tuple[str, ...]) -> list[str]:
    outside: list[str] = []
    for path in changed_files:
        if not any(path == prefix or path.startswith(prefix) for prefix in allowed_paths):
            outside.append(path)
    return outside


def _protected_hits(changed_files: list[str], protected_paths: tuple[str, ...]) -> list[str]:
    return [path for path in changed_files if any(path == pref or path.startswith(pref) for pref in protected_paths)]


def _proposer(context: DebateContext) -> DebateOutput:
    candidate_files = context.changed_files if context.changed_files else ["autodev/worker_outputs/<task_slug>.md"]
    risks = [
        "Gate setup can fail in constrained environments.",
        "Task scope could drift beyond allowed paths.",
        "Regression guard may block completion due to missing baseline flags.",
    ]
    summary = (
        f"Goal: {context.task_description}. "
        f"Minimal changes in {', '.join(candidate_files[:3])}. "
        f"Verification via gates: {', '.join(context.gate_names)}."
    )
    return DebateOutput(
        role="proposer",
        passed=True,
        veto=False,
        reasons=["Plan is incremental and scoped."],
        required_changes=[],
        risk_level="medium",
        stop_retries=False,
        plan_summary=summary,
        failure_modes=risks,
    )


def _skeptic(context: DebateContext) -> DebateOutput:
    reasons: list[str] = []
    required: list[str] = []
    failure_modes = [
        "Proposed changes may violate path restrictions.",
        "Diff budget may exceed configured limits.",
        "Safety controls could be weakened by runtime edits.",
    ]
    if context.require_3_failure_modes and len(failure_modes) < 3:
        failure_modes.extend(["Missing third failure mode."])

    if not context.branch_name.startswith("agent/"):
        reasons.append("Branch naming invariant violated (must start with agent/).")
        required.append("Use agent/YYYY-MM-DD/<task_slug> branch.")
    if context.allow_network:
        reasons.append("Default networking enabled; invariant requires no-network by default.")
        required.append("Disable default networking.")
    outside = _any_outside_allowed(context.changed_files, context.allowed_paths)
    if outside:
        reasons.append(f"Changed paths outside allowed scope: {', '.join(outside)}")
        required.append("Restrict edits to allowed paths only.")
    if context.changed_lines > context.max_changed_lines_per_attempt:
        reasons.append(
            f"Line budget exceeded ({context.changed_lines} > {context.max_changed_lines_per_attempt})."
        )
        required.append("Reduce changed lines to stay within budget.")
    if context.changed_file_count > context.max_changed_files_per_attempt:
        reasons.append(
            f"File budget exceeded ({context.changed_file_count} > {context.max_changed_files_per_attempt})."
        )
        required.append("Reduce number of changed files.")
    if any(path.endswith("autodev/runtime/gates.py") for path in context.changed_files):
        reasons.append("Gate logic was modified; skeptic treats this as high-risk without explicit task permission.")
        required.append("Avoid modifying deterministic gate logic unless explicitly requested.")
    if any(path.endswith("autodev/runtime/regression_guard.py") for path in context.changed_files):
        reasons.append("Regression guard logic was modified; possible metric gaming risk.")
        required.append("Avoid modifying regression guard without explicit permission.")
    if any(path.endswith("autodev/runtime/sandbox_runner.py") for path in context.changed_files):
        reasons.append("Sandbox runner was modified; potential safety control weakening.")
        required.append("Avoid weakening sandbox controls.")
    if any(path.endswith("autodev/evals/run_evals.py") for path in context.changed_files):
        reasons.append("Eval harness changed; risk of metric manipulation.")
        required.append("Do not modify eval harness unless task explicitly allows.")

    veto = bool(reasons)
    return DebateOutput(
        role="skeptic",
        passed=not veto,
        veto=veto,
        reasons=reasons or ["No skeptic objections for this phase."],
        required_changes=required,
        risk_level="high" if veto else "low",
        stop_retries=veto,
        plan_summary="Adversarial review complete.",
        failure_modes=failure_modes,
    )


def _auditor(context: DebateContext) -> DebateOutput:
    reasons: list[str] = []
    required: list[str] = []
    protected = _protected_hits(context.changed_files, context.protected_paths)
    if protected:
        reasons.append(f"Protected path changes detected: {', '.join(protected)}")
        required.append("Revert protected path edits.")

    suspicious = [
        path
        for path in context.changed_files
        if any(token in path.lower() for token in ("secret", "token", "credential", "password", "key"))
    ]
    if suspicious:
        reasons.append(f"Potential secrets-related paths touched: {', '.join(suspicious)}")
        required.append("Remove secrets-related modifications.")

    if any(path.endswith(".github/workflows/autodev-ci.yml") for path in context.changed_files):
        reasons.append("CI workflow changes detected without explicit task permission.")
        required.append("Avoid CI changes unless task explicitly allows.")

    veto = bool(reasons)
    return DebateOutput(
        role="auditor",
        passed=not veto,
        veto=veto,
        reasons=reasons or ["Policy audit passed."],
        required_changes=required,
        risk_level="high" if veto else "low",
        stop_retries=veto,
        plan_summary="Policy compliance review complete.",
        failure_modes=[
            "Secrets exposure risk",
            "Unsafe subprocess or allowlist bypass",
            "Unauthorized CI/gating changes",
        ],
    )


def run_pre_change_debate(context: DebateContext) -> dict[str, DebateOutput]:
    return {
        "proposer": _proposer(context),
        "skeptic": _skeptic(context),
        "auditor": _auditor(context),
    }


def run_post_change_debate(context: DebateContext) -> dict[str, DebateOutput]:
    return {
        "proposer": _proposer(context),
        "skeptic": _skeptic(context),
        "auditor": _auditor(context),
    }


def serialize_debate(outputs: dict[str, DebateOutput]) -> dict[str, Any]:
    return {role: asdict(result) for role, result in outputs.items()}


def debate_veto(outputs: dict[str, DebateOutput]) -> tuple[bool, str | None, DebateOutput | None]:
    for role in ("skeptic", "auditor"):
        result = outputs.get(role)
        if result and result.veto:
            return True, role, result
    return False, None, None

