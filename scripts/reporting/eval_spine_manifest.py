#!/usr/bin/env python3
"""Build and validate offline Evaluation Spine report manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "job_id",
    "lane",
    "supporting_lanes",
    "mode",
    "production_data_access",
    "branch",
    "head",
    "base_head",
    "worktree",
    "task_card",
    "output_dir",
    "started_at",
    "completed_at",
    "status",
    "verdicts",
    "scorecards",
    "validation_commands",
    "changed_files",
    "data_missing",
    "degraded_states",
    "source_artifacts",
    "save_recommendation",
    "do_not_overclaim",
]

LIST_FIELDS = {
    "supporting_lanes",
    "verdicts",
    "scorecards",
    "validation_commands",
    "changed_files",
    "data_missing",
    "degraded_states",
    "source_artifacts",
    "do_not_overclaim",
}

SCALAR_FIELDS = set(REQUIRED_FIELDS) - LIST_FIELDS - {"task_card"}

SAVE_RECOMMENDATIONS = {"SAVE_RECOMMENDED", "NO_SAVE_NEEDED", "SAVE_DEFERRED", "DATA_MISSING"}
EXPECTED_NON_FAILURE_CLASSIFICATIONS = {
    "expected_404",
    "expected_empty",
    "expected_empty_state",
    "expected_absent",
}

DEFAULT_DO_NOT_OVERCLAIM = [
    "canonical_core must not be presented as broad production extraction coverage",
    "Direct runtime stability must not imply Cockpit route stability",
    "Memory context must not become financial truth",
    "canonical_core does not prove broad ASX production extraction coverage",
    "Production-data access must be explicit and scoped",
]

FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
README_KEY_RE = re.compile(r"^(?:[-*]\s*)?(?P<key>[A-Za-z][A-Za-z0-9 /_-]{1,80}):\s*`?(?P<value>[^`]+?)`?\s*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def discover_repo_root(start: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return start.resolve()
    return Path(completed.stdout.strip()).resolve()


def coerce_frontmatter_value(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return ""
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    if stripped.lower() in {"null", "none"}:
        return None
    if re.fullmatch(r"-?[0-9]+", stripped):
        try:
            return int(stripped)
        except ValueError:
            return stripped
    return stripped.strip("'\"")


def parse_task_card_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("missing_yaml_frontmatter")
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in match.group("body").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  - ") and current_list_key:
            metadata[current_list_key].append(coerce_frontmatter_value(raw_line[4:]))
            continue
        current_list_key = None
        if ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        if raw_value.strip() == "":
            metadata[key] = []
            current_list_key = key
        else:
            metadata[key] = coerce_frontmatter_value(raw_value)
    return metadata


def source_artifact(path: Path, repo_root: Path, artifact_type: str, notes: str = "") -> dict[str, Any]:
    return {
        "path": repo_relative(path, repo_root),
        "artifact_type": artifact_type,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        "notes": notes,
    }


def add_missing(manifest: dict[str, Any], field: str, description: str, source_artifact_path: str) -> None:
    items = manifest.setdefault("data_missing", [])
    if any(item.get("field") == field for item in items if isinstance(item, dict)):
        return
    items.append(
        {
            "field": field,
            "code": f"missing_{field}",
            "description": description,
            "blocked_by_policy": False,
            "blocked_by_environment": False,
            "expected_empty_state": False,
            "source_artifact": source_artifact_path,
        }
    )


def readme_facts(path: Path, max_lines: int = 80) -> dict[str, Any]:
    facts: dict[str, Any] = {"verdicts": [], "save_recommendation": None}
    if not path.exists():
        return facts
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines]:
        line = raw_line.strip()
        if not line:
            continue
        match = README_KEY_RE.match(line)
        if not match:
            continue
        key = match.group("key").strip().lower().replace(" ", "_").replace("/", "_")
        value = match.group("value").strip()
        if key in {"branch", "head", "worktree", "mode", "status"}:
            facts[key] = value
        elif key.endswith("status") or key in {"verdict", "final_verdict", "evaluation_spine_status"}:
            facts["verdicts"].append(
                {
                    "verdict": value,
                    "truth_status": key,
                    "confidence": "reported",
                    "notes": "Parsed from README top-level verdict/status line.",
                    "source_artifact": path.name,
                }
            )
        elif key in {"project_memory_save_recommendation", "save_recommendation"}:
            facts["save_recommendation"] = value
    return facts


def normalize_changed_files(diff_check: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in diff_check.get("changed_files", []) if isinstance(diff_check, dict) else []:
        if isinstance(item, dict):
            rows.append(
                {
                    "path": item.get("path"),
                    "status": item.get("status"),
                    "allowed_by_task_card": item.get("allowed_by_task_card", item.get("path") not in diff_check.get("disallowed_files", [])),
                }
            )
    return rows


def normalize_validation_commands(validation: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if not isinstance(validation, dict):
        return []
    commands = validation.get("validation_commands", validation.get("commands", []))
    if not isinstance(commands, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in commands:
        if isinstance(item, str):
            rows.append({"command": item, "cwd": None, "result": None, "exit_code": None, "notes": None})
        elif isinstance(item, dict):
            rows.append(
                {
                    "command": item.get("command") or item.get("cmd"),
                    "cwd": item.get("cwd"),
                    "result": item.get("result") or item.get("status"),
                    "exit_code": item.get("exit_code"),
                    "notes": item.get("notes"),
                }
            )
    return rows


def unknown_fields(source: dict[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: value for key, value in source.items() if key not in known}


def empty_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = {field: None for field in REQUIRED_FIELDS}
    for field in LIST_FIELDS:
        manifest[field] = []
    manifest["do_not_overclaim"] = list(DEFAULT_DO_NOT_OVERCLAIM)
    manifest["extras"] = {}
    manifest["manifest_version"] = "evaluation_spine_manifest_v1"
    manifest["generated_at"] = utc_now()
    return manifest


def build_manifest(report_dir: Path, task_card: Path | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or discover_repo_root(Path.cwd())
    report_dir = report_dir.resolve(strict=False)
    manifest = empty_manifest()
    manifest["output_dir"] = repo_relative(report_dir, repo_root)

    if task_card:
        task_card = task_card.resolve(strict=False)
        if task_card.exists():
            task_meta = parse_task_card_frontmatter(task_card)
            manifest["source_artifacts"].append(source_artifact(task_card, repo_root, "task_card"))
            manifest["task_card"] = {
                "path": repo_relative(task_card, repo_root),
                "sha256": sha256_file(task_card),
                "validation_ok": None,
                "validation_issues": [],
            }
            manifest["job_id"] = task_meta.get("job_id")
            manifest["lane"] = task_meta.get("lane")
            manifest["mode"] = task_meta.get("mutation_mode")
            manifest["production_data_access"] = task_meta.get("production_data_access")
            manifest["output_dir"] = task_meta.get("output_dir") or manifest["output_dir"]
            supporting_lanes = task_meta.get("supporting_lanes", [])
            if isinstance(supporting_lanes, list):
                manifest["supporting_lanes"] = supporting_lanes
            manifest["extras"]["task_card"] = unknown_fields(
                task_meta,
                {
                    "job_id",
                    "lane",
                    "mutation_mode",
                    "production_data_access",
                    "output_dir",
                    "supporting_lanes",
                },
            )
        else:
            add_missing(manifest, "task_card", f"Task card does not exist: {task_card}", "manifest_generator")

    status_path = report_dir / "status.json"
    status = load_json(status_path)
    if isinstance(status, dict):
        manifest["source_artifacts"].append(source_artifact(status_path, repo_root, "status_json"))
        manifest["job_id"] = manifest["job_id"] or status.get("job_id")
        manifest["lane"] = manifest["lane"] or status.get("lane")
        manifest["branch"] = status.get("branch") or manifest["branch"]
        manifest["worktree"] = status.get("worktree") or manifest["worktree"]
        manifest["started_at"] = status.get("started_at") or status.get("claimed_at") or manifest["started_at"]
        manifest["completed_at"] = status.get("completed_at") or status.get("released_at") or status.get("updated_at") or manifest["completed_at"]
        manifest["status"] = status.get("status") or manifest["status"]
        manifest["output_dir"] = status.get("output_dir") or manifest["output_dir"]
        manifest["mode"] = status.get("mutation_mode") or manifest["mode"]
        if manifest["production_data_access"] is None:
            manifest["production_data_access"] = status.get("production_data_access")
        manifest["extras"]["status"] = unknown_fields(
            status,
            {
                "job_id",
                "lane",
                "branch",
                "worktree",
                "started_at",
                "claimed_at",
                "completed_at",
                "released_at",
                "updated_at",
                "status",
                "output_dir",
                "mutation_mode",
                "production_data_access",
            },
        )

    diff_path = report_dir / "diff-check.json"
    diff_check = load_json(diff_path)
    if isinstance(diff_check, dict):
        manifest["source_artifacts"].append(source_artifact(diff_path, repo_root, "diff_check_json"))
        manifest["changed_files"] = normalize_changed_files(diff_check)
        validation = diff_check.get("validation")
        if isinstance(validation, dict):
            metadata = validation.get("metadata", {})
            if isinstance(metadata, dict):
                manifest["job_id"] = manifest["job_id"] or metadata.get("job_id")
                manifest["lane"] = manifest["lane"] or metadata.get("lane")
                manifest["mode"] = manifest["mode"] or metadata.get("mutation_mode")
        manifest["extras"]["diff_check"] = unknown_fields(diff_check, {"changed_files", "validation", "disallowed_files"})

    validation_path = report_dir / "validation.json"
    validation_json = load_json(validation_path)
    if validation_json is not None:
        manifest["source_artifacts"].append(source_artifact(validation_path, repo_root, "validation_json"))
        manifest["validation_commands"] = normalize_validation_commands(validation_json)
        if isinstance(validation_json, dict):
            manifest["extras"]["validation"] = unknown_fields(validation_json, {"validation_commands", "commands"})

    readme_path = report_dir / "README.md"
    readme = readme_facts(readme_path)
    if readme_path.exists():
        manifest["source_artifacts"].append(source_artifact(readme_path, repo_root, "readme"))
    for field in ("branch", "head", "worktree", "mode", "status"):
        if manifest.get(field) is None and readme.get(field):
            manifest[field] = readme[field]
    if readme.get("save_recommendation"):
        manifest["save_recommendation"] = readme["save_recommendation"]
    manifest["verdicts"].extend(readme.get("verdicts", []))

    if manifest["supporting_lanes"] is None:
        manifest["supporting_lanes"] = []
    if manifest["production_data_access"] is None:
        manifest["production_data_access"] = False
        add_missing(manifest, "production_data_access", "Production data access was not recorded; defaulted false for static offline manifest.", "manifest_generator")

    for field in SCALAR_FIELDS:
        if manifest.get(field) in {None, ""}:
            add_missing(manifest, field, f"{field} was not found in task card, status.json, diff-check.json, validation.json, or README top-level lines.", "manifest_generator")
    if manifest.get("task_card") is None:
        add_missing(manifest, "task_card", "No task card was supplied or resolved.", "manifest_generator")

    return manifest


def missing_fields(data_missing: Any) -> set[str]:
    fields: set[str] = set()
    if not isinstance(data_missing, list):
        return fields
    for item in data_missing:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        if isinstance(field, str):
            fields.add(field)
        code = item.get("code")
        if isinstance(code, str) and code.startswith("missing_"):
            fields.add(code[len("missing_") :])
    return fields


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    known_missing = missing_fields(manifest.get("data_missing"))
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            issues.append(f"{field}: required field is missing")
            continue
        value = manifest.get(field)
        if field in LIST_FIELDS and not isinstance(value, list):
            issues.append(f"{field}: must be a list")
        if field in SCALAR_FIELDS and value in {None, ""} and field not in known_missing:
            issues.append(f"{field}: missing value must be represented in data_missing")
    if manifest.get("task_card") is None and "task_card" not in known_missing:
        issues.append("task_card: missing value must be represented in data_missing")
    if manifest.get("task_card") is not None and not isinstance(manifest.get("task_card"), dict):
        issues.append("task_card: must be an object or null with data_missing")
    if not isinstance(manifest.get("production_data_access"), bool):
        if "production_data_access" not in known_missing:
            issues.append("production_data_access: must be a boolean")
    save_recommendation = manifest.get("save_recommendation")
    if save_recommendation not in SAVE_RECOMMENDATIONS and "save_recommendation" not in known_missing:
        issues.append("save_recommendation: invalid value")

    scorecards = manifest.get("scorecards")
    if isinstance(scorecards, list):
        for idx, row in enumerate(scorecards):
            if not isinstance(row, dict):
                issues.append(f"scorecards[{idx}]: must be an object")
                continue
            profile = row.get("scorecard_profile")
            if not isinstance(profile, str) or not profile.strip():
                issues.append(f"scorecards[{idx}].scorecard_profile: required")
            if profile == "canonical_core":
                row_guard = str(row.get("overclaim_guard", ""))
                global_guards = " ".join(str(item) for item in manifest.get("do_not_overclaim", []))
                if "canonical_core" not in row_guard and "canonical_core" not in global_guards:
                    issues.append(f"scorecards[{idx}].overclaim_guard: canonical_core requires a do-not-overclaim guard")

    for idx, item in enumerate(manifest.get("degraded_states", [])):
        if not isinstance(item, dict):
            issues.append(f"degraded_states[{idx}]: must be an object")
            continue
        classification = item.get("classification")
        if classification in EXPECTED_NON_FAILURE_CLASSIFICATIONS and item.get("is_failure") is True:
            issues.append(f"degraded_states[{idx}]: expected states must not be marked as failures")

    return issues


def write_manifest(manifest: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    manifest = build_manifest(
        Path(args.report_dir),
        task_card=Path(args.task_card) if args.task_card else None,
        repo_root=discover_repo_root(Path.cwd()),
    )
    issues = validate_manifest(manifest)
    if args.out:
        write_manifest(manifest, Path(args.out))
    else:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    if issues:
        for issue in issues:
            print(f"manifest validation issue: {issue}", file=sys.stderr)
        return 1
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    payload = load_json(Path(args.manifest))
    if not isinstance(payload, dict):
        print("manifest must be a JSON object", file=sys.stderr)
        return 1
    issues = validate_manifest(payload)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "issues": []}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and validate offline Evaluation Spine manifests.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build a manifest from a task card and report directory")
    build.add_argument("--task-card", help="task card markdown path")
    build.add_argument("--report-dir", required=True, help="report directory to inspect")
    build.add_argument("--out", help="output manifest.json path")
    build.set_defaults(func=cmd_build)

    validate = sub.add_parser("validate", help="validate a manifest JSON file")
    validate.add_argument("manifest", help="manifest JSON path")
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
