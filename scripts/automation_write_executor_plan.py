#!/usr/bin/env python3
"""Dry-run executor plan renderer for Tenn automation write manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


SCHEMA_VERSION = 1
DEFAULT_REPO = "0rl4nd0l/tenn"
WRITE_ACTIONS = {
    "open_issue",
    "comment_existing_issue",
    "comment_existing_pr",
    "create_draft_pr",
    "park_high_risk",
}
SUPPORTED_ACTIONS = WRITE_ACTIONS | {"review_only"}
ALLOWED_COMMAND_PREFIXES = {
    ("gh", "issue", "create"),
    ("gh", "issue", "comment"),
    ("gh", "pr", "comment"),
    ("gh", "pr", "create"),
    ("git", "worktree", "add"),
}


def _string_value(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _bool_value(payload: dict[str, object], key: str) -> bool:
    return payload.get(key) is True


def _number_text(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip().lstrip("#").isdigit():
        return value.strip().lstrip("#")
    return ""


def _action(manifest: dict[str, object]) -> tuple[str, dict[str, object]]:
    action = manifest.get("action")
    if not isinstance(action, dict):
        return "", {}
    action_type = _string_value(action, "type")
    target = action.get("target")
    return action_type, dict(target) if isinstance(target, dict) else {}


def _candidate(manifest: dict[str, object]) -> dict[str, object]:
    candidate = manifest.get("candidate")
    return dict(candidate) if isinstance(candidate, dict) else {}


def _manifest_blockers(manifest: dict[str, object]) -> list[str]:
    blockers = manifest.get("blockers")
    if not isinstance(blockers, list):
        return []
    return [str(blocker) for blocker in blockers if str(blocker)]


def _body_placeholder(source: str) -> str:
    return f"<body-file-from:{source}>"


def _candidate_body_source(manifest: dict[str, object], target: dict[str, object]) -> str:
    return _string_value(target, "body_source") or _string_value(_candidate(manifest), "evidence_path")


def _command(surface: str, argv: list[str], *, body_source: str = "", note: str = "") -> dict[str, object]:
    return {
        "surface": surface,
        "argv": argv,
        "execute": False,
        "writes_if_executed": True,
        "body_source": body_source,
        "note": note,
    }


def _missing(target: dict[str, object], required: Sequence[str]) -> list[str]:
    return [f"target_{key}_missing" for key in required if not _string_value(target, key)]


def _validate_command(command: dict[str, object]) -> list[str]:
    argv = command.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) and item for item in argv):
        return ["command_argv_invalid"]
    prefix = tuple(argv[:3])
    if prefix not in ALLOWED_COMMAND_PREFIXES:
        return [f"command_surface_not_allowed:{' '.join(argv[:3])}"]
    if command.get("execute") is not False:
        return ["command_execute_flag_not_false"]
    return []


def _plan_open_issue(target: dict[str, object], repo: str) -> tuple[list[dict[str, object]], list[str]]:
    blockers = _missing(target, ["title", "body_source", "root_cause", "lane", "risk"])
    if blockers:
        return [], blockers
    body_source = _string_value(target, "body_source")
    command = _command(
        "github_issue_create",
        [
            "gh",
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            _string_value(target, "title"),
            "--body-file",
            _body_placeholder(body_source),
        ],
        body_source=body_source,
        note="dry-run issue creation plan only",
    )
    return [command], _validate_command(command)


def _plan_comment(kind: str, manifest: dict[str, object], target: dict[str, object], repo: str) -> tuple[list[dict[str, object]], list[str]]:
    number = _number_text(target.get("number"))
    body_source = _candidate_body_source(manifest, target)
    blockers: list[str] = []
    if not number:
        blockers.append(f"target_{kind}_number_missing")
    if not body_source:
        blockers.append("target_body_source_missing")
    if blockers:
        return [], blockers
    subcommand = "issue" if kind == "issue" else "pr"
    command = _command(
        f"github_{kind}_comment",
        [
            "gh",
            subcommand,
            "comment",
            number,
            "--repo",
            repo,
            "--body-file",
            _body_placeholder(body_source),
        ],
        body_source=body_source,
        note="dry-run comment plan only",
    )
    return [command], _validate_command(command)


def _plan_draft_pr(target: dict[str, object], repo: str) -> tuple[list[dict[str, object]], list[str]]:
    blockers = _missing(target, ["branch", "base", "title", "body", "validation"])
    if blockers:
        return [], blockers
    body_source = "manifest.action.target.body"
    command = _command(
        "github_pr_create",
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--draft",
            "--base",
            _string_value(target, "base"),
            "--head",
            _string_value(target, "branch"),
            "--title",
            _string_value(target, "title"),
            "--body-file",
            _body_placeholder(body_source),
        ],
        body_source=body_source,
        note=f"validation required before execution: {_string_value(target, 'validation')}",
    )
    return [command], _validate_command(command)


def _plan_high_risk_parking(target: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
    blockers = _missing(target, ["worktree", "branch", "base"])
    if blockers:
        return [], blockers
    command = _command(
        "git_worktree_add",
        [
            "git",
            "worktree",
            "add",
            "-b",
            _string_value(target, "branch"),
            _string_value(target, "worktree"),
            _string_value(target, "base"),
        ],
        note="dry-run high-risk isolation plan only",
    )
    return [command], _validate_command(command)


def build_executor_plan(manifest: dict[str, object], *, repo: str = DEFAULT_REPO) -> dict[str, object]:
    action_type, target = _action(manifest)
    blockers: list[str] = []
    commands: list[dict[str, object]] = []

    if not _bool_value(manifest, "read_only"):
        blockers.append("manifest_not_read_only")
    if action_type not in SUPPORTED_ACTIONS:
        blockers.append("unsupported_action")

    manifest_status = _string_value(manifest, "status") or "data_missing"
    may_execute = _bool_value(manifest, "may_execute")
    if "manifest_not_read_only" in blockers:
        status = "blocked"
        blockers.extend(_manifest_blockers(manifest))
    elif action_type == "review_only":
        status = "owner_review_required"
        blockers.extend(_manifest_blockers(manifest))
    elif action_type in WRITE_ACTIONS and not may_execute:
        status = "blocked"
        blockers.append("manifest_may_execute_false")
        blockers.extend(_manifest_blockers(manifest))
    elif manifest_status != "eligible":
        status = "blocked"
        blockers.append(f"manifest_status_not_eligible:{manifest_status}")
        blockers.extend(_manifest_blockers(manifest))
    elif not blockers:
        if action_type == "open_issue":
            commands, command_blockers = _plan_open_issue(target, repo)
        elif action_type == "comment_existing_issue":
            commands, command_blockers = _plan_comment("issue", manifest, target, repo)
        elif action_type == "comment_existing_pr":
            commands, command_blockers = _plan_comment("pr", manifest, target, repo)
        elif action_type == "create_draft_pr":
            commands, command_blockers = _plan_draft_pr(target, repo)
        elif action_type == "park_high_risk":
            commands, command_blockers = _plan_high_risk_parking(target)
        else:
            commands, command_blockers = [], ["unsupported_action"]
        blockers.extend(command_blockers)
        status = "planned" if not blockers else "blocked"
    else:
        status = "blocked"

    if blockers:
        commands = []

    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "execute": False,
        "status": status,
        "manifest_status": manifest_status,
        "manifest_may_execute": may_execute,
        "action": action_type or "DATA_MISSING",
        "target": target,
        "commands": commands,
        "blockers": sorted(set(blockers)),
        "requires_final_owner_confirmation": True,
        "executor_required": True,
        "safe_to_execute_in_this_helper": False,
        "notes": [
            "This helper renders a future write plan only.",
            "It never executes GitHub, git, host-state, runtime, timer, or data writes.",
        ],
    }


def load_json_source(inline_json: str | None, path: Path | None, *, source_name: str) -> dict[str, object]:
    if inline_json and path:
        raise ValueError(f"{source_name}: provide inline JSON or path, not both")
    if not inline_json and not path:
        raise ValueError(f"{source_name}: JSON source is required")
    text = inline_json if inline_json is not None else path.read_text(encoding="utf-8")  # type: ignore[union-attr]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{source_name}: JSON must be an object")
    return dict(payload)


def format_plan(plan: dict[str, object]) -> str:
    lines = [
        f"status: {plan.get('status')}",
        f"action: {plan.get('action')}",
        "read_only: true",
        "execute: false",
        "requires_final_owner_confirmation: true",
    ]
    commands = plan.get("commands")
    if isinstance(commands, list) and commands:
        lines.append("commands:")
        for command in commands:
            if isinstance(command, dict) and isinstance(command.get("argv"), list):
                lines.append("- " + " ".join(str(part) for part in command["argv"]))
    blockers = plan.get("blockers")
    if isinstance(blockers, list) and blockers:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in blockers)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="render a dry-run executor plan without performing writes")
    manifest_group = plan.add_mutually_exclusive_group(required=True)
    manifest_group.add_argument("--manifest-json")
    manifest_group.add_argument("--manifest-path", type=Path)
    plan.add_argument("--repo", default=DEFAULT_REPO)
    plan.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "plan":
        try:
            manifest = load_json_source(args.manifest_json, args.manifest_path, source_name="manifest")
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        plan = build_executor_plan(manifest, repo=args.repo)
        if args.json:
            print(json.dumps(plan, indent=2, sort_keys=True))
        else:
            print(format_plan(plan))
        return 0 if plan["status"] in {"planned", "owner_review_required"} else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
