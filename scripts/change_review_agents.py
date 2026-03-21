#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = REPO_ROOT / "reports" / "change_review_agents"
ROLE_CHOICES = ("consistency", "validation", "planner", "all")
HIGH = "high"
MEDIUM = "medium"
LOW = "low"
INFO = "info"
CRITICAL_PATH_PREFIXES = (
    "financial-engine_v2/backend/app/services/",
    "financial-engine_v2/backend/app/api/",
    "financial-engine_v2/backend/app/core/",
    "scripts/news_pipeline/",
)


@dataclass
class CommandResult:
    label: str
    command: str
    exit_code: int | None
    status: str
    summary: str
    output_excerpt: str


@dataclass
class Finding:
    severity: str
    reviewer: str
    title: str
    details: str
    files: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class ChangeSummary:
    branch: str
    head_sha: str
    timestamp_utc: str
    signature: str
    event_id: str
    status_lines: list[str]
    tracked_files: list[str]
    untracked_files: list[str]
    changed_files: list[str]
    diff_stat: str
    diff_check_output: str
    dirty: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    pieces = []
    for char in value:
        pieces.append(char if char.isalnum() else "-")
    compact = "".join(pieces).strip("-")
    return compact or "detached"


def trim_output(text: str, max_chars: int = 6000, tail_lines: int = 40) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""
    lines = clean.splitlines()
    if len(lines) > tail_lines:
        clean = "\n".join(lines[-tail_lines:])
    if len(clean) > max_chars:
        clean = clean[-max_chars:]
    return clean


def severity_rank(value: str) -> int:
    order = {HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3}
    return order.get(value, 9)


def resolve_python_executable(repo_root: Path) -> str:
    candidates = [
        os.environ.get("CHANGE_REVIEW_PYTHON", "").strip(),
        os.environ.get("VIRTUAL_ENV", "").strip(),
        str(repo_root / "financial-engine_v2" / ".venv" / "bin" / "python"),
        str(repo_root / ".venv" / "bin" / "python"),
        sys.executable,
        shutil.which("python3") or "",
    ]
    for candidate in candidates:
        value = str(candidate or "").strip()
        if not value:
            continue
        path = Path(value)
        if path.is_dir():
            path = path / "bin" / "python"
            value = str(path)
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return sys.executable


def run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int = 30,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=check,
    )


def run_optional_command(
    label: str,
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> CommandResult:
    command = shlex.join(args)
    try:
        completed = run_command(args, cwd=cwd, timeout_seconds=timeout_seconds)
    except FileNotFoundError:
        return CommandResult(
            label=label,
            command=command,
            exit_code=None,
            status="skipped",
            summary="required executable was not available",
            output_excerpt="",
        )
    except subprocess.TimeoutExpired as exc:
        combined = f"{exc.stdout or ''}\n{exc.stderr or ''}"
        return CommandResult(
            label=label,
            command=command,
            exit_code=None,
            status="timeout",
            summary=f"timed out after {timeout_seconds}s",
            output_excerpt=trim_output(combined),
        )

    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    status = "passed" if completed.returncode == 0 else "failed"
    summary = "completed successfully" if completed.returncode == 0 else f"exited with code {completed.returncode}"
    return CommandResult(
        label=label,
        command=command,
        exit_code=completed.returncode,
        status=status,
        summary=summary,
        output_excerpt=trim_output(combined),
    )


def git_lines(args: Sequence[str], *, cwd: Path) -> list[str]:
    completed = run_command(("git", *args), cwd=cwd, timeout_seconds=30, check=False)
    if completed.returncode != 0:
        message = trim_output("\n".join(part for part in (completed.stdout, completed.stderr) if part))
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return [line for line in completed.stdout.splitlines() if line.strip()]


def git_text(args: Sequence[str], *, cwd: Path) -> str:
    completed = run_command(("git", *args), cwd=cwd, timeout_seconds=60, check=False)
    if completed.returncode != 0:
        message = trim_output("\n".join(part for part in (completed.stdout, completed.stderr) if part))
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return completed.stdout


def snapshot_changes(repo_root: Path) -> ChangeSummary:
    branch = git_text(("rev-parse", "--abbrev-ref", "HEAD"), cwd=repo_root).strip() or "HEAD"
    head_sha = git_text(("rev-parse", "HEAD"), cwd=repo_root).strip()
    status_lines = git_lines(("status", "--short", "--untracked-files=all"), cwd=repo_root)
    tracked_files = git_lines(("diff", "--name-only", "HEAD"), cwd=repo_root)
    untracked_files = git_lines(("ls-files", "--others", "--exclude-standard"), cwd=repo_root)
    changed_files = sorted(dict.fromkeys(tracked_files + untracked_files))
    diff_stat = git_text(("diff", "--stat", "HEAD"), cwd=repo_root).strip()

    diff_check = run_optional_command(
        "git_diff_check",
        ("git", "diff", "--check", "HEAD"),
        cwd=repo_root,
        timeout_seconds=30,
    )
    diff_check_output = diff_check.output_excerpt if diff_check.status != "passed" else ""

    dirty = bool(status_lines)
    signature_source = "\n".join(status_lines) if dirty else f"clean:{head_sha}"
    signature = hashlib.sha256(signature_source.encode("utf-8")).hexdigest()[:12]
    event_id = f"{slugify(branch)}-{signature}"
    return ChangeSummary(
        branch=branch,
        head_sha=head_sha,
        timestamp_utc=utc_now(),
        signature=signature,
        event_id=event_id,
        status_lines=status_lines,
        tracked_files=tracked_files,
        untracked_files=untracked_files,
        changed_files=changed_files,
        diff_stat=diff_stat,
        diff_check_output=diff_check_output,
        dirty=dirty,
    )


def looks_like_test_file(path: str) -> bool:
    file_name = Path(path).name
    if file_name == "conftest.py":
        return False
    return (
        file_name.startswith("test_")
        or "/tests/" in path
        or path.startswith("scripts/test_")
        or path.startswith("autodev/tests/")
    )


def classify_paths(paths: Iterable[str]) -> dict[str, list[str]]:
    buckets = {
        "docs": [],
        "tests": [],
        "python": [],
        "backend": [],
        "cockpit": [],
        "scripts": [],
        "critical": [],
    }
    for path in sorted(dict.fromkeys(paths)):
        if path.endswith(".md") or path.startswith("docs/"):
            buckets["docs"].append(path)
        if looks_like_test_file(path):
            buckets["tests"].append(path)
        if path.endswith(".py"):
            buckets["python"].append(path)
        if path.startswith("financial-engine_v2/backend/"):
            buckets["backend"].append(path)
        if path.startswith("financial-engine_v2/cockpit/"):
            buckets["cockpit"].append(path)
        if path.startswith("scripts/"):
            buckets["scripts"].append(path)
        if path.startswith(CRITICAL_PATH_PREFIXES):
            buckets["critical"].append(path)
    return buckets


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def read_last_jsonl_record(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last_line = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            candidate = line.strip()
            if candidate:
                last_line = candidate
    if not last_line:
        return None
    return json.loads(last_line)


def build_untracked_preview(repo_root: Path, files: Sequence[str], max_lines: int = 40) -> str:
    blocks: list[str] = []
    for relative_path in files:
        target = repo_root / relative_path
        if not target.exists():
            blocks.append(f"## {relative_path}\nmissing on disk\n")
            continue
        if target.is_dir():
            blocks.append(f"## {relative_path}\ndirectory\n")
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            blocks.append(f"## {relative_path}\nbinary or non-utf8 content\n")
            continue
        excerpt = "\n".join(text.splitlines()[:max_lines]).strip()
        blocks.append(f"## {relative_path}\n{excerpt}\n")
    return "\n".join(blocks).strip()


def persist_common_event_artifacts(summary: ChangeSummary, repo_root: Path, state_dir: Path) -> Path:
    event_dir = state_dir / "events" / summary.event_id
    event_dir.mkdir(parents=True, exist_ok=True)
    metadata = asdict(summary)
    write_json(event_dir / "summary.json", metadata)
    write_text(event_dir / "status.txt", "\n".join(summary.status_lines).strip() + "\n")
    write_text(event_dir / "diff_stat.txt", (summary.diff_stat or "").strip() + "\n")
    tracked_patch = git_text(("diff", "--no-color", "--unified=3", "HEAD"), cwd=repo_root)
    write_text(event_dir / "tracked.diff", tracked_patch)
    if summary.untracked_files:
        write_text(event_dir / "untracked_files.txt", "\n".join(summary.untracked_files) + "\n")
        write_text(event_dir / "untracked_preview.md", build_untracked_preview(repo_root, summary.untracked_files))
    return event_dir


def make_finding(
    reviewer: str,
    severity: str,
    title: str,
    details: str,
    *,
    files: Sequence[str] | None = None,
    evidence: Sequence[str] | None = None,
) -> Finding:
    return Finding(
        reviewer=reviewer,
        severity=severity,
        title=title,
        details=details.strip(),
        files=list(files or []),
        evidence=list(evidence or []),
    )


def build_consistency_findings(summary: ChangeSummary) -> list[Finding]:
    findings: list[Finding] = []
    buckets = classify_paths(summary.changed_files)
    has_code_changes = bool(buckets["backend"] or buckets["scripts"] or buckets["cockpit"])
    has_test_changes = bool(buckets["tests"])
    has_docs_changes = bool(buckets["docs"])
    domain_count = sum(bool(paths) for paths in (buckets["docs"], buckets["backend"], buckets["cockpit"], buckets["scripts"]))

    if summary.diff_check_output:
        findings.append(
            make_finding(
                "consistency",
                HIGH,
                "Patch hygiene issues detected",
                "git diff --check reported patch formatting or conflict-marker problems.",
                files=summary.changed_files,
                evidence=[summary.diff_check_output],
            )
        )
    if buckets["critical"] and not has_test_changes:
        findings.append(
            make_finding(
                "consistency",
                MEDIUM,
                "Critical runtime paths changed without test updates",
                "A critical runtime surface changed in the worktree, but the same change set does not include test updates.",
                files=buckets["critical"],
                evidence=["No changed test files were detected in the current worktree snapshot."],
            )
        )
    if has_code_changes and not has_test_changes and not buckets["critical"]:
        findings.append(
            make_finding(
                "consistency",
                LOW,
                "Code changes are not paired with test changes",
                "The change set touches executable code without any changed tests in the same diff. This is a review flag, not proof of breakage.",
                files=buckets["backend"] + buckets["scripts"] + buckets["cockpit"],
            )
        )
    if buckets["critical"] and not has_docs_changes:
        findings.append(
            make_finding(
                "consistency",
                LOW,
                "Critical change set has no matching docs update",
                "A critical runtime surface changed without any docs or architecture files in the same diff. Confirm whether the change is intentionally implementation-only.",
                files=buckets["critical"],
            )
        )
    if len(summary.changed_files) >= 10 and domain_count >= 3:
        findings.append(
            make_finding(
                "consistency",
                LOW,
                "Cross-domain change set is broad",
                "The current worktree spans multiple domains, which increases review and validation surface area.",
                files=summary.changed_files,
                evidence=[summary.diff_stat] if summary.diff_stat else [],
            )
        )
    if summary.untracked_files:
        findings.append(
            make_finding(
                "consistency",
                INFO,
                "Untracked files are present",
                "Untracked files are part of the monitored worktree state but are easy to miss in a normal tracked diff review.",
                files=summary.untracked_files,
            )
        )
    return sorted(findings, key=lambda item: (severity_rank(item.severity), item.title))


def discover_test_targets(changed_files: Sequence[str], repo_root: Path, max_targets: int = 6) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add_target(path: Path) -> None:
        if not path.exists() or not path.is_file():
            return
        relative = str(path.relative_to(repo_root))
        if relative in seen:
            return
        seen.add(relative)
        candidates.append(relative)

    for relative_path in changed_files:
        path = Path(relative_path)
        if looks_like_test_file(relative_path):
            add_target(repo_root / relative_path)

    for relative_path in changed_files:
        if len(candidates) >= max_targets:
            break
        if not relative_path.endswith(".py") or looks_like_test_file(relative_path):
            continue
        path = Path(relative_path)
        if relative_path.startswith("scripts/"):
            add_target(repo_root / "scripts" / f"test_{path.stem}.py")
        if relative_path.startswith("financial-engine_v2/backend/"):
            tests_root = repo_root / "financial-engine_v2" / "backend" / "tests"
            if tests_root.exists():
                for match in sorted(tests_root.rglob(f"*{path.stem}*.py")):
                    add_target(match)
                    if len(candidates) >= max_targets:
                        break
        if relative_path.startswith("autodev/"):
            tests_root = repo_root / "autodev" / "tests"
            if tests_root.exists():
                add_target(tests_root / f"test_{path.stem}.py")
        if len(candidates) >= max_targets:
            break
    return candidates


def resolve_ruff_command(repo_root: Path, python_bin: str) -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    probe = run_optional_command(
        "ruff_probe",
        (python_bin, "-m", "ruff", "--version"),
        cwd=repo_root,
        timeout_seconds=15,
    )
    if probe.status == "passed":
        return [python_bin, "-m", "ruff"]
    return None


def build_validation_results(summary: ChangeSummary, repo_root: Path) -> list[CommandResult]:
    results: list[CommandResult] = []
    python_bin = resolve_python_executable(repo_root)
    py_files = [path for path in summary.changed_files if path.endswith(".py") and (repo_root / path).exists()]
    if summary.diff_check_output:
        results.append(
            CommandResult(
                label="git_diff_check",
                command="git diff --check HEAD",
                exit_code=1,
                status="failed",
                summary="git diff --check reported patch issues",
                output_excerpt=summary.diff_check_output,
            )
        )
    else:
        results.append(
            CommandResult(
                label="git_diff_check",
                command="git diff --check HEAD",
                exit_code=0,
                status="passed",
                summary="completed successfully",
                output_excerpt="",
            )
        )
    if py_files:
        compile_cmd = [python_bin, "-m", "py_compile", *py_files]
        results.append(run_optional_command("py_compile", compile_cmd, cwd=repo_root, timeout_seconds=60))

        ruff_cmd = resolve_ruff_command(repo_root, python_bin)
        if ruff_cmd is None:
            results.append(
                CommandResult(
                    label="ruff",
                    command="ruff check <changed python files>",
                    exit_code=None,
                    status="skipped",
                    summary="ruff was not available in PATH or as a Python module",
                    output_excerpt="",
                )
            )
        else:
            results.append(
                run_optional_command(
                    "ruff",
                    (*ruff_cmd, "check", *py_files),
                    cwd=repo_root,
                    timeout_seconds=120,
                )
            )

    test_targets = discover_test_targets(summary.changed_files, repo_root)
    if test_targets:
        results.append(
            run_optional_command(
                "pytest_targeted",
                (python_bin, "-m", "pytest", "-q", *test_targets),
                cwd=repo_root,
                timeout_seconds=300,
            )
        )
    else:
        results.append(
            CommandResult(
                label="pytest_targeted",
                command="python -m pytest -q <derived test targets>",
                exit_code=None,
                status="skipped",
                summary="no direct test targets were derived from the changed files",
                output_excerpt="",
            )
        )
    return results


def build_validation_findings(results: Sequence[CommandResult]) -> list[Finding]:
    findings: list[Finding] = []
    for result in results:
        if result.status == "failed":
            findings.append(
                make_finding(
                    "validation",
                    HIGH,
                    f"{result.label} failed",
                    result.summary,
                    evidence=[result.command, result.output_excerpt] if result.output_excerpt else [result.command],
                )
            )
        elif result.status == "timeout":
            findings.append(
                make_finding(
                    "validation",
                    HIGH,
                    f"{result.label} timed out",
                    result.summary,
                    evidence=[result.command, result.output_excerpt] if result.output_excerpt else [result.command],
                )
            )
        elif result.status == "skipped":
            findings.append(
                make_finding(
                    "validation",
                    INFO,
                    f"{result.label} skipped",
                    result.summary,
                    evidence=[result.command],
                )
            )
    return sorted(findings, key=lambda item: (severity_rank(item.severity), item.title))


def load_role_payload(event_dir: Path, role: str) -> dict[str, Any] | None:
    path = event_dir / f"{role}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_planner_payload(summary: ChangeSummary, event_dir: Path) -> dict[str, Any]:
    consistency_payload = load_role_payload(event_dir, "consistency") or {}
    validation_payload = load_role_payload(event_dir, "validation") or {}
    consistency_findings = [Finding(**item) for item in consistency_payload.get("findings", [])]
    validation_findings = [Finding(**item) for item in validation_payload.get("findings", [])]
    validation_results = [CommandResult(**item) for item in validation_payload.get("results", [])]

    prioritized_findings = sorted(consistency_findings + validation_findings, key=lambda item: (severity_rank(item.severity), item.title))
    steps: list[str] = []
    if any(item.severity == HIGH for item in prioritized_findings):
        steps.append("Inspect the highest-severity findings in the current event directory before making further unrelated edits.")
    failing_results = [result for result in validation_results if result.status in {"failed", "timeout"}]
    if failing_results:
        failed_labels = ", ".join(result.label for result in failing_results)
        steps.append(f"Reproduce and repair the failing validation commands: {failed_labels}.")
    if any(item.title == "Critical runtime paths changed without test updates" for item in consistency_findings):
        steps.append("Add or update targeted tests for the critical runtime files in this change set.")
    if any(item.title == "Critical change set has no matching docs update" for item in consistency_findings):
        steps.append("Confirm whether an architecture or runbook update is required for the critical runtime changes.")
    if not steps:
        steps.append("No blocking issues were detected; continue development and let the monitor watch for the next change.")

    subagents: list[dict[str, str]] = []
    subagents.append(
        {
            "name": "change_issue_triage_agent",
            "scope": f"reports/change_review_agents/events/{summary.event_id}/",
            "task": "Use .cursor/agents/change_issue_triage.md to extract the diff context, validate the highest-severity review flags, and return a minimal repair plan.",
        }
    )
    if failing_results:
        subagents.append(
            {
                "name": "validation_failure_investigator",
                "scope": f"reports/change_review_agents/events/{summary.event_id}/validation.json",
                "task": "Focus on the failing validation commands, reproduce the failure mode from the saved output, and identify the narrowest file-level fix.",
            }
        )
    if summary.changed_files:
        subagents.append(
            {
                "name": "repair_worker",
                "scope": ", ".join(summary.changed_files[:6]),
                "task": "After the issue is confirmed, implement the smallest possible fix and rerun the targeted validators recorded for this event.",
            }
        )

    highest = prioritized_findings[0].severity if prioritized_findings else INFO
    return {
        "event_id": summary.event_id,
        "branch": summary.branch,
        "timestamp_utc": summary.timestamp_utc,
        "highest_severity": highest,
        "priority_steps": steps,
        "subagents": subagents,
        "finding_count": len(prioritized_findings),
    }


def render_findings_markdown(summary: ChangeSummary, findings: Sequence[Finding], reviewer: str) -> str:
    lines = [
        f"# {reviewer.title()} Review",
        "",
        f"- Event: `{summary.event_id}`",
        f"- Branch: `{summary.branch}`",
        f"- Head: `{summary.head_sha[:12]}`",
        f"- Timestamp: `{summary.timestamp_utc}`",
        f"- Changed files: `{len(summary.changed_files)}`",
        "",
    ]
    if not findings:
        lines.append("No issues detected by this reviewer.")
        lines.append("")
        return "\n".join(lines)

    for index, finding in enumerate(findings, start=1):
        lines.append(f"## {index}. [{finding.severity}] {finding.title}")
        lines.append(finding.details)
        if finding.files:
            lines.append("")
            lines.append("Files:")
            for path in finding.files:
                lines.append(f"- `{path}`")
        if finding.evidence:
            lines.append("")
            lines.append("Evidence:")
            for item in finding.evidence:
                lines.append(f"- `{trim_output(item, max_chars=500, tail_lines=10)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_validation_markdown(summary: ChangeSummary, results: Sequence[CommandResult], findings: Sequence[Finding]) -> str:
    lines = [
        "# Validation Review",
        "",
        f"- Event: `{summary.event_id}`",
        f"- Branch: `{summary.branch}`",
        f"- Timestamp: `{summary.timestamp_utc}`",
        "",
    ]
    for result in results:
        lines.append(f"## {result.label} [{result.status}]")
        lines.append(f"- Command: `{result.command}`")
        lines.append(f"- Summary: {result.summary}")
        if result.output_excerpt:
            lines.append("- Output excerpt:")
            lines.append("```text")
            lines.append(result.output_excerpt)
            lines.append("```")
        lines.append("")
    if findings:
        lines.append("## Findings")
        lines.append("")
        for finding in findings:
            lines.append(f"- [{finding.severity}] {finding.title}: {finding.details}")
    return "\n".join(lines).rstrip() + "\n"


def render_planner_markdown(summary: ChangeSummary, payload: dict[str, Any]) -> str:
    lines = [
        "# Repair Plan",
        "",
        f"- Event: `{summary.event_id}`",
        f"- Branch: `{summary.branch}`",
        f"- Highest severity: `{payload['highest_severity']}`",
        "",
        "## Priority Steps",
        "",
    ]
    for index, step in enumerate(payload["priority_steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Suggested Subagents", ""])
    for agent in payload["subagents"]:
        lines.append(f"- `{agent['name']}`")
        lines.append(f"  Scope: `{agent['scope']}`")
        lines.append(f"  Task: {agent['task']}")
    lines.append("")
    return "\n".join(lines)


def render_overview(summary: ChangeSummary, event_dir: Path, state_dir: Path) -> str:
    consistency_payload = load_role_payload(event_dir, "consistency") or {}
    validation_payload = load_role_payload(event_dir, "validation") or {}
    planner_payload = load_role_payload(event_dir, "planner") or {}
    external_findings_path = event_dir / "external_agent_findings.md"
    latest_external_findings_path = state_dir / "latest" / "external_agent_findings.md"
    consistency_findings = consistency_payload.get("findings", [])
    validation_findings = validation_payload.get("findings", [])
    validation_results = validation_payload.get("results", [])
    planner_steps = planner_payload.get("priority_steps", [])

    combined_findings = sorted(
        [Finding(**item) for item in consistency_findings + validation_findings],
        key=lambda item: (severity_rank(item.severity), item.title),
    )
    top_severity = combined_findings[0].severity if combined_findings else INFO
    lines = [
        "# Change Review Overview",
        "",
        f"- Event: `{summary.event_id}`",
        f"- Branch: `{summary.branch}`",
        f"- Head: `{summary.head_sha[:12]}`",
        f"- Highest severity: `{top_severity}`",
        f"- Changed files: `{len(summary.changed_files)}`",
        "",
        "## Changed Files",
        "",
    ]
    if summary.changed_files:
        for path in summary.changed_files:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Findings", ""])
    if combined_findings:
        for finding in combined_findings:
            lines.append(f"- [{finding.severity}] {finding.title}")
    else:
        lines.append("- No issues detected.")
    lines.extend(["", "## Validation Status", ""])
    if validation_results:
        for result in validation_results:
            lines.append(f"- `{result['label']}`: `{result['status']}`")
    else:
        lines.append("- No validation results yet.")
    lines.extend(["", "## Priority Steps", ""])
    if planner_steps:
        for step in planner_steps:
            lines.append(f"- {step}")
    else:
        lines.append("- Waiting for planner output.")
    external_review_paths: list[str] = []
    if external_findings_path.exists():
        external_review_paths.append(f"reports/change_review_agents/events/{summary.event_id}/external_agent_findings.md")
    if latest_external_findings_path.exists():
        latest_external = "reports/change_review_agents/latest/external_agent_findings.md"
        if latest_external not in external_review_paths:
            external_review_paths.append(latest_external)
    if external_review_paths:
        lines.extend(
            [
                "",
                "## External Reviews",
                "",
            ]
        )
        for external_review_path in external_review_paths:
            lines.append(f"- `{external_review_path}`")
    lines.extend(
        [
            "",
            "## Event Files",
            "",
            f"- Summary: `reports/change_review_agents/events/{summary.event_id}/summary.json`",
            f"- Diff: `reports/change_review_agents/events/{summary.event_id}/tracked.diff`",
            f"- Plan: `reports/change_review_agents/events/{summary.event_id}/planner.md`",
        ]
    )
    if external_findings_path.exists():
        lines.append(f"- External findings: `reports/change_review_agents/events/{summary.event_id}/external_agent_findings.md`")
    lines.append("")
    return "\n".join(lines)


def persist_role_output(
    summary: ChangeSummary,
    state_dir: Path,
    role: str,
    payload: dict[str, Any],
    markdown: str,
) -> None:
    event_dir = state_dir / "events" / summary.event_id
    write_json(event_dir / f"{role}.json", payload)
    write_text(event_dir / f"{role}.md", markdown)
    latest_dir = state_dir / "latest"
    write_json(latest_dir / f"{role}.json", payload)
    write_text(latest_dir / f"{role}.md", markdown)
    overview = render_overview(summary, event_dir, state_dir)
    write_text(latest_dir / "overview.md", overview)


def write_alert(summary: ChangeSummary, state_dir: Path, planner_payload: dict[str, Any]) -> None:
    alerts_path = state_dir / "alerts.jsonl"
    record = {
        "branch": summary.branch,
        "event_id": summary.event_id,
        "highest_severity": planner_payload["highest_severity"],
        "priority_steps": planner_payload["priority_steps"],
        "timestamp_utc": summary.timestamp_utc,
    }
    previous = read_last_jsonl_record(alerts_path)
    if previous is not None and all(previous.get(key) == record.get(key) for key in ("branch", "event_id", "highest_severity", "priority_steps")):
        return
    append_jsonl(alerts_path, record)


def run_consistency_role(summary: ChangeSummary, repo_root: Path, state_dir: Path) -> None:
    findings = build_consistency_findings(summary)
    payload = {
        "event_id": summary.event_id,
        "branch": summary.branch,
        "timestamp_utc": summary.timestamp_utc,
        "findings": [asdict(item) for item in findings],
    }
    markdown = render_findings_markdown(summary, findings, "consistency")
    persist_role_output(summary, state_dir, "consistency", payload, markdown)


def run_validation_role(summary: ChangeSummary, repo_root: Path, state_dir: Path) -> None:
    results = build_validation_results(summary, repo_root)
    findings = build_validation_findings(results)
    payload = {
        "event_id": summary.event_id,
        "branch": summary.branch,
        "timestamp_utc": summary.timestamp_utc,
        "results": [asdict(item) for item in results],
        "findings": [asdict(item) for item in findings],
    }
    markdown = render_validation_markdown(summary, results, findings)
    persist_role_output(summary, state_dir, "validation", payload, markdown)


def run_planner_role(summary: ChangeSummary, repo_root: Path, state_dir: Path) -> None:
    payload = build_planner_payload(summary, state_dir / "events" / summary.event_id)
    markdown = render_planner_markdown(summary, payload)
    persist_role_output(summary, state_dir, "planner", payload, markdown)
    write_alert(summary, state_dir, payload)


def run_role(role: str, summary: ChangeSummary, repo_root: Path, state_dir: Path) -> None:
    persist_common_event_artifacts(summary, repo_root, state_dir)
    if role == "consistency":
        run_consistency_role(summary, repo_root, state_dir)
    elif role == "validation":
        run_validation_role(summary, repo_root, state_dir)
    elif role == "planner":
        run_planner_role(summary, repo_root, state_dir)
    elif role == "all":
        run_consistency_role(summary, repo_root, state_dir)
        run_validation_role(summary, repo_root, state_dir)
        run_planner_role(summary, repo_root, state_dir)
    else:
        raise ValueError(f"Unsupported role: {role}")


def last_seen_path(state_dir: Path, role: str) -> Path:
    return state_dir / "state" / f"{role}.last_signature"


def load_last_seen_signature(state_dir: Path, role: str) -> str:
    path = last_seen_path(state_dir, role)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def store_last_seen_signature(state_dir: Path, role: str, signature: str) -> None:
    write_text(last_seen_path(state_dir, role), signature + "\n")


def planner_output_is_stale(summary: ChangeSummary, state_dir: Path) -> bool:
    event_dir = state_dir / "events" / summary.event_id
    planner_path = event_dir / "planner.json"
    if not planner_path.exists():
        return True
    planner_mtime = planner_path.stat().st_mtime
    for dependency_name in ("consistency.json", "validation.json"):
        dependency_path = event_dir / dependency_name
        if dependency_path.exists() and dependency_path.stat().st_mtime > planner_mtime:
            return True
    return False


def should_run_role(role: str, summary: ChangeSummary, state_dir: Path, previous_signature: str) -> bool:
    if summary.signature != previous_signature:
        return True
    if role == "planner" and planner_output_is_stale(summary, state_dir):
        return True
    return False


def log_watch_error(role: str, exc: Exception) -> None:
    print(f"[{utc_now()}] [change-review] {role} error: {exc}", file=sys.stderr, flush=True)


def watch(role: str, repo_root: Path, state_dir: Path, poll_seconds: float, once: bool) -> int:
    if role not in ROLE_CHOICES:
        raise ValueError(f"Unsupported role: {role}")
    state_dir.mkdir(parents=True, exist_ok=True)
    while True:
        had_error = False
        try:
            summary = snapshot_changes(repo_root)
            previous = load_last_seen_signature(state_dir, role)
            if should_run_role(role, summary, state_dir, previous):
                run_role(role, summary, repo_root, state_dir)
                store_last_seen_signature(state_dir, role, summary.signature)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            had_error = True
            log_watch_error(role, exc)
        if once:
            return 1 if had_error else 0
        time.sleep(poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persistent change-review agents for the TENN worktree.")
    parser.add_argument("--role", choices=ROLE_CHOICES, default="all", help="Reviewer role to run.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Output directory for events and latest summaries.")
    parser.add_argument("--poll-seconds", type=float, default=6.0, help="Polling interval while watching.")
    parser.add_argument("--once", action="store_true", help="Analyze the current worktree once and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    state_dir = Path(args.state_dir).resolve()
    return watch(args.role, repo_root, state_dir, poll_seconds=max(1.0, args.poll_seconds), once=bool(args.once))


if __name__ == "__main__":
    raise SystemExit(main())
