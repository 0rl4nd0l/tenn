#!/usr/bin/env python3
"""Validate non-production Codex/dev agent task cards and watchdog state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only when dependency is absent
    yaml = None


VALID_LANES = {
    "Financial Truth",
    "Evaluation",
    "Provenance",
    "Query Orchestration",
    "Memory",
    "Reporting",
}
VALID_MUTATION_MODES = {"audit_only", "safe_extension", "blocked"}
REQUIRED_FIELDS = {
    "job_id",
    "lane",
    "owner",
    "allowed_files",
    "approval_required",
    "timeout_seconds",
    "output_dir",
    "mutation_mode",
    "production_data_access",
}
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    metadata: dict[str, Any]
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "metadata": self.metadata,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class ParsedTaskCard:
    frontmatter_block: str
    frontmatter_yaml: str
    body: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class WatchdogState:
    timeout_seconds: int
    max_timeout_streak: int
    started_at: str
    ended_at: str | None
    status: str
    abort_reason: str | None
    timeout_streak: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_yaml() -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse task-card frontmatter but is not available")


def parse_task_card(markdown: str) -> ParsedTaskCard:
    """Parse a Markdown task card with YAML frontmatter."""
    _require_yaml()
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        raise ValueError("missing_yaml_frontmatter")

    raw_yaml = match.group("yaml")
    loaded = yaml.safe_load(raw_yaml)  # type: ignore[union-attr]
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter_must_be_mapping")

    return ParsedTaskCard(
        frontmatter_block=markdown[: match.end()],
        frontmatter_yaml=raw_yaml,
        body=markdown[match.end() :],
        metadata=dict(loaded),
    )


def replace_body_preserving_frontmatter(markdown: str, new_body: str) -> str:
    """Replace Markdown body text while preserving frontmatter bytes unchanged."""
    parsed = parse_task_card(markdown)
    body = new_body
    if body and not body.startswith(("\n", "\r\n")):
        body = "\n" + body
    if body and not body.endswith("\n"):
        body += "\n"
    return f"{parsed.frontmatter_block}{body}"


def validate_task_card_markdown(markdown: str) -> ValidationResult:
    try:
        parsed = parse_task_card(markdown)
    except ValueError as exc:
        return ValidationResult(
            ok=False,
            metadata={},
            issues=[ValidationIssue("frontmatter", str(exc))],
        )

    metadata = parsed.metadata
    issues: list[ValidationIssue] = []
    missing = sorted(field for field in REQUIRED_FIELDS if field not in metadata)
    for field in missing:
        issues.append(ValidationIssue(field, "required field is missing"))

    job_id = metadata.get("job_id")
    if not isinstance(job_id, str) or not job_id.strip():
        issues.append(ValidationIssue("job_id", "must be a non-empty string"))
        job_id_text = ""
    else:
        job_id_text = job_id.strip()
        if not JOB_ID_RE.fullmatch(job_id_text):
            issues.append(ValidationIssue("job_id", "must contain only letters, numbers, dot, underscore, or dash"))

    lane = metadata.get("lane")
    if lane is not None and lane not in VALID_LANES:
        issues.append(ValidationIssue("lane", f"must be one of: {', '.join(sorted(VALID_LANES))}"))

    owner = metadata.get("owner")
    if owner is not None and (not isinstance(owner, str) or not owner.strip()):
        issues.append(ValidationIssue("owner", "must be a non-empty string"))

    allowed_files = metadata.get("allowed_files")
    if allowed_files is not None:
        if not isinstance(allowed_files, list) or not allowed_files:
            issues.append(ValidationIssue("allowed_files", "must be a non-empty list"))
        else:
            for idx, item in enumerate(allowed_files):
                if not isinstance(item, str) or not item.strip():
                    issues.append(ValidationIssue(f"allowed_files[{idx}]", "must be a non-empty string"))

    approval_required = metadata.get("approval_required")
    if approval_required is not None and not isinstance(approval_required, bool):
        issues.append(ValidationIssue("approval_required", "must be a boolean"))

    timeout_seconds = metadata.get("timeout_seconds")
    if timeout_seconds is not None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            issues.append(ValidationIssue("timeout_seconds", "must be a positive integer"))

    mutation_mode = metadata.get("mutation_mode")
    if mutation_mode is not None and mutation_mode not in VALID_MUTATION_MODES:
        issues.append(ValidationIssue("mutation_mode", "must be audit_only, safe_extension, or blocked"))

    if metadata.get("production_data_access") is not False:
        issues.append(ValidationIssue("production_data_access", "must be literal false"))

    if (
        approval_required is False
        and mutation_mode == "safe_extension"
        and metadata.get("allow_unapproved_safe_extension") is not True
    ):
        issues.append(
            ValidationIssue(
                "approval_required",
                "safe_extension jobs require approval_required=true unless allow_unapproved_safe_extension=true",
            )
        )

    output_dir = metadata.get("output_dir")
    if output_dir is not None:
        issues.extend(_validate_output_dir(output_dir, job_id_text))

    return ValidationResult(ok=not issues, metadata=metadata, issues=issues)


def _validate_output_dir(output_dir: Any, job_id: str) -> list[ValidationIssue]:
    if not isinstance(output_dir, str) or not output_dir.strip():
        return [ValidationIssue("output_dir", "must be a non-empty relative path")]

    raw = output_dir.strip()
    path = PurePosixPath(raw)
    if path.is_absolute():
        return [ValidationIssue("output_dir", "must be relative and under reports/agent_jobs/<job_id>")]
    if any(part in {"", ".", ".."} for part in path.parts):
        return [ValidationIssue("output_dir", "must not contain empty, current, or parent path segments")]
    if len(path.parts) < 3 or path.parts[:2] != ("reports", "agent_jobs"):
        return [ValidationIssue("output_dir", "must be under reports/agent_jobs/<job_id>")]
    if job_id and path.parts[2] != job_id:
        return [ValidationIssue("output_dir", "third path segment must match job_id")]
    return []


def resolve_report_dir(output_dir: str, job_id: str, repo_root: Path | None = None) -> Path:
    issues = _validate_output_dir(output_dir, job_id)
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues))
    root = (repo_root or Path.cwd()).resolve()
    allowed_root = root / "reports" / "agent_jobs"
    report_dir = (root / output_dir).resolve()

    for candidate in (root / "reports", allowed_root, allowed_root / job_id):
        if candidate.exists() and candidate.is_symlink():
            raise ValueError("output_dir must not use symlinked report directories")

    try:
        report_dir.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("resolved output_dir must stay under reports/agent_jobs/<job_id>") from exc

    return report_dir


def write_validation_report(result: ValidationResult, output_dir: str, job_id: str, repo_root: Path | None = None) -> Path:
    report_dir = resolve_report_dir(output_dir, job_id, repo_root=repo_root)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "validation.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report_path


def _coerce_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return _coerce_now(dt).isoformat().replace("+00:00", "Z")


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def start_watchdog(timeout_seconds: int, max_timeout_streak: int, *, now: datetime | None = None) -> WatchdogState:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    if isinstance(max_timeout_streak, bool) or not isinstance(max_timeout_streak, int) or max_timeout_streak <= 0:
        raise ValueError("max_timeout_streak must be a positive integer")
    return WatchdogState(
        timeout_seconds=timeout_seconds,
        max_timeout_streak=max_timeout_streak,
        started_at=_to_iso(_coerce_now(now)),
        ended_at=None,
        status="running",
        abort_reason=None,
        timeout_streak=0,
    )


def record_watchdog_event(
    state: WatchdogState,
    *,
    timed_out: bool,
    now: datetime | None = None,
) -> WatchdogState:
    if state.status != "running":
        return state

    current = _coerce_now(now)
    started = _from_iso(state.started_at)
    elapsed_seconds = max(0.0, (current - started).total_seconds())
    timeout_streak = state.timeout_streak + 1 if timed_out else 0

    abort_reason: str | None = None
    if elapsed_seconds >= state.timeout_seconds:
        abort_reason = f"timeout_seconds exceeded ({elapsed_seconds:.0f}s >= {state.timeout_seconds}s)"
    elif timed_out and timeout_streak >= state.max_timeout_streak:
        abort_reason = f"max_timeout_streak reached ({timeout_streak} >= {state.max_timeout_streak})"

    if abort_reason:
        return WatchdogState(
            timeout_seconds=state.timeout_seconds,
            max_timeout_streak=state.max_timeout_streak,
            started_at=state.started_at,
            ended_at=_to_iso(current),
            status="aborted",
            abort_reason=abort_reason,
            timeout_streak=timeout_streak,
        )

    return WatchdogState(
        timeout_seconds=state.timeout_seconds,
        max_timeout_streak=state.max_timeout_streak,
        started_at=state.started_at,
        ended_at=None,
        status="running",
        abort_reason=None,
        timeout_streak=timeout_streak,
    )


def complete_watchdog(state: WatchdogState, *, now: datetime | None = None) -> WatchdogState:
    if state.status != "running":
        return state
    return WatchdogState(
        timeout_seconds=state.timeout_seconds,
        max_timeout_streak=state.max_timeout_streak,
        started_at=state.started_at,
        ended_at=_to_iso(_coerce_now(now)),
        status="completed",
        abort_reason=None,
        timeout_streak=state.timeout_streak,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate a Markdown task card")
    validate.add_argument("task_card", type=Path)
    validate.add_argument("--write-report", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        markdown = args.task_card.read_text(encoding="utf-8")
        result = validate_task_card_markdown(markdown)
        if args.write_report and "job_id" in result.metadata and "output_dir" in result.metadata:
            try:
                write_validation_report(result, str(result.metadata["output_dir"]), str(result.metadata["job_id"]))
            except ValueError:
                pass
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
