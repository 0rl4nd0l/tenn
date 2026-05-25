#!/usr/bin/env python3
"""Validate merge parking docs and schemas with explicit or changed-file scope."""

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


MERGE_PARKING_DIR = PurePosixPath("docs/agent_registry/merge_parking")
ENTRY_SCHEMA_PATH = "docs/agent_registry/merge_parking/merge_parking_entry_schema_v1.json"
REGISTRY_SCHEMA_PATH = "docs/agent_registry/merge_parking/registry_schema_v1.json"
README_PATH = "docs/agent_registry/merge_parking/README.md"
REGISTRY_PATH = "docs/agent_registry/merge_parking/REGISTRY.md"

VALID_STATUSES = {
    "PARKED_READY_FOR_REVIEW",
    "PARKED_BLOCKED_BY_DEPENDENCY",
    "PARKED_NEEDS_REBASE",
    "PARKED_NEEDS_VALIDATION",
    "PARKED_NEEDS_HUMAN_DECISION",
    "PARKED_SUPERSEDED",
    "MERGED",
    "REJECTED",
    "ABANDONED",
}
VALID_LANES = {
    "Financial Truth",
    "Evaluation",
    "Provenance",
    "Query Orchestration",
    "Memory",
    "Reporting",
}
VALID_MODES = {"audit_only", "safe_extension", "blocked"}
VALID_VALIDATION_RESULTS = {"passed", "failed", "partial", "not_run"}
VALID_REGISTRY_STATUSES = {"active", "frozen", "archived"}
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)

REQUIRED_ENTRY_FIELDS = {
    "schema_version",
    "parking_id",
    "status",
    "job_id",
    "lane",
    "mode",
    "source_branch",
    "source_worktree",
    "base_head",
    "current_head",
    "task_card",
    "report_dir",
    "output_dir",
    "changed_files",
    "validation_commands",
    "validation_result",
    "blocked_by",
    "ready_for_merge",
    "review_required",
    "do_not_merge_before",
    "data_missing",
    "next_agent_should",
    "next_agent_must_not",
}
REQUIRED_REGISTRY_FIELDS = {
    "schema_version",
    "registry_id",
    "status",
    "updated_at",
    "active_parking_count",
    "recently_resolved_count",
    "notes",
}


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
class ValidationResult:
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


def _read_frontmatter(path: Path, display_path: str) -> tuple[dict[str, Any], list[ValidationIssue]]:
    if yaml is None:
        return {}, [_data_missing(display_path, "frontmatter", "PyYAML is required to parse Markdown frontmatter")]
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


def _metadata_for_path(path: Path, display_path: str, artifact_type: str) -> tuple[dict[str, Any], list[ValidationIssue]]:
    if display_path.endswith(".json") and artifact_type in {"entry_json", "registry_json"}:
        payload, issues = _read_json(path, display_path)
        if issues:
            return {}, issues
        if not isinstance(payload, dict):
            return {}, [_issue(display_path, "json", "must be a JSON object")]
        return dict(payload), []
    return _read_frontmatter(path, display_path)


def _validate_required(metadata: dict[str, Any], required: set[str], path: str) -> list[ValidationIssue]:
    return [_data_missing(path, field, "required field is missing") for field in sorted(required - metadata.keys())]


def _validate_no_extra(metadata: dict[str, Any], allowed: set[str], path: str) -> list[ValidationIssue]:
    return [_issue(path, field, "is not allowed by this schema") for field in sorted(metadata.keys() - allowed)]


def _validate_non_empty_string(metadata: dict[str, Any], field: str, path: str) -> list[ValidationIssue]:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        return [_issue(path, field, "must be a non-empty string")]
    return []


def _validate_string_list(
    metadata: dict[str, Any],
    field: str,
    path: str,
    *,
    min_items: int = 0,
) -> list[ValidationIssue]:
    value = metadata.get(field)
    if not isinstance(value, list) or len(value) < min_items:
        return [_issue(path, field, f"must be a list with at least {min_items} item(s)")]
    issues: list[ValidationIssue] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(_issue(path, f"{field}[{idx}]", "must be a non-empty string"))
    return issues


def _validate_report_path(value: Any, field: str, path: str) -> list[ValidationIssue]:
    if not isinstance(value, str) or not value.strip():
        return [_issue(path, field, "must be a non-empty relative report path")]
    try:
        normalized = PurePosixPath(_normalize_repo_path(value))
    except ValueError as exc:
        return [_issue(path, field, str(exc))]
    if len(normalized.parts) != 3 or normalized.parts[:2] != ("reports", "agent_jobs"):
        return [_issue(path, field, "must be reports/agent_jobs/<job_id>")]
    return []


def _validate_task_card(value: Any, path: str) -> list[ValidationIssue]:
    if not isinstance(value, str) or not value.strip():
        return [_issue(path, "task_card", "must be a non-empty task-card path")]
    try:
        normalized = PurePosixPath(_normalize_repo_path(value))
    except ValueError as exc:
        return [_issue(path, "task_card", str(exc))]
    if len(normalized.parts) != 3 or normalized.parts[:2] != ("docs", "agent_tasks") or normalized.suffix != ".md":
        return [_issue(path, "task_card", "must be docs/agent_tasks/<job_id>.md")]
    return []


def validate_entry_payload(metadata: dict[str, Any], path: str) -> list[ValidationIssue]:
    issues = _validate_required(metadata, REQUIRED_ENTRY_FIELDS, path)
    issues.extend(_validate_no_extra(metadata, REQUIRED_ENTRY_FIELDS, path))

    if metadata.get("schema_version") != "merge_parking_entry_v1":
        issues.append(_issue(path, "schema_version", "must be merge_parking_entry_v1"))
    if metadata.get("status") not in VALID_STATUSES:
        issues.append(_issue(path, "status", f"must be one of: {', '.join(sorted(VALID_STATUSES))}"))
    if metadata.get("lane") not in VALID_LANES:
        issues.append(_issue(path, "lane", f"must be one of: {', '.join(sorted(VALID_LANES))}"))
    if metadata.get("mode") not in VALID_MODES:
        issues.append(_issue(path, "mode", "must be audit_only, safe_extension, or blocked"))
    if metadata.get("validation_result") not in VALID_VALIDATION_RESULTS:
        issues.append(_issue(path, "validation_result", "must be passed, failed, partial, or not_run"))

    for field in (
        "parking_id",
        "job_id",
        "source_branch",
        "source_worktree",
        "base_head",
        "current_head",
        "do_not_merge_before",
    ):
        issues.extend(_validate_non_empty_string(metadata, field, path))

    for field in ("parking_id", "job_id"):
        value = metadata.get(field)
        if isinstance(value, str) and value and not JOB_ID_RE.fullmatch(value):
            issues.append(_issue(path, field, "must contain only letters, numbers, dot, underscore, or dash"))

    issues.extend(_validate_task_card(metadata.get("task_card"), path))
    issues.extend(_validate_report_path(metadata.get("report_dir"), "report_dir", path))
    issues.extend(_validate_report_path(metadata.get("output_dir"), "output_dir", path))
    for field in ("changed_files", "validation_commands", "next_agent_should", "next_agent_must_not"):
        issues.extend(_validate_string_list(metadata, field, path, min_items=1))
    for field in ("blocked_by", "data_missing"):
        issues.extend(_validate_string_list(metadata, field, path))

    if "ready_for_merge" in metadata and not isinstance(metadata.get("ready_for_merge"), bool):
        issues.append(_issue(path, "ready_for_merge", "must be a boolean"))

    review_required = metadata.get("review_required")
    if not isinstance(review_required, dict):
        issues.append(_issue(path, "review_required", "must be a mapping with human and gpt review booleans"))
    else:
        if review_required.get("human") is not True:
            issues.append(_issue(path, "review_required.human", "must be literal true"))
        if review_required.get("gpt") is not True:
            issues.append(_issue(path, "review_required.gpt", "must be literal true"))
        notes = review_required.get("notes")
        if notes is not None and (
            not isinstance(notes, list) or any(not isinstance(item, str) for item in notes)
        ):
            issues.append(_issue(path, "review_required.notes", "must be a list of strings when present"))

    if metadata.get("ready_for_merge") is True and not isinstance(review_required, dict):
        issues.append(_issue(path, "ready_for_merge", "true requires review_required metadata"))

    return issues


def validate_registry_payload(metadata: dict[str, Any], path: str) -> list[ValidationIssue]:
    issues = _validate_required(metadata, REQUIRED_REGISTRY_FIELDS, path)
    issues.extend(_validate_no_extra(metadata, REQUIRED_REGISTRY_FIELDS, path))
    if metadata.get("schema_version") != "merge_parking_registry_v1":
        issues.append(_issue(path, "schema_version", "must be merge_parking_registry_v1"))
    if metadata.get("registry_id") != "merge_parking_registry":
        issues.append(_issue(path, "registry_id", "must be merge_parking_registry"))
    if metadata.get("status") not in VALID_REGISTRY_STATUSES:
        issues.append(_issue(path, "status", "must be active, frozen, or archived"))
    issues.extend(_validate_non_empty_string(metadata, "updated_at", path))
    for field in ("active_parking_count", "recently_resolved_count"):
        value = metadata.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            issues.append(_issue(path, field, "must be a non-negative integer"))
    issues.extend(_validate_string_list(metadata, "notes", path))
    return issues


def validate_artifact(path: Path, repo_root: Path, artifact_type: str) -> FileValidation:
    display_path = _repo_relative(path, repo_root)
    if artifact_type == "json_schema":
        payload, issues = _read_json(path, display_path)
        if issues:
            return FileValidation(display_path, artifact_type, False, issues)
        if not isinstance(payload, dict):
            return FileValidation(display_path, artifact_type, False, [_issue(display_path, "json", "must be an object")])
        for field in ("$schema", "type", "properties", "required"):
            if field not in payload:
                issues.append(_data_missing(display_path, field, "required JSON schema field is missing"))
        if payload.get("type") != "object":
            issues.append(_issue(display_path, "type", "must be object"))
        return FileValidation(display_path, artifact_type, not issues, issues)

    metadata, issues = _metadata_for_path(path, display_path, artifact_type)
    if issues:
        return FileValidation(display_path, artifact_type, False, issues)
    if artifact_type in {"registry_markdown", "registry_json"}:
        issues.extend(validate_registry_payload(metadata, display_path))
    else:
        issues.extend(validate_entry_payload(metadata, display_path))
    return FileValidation(display_path, artifact_type, not issues, issues)


def _artifact_type(path: str) -> str | None:
    posix = PurePosixPath(path)
    if not path.startswith(f"{MERGE_PARKING_DIR.as_posix()}/"):
        return None
    if path == README_PATH:
        return None
    if path in {ENTRY_SCHEMA_PATH, REGISTRY_SCHEMA_PATH}:
        return "json_schema"
    if path == REGISTRY_PATH:
        return "registry_markdown"
    if posix.suffix == ".md":
        return "entry_markdown"
    if posix.suffix == ".json":
        if "registry" in posix.stem:
            return "registry_json"
        return "entry_json"
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
) -> ValidationResult:
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
                top_issues.append(_issue(rel_path, "path", "unsupported merge parking artifact path"))
            else:
                skipped.append(SkippedFile(rel_path, "not a merge parking artifact"))
            continue
        checked.append(validate_artifact(root / rel_path, root, artifact_type))

    all_file_issues = [issue for checked_file in checked for issue in checked_file.issues]
    scope = "changed-files" if changed and not paths else "explicit-and-changed" if changed else "explicit"
    return ValidationResult(
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
        help="validate explicit merge parking files, or only changed files with --changed",
        description=(
            "Validate merge parking registry/index files, entry files, and schema JSON. "
            "This command never scans historical artifacts by default; pass file paths or --changed."
        ),
    )
    validate.add_argument("paths", nargs="*", type=Path, help="specific files to validate")
    validate.add_argument("--repo-root", type=Path, default=Path.cwd(), help="repository root for relative paths")
    validate.add_argument("--changed", action="store_true", help="validate only changed merge parking files")
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
