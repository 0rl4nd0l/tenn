"""Autonomous development loop entrypoint.

Integration note:
- Current worker flow invokes a selected worker once per retry attempt.
- Task schema is sourced from task_queue.Task: task_id, milestone_id, slug, title, completed, line_number.
- Worker hooks in before gates and returns structured status for retry control.
- Loop output expectations: run report, commands log, worker artifacts, daily summary.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from autodev.runtime.config import AutoDevConfig, load_config
from autodev.runtime.debate import (
    DebateContext,
    debate_veto,
    run_post_change_debate,
    run_pre_change_debate,
    serialize_debate,
)
from autodev.runtime.gates import GateResult, run_gates, validate_definition_of_done
from autodev.runtime.pr_ops import PRResult, create_pr_or_fallback
from autodev.runtime.regression_guard import RegressionResult, evaluate_regression
from autodev.runtime.repo_ops import (
    RepoResult,
    build_agent_branch,
    changed_files,
    commit_all_changes,
    create_or_checkout_branch,
    diff_numstat,
    has_diff,
    revert_paths,
)
from autodev.runtime.sandbox_runner import CommandResult
from autodev.runtime.task_discovery import (
    append_tasks_to_queue,
    mark_discovery_run,
    scan_repo,
    should_run_discovery,
)
from autodev.runtime.task_queue import Milestone, Task, get_next_incomplete_task, load_milestones, load_tasks
from autodev.runtime.worker_interface import WorkerRequest, WorkerResult, run_worker, select_worker


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    daily_report_path: Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_run_context(config: AutoDevConfig) -> RunContext:
    now = _utc_now()
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    run_dir = config.repo_path / "autodev" / "reports" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    daily_report_path = config.repo_path / "autodev" / "reports" / "daily" / f"{now.strftime('%Y-%m-%d')}.md"
    daily_report_path.parent.mkdir(parents=True, exist_ok=True)
    return RunContext(run_id=run_id, run_dir=run_dir, daily_report_path=daily_report_path)


def _load_specs(config: AutoDevConfig) -> tuple[list[Task], dict[str, Milestone]]:
    tasks = load_tasks(config.repo_path / "autodev" / "spec" / "TASKS.md")
    milestones = load_milestones(config.repo_path / "autodev" / "spec" / "MILESTONES.md")
    return tasks, milestones


def _attempt_targeted_fix(config: AutoDevConfig, gate_results: list[GateResult], run_dir: Path, retry_idx: int) -> str:
    note_path = run_dir / f"targeted_fix_attempt_{retry_idx}.md"
    first_failure = next((g for g in gate_results if not g.passed), None)
    failure_name = first_failure.name if first_failure else "unknown"
    note = (
        f"# Targeted Fix Attempt {retry_idx}\n\n"
        f"- First failing gate: `{failure_name}`\n"
        "- Automatic code modification is intentionally conservative in this scaffold.\n"
        "- Human review or worker plugin integration is recommended for complex fixes.\n"
    )
    note_path.write_text(note, encoding="utf-8")
    return str(note_path.relative_to(config.repo_path))


def _mark_task_complete(config: AutoDevConfig, task: Task) -> None:
    tasks_path = config.repo_path / "autodev" / "spec" / "TASKS.md"
    lines = tasks_path.read_text(encoding="utf-8").splitlines()
    updated = False
    line_idx = task.line_number - 1
    if 0 <= line_idx < len(lines):
        stripped = lines[line_idx].strip()
        if stripped.startswith("- [ ]") and task.task_id in stripped:
            lines[line_idx] = lines[line_idx].replace("- [ ]", "- [x]", 1)
            updated = True
    if not updated:
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("- [ ]") and task.task_id in stripped:
                lines[idx] = line.replace("- [ ]", "- [x]", 1)
                updated = True
                break
    if updated:
        tasks_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _serialize_repo_result(item: RepoResult) -> dict[str, Any]:
    return {
        "command": item.command,
        "exit_code": item.exit_code,
        "stdout": item.stdout,
        "stderr": item.stderr,
    }


def _serialize_gate_result(item: GateResult) -> dict[str, Any]:
    return {
        "name": item.name,
        "command": item.command,
        "passed": item.passed,
        "exit_code": item.result.exit_code,
        "used_docker": item.result.used_docker,
        "log_path": str(item.log_path),
        "failure_reason": item.failure_reason,
        "stop_retries": item.stop_retries,
    }


def _serialize_worker_result(result: WorkerResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "summary": result.summary,
        "files_changed": result.files_changed,
        "lines_changed": result.lines_changed,
        "commit_created": result.commit_created,
        "block_reason": result.block_reason,
        "artifacts": result.artifacts or [],
    }


def _serialize_regression_result(result: RegressionResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "passed": result.passed,
        "decision": result.decision,
        "stop_retries": result.stop_retries,
        "baseline_path": result.baseline_path,
        "violations": [
            {
                "metric": item.metric,
                "baseline": item.baseline,
                "current": item.current,
                "allowed": item.allowed,
                "direction": item.direction,
            }
            for item in result.violations
        ],
    }


def _write_regression_artifact(context: RunContext, payload: dict[str, Any]) -> Path:
    path = context.run_dir / "regression.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_debate_artifact(context: RunContext, name: str, payload: dict[str, Any]) -> Path:
    path = context.run_dir / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _delta_changed_lines(
    baseline: dict[str, tuple[int, int]],
    current: dict[str, tuple[int, int]],
    scope_prefix: str | None = None,
) -> int:
    total = 0
    for path, (curr_add, curr_del) in current.items():
        if scope_prefix and not path.startswith(scope_prefix):
            continue
        base_add, base_del = baseline.get(path, (0, 0))
        total += max(0, curr_add - base_add) + max(0, curr_del - base_del)
    return total


def _delta_changed_files(
    baseline: dict[str, tuple[int, int]],
    current: dict[str, tuple[int, int]],
    scope_prefix: str | None = None,
) -> list[str]:
    changed: list[str] = []
    for path, (curr_add, curr_del) in current.items():
        if scope_prefix and not path.startswith(scope_prefix):
            continue
        base_add, base_del = baseline.get(path, (0, 0))
        if max(0, curr_add - base_add) + max(0, curr_del - base_del) > 0:
            changed.append(path)
    return sorted(changed)


def _write_worker_artifacts(
    context: RunContext,
    selected_worker: str,
    request: WorkerRequest,
    result: WorkerResult,
) -> None:
    worker_json = context.run_dir / "worker.json"
    worker_log = context.run_dir / "worker.log"
    payload = {
        "selected_worker": selected_worker,
        "request": {
            "task_id": request.task_id,
            "task_slug": request.task_slug,
            "task_description": request.task_description,
            "allowed_paths": list(request.allowed_paths),
            "repo_root": str(request.repo_root),
            "branch_name": request.branch_name,
            "max_changed_lines_per_attempt": request.max_changed_lines_per_attempt,
            "max_changed_files_per_attempt": request.max_changed_files_per_attempt,
            "allow_network": request.allow_network,
            "protected_paths": list(request.protected_paths),
            "attempt_index": request.attempt_index,
        },
        "result": _serialize_worker_result(result),
    }
    worker_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with worker_log.open("a", encoding="utf-8") as handle:
        handle.write(
            f"attempt={request.attempt_index} worker={selected_worker} "
            f"status={result.status} lines_changed={result.lines_changed} "
            f"files={len(result.files_changed)} summary={result.summary}\n"
        )


def _worker_gate_failure(
    name: str,
    reason: str,
    message: str,
    log_path: Path,
    stop_retries: bool,
) -> GateResult:
    return GateResult(
        name=name,
        command=["worker"],
        result=CommandResult(
            command=["worker"],
            exit_code=1,
            stdout="",
            stderr=message,
            started_at="n/a",
            duration_seconds=0.0,
            log_path=log_path,
            used_docker=False,
        ),
        passed=False,
        log_path=log_path,
        failure_reason=reason,
        stop_retries=stop_retries,
    )


def _enforce_worker_policy(
    config: AutoDevConfig,
    baseline_numstat: dict[str, tuple[int, int]],
    run_dir: Path,
    phase: str,
) -> GateResult | None:
    current_numstat = diff_numstat(config.repo_path)
    changed_lines = _delta_changed_lines(baseline_numstat, current_numstat)
    changed_paths = _delta_changed_files(baseline_numstat, current_numstat)
    policy_log = run_dir / "logs" / f"worker_policy_{phase}.json"
    policy_log.parent.mkdir(parents=True, exist_ok=True)

    protected_hit = [path for path in changed_paths if any(path.startswith(p) for p in config.protected_paths)]
    if protected_hit:
        policy_log.write_text(
            json.dumps(
                {
                    "reason": "protected_path_edit",
                    "phase": phase,
                    "protected_paths": list(config.protected_paths),
                    "changed_paths": changed_paths,
                    "violations": protected_hit,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return _worker_gate_failure(
            name="worker_policy",
            reason="protected_path_edit",
            message=f"Worker touched protected paths: {', '.join(protected_hit)}",
            log_path=policy_log,
            stop_retries=True,
        )

    if changed_lines > config.max_changed_lines_per_attempt:
        policy_log.write_text(
            json.dumps(
                {
                    "reason": "change_budget_exceeded",
                    "phase": phase,
                    "changed_lines": changed_lines,
                    "max_changed_lines_per_attempt": config.max_changed_lines_per_attempt,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return _worker_gate_failure(
            name="worker_policy",
            reason="change_budget_exceeded",
            message=(
                f"Changed line budget exceeded: {changed_lines} > "
                f"{config.max_changed_lines_per_attempt}"
            ),
            log_path=policy_log,
            stop_retries=True,
        )

    if len(changed_paths) > config.max_changed_files_per_attempt:
        policy_log.write_text(
            json.dumps(
                {
                    "reason": "changed_files_exceeded",
                    "phase": phase,
                    "changed_files": changed_paths,
                    "max_changed_files_per_attempt": config.max_changed_files_per_attempt,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return _worker_gate_failure(
            name="worker_policy",
            reason="changed_files_exceeded",
            message=(
                f"Changed file budget exceeded: {len(changed_paths)} > "
                f"{config.max_changed_files_per_attempt}"
            ),
            log_path=policy_log,
            stop_retries=True,
        )
    return None


def _build_debate_context(
    config: AutoDevConfig,
    task: Task,
    milestone: Milestone,
    branch_name: str,
    changed_files: list[str],
    changed_lines: int,
    phase: str,
) -> DebateContext:
    return DebateContext(
        phase=phase,
        task_id=task.task_id,
        task_slug=task.slug,
        task_description=task.title,
        milestone_dod=milestone.dod,
        branch_name=branch_name,
        repo_root=config.repo_path,
        allowed_paths=config.allowed_paths,
        protected_paths=config.protected_paths,
        changed_files=changed_files,
        changed_lines=changed_lines,
        changed_file_count=len(changed_files),
        max_changed_lines_per_attempt=config.max_changed_lines_per_attempt,
        max_changed_files_per_attempt=config.max_changed_files_per_attempt,
        allow_network=config.allow_network,
        strictness=config.debate_strictness,
        require_3_failure_modes=config.debate_require_3_failure_modes,
        gate_names=milestone.commands or ["ruff", "pytest", "eval"],
    )


def _write_run_report(
    config: AutoDevConfig,
    context: RunContext,
    task: Task,
    branch_name: str,
    gate_results: list[GateResult],
    repo_results: list[RepoResult],
    pr_result: PRResult | None,
    next_action: str,
    dod_ok: bool,
    dod_errors: list[str],
    retries_used: int,
    worker_results: list[dict[str, Any]],
    debate_pre: dict[str, Any] | None,
    debate_post: dict[str, Any] | None,
    regression_result: dict[str, Any] | None,
    regression_path: str | None,
    fix_notes: list[str],
) -> None:
    report_path = context.run_dir / "report.md"
    commands_payload = {
        "repo_commands": [_serialize_repo_result(result) for result in repo_results],
        "gate_commands": [_serialize_gate_result(result) for result in gate_results],
        "worker": worker_results,
        "debate_pre": debate_pre,
        "debate_post": debate_post,
        "regression": regression_result,
    }
    (context.run_dir / "commands.json").write_text(
        json.dumps(commands_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Autodev Run Report",
        "",
        f"- task id: `{task.task_id}`",
        f"- task title: {task.title}",
        f"- branch name: `{branch_name}`",
        f"- retries used: `{retries_used}`",
        f"- definition of done: `{'pass' if dod_ok else 'fail'}`",
        "",
        "## Gate Results",
    ]
    for gate in gate_results:
        detail = gate.result.stderr.strip().splitlines()[0] if gate.result.stderr.strip() else "n/a"
        lines.append(
            f"- `{gate.name}`: {'PASS' if gate.passed else 'FAIL'} "
            f"(exit={gate.result.exit_code}, reason={gate.failure_reason or 'n/a'}, log=`{gate.log_path}`)"
        )
        if not gate.passed:
            lines.append(f"  - detail: {detail}")
    lines.extend(["", "## Commands Executed", "- See `commands.json` for full command log."])
    lines.extend(["", "## Worker Attempts"])
    if worker_results:
        for worker in worker_results:
            lines.append(
                f"- attempt `{worker['attempt_index']}`: "
                f"worker=`{worker['worker_name']}` status=`{worker['status']}` "
                f"lines_changed=`{worker['lines_changed']}`"
            )
            lines.append(f"  - summary: {worker['summary']}")
    else:
        lines.append("- No worker attempts recorded.")
    lines.extend(["", "## Debate"])
    if debate_pre is None:
        lines.append("- pre: not run")
    else:
        pre_veto = debate_pre.get("meta", {}).get("veto", False)
        pre_role = debate_pre.get("meta", {}).get("veto_role")
        lines.append(f"- pre veto: `{pre_veto}` role=`{pre_role or 'none'}`")
        pre_risk = debate_pre.get("roles", {}).get("skeptic", {}).get("risk_level", "unknown")
        lines.append(f"- pre risk level: `{pre_risk}`")
    if debate_post is None:
        lines.append("- post: not run")
    else:
        post_veto = debate_post.get("meta", {}).get("veto", False)
        post_role = debate_post.get("meta", {}).get("veto_role")
        lines.append(f"- post veto: `{post_veto}` role=`{post_role or 'none'}`")
        post_risk = debate_post.get("roles", {}).get("skeptic", {}).get("risk_level", "unknown")
        lines.append(f"- post risk level: `{post_risk}`")
    top_reasons: list[str] = []
    for payload in (debate_pre, debate_post):
        if not payload:
            continue
        for role in ("skeptic", "auditor"):
            reasons = payload.get("roles", {}).get(role, {}).get("reasons", [])
            if reasons:
                top_reasons.extend(reasons[:1])
    if top_reasons:
        lines.append("- top reasons:")
        for item in top_reasons[:3]:
            lines.append(f"  - {item}")
    lines.extend(["", "## Regression Guard"])
    if regression_result is None:
        lines.append("- not evaluated")
    else:
        lines.append(
            f"- decision: `{regression_result.get('decision', 'unknown')}` "
            f"(passed=`{regression_result.get('passed', False)}`)"
        )
        lines.append(f"- stop_retries: `{regression_result.get('stop_retries', False)}`")
        if regression_path:
            lines.append(f"- artifact: `{regression_path}`")
        violations = regression_result.get("violations", [])
        if violations:
            lines.append("- violations:")
            for item in violations:
                lines.append(
                    "  - "
                    f"{item.get('metric')}: baseline={item.get('baseline')} "
                    f"current={item.get('current')} allowed={item.get('allowed')} "
                    f"direction={item.get('direction')}"
                )
    lines.extend(["", "## Fix Attempts"])
    if fix_notes:
        for fix in fix_notes:
            lines.append(f"- `{fix}`")
    else:
        lines.append("- None")
    lines.extend(["", "## DoD Errors"])
    if dod_errors:
        for err in dod_errors:
            lines.append(f"- {err}")
    else:
        lines.append("- None")
    lines.extend(["", "## PR Result"])
    if pr_result:
        lines.append(f"- mode: `{pr_result.mode}`")
        lines.append(f"- success: `{pr_result.success}`")
        lines.append(f"- message: {pr_result.message}")
        if pr_result.artifact_path:
            lines.append(f"- artifact: `{pr_result.artifact_path}`")
    else:
        lines.append("- Not attempted.")
    lines.extend(["", "## Next Action", f"- {next_action}", ""])
    report_path.write_text("\n".join(lines), encoding="utf-8")

    daily_line = (
        f"- {context.run_id} | task={task.task_id} | branch={branch_name} | "
        f"gates={'pass' if all(g.passed for g in gate_results) else 'fail'} | "
        f"dod={'pass' if dod_ok else 'fail'} | next={next_action}"
    )
    with context.daily_report_path.open("a", encoding="utf-8") as handle:
        handle.write(daily_line + "\n")

    if config.notification_mode == "stdout":
        print(daily_line)
    if config.notification_webhook_file:
        with config.notification_webhook_file.open("a", encoding="utf-8") as handle:
            handle.write(daily_line + "\n")


def run_once(config: AutoDevConfig) -> int:
    context = _new_run_context(config)
    if config.enable_task_discovery:
        if should_run_discovery(
            config.discovery_interval_seconds,
            repo_path=config.repo_path,
        ):
            discovered = scan_repo(config.repo_path)
            append_tasks_to_queue(config.repo_path, discovered)
            mark_discovery_run(repo_path=config.repo_path)
            if config.notification_mode == "stdout":
                print("Discovery executed")
        elif config.notification_mode == "stdout":
            print("Discovery skipped (interval not reached)")
    tasks, milestones = _load_specs(config)
    task = get_next_incomplete_task(tasks)
    if task is None:
        (context.run_dir / "report.md").write_text("# No pending tasks\n", encoding="utf-8")
        no_task_line = f"- {context.run_id} | no pending tasks"
        with context.daily_report_path.open("a", encoding="utf-8") as handle:
            handle.write(no_task_line + "\n")
        if config.notification_mode == "stdout":
            print(no_task_line)
        if config.notification_webhook_file:
            with config.notification_webhook_file.open("a", encoding="utf-8") as handle:
                handle.write(no_task_line + "\n")
        return 0

    milestone = milestones.get(task.milestone_id)
    if milestone is None:
        raise RuntimeError(f"Task '{task.task_id}' references unknown milestone '{task.milestone_id}'.")

    branch_name = build_agent_branch(task.slug)
    repo_results = create_or_checkout_branch(config.repo_path, branch_name)
    baseline_numstat = diff_numstat(config.repo_path)

    retries = 0
    gate_results: list[GateResult] = []
    fix_notes: list[str] = []
    worker_results: list[dict[str, Any]] = []
    debate_pre_payload: dict[str, Any] | None = None
    debate_post_payload: dict[str, Any] | None = None
    regression_payload: dict[str, Any] | None = None
    regression_artifact_path: str | None = None
    while retries < config.max_retries:
        retries += 1

        if config.enable_debate:
            pre_context = _build_debate_context(
                config=config,
                task=task,
                milestone=milestone,
                branch_name=branch_name,
                changed_files=[],
                changed_lines=0,
                phase=f"pre_change_attempt_{retries}",
            )
            pre_outputs = run_pre_change_debate(pre_context)
            veto, veto_role, veto_output = debate_veto(pre_outputs)
            debate_pre_payload = {
                "attempt_index": retries,
                "phase": pre_context.phase,
                "meta": {
                    "veto": veto,
                    "veto_role": veto_role,
                    "stop_retries": bool(veto_output.stop_retries) if veto_output else False,
                },
                "roles": serialize_debate(pre_outputs),
            }
            _write_debate_artifact(context, "debate_pre.json", debate_pre_payload)
            if veto and veto_output:
                debate_post_payload = {
                    "attempt_index": retries,
                    "phase": f"post_change_attempt_{retries}",
                    "meta": {"status": "not_run", "reason": "pre_veto"},
                    "roles": {},
                }
                _write_debate_artifact(context, "debate_post.json", debate_post_payload)
                debate_log = context.run_dir / "logs" / f"debate_pre_veto_{retries}.json"
                debate_log.parent.mkdir(parents=True, exist_ok=True)
                debate_log.write_text(json.dumps(debate_pre_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                gate_results = [
                    _worker_gate_failure(
                        name="debate_pre",
                        reason="debate_pre_veto",
                        message=f"Blocked by {veto_role}: {'; '.join(veto_output.reasons)}",
                        log_path=debate_log,
                        stop_retries=veto_output.stop_retries,
                    )
                ]
                break

        selected_worker = select_worker(config, task)
        worker_request = WorkerRequest(
            task_id=task.task_id,
            task_slug=task.slug,
            task_description=task.title,
            allowed_paths=config.allowed_paths,
            repo_root=config.repo_path,
            branch_name=branch_name,
            max_changed_lines_per_attempt=config.max_changed_lines_per_attempt,
            max_changed_files_per_attempt=config.max_changed_files_per_attempt,
            allow_network=config.allow_network,
            llm_routing_mode=config.llm_routing_mode,
            llm_provider_balanced=config.llm_provider_balanced,
            llm_provider_heavy=config.llm_provider_heavy,
            llama_cpp_base_url=config.llama_cpp_base_url,
            llama_cpp_api_key=config.llama_cpp_api_key,
            llama_cpp_model_balanced=config.llama_cpp_model_balanced,
            llama_cpp_model_heavy=config.llama_cpp_model_heavy,
            ollama_host=config.ollama_host,
            ollama_model_balanced=config.ollama_model_balanced,
            ollama_model_heavy=config.ollama_model_heavy,
            ollama_timeout_seconds=config.ollama_timeout_seconds,
            openai_model=config.openai_model,
            llm_max_generation_attempts=config.llm_max_generation_attempts,
            protected_paths=config.protected_paths,
            run_dir=context.run_dir,
            attempt_index=retries,
        )
        worker_result = run_worker(worker_request, selected_worker)
        _write_worker_artifacts(context, selected_worker, worker_request, worker_result)
        worker_results.append(
            {
                "attempt_index": retries,
                "worker_name": selected_worker,
                "status": worker_result.status,
                "summary": worker_result.summary,
                "lines_changed": worker_result.lines_changed,
                "files_changed": worker_result.files_changed,
                "block_reason": worker_result.block_reason,
                "artifacts": worker_result.artifacts or [],
            }
        )

        if config.enable_debate:
            changed_now = _delta_changed_files(baseline_numstat, diff_numstat(config.repo_path))
            lines_now = _delta_changed_lines(baseline_numstat, diff_numstat(config.repo_path))
            post_context = _build_debate_context(
                config=config,
                task=task,
                milestone=milestone,
                branch_name=branch_name,
                changed_files=changed_now,
                changed_lines=lines_now,
                phase=f"post_change_attempt_{retries}",
            )
            post_outputs = run_post_change_debate(post_context)
            veto, veto_role, veto_output = debate_veto(post_outputs)
            debate_post_payload = {
                "attempt_index": retries,
                "phase": post_context.phase,
                "meta": {
                    "veto": veto,
                    "veto_role": veto_role,
                    "stop_retries": bool(veto_output.stop_retries) if veto_output else False,
                },
                "roles": serialize_debate(post_outputs),
            }
            _write_debate_artifact(context, "debate_post.json", debate_post_payload)
            if veto and veto_output:
                rollback_paths = sorted(set(worker_result.files_changed + changed_now))
                repo_results.extend(revert_paths(config.repo_path, rollback_paths))
                debate_log = context.run_dir / "logs" / f"debate_post_veto_{retries}.json"
                debate_log.parent.mkdir(parents=True, exist_ok=True)
                debate_log.write_text(json.dumps(debate_post_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                gate_results = [
                    _worker_gate_failure(
                        name="debate_post",
                        reason="debate_post_veto",
                        message=f"Blocked by {veto_role}: {'; '.join(veto_output.reasons)}",
                        log_path=debate_log,
                        stop_retries=veto_output.stop_retries,
                    )
                ]
                break

        if worker_result.status == "blocked":
            blocked_log = context.run_dir / "logs" / f"worker_blocked_{retries}.json"
            blocked_log.parent.mkdir(parents=True, exist_ok=True)
            blocked_log.write_text(
                json.dumps(
                    {
                        "reason": "worker_blocked",
                        "attempt": retries,
                        "block_reason": worker_result.block_reason,
                        "summary": worker_result.summary,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            gate_results = [
                _worker_gate_failure(
                    name="worker_blocked",
                    reason="worker_blocked",
                    message=worker_result.summary,
                    log_path=blocked_log,
                    stop_retries=True,
                )
            ]
            break

        pre_policy = _enforce_worker_policy(
            config=config,
            baseline_numstat=baseline_numstat,
            run_dir=context.run_dir,
            phase=f"pre_gate_attempt_{retries}",
        )
        if pre_policy is not None:
            gate_results = [pre_policy]
            break

        if worker_result.status == "error":
            error_log = context.run_dir / "logs" / f"worker_error_{retries}.json"
            error_log.write_text(
                json.dumps(
                    {
                        "reason": "worker_error",
                        "attempt": retries,
                        "summary": worker_result.summary,
                        "block_reason": worker_result.block_reason,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            gate_results = [
                _worker_gate_failure(
                    name="worker_error",
                    reason="worker_error",
                    message=worker_result.summary,
                    log_path=error_log,
                    stop_retries=False,
                )
            ]
            note_rel = _attempt_targeted_fix(config, gate_results, context.run_dir, retries)
            fix_notes.append(note_rel)
            continue

        gate_results = run_gates(milestone=milestone, config=config, run_dir=context.run_dir)
        all_passed, _ = validate_definition_of_done(milestone, gate_results, config.repo_path)
        if worker_result.status == "no_change" and not all_passed:
            no_change_log = context.run_dir / "logs" / f"worker_no_change_{retries}.json"
            no_change_log.write_text(
                json.dumps(
                    {
                        "reason": "worker_no_change_unsatisfied",
                        "attempt": retries,
                        "summary": worker_result.summary,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            fix_notes.append(str(no_change_log.relative_to(config.repo_path)))
        if all_passed:
            break
        if any(g.stop_retries for g in gate_results):
            break
        note_rel = _attempt_targeted_fix(config, gate_results, context.run_dir, retries)
        fix_notes.append(note_rel)

    dod_ok, dod_errors = validate_definition_of_done(milestone, gate_results, config.repo_path)
    pr_result: PRResult | None = None
    next_action = "Escalate to human review with failure report."
    if dod_ok:
        post_policy = _enforce_worker_policy(
            config=config,
            baseline_numstat=baseline_numstat,
            run_dir=context.run_dir,
            phase="post_gate_pre_pr",
        )
        if post_policy is not None:
            dod_ok = False
            gate_results = [*gate_results, post_policy]
            dod_errors = [f"Worker policy failed before PR: {post_policy.failure_reason}"]
        else:
            eval_results_path = config.repo_path / "autodev" / "evals" / "results.json"
            eval_metrics: dict[str, Any] = {}
            if not eval_results_path.exists():
                dod_ok = False
                dod_errors = ["Regression guard blocked: missing eval results file."]
                regression_gate_log = context.run_dir / "logs" / "regression_guard_missing_eval.json"
                regression_gate_log.parent.mkdir(parents=True, exist_ok=True)
                regression_gate_log.write_text(
                    json.dumps(
                        {"reason": "missing_eval_results", "path": str(eval_results_path)},
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                gate_results = [
                    *gate_results,
                    _worker_gate_failure(
                        name="regression_guard",
                        reason="missing_eval_results",
                        message="Regression guard could not load eval metrics.",
                        log_path=regression_gate_log,
                        stop_retries=True,
                    ),
                ]
                regression_payload = {
                    "decision": "missing_eval_results",
                    "passed": False,
                    "stop_retries": True,
                    "violations": [],
                    "baseline_path": str(config.baseline_path),
                }
                regression_artifact_path = str(
                    _write_regression_artifact(context, regression_payload).relative_to(config.repo_path)
                )
            else:
                try:
                    eval_payload = json.loads(eval_results_path.read_text(encoding="utf-8"))
                    eval_metrics = eval_payload.get("metrics", {})
                    if not isinstance(eval_metrics, dict):
                        raise ValueError("metrics field must be an object")
                except Exception as exc:
                    dod_ok = False
                    dod_errors = [f"Regression guard blocked: invalid eval results ({exc})."]
                    regression_gate_log = context.run_dir / "logs" / "regression_guard_invalid_eval.json"
                    regression_gate_log.parent.mkdir(parents=True, exist_ok=True)
                    regression_gate_log.write_text(
                        json.dumps(
                            {"reason": "invalid_eval_results", "error": str(exc)},
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    gate_results = [
                        *gate_results,
                        _worker_gate_failure(
                            name="regression_guard",
                            reason="invalid_eval_results",
                            message="Regression guard could not parse eval metrics.",
                            log_path=regression_gate_log,
                            stop_retries=True,
                        ),
                    ]
                    regression_payload = {
                        "decision": "invalid_eval_results",
                        "passed": False,
                        "stop_retries": True,
                        "violations": [],
                        "baseline_path": str(config.baseline_path),
                    }
                    regression_artifact_path = str(
                        _write_regression_artifact(context, regression_payload).relative_to(config.repo_path)
                    )

            if dod_ok:
                regression_result = evaluate_regression(
                    current_metrics=eval_metrics,
                    baseline_path=config.baseline_path,
                    tolerances=config.regression_tolerances,
                    protected_metrics=config.protected_metrics,
                    allow_baseline_init=config.allow_baseline_init,
                    allow_baseline_update=config.allow_baseline_update,
                    gates_passed=True,
                    run_id=context.run_id,
                )
                regression_payload = _serialize_regression_result(regression_result)
                regression_artifact_path = str(
                    _write_regression_artifact(
                        context,
                        regression_payload or {"decision": "unknown", "passed": False},
                    ).relative_to(config.repo_path)
                )
                if not regression_result.passed:
                    dod_ok = False
                    dod_errors = [f"Blocked by regression guard ({regression_result.decision})."]
                    regression_gate_log = context.run_dir / "logs" / "regression_guard_failed.json"
                    regression_gate_log.parent.mkdir(parents=True, exist_ok=True)
                    regression_gate_log.write_text(
                        json.dumps(regression_payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    gate_results = [
                        *gate_results,
                        _worker_gate_failure(
                            name="regression_guard",
                            reason=regression_result.decision,
                            message="Regression guard detected non-allowed metric regression.",
                            log_path=regression_gate_log,
                            stop_retries=regression_result.stop_retries,
                        ),
                    ]

        if dod_ok and has_diff(config.repo_path):
            commit_message = f"autodev: {task.task_id} {task.slug}"
            commit_results = commit_all_changes(config.repo_path, commit_message)
            repo_results.extend(commit_results)
            last_commit = commit_results[-1] if commit_results else None
            if last_commit is None or last_commit.exit_code != 0:
                dod_ok = False
                dod_errors = ["Failed to commit worker changes before PR stage."]
            else:
                worker_results.append(
                    {
                        "attempt_index": retries,
                        "worker_name": "commit_stage",
                        "status": "changed",
                        "summary": "Committed worker changes on agent branch.",
                        "lines_changed": 0,
                        "files_changed": changed_files(config.repo_path),
                        "block_reason": None,
                        "artifacts": [],
                    }
                )

    if dod_ok:
        _mark_task_complete(config, task)
        pr_result = create_pr_or_fallback(
            repo_path=config.repo_path,
            branch_name=branch_name,
            task_title=task.title,
            run_dir=context.run_dir,
            pr_mode=config.pr_mode,
        )
        next_action = "Review patch/PR and continue with next task."

    if regression_payload is None:
        regression_payload = {
            "decision": "not_evaluated",
            "passed": False,
            "stop_retries": False,
            "violations": [],
            "baseline_path": str(config.baseline_path),
        }
        regression_artifact_path = str(
            _write_regression_artifact(context, regression_payload).relative_to(config.repo_path)
        )
    if debate_pre_payload is None:
        debate_pre_payload = {"meta": {"status": "not_run"}}
        _write_debate_artifact(context, "debate_pre.json", debate_pre_payload)
    if debate_post_payload is None:
        debate_post_payload = {"meta": {"status": "not_run"}}
        _write_debate_artifact(context, "debate_post.json", debate_post_payload)

    _write_run_report(
        config=config,
        context=context,
        task=task,
        branch_name=branch_name,
        gate_results=gate_results,
        repo_results=repo_results,
        pr_result=pr_result,
        next_action=next_action,
        dod_ok=dod_ok,
        dod_errors=dod_errors,
        retries_used=retries,
        worker_results=worker_results,
        debate_pre=debate_pre_payload,
        debate_post=debate_post_payload,
        regression_result=regression_payload,
        regression_path=regression_artifact_path,
        fix_notes=fix_notes,
    )
    return 0


def run_daemon(config: AutoDevConfig) -> int:
    while True:
        run_once(config)
        time.sleep(config.daemon_interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe autonomous development loop.")
    parser.add_argument("--once", action="store_true", help="Run a single loop iteration.")
    parser.add_argument("--daemon", action="store_true", help="Run continuously.")
    args = parser.parse_args()
    if not args.once and not args.daemon:
        parser.error("Choose one of --once or --daemon.")
    config = load_config()
    if args.once:
        return run_once(config)
    return run_daemon(config)


if __name__ == "__main__":
    raise SystemExit(main())
