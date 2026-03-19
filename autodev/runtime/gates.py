"""Deterministic gate execution and milestone DoD enforcement."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from autodev.runtime.config import AutoDevConfig
from autodev.runtime.sandbox_runner import CommandResult, run_command
from autodev.runtime.task_queue import Milestone


@dataclass(frozen=True)
class GateResult:
    name: str
    command: list[str]
    result: CommandResult
    passed: bool
    log_path: Path
    failure_reason: str | None = None
    stop_retries: bool = False


def _gate_command(name: str, python_bin: str) -> list[str]:
    if name == "ruff":
        return ["ruff", "check", "--no-cache", "autodev"]
    if name == "pytest":
        return ["pytest", "-q", "autodev/tests"]
    if name == "eval":
        return [python_bin, "autodev/evals/run_evals.py"]
    raise ValueError(f"Unknown gate '{name}'")


def run_gates(
    milestone: Milestone,
    config: AutoDevConfig,
    run_dir: Path,
) -> list[GateResult]:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    gate_results: list[GateResult] = []

    for tool_name, command in (
        ("ruff", ["ruff", "--version"]),
        ("pytest", ["pytest", "--version"]),
    ):
        preflight_log = logs_dir / f"preflight_{tool_name}.json"
        try:
            preflight_result = run_command(
                command=command,
                cwd=config.repo_path,
                timeout_seconds=config.gate_timeout_seconds,
                allow_network=config.allow_network,
                prefer_docker=config.use_docker_if_available,
                docker_image=config.docker_image,
                dockerfile_path=config.dockerfile_path,
                docker_auto_build=config.docker_auto_build,
                log_path=preflight_log,
            )
        except Exception as exc:
            preflight_log.write_text(
                json.dumps(
                    {
                        "stage": "preflight",
                        "tool": tool_name,
                        "command": command,
                        "failure_reason": "missing_tools",
                        "error": str(exc),
                        "action": (
                            "Install Docker and build autodev-gates image or run "
                            "autodev/scripts/bootstrap_dev_env.sh"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            synthetic = CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=(
                    f"Preflight failed for '{tool_name}' with setup error: {exc}. "
                    "Install Docker and build the gate image, or run autodev/scripts/bootstrap_dev_env.sh."
                ),
                started_at="n/a",
                duration_seconds=0.0,
                log_path=preflight_log,
                used_docker=False,
            )
            gate_results.append(
                GateResult(
                    name=f"preflight_{tool_name}",
                    command=command,
                    result=synthetic,
                    passed=False,
                    log_path=preflight_log,
                    failure_reason="missing_tools",
                    stop_retries=True,
                )
            )
            return gate_results
        if preflight_result.exit_code != 0:
            guidance = (
                "Missing required gate tool inside sandbox. "
                "Build gate image with "
                "'docker build -t autodev-gates:latest -f autodev/docker/Dockerfile .' "
                "or run autodev/scripts/bootstrap_dev_env.sh."
            )
            enriched = CommandResult(
                command=preflight_result.command,
                exit_code=preflight_result.exit_code,
                stdout=preflight_result.stdout,
                stderr=(preflight_result.stderr + "\n" + guidance).strip(),
                started_at=preflight_result.started_at,
                duration_seconds=preflight_result.duration_seconds,
                log_path=preflight_result.log_path,
                used_docker=preflight_result.used_docker,
            )
            gate_results.append(
                GateResult(
                    name=f"preflight_{tool_name}",
                    command=command,
                    result=enriched,
                    passed=False,
                    log_path=preflight_log,
                    failure_reason="missing_tools",
                    stop_retries=True,
                )
            )
            return gate_results

    gate_order = milestone.commands or ["ruff", "pytest", "eval"]
    for gate_name in gate_order:
        command = _gate_command(gate_name, config.python_bin)
        log_path = logs_dir / f"gate_{gate_name}.json"
        try:
            cmd_result = run_command(
                command=command,
                cwd=config.repo_path,
                timeout_seconds=config.gate_timeout_seconds,
                allow_network=config.allow_network,
                prefer_docker=config.use_docker_if_available,
                docker_image=config.docker_image,
                dockerfile_path=config.dockerfile_path,
                docker_auto_build=config.docker_auto_build,
                log_path=log_path,
            )
        except Exception as exc:
            cmd_result = CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=f"Gate setup failed: {exc}",
                started_at="n/a",
                duration_seconds=0.0,
                log_path=log_path,
                used_docker=False,
            )
            gate_results.append(
                GateResult(
                    name=gate_name,
                    command=command,
                    result=cmd_result,
                    passed=False,
                    log_path=log_path,
                    failure_reason="sandbox_setup_error",
                    stop_retries=True,
                )
            )
            break
        passed = cmd_result.exit_code == 0
        gate_results.append(
            GateResult(
                name=gate_name,
                command=command,
                result=cmd_result,
                passed=passed,
                log_path=log_path,
            )
        )
        if not passed:
            break
    return gate_results


def all_gates_passed(gate_results: list[GateResult], required_gates: list[str]) -> bool:
    if not gate_results:
        return False
    required = required_gates or ["ruff", "pytest", "eval"]
    by_name = {g.name: g for g in gate_results}
    for gate_name in required:
        gate = by_name.get(gate_name)
        if gate is None or not gate.passed:
            return False
    return True


def validate_definition_of_done(
    milestone: Milestone,
    gate_results: list[GateResult],
    repo_path: Path,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    gates_ok = all_gates_passed(gate_results, milestone.commands)
    if not gates_ok:
        errors.append("One or more required gates failed.")
        return (False, errors)

    for artifact in milestone.required_artifacts:
        artifact_path = repo_path / artifact
        if not artifact_path.exists():
            errors.append(f"Missing required artifact: {artifact}")

    if milestone.thresholds:
        eval_path = repo_path / "autodev/evals/results.json"
        if not eval_path.exists():
            errors.append("Missing eval results file for threshold validation.")
        else:
            try:
                payload = json.loads(eval_path.read_text(encoding="utf-8"))
                metrics = payload.get("metrics", {})
            except Exception as exc:
                errors.append(f"Unable to parse eval results: {exc}")
                metrics = {}
            for metric_name, threshold in milestone.thresholds.items():
                raw_value = metrics.get(metric_name)
                if raw_value is None:
                    errors.append(f"Missing metric '{metric_name}' for threshold check.")
                    continue
                try:
                    metric_value = float(raw_value)
                except (TypeError, ValueError):
                    errors.append(f"Metric '{metric_name}' is non-numeric: {raw_value!r}")
                    continue
                if metric_value < threshold:
                    errors.append(
                        f"Metric '{metric_name}' below threshold ({metric_value} < {threshold})."
                    )
    return (len(errors) == 0, errors)
