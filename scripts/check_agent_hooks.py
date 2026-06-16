#!/usr/bin/env python3
"""Report whether this worktree's Git hooks resolve to expected executable files."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_HOOKS = ("pre-commit", "pre-push")


@dataclass(frozen=True)
class HookStatus:
    name: str
    path: str
    exists: bool
    executable: bool
    expected_fingerprint: str | None
    fingerprint_present: bool | None


@dataclass(frozen=True)
class HookReport:
    ok: bool
    repo_root: str
    git_common_dir: str | None
    configured_hooks_path: str | None
    effective_hooks_dir: str | None
    effective_hooks_dir_exists: bool
    effective_hooks_dir_is_dir: bool
    hooks: list[HookStatus]
    issues: list[str]


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _resolve_repo_root(start: Path) -> Path:
    return Path(_git(start, "rev-parse", "--show-toplevel")).resolve()


def _resolve_configured_hooks_path(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    value = completed.stdout.strip()
    return value or None


def _effective_hooks_dir(repo_root: Path) -> Path:
    git_path_hooks = _git(repo_root, "rev-parse", "--git-path", "hooks")
    candidate = Path(git_path_hooks)
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (repo_root / candidate).resolve(strict=False)


def _parse_expected_fingerprints(values: Sequence[str]) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--expect-fingerprint values must use hook=substring")
        hook, fingerprint = value.split("=", 1)
        hook = hook.strip()
        fingerprint = fingerprint.strip()
        if not hook or not fingerprint:
            raise ValueError("--expect-fingerprint values must use hook=substring")
        fingerprints[hook] = fingerprint
    return fingerprints


def build_report(
    *,
    repo_root: Path,
    hook_names: Sequence[str] = DEFAULT_HOOKS,
    expected_fingerprints: dict[str, str] | None = None,
) -> HookReport:
    root = _resolve_repo_root(repo_root)
    configured_hooks_path = _resolve_configured_hooks_path(root)
    hooks_dir = _effective_hooks_dir(root)
    git_common_dir: str | None
    try:
        git_common_dir = _git(root, "rev-parse", "--git-common-dir")
    except subprocess.CalledProcessError:
        git_common_dir = None

    fingerprints = expected_fingerprints or {}
    statuses: list[HookStatus] = []
    issues: list[str] = []
    hooks_dir_exists = hooks_dir.exists()
    hooks_dir_is_dir = hooks_dir.is_dir()
    if not hooks_dir_exists:
        issues.append(f"hooks directory missing at {hooks_dir}")
    elif not hooks_dir_is_dir:
        issues.append(f"hooks path is not a directory at {hooks_dir}")

    for hook_name in hook_names:
        hook_path = hooks_dir / hook_name
        exists = hook_path.is_file()
        executable = exists and os.access(hook_path, os.X_OK)
        expected = fingerprints.get(hook_name)
        fingerprint_present: bool | None = None
        if expected is not None:
            if exists:
                try:
                    fingerprint_present = expected in hook_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    fingerprint_present = False
            else:
                fingerprint_present = False

        if not exists:
            issues.append(f"{hook_name} missing at {hook_path}")
        elif not executable:
            issues.append(f"{hook_name} is not executable at {hook_path}")
        if expected is not None and fingerprint_present is not True:
            issues.append(f"{hook_name} does not contain expected fingerprint: {expected}")

        statuses.append(
            HookStatus(
                name=hook_name,
                path=str(hook_path),
                exists=exists,
                executable=executable,
                expected_fingerprint=expected,
                fingerprint_present=fingerprint_present,
            )
        )

    return HookReport(
        ok=not issues,
        repo_root=str(root),
        git_common_dir=git_common_dir,
        configured_hooks_path=configured_hooks_path,
        effective_hooks_dir=str(hooks_dir),
        effective_hooks_dir_exists=hooks_dir_exists,
        effective_hooks_dir_is_dir=hooks_dir_is_dir,
        hooks=statuses,
        issues=issues,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--hook", action="append", dest="hooks", help="Hook name to require; repeatable")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when required hooks are missing or invalid")
    parser.add_argument(
        "--expect-fingerprint",
        action="append",
        default=[],
        help="Require a substring inside a hook file, formatted hook=substring",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_report(
            repo_root=args.repo_root,
            hook_names=args.hooks or DEFAULT_HOOKS,
            expected_fingerprints=_parse_expected_fingerprints(args.expect_fingerprint),
        )
    except Exception as exc:
        payload = {
            "ok": False,
            "repo_root": str(args.repo_root),
            "git_common_dir": None,
            "configured_hooks_path": None,
            "effective_hooks_dir": None,
            "effective_hooks_dir_exists": False,
            "effective_hooks_dir_is_dir": False,
            "hooks": [],
            "issues": [str(exc)],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0 if report.ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
