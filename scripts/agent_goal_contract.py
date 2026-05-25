#!/usr/bin/env python3
"""Validate repo-native goal and status artifacts with explicit scope only."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

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
VALID_MODES = {"audit_only", "safe_extension", "blocked"}
VALID_GOAL_STATUSES = {"draft", "active", "blocked", "complete", "superseded"}
VALID_MERGE_PARKING_STATUSES = {
    "not_implemented",
    "not_started",
    "docs_only",
    "blocked",
    "ready_for_later_slice",
}
REQUIRED_GOAL_FIELDS = {
    "schema_version",
    "goal_id",
    "status",
    "owner",
    "mode",
    "objective",
    "primary_lane",
    "supporting_lanes",
    "task_card",
    "output_dir",
    "validation",
    "hard_stops",
    "merge_parking_status",
    "save_recommendation",
}
REQUIRED_STATUS_FIELDS = {
    "job_id",
    "lane",
    "mode",
    "branch",
    "head",
    "validation_passed",
    "files_changed",
    "key_findings",
    "recommended_next_task",
    "hard_blockers",
    "data_missing",
}
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    field: str
    message: str
    code: str = "invalid"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class FileValidation:
    path: str
    artifact_type: str
    ok: bool
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "artifact_type": self.artifact_type,
            "ok": self.ok,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SkippedFile:
    path: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ContractResult:
    ok: bool
    scope: str
    checked_files: list[FileValidation]
    skipped_files: list[SkippedFile]
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "scope": self.scope,
            "checked_files": [checked.to_dict() for checked in self.checked_files],
            "skipped_files": [skipped.to_dict() for skipped in self.skipped_files],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _issue(path: str, field: str, message: str, code: str = "invalid") -> ValidationIssue:
    return ValidationIssue(path=path, field=field, message=message, code=code)


def _data_missing(path: str, field: str, message: str) -> ValidationIssue:
    return _issue(path, field, f"DATA_MISSING: {message}", code="DATA_MISSING")


def _require_yaml(path: str) -> list[ValidationIssue]:
    if yaml is None:
        return [_data_missing(path, "frontmatter", "PyYAML is required to parse goal frontmatter")]
    return []


def _normalize_repo_path(path_text: str) -> str:
    path = PurePosixPath(path_text.strip().replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"path must be repo-relative without parent segments: {path_text}")
    return path.as_posix()


def _repo_relative(path: Path, repo_root: Path) -> str:
    candidate = path
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ValueError(f"{path} is outside repo root {repo_root}") from exc
    return _normalize_repo_path(candidate.as_posix())


def _read_json(path: Path, display_path: str) -> tuple[Any | None, list[ValidationIssue]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [_data_missing(display_path, "path", "file does not exist")]
    except json.JSONDecodeError as exc:
        return None, [_issue(display_path, "json", str(exc))]


def _parse_goal_frontmatter(path: Path, display_path: str) -> tuple[dict[str, Any], list[ValidationIssue]]:
    issues = _require_yaml(display_path)
    if issues:
        return {}, issues
    try:
        markdown = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, [_data_missing(display_path, "path", "file does not exist")]

    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, [_data_missing(display_path, "frontmatter", "missing YAML frontmatter")]

    loaded = yaml.safe_load(match.group("yaml"))  # type: ignore[union-attr]
    if not isinstance(loaded, dict):
        return {}, [_issue(display_path, "frontmatter", "frontmatter must be a mapping")]
    return dict(loaded), []


def _validate_non_empty_string(metadata: dict[str, Any], field: str, path: str) -> list[ValidationIssue]:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        return [_issue(path, field, "must be a non-empty string")]
    return []


def _validate_string_list(metadata: dict[str, Any], field: str, path: str, *, min_items: int = 0) -> list[ValidationIssue]:
    value = metadata.get(field)
    if not isinstance(value, list) or len(value) < min_items:
        return [_issue(path, field, f"must be a list with at least {min_items} item(s)")]
    issues: list[ValidationIssue] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(_issue(path, f"{field}[{idx}]", "must be a non-empty string"))
    return issues


def _validate_task_card_output_pair(metadata: dict[str, Any], path: str) -> list[ValidationIssue]:
    task_card = metadata.get("task_card")
    output_dir = metadata.get("output_dir")
    issues: list[ValidationIssue] = []

    if not isinstance(task_card, str):
        return issues
    if not isinstance(output_dir, str):
        return issues

    try:
        task_path = PurePosixPath(_normalize_repo_path(task_card))
        output_path = PurePosixPath(_normalize_repo_path(output_dir))
    except ValueError as exc:
        return [_issue(path, "task_card", str(exc))]

    if len(task_path.parts) != 3 or task_path.parts[:2] != ("docs", "agent_tasks") or task_path.suffix != ".md":
        issues.append(_issue(path, "task_card", "must be under docs/agent_tasks/<job_id>.md"))
    if len(output_path.parts) != 3 or output_path.parts[:2] != ("reports", "agent_jobs"):
        issues.append(_issue(path, "output_dir", "must be reports/agent_jobs/<job_id>"))

    if not issues and task_path.stem != output_path.parts[2]:
        issues.append(
            _issue(
                path,
                "output_dir",
                "task_card basename must match output_dir job_id segment",
            )
        )
    return issues


def validate_goal_file(path: Path, repo_root: Path) -> FileValidation:
    display_path = _repo_relative(path, repo_root)
    metadata, issues = _parse_goal_frontmatter(path, display_path)
    if issues:
        return FileValidation(display_path, "goal", False, issues)

    missing = sorted(field for field in REQUIRED_GOAL_FIELDS if field not in metadata)
    issues.extend(_data_missing(display_path, field, "required goal frontmatter field is missing") for field in missing)
    extra = sorted(field for field in metadata if field not in REQUIRED_GOAL_FIELDS)
    for field in extra:
        issues.append(_issue(display_path, field, "is not allowed by goal_schema_v1"))

    if metadata.get("schema_version") != "goal_schema_v1":
        issues.append(_issue(display_path, "schema_version", "must be goal_schema_v1"))

    issues.extend(_validate_non_empty_string(metadata, "goal_id", display_path))
    goal_id = metadata.get("goal_id")
    if isinstance(goal_id, str) and goal_id and not JOB_ID_RE.fullmatch(goal_id):
        issues.append(_issue(display_path, "goal_id", "must contain only letters, numbers, dot, underscore, or dash"))

    if metadata.get("status") not in VALID_GOAL_STATUSES:
        issues.append(_issue(display_path, "status", f"must be one of: {', '.join(sorted(VALID_GOAL_STATUSES))}"))
    if metadata.get("mode") not in VALID_MODES:
        issues.append(_issue(display_path, "mode", "must be audit_only, safe_extension, or blocked"))
    if metadata.get("primary_lane") not in VALID_LANES:
        issues.append(_issue(display_path, "primary_lane", f"must be one of: {', '.join(sorted(VALID_LANES))}"))
    if metadata.get("merge_parking_status") not in VALID_MERGE_PARKING_STATUSES:
        issues.append(
            _issue(
                display_path,
                "merge_parking_status",
                f"must be one of: {', '.join(sorted(VALID_MERGE_PARKING_STATUSES))}",
            )
        )

    for field in ("owner", "objective", "task_card", "output_dir", "save_recommendation"):
        issues.extend(_validate_non_empty_string(metadata, field, display_path))
    issues.extend(_validate_string_list(metadata, "supporting_lanes", display_path))
    supporting_lanes = metadata.get("supporting_lanes")
    if isinstance(supporting_lanes, list) and len(set(supporting_lanes)) != len(supporting_lanes):
        issues.append(_issue(display_path, "supporting_lanes", "must not contain duplicates"))
    issues.extend(_validate_string_list(metadata, "validation", display_path, min_items=1))
    issues.extend(_validate_string_list(metadata, "hard_stops", display_path, min_items=1))
    issues.extend(_validate_task_card_output_pair(metadata, display_path))

    return FileValidation(display_path, "goal", not issues, issues)


def validate_status_file(path: Path, repo_root: Path) -> FileValidation:
    display_path = _repo_relative(path, repo_root)
    payload, issues = _read_json(path, display_path)
    if issues:
        return FileValidation(display_path, "status", False, issues)
    if not isinstance(payload, dict):
        return FileValidation(display_path, "status", False, [_issue(display_path, "json", "must be a JSON object")])

    missing = sorted(field for field in REQUIRED_STATUS_FIELDS if field not in payload)
    issues.extend(_data_missing(display_path, field, "required status field is missing") for field in missing)

    for field in ("job_id", "branch", "head"):
        if field in payload and (not isinstance(payload[field], str) or not payload[field].strip()):
            issues.append(_issue(display_path, field, "must be a non-empty string"))
    if payload.get("lane") not in VALID_LANES and "lane" in payload:
        issues.append(_issue(display_path, "lane", f"must be one of: {', '.join(sorted(VALID_LANES))}"))
    if payload.get("mode") not in VALID_MODES and "mode" in payload:
        issues.append(_issue(display_path, "mode", "must be audit_only, safe_extension, or blocked"))
    if "validation_passed" in payload and not isinstance(payload["validation_passed"], bool):
        issues.append(_issue(display_path, "validation_passed", "must be a boolean"))
    for field in ("files_changed", "key_findings", "hard_blockers", "data_missing"):
        if field in payload and not isinstance(payload[field], list):
            issues.append(_issue(display_path, field, "must be a list"))
        elif field in payload:
            for idx, item in enumerate(payload[field]):
                if not isinstance(item, str):
                    issues.append(_issue(display_path, f"{field}[{idx}]", "must be a string"))
    if "recommended_next_task" in payload and not (
        payload["recommended_next_task"] is None or isinstance(payload["recommended_next_task"], str)
    ):
        issues.append(_issue(display_path, "recommended_next_task", "must be a string or null"))

    return FileValidation(display_path, "status", not issues, issues)


def validate_schema_file(path: Path, repo_root: Path) -> FileValidation:
    display_path = _repo_relative(path, repo_root)
    payload, issues = _read_json(path, display_path)
    if issues:
        return FileValidation(display_path, "json_schema", False, issues)
    if not isinstance(payload, dict):
        return FileValidation(display_path, "json_schema", False, [_issue(display_path, "json", "must be a JSON object")])

    for field in ("$schema", "type", "properties", "required"):
        if field not in payload:
            issues.append(_data_missing(display_path, field, "required JSON schema field is missing"))
    if payload.get("type") != "object":
        issues.append(_issue(display_path, "type", "must be object"))
    if "properties" in payload and not isinstance(payload["properties"], dict):
        issues.append(_issue(display_path, "properties", "must be an object"))
    if "required" in payload and not isinstance(payload["required"], list):
        issues.append(_issue(display_path, "required", "must be a list"))

    return FileValidation(display_path, "json_schema", not issues, issues)


def _artifact_type(path: str) -> str | None:
    posix = PurePosixPath(path)
    if path in {"docs/goals/goal_schema_v1.json", "reports/agent_jobs/status_schema_v1.json"}:
        return "json_schema"
    if path == "docs/goals/README.md":
        return None
    if path.startswith("docs/goals/") and posix.suffix == ".md":
        return "goal"
    if path.startswith("reports/agent_jobs/") and posix.name == "status.json":
        return "status"
    return None


def _parse_git_status_porcelain(output: str) -> list[str]:
    paths: list[str] = []
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        if raw_line.startswith("?? "):
            paths.append(_normalize_repo_path(raw_line[3:]))
            continue
        if len(raw_line) < 4:
            continue
        path_text = raw_line[3:]
        if " -> " in path_text:
            old_path, new_path = path_text.split(" -> ", 1)
            paths.append(_normalize_repo_path(old_path))
            paths.append(_normalize_repo_path(new_path))
        else:
            paths.append(_normalize_repo_path(path_text))
    return paths


def read_changed_paths(repo_root: Path, *, base_ref: str | None = None) -> list[str]:
    if base_ref:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", f"{base_ref}...HEAD"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return sorted({_normalize_repo_path(line) for line in completed.stdout.splitlines() if line.strip()})

    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return sorted(set(_parse_git_status_porcelain(completed.stdout)))


def validate_paths(
    paths: Sequence[Path],
    *,
    repo_root: Path | None = None,
    changed: bool = False,
    base_ref: str | None = None,
) -> ContractResult:
    root = (repo_root or Path.cwd()).resolve()
    top_issues: list[ValidationIssue] = []
    selected: list[tuple[str, bool]] = []

    for path in paths:
        try:
            selected.append((_repo_relative(path, root), True))
        except ValueError as exc:
            top_issues.append(_issue(str(path), "path", str(exc)))

    if changed:
        try:
            selected.extend((path, False) for path in read_changed_paths(root, base_ref=base_ref))
        except (subprocess.CalledProcessError, ValueError) as exc:
            top_issues.append(_data_missing(".", "git", str(exc)))

    if not selected and not top_issues:
        top_issues.append(
            _data_missing(
                ".",
                "scope",
                "explicit paths or --changed is required; refusing to scan historical artifacts",
            )
        )

    checked: list[FileValidation] = []
    skipped: list[SkippedFile] = []
    seen: set[str] = set()
    for rel_path, explicit in selected:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        artifact_type = _artifact_type(rel_path)
        if artifact_type is None:
            if explicit:
                top_issues.append(_issue(rel_path, "path", "unsupported artifact path for goal contract validation"))
            else:
                skipped.append(SkippedFile(rel_path, "not a goal/status/schema artifact"))
            continue

        full_path = root / rel_path
        if artifact_type == "goal":
            checked.append(validate_goal_file(full_path, root))
        elif artifact_type == "status":
            checked.append(validate_status_file(full_path, root))
        else:
            checked.append(validate_schema_file(full_path, root))

    all_file_issues = [issue for file_result in checked for issue in file_result.issues]
    scope = "changed-files" if changed and not paths else "explicit-and-changed" if changed else "explicit"
    return ContractResult(
        ok=not top_issues and not all_file_issues,
        scope=scope,
        checked_files=checked,
        skipped_files=skipped,
        issues=top_issues,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser(
        "validate",
        help="validate explicit goal/status/schema files, or only changed files with --changed",
        description=(
            "Validate repo-native goal frontmatter, agent-job status JSON, and "
            "schema JSON. This command never scans historical artifacts by "
            "default; pass file paths or --changed."
        ),
    )
    validate.add_argument("paths", nargs="*", type=Path, help="specific files to validate")
    validate.add_argument("--repo-root", type=Path, default=Path.cwd(), help="repository root for relative paths")
    validate.add_argument("--changed", action="store_true", help="validate only changed goal/status/schema files")
    validate.add_argument(
        "--base-ref",
        help="with --changed, use git diff --name-only <base-ref>...HEAD instead of worktree status",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        result = validate_paths(
            args.paths,
            repo_root=args.repo_root,
            changed=args.changed,
            base_ref=args.base_ref,
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
