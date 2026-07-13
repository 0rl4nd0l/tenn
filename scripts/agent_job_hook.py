#!/usr/bin/env python3
"""Codex/Claude/Gemini hook wrapper for the Tenn dev-agent task-card contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


ACTIVE_TASK_MARKER = Path(".tenn/active_agent_task")
CONTRACT_SCRIPT = Path("scripts/agent_job_contract.py")
REGISTRY_SCRIPT = Path("scripts/agent_job_registry.py")
DECISION_LEDGER_SCRIPT = Path("scripts/agent_decision_ledger.py")


@dataclass(frozen=True)
class ActiveTaskCard:
    source: str
    display_path: str
    path: Path


@dataclass(frozen=True)
class ContractRun:
    name: str
    returncode: int
    stdout: str
    stderr: str
    parsed: dict[str, Any] | None


def _read_hook_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("hook stdin JSON must be an object")
    return loaded


def _resolve_control_plane_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if all(
            (candidate / script).is_file()
            for script in (CONTRACT_SCRIPT, REGISTRY_SCRIPT, DECISION_LEDGER_SCRIPT)
        ):
            return candidate
    raise RuntimeError("could not resolve Tenn control-plane root")


def _resolve_repo_root(start: Path | None = None) -> Path:
    return (start or Path.cwd()).resolve()


def _resolve_card_path(repo_root: Path, raw_path: str, source: str) -> ActiveTaskCard:
    if not raw_path.strip():
        raise ValueError(f"{source} is empty")

    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve(strict=False)

    try:
        display_path = resolved.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{source} must point to a task card inside the repo") from exc

    return ActiveTaskCard(source=source, display_path=display_path, path=resolved)


def find_active_task_card(repo_root: Path, env: Mapping[str, str] | None = None) -> ActiveTaskCard | None:
    values = env or os.environ
    env_card = values.get("TENN_AGENT_TASK_CARD", "").strip()
    if env_card:
        return _resolve_card_path(repo_root, env_card, "TENN_AGENT_TASK_CARD")

    marker = repo_root / ACTIVE_TASK_MARKER
    if not marker.exists():
        return None

    marker_value = marker.read_text(encoding="utf-8").strip().splitlines()
    if not marker_value:
        return None
    return _resolve_card_path(repo_root, marker_value[0], ACTIVE_TASK_MARKER.as_posix())


def _run_script(
    control_plane_root: Path,
    repo_root: Path,
    script_path: Path,
    name: str,
    args: list[str],
) -> ContractRun:
    script = control_plane_root / script_path
    if not script.exists():
        return ContractRun(
            name=name,
            returncode=1,
            stdout="",
            stderr=f"missing script: {script_path.as_posix()}",
            parsed=None,
        )

    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = completed.stdout.strip()
    parsed: dict[str, Any] | None = None
    if stdout:
        try:
            loaded = json.loads(stdout)
            if isinstance(loaded, dict):
                parsed = loaded
        except json.JSONDecodeError:
            parsed = None

    return ContractRun(
        name=name,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=completed.stderr.strip(),
        parsed=parsed,
    )


def _run_contract(
    control_plane_root: Path,
    repo_root: Path,
    name: str,
    args: list[str],
) -> ContractRun:
    return _run_script(control_plane_root, repo_root, CONTRACT_SCRIPT, name, args)


def _run_registry(
    control_plane_root: Path,
    repo_root: Path,
    name: str,
    args: list[str],
) -> ContractRun:
    return _run_script(control_plane_root, repo_root, REGISTRY_SCRIPT, name, args)


def _run_decision_ledger(
    control_plane_root: Path,
    repo_root: Path,
    name: str,
    args: list[str],
) -> ContractRun:
    return _run_script(
        control_plane_root,
        repo_root,
        DECISION_LEDGER_SCRIPT,
        name,
        args,
    )


def _issue_messages(payload: dict[str, Any] | None) -> list[str]:
    if not payload:
        return []

    issues: list[str] = []
    omitted = 0

    def append_issue(message: str) -> None:
        nonlocal omitted
        if len(issues) < 8:
            issues.append(message)
        else:
            omitted += 1

    for issue in payload.get("issues", []) or []:
        if isinstance(issue, dict):
            field = issue.get("field", "issue")
            message = issue.get("message", "")
            append_issue(f"{field}: {message}".strip())
        elif isinstance(issue, str) and issue.strip():
            append_issue(issue.strip())

    data_missing = payload.get("data_missing")
    if isinstance(data_missing, list) and data_missing:
        append_issue("data_missing: " + ", ".join(str(item) for item in data_missing))

    validation = payload.get("validation")
    if isinstance(validation, dict):
        for issue in validation.get("issues", []) or []:
            if isinstance(issue, dict):
                field = issue.get("field", "validation")
                message = issue.get("message", "")
                append_issue(f"{field}: {message}".strip())

    disallowed = payload.get("disallowed_files")
    if isinstance(disallowed, list) and disallowed:
        sample = ", ".join(str(item) for item in disallowed[:8])
        if len(disallowed) > 8:
            sample = f"{sample}, +{len(disallowed) - 8} more"
        append_issue(f"disallowed_files: {sample}")

    if omitted:
        issues.append(f"+{omitted} more issues")

    return issues


def _task_card_requires_strict_closeout(card: ActiveTaskCard, validate: ContractRun) -> bool:
    if validate.parsed:
        metadata = validate.parsed.get("metadata")
        if isinstance(metadata, dict):
            if "control_contract_version" in metadata:
                version = metadata.get("control_contract_version")
                return not (type(version) is int and version == 1)

    try:
        lines = card.path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    if not lines or lines[0].strip() != "---":
        return False

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")):
            continue
        key, separator, raw_value = line.partition(":")
        if separator and key.strip() == "control_contract_version":
            value = raw_value.split("#", 1)[0].strip()
            return value != "1"
    return False


def _synthetic_run(name: str, *, ok: bool, issues: list[dict[str, str]] | None = None) -> ContractRun:
    payload: dict[str, Any] = {"ok": ok}
    if issues:
        payload["issues"] = issues
    return ContractRun(
        name=name,
        returncode=0 if ok else 1,
        stdout=json.dumps(payload, sort_keys=True),
        stderr="",
        parsed=payload,
    )


def _v2_decision_closeout_runs(
    control_plane_root: Path,
    repo_root: Path,
    *,
    metadata: Mapping[str, Any],
    list_active: ContractRun,
) -> list[ContractRun]:
    """Prove RUN_OUTCOME is represented by this run's validated decision entry."""

    job_id = metadata.get("job_id")
    output_dir = metadata.get("output_dir")
    fingerprint = metadata.get("computed_scope_fingerprint")
    if not all(isinstance(value, str) and value.strip() for value in (job_id, output_dir, fingerprint)):
        return [
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[{"field": "task_card", "message": "missing V2 closeout identity fields"}],
            )
        ]

    outcome_path = repo_root / str(output_dir) / "RUN_OUTCOME.json"
    try:
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[{"field": "RUN_OUTCOME.json", "message": str(exc)}],
            )
        ]
    if not isinstance(outcome, Mapping):
        return [
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[{"field": "RUN_OUTCOME.json", "message": "must contain a JSON object"}],
            )
        ]

    active_jobs = list_active.parsed.get("active_jobs") if list_active.parsed else None
    current_active = None
    if isinstance(active_jobs, list):
        for active in active_jobs:
            if (
                isinstance(active, Mapping)
                and active.get("job_id") == job_id
                and active.get("status", "active") == "active"
                and active.get("stale") is not True
            ):
                current_active = active
                break
    run_id = current_active.get("session_id") if isinstance(current_active, Mapping) else None
    if (
        not isinstance(run_id, str)
        or not run_id.strip()
        or current_active.get("scope_fingerprint") != fingerprint
    ):
        return [
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[
                    {
                        "field": "active_job",
                        "message": "current V2 job identity and matching scope fingerprint are required",
                    }
                ],
            )
        ]

    outcome_status = outcome.get("status")
    search = _run_decision_ledger(
        control_plane_root,
        repo_root,
        "decision-ledger-closeout-search",
        [
            "search",
            "--repo-root",
            str(repo_root),
            "--scope-fingerprint",
            str(fingerprint),
            "--task-id",
            str(job_id),
            "--run-id",
            run_id,
            "--outcome-status",
            str(outcome_status),
        ],
    )
    if search.returncode != 0 or search.parsed is None or search.parsed.get("ok") is not True:
        return [search]

    matches = search.parsed.get("matches")
    matching_ids: list[str] = []
    if isinstance(matches, list):
        for match in matches:
            entry = match.get("entry") if isinstance(match, Mapping) else None
            if not isinstance(entry, Mapping):
                continue
            if (
                entry.get("phase_before") == outcome.get("state_before")
                and entry.get("phase_after") == outcome.get("state_after")
            ):
                decision_id = entry.get("decision_id")
                if isinstance(decision_id, str):
                    matching_ids.append(decision_id)
    if not matching_ids:
        return [
            search,
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[
                    {
                        "field": "decision_ledger",
                        "message": "no validated entry matches the current task, run, outcome status, scope, and phases",
                    }
                ],
            ),
        ]
    return [
        search,
        ContractRun(
            name="decision-ledger-closeout-match",
            returncode=0,
            stdout=json.dumps({"ok": True, "matching_decision_ids": matching_ids}, sort_keys=True),
            stderr="",
            parsed={"ok": True, "matching_decision_ids": matching_ids},
        ),
    ]


def _summarize_failure(card: ActiveTaskCard, runs: list[ContractRun]) -> str:
    details: list[str] = []
    for run in runs:
        if run.returncode == 0 and run.parsed is not None and run.parsed.get("ok", True):
            continue
        run_details = _issue_messages(run.parsed)
        if not run_details and run.stderr:
            run_details = [run.stderr[:500]]
        if not run_details and run.stdout and run.parsed is None:
            run_details = [f"{run.name} emitted non-JSON output"]
        if not run_details:
            run_details = [f"{run.name} exited {run.returncode}"]
        details.append(f"{run.name}: {'; '.join(run_details)}")

    reason = "; ".join(details) if details else "contract check failed"
    return f"Tenn agent-job contract blocked {card.display_path}: {reason}"


def _allow_payload(platform: str, message: str | None = None) -> dict[str, str]:
    if platform == "gemini":
        payload = {"decision": "allow"}
        if message:
            payload["additionalContext"] = message
        return payload

    if message:
        return {"systemMessage": message}
    return {}


def _blocking_payload(message: str, *, platform: str = "codex") -> dict[str, str]:
    if platform == "gemini":
        return {
            "decision": "block",
            "reason": message,
            "additionalContext": message,
        }

    return {
        "decision": "block",
        "reason": message,
        "systemMessage": message,
    }


def build_hook_payload(
    *,
    repo_root: Path,
    env: Mapping[str, str] | None = None,
    platform: str = "codex",
    event: str = "Stop",
) -> dict[str, Any]:
    control_plane_root = _resolve_control_plane_root()
    card = find_active_task_card(repo_root, env=env)
    if card is None:
        return _allow_payload(platform)

    if not card.path.exists():
        message = f"Tenn agent-job contract warning: task card not found: {card.display_path}"
        if event in {"Stop", "SessionEnd"}:
            return _allow_payload(platform, message)
        return _blocking_payload(message, platform=platform)

    validate = _run_contract(
        control_plane_root,
        repo_root,
        "validate",
        ["validate", card.display_path],
    )
    strict_contract = _task_card_requires_strict_closeout(card, validate)
    list_active = _run_registry(
        control_plane_root,
        repo_root,
        "list-active",
        ["list-active", "--read-only", "--repo-root", str(repo_root)],
    )
    runs = [validate, list_active]

    if event == "BeforeTool":
        check_diff = _run_contract(
            control_plane_root,
            repo_root,
            "check-diff",
            ["check-diff", card.display_path, "--repo-root", str(repo_root), "--no-write-report"],
        )
        runs.append(check_diff)
    elif event in {"Stop", "SessionEnd"}:
        closeout = _run_contract(
            control_plane_root,
            repo_root,
            "check-closeout",
            ["check-closeout", card.display_path, "--repo-root", str(repo_root)],
        )
        runs.append(closeout)
        metadata = validate.parsed.get("metadata") if validate.parsed else None
        if (
            isinstance(metadata, Mapping)
            and type(metadata.get("control_contract_version")) is int
            and metadata.get("control_contract_version") == 2
        ):
            decision_ledger = _run_decision_ledger(
                control_plane_root,
                repo_root,
                "decision-ledger-validate",
                ["validate", "--repo-root", str(repo_root)],
            )
            runs.append(decision_ledger)
            if (
                closeout.returncode == 0
                and closeout.parsed is not None
                and closeout.parsed.get("ok") is True
                and decision_ledger.returncode == 0
                and decision_ledger.parsed is not None
                and decision_ledger.parsed.get("ok") is True
            ):
                runs.extend(
                    _v2_decision_closeout_runs(
                        control_plane_root,
                        repo_root,
                        metadata=metadata,
                        list_active=list_active,
                    )
                )

    passed = all(
        run.returncode == 0 and run.parsed is not None and run.parsed.get("ok", False)
        for run in runs
    )
    if not passed:
        message = _summarize_failure(card, runs)
        if event in {"Stop", "SessionEnd"} and not strict_contract:
            return _allow_payload(platform, message)
        return _blocking_payload(message, platform=platform)

    if event in {"Stop", "SessionEnd"}:
        return _allow_payload(platform)

    if platform == "codex" and event == "Stop":
        return _allow_payload(platform)

    return _allow_payload(platform, f"Tenn agent-job contract passed: {card.display_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("codex", "claude", "gemini"), default="codex")
    parser.add_argument("--event", choices=("Stop", "SessionEnd", "BeforeTool"), default="Stop")
    parser.add_argument("--repo-root", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _read_hook_stdin()
        repo_root = _resolve_repo_root(args.repo_root)
        payload = build_hook_payload(repo_root=repo_root, platform=args.platform, event=args.event)
    except Exception as exc:
        payload = _blocking_payload(f"Tenn agent-job hook failed: {exc}", platform=args.platform)

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
