#!/usr/bin/env python3
"""Codex/Claude/Gemini hook wrapper for the Tenn dev-agent task-card contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

try:
    from scripts import agent_decision_ledger as decision_ledger_module
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import agent_decision_ledger as decision_ledger_module  # type: ignore


ACTIVE_TASK_MARKER = Path(".tenn/active_agent_task")
CONTRACT_SCRIPT = Path("scripts/agent_job_contract.py")
REGISTRY_SCRIPT = Path("scripts/agent_job_registry.py")
DECISION_LEDGER_SCRIPT = Path("scripts/agent_decision_ledger.py")
V2_ACTIVE_SELECTOR_FIELDS = (
    "job_id",
    "session_id",
    "task_card",
    "task_card_sha256",
    "scope_fingerprint",
    "project_id",
    "claim_id",
    "hypothesis_id",
    "program_track",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)
V2_SEMANTIC_IDENTITY_FIELDS = (
    "project_id",
    "claim_id",
    "hypothesis_id",
    "program_track",
    "source_class",
    "dataset_version",
    "evidence_hash",
    "target_transition",
)
V2_REQUIRED_ENV = "TENN_V2_REQUIRED"
FILE_MUTATION_TOOLS = {"apply_patch", "edit", "replace", "write", "write_file"}
SHELL_TOOL_NAMES = {"bash", "run_shell_command", "shell"}
READ_ONLY_COMMANDS = {
    "cat",
    "cksum",
    "grep",
    "head",
    "jq",
    "ls",
    "pwd",
    "readlink",
    "realpath",
    "rg",
    "sha256sum",
    "stat",
    "tail",
    "test",
    "true",
    "wc",
}
READ_ONLY_GIT_COMMANDS = {
    "diff",
    "log",
    "ls-files",
    "merge-base",
    "rev-parse",
    "show",
    "show-ref",
    "status",
}
READ_ONLY_SYSTEMCTL_COMMANDS = {
    "cat",
    "is-active",
    "is-enabled",
    "list-dependencies",
    "list-jobs",
    "list-timers",
    "list-unit-files",
    "list-units",
    "show",
    "status",
}
RUNTIME_SYSTEMCTL_COMMANDS = {
    "daemon-reload",
    "disable",
    "enable",
    "kill",
    "mask",
    "reload",
    "restart",
    "start",
    "stop",
    "unmask",
}
PUBLISH_GIT_COMMANDS = {"add", "commit", "push"}
MODEL_SUFFIXES = {
    ".bin",
    ".joblib",
    ".onnx",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".safetensors",
}
DATASET_SUFFIXES = {".arrow", ".csv", ".feather", ".jsonl", ".parquet"}
DATABASE_SUFFIXES = {".db", ".db3", ".sqlite", ".sqlite3"}
DATABASE_SIDECAR_SUFFIXES = tuple(
    f"{suffix}{sidecar}"
    for suffix in sorted(DATABASE_SUFFIXES)
    for sidecar in ("-journal", "-shm", "-wal")
)
PATCH_FILE_RE = re.compile(
    r"^\*\*\*\s+(Add|Update|Delete)\s+File:\s*(.+?)\s*$", re.MULTILINE
)


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


@dataclass(frozen=True)
class ToolAdmission:
    """Fail-closed V2 classification for one proposed tool invocation."""

    classified: bool
    capabilities: frozenset[str] = frozenset()
    issue: str | None = None


def _read_hook_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("hook stdin JSON must be an object")
    return loaded


def _env_flag(values: Mapping[str, str], name: str) -> bool:
    return values.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _hook_tool_name(hook_input: Mapping[str, Any] | None) -> str:
    if not hook_input:
        return ""
    value = hook_input.get("tool_name", hook_input.get("toolName", ""))
    return str(value).strip() if isinstance(value, str) else ""


def _hook_tool_input(hook_input: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not hook_input:
        return {}
    value = hook_input.get("tool_input", hook_input.get("toolInput", {}))
    return value if isinstance(value, Mapping) else {}


def _bash_command(hook_input: Mapping[str, Any] | None) -> str:
    tool_input = _hook_tool_input(hook_input)
    value = tool_input.get("command", tool_input.get("cmd", ""))
    return str(value).strip() if isinstance(value, str) else ""


def _repo_relative_path(repo_root: Path, raw_path: str) -> str | None:
    candidate = Path(raw_path.strip()).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        return candidate.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return None


def _is_task_card_path(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path)
    return (
        candidate.parent.as_posix() == "docs/agent_tasks"
        and candidate.suffix.lower() == ".md"
        and candidate.name not in {"", ".md"}
    )


def _mutation_paths(
    repo_root: Path,
    tool_name: str,
    hook_input: Mapping[str, Any] | None,
) -> list[str] | None:
    normalized_tool = tool_name.strip().lower()
    tool_input = _hook_tool_input(hook_input)
    if normalized_tool == "apply_patch":
        patch = tool_input.get("patch")
        if not isinstance(patch, str) or not patch.strip():
            return None
        matches = PATCH_FILE_RE.findall(patch)
        if not matches or "*** Move to:" in patch:
            return None
        paths: list[str] = []
        for _, raw_path in matches:
            path = _repo_relative_path(repo_root, raw_path)
            if path is None:
                return None
            paths.append(path)
        return paths
    if normalized_tool in {"edit", "replace", "write", "write_file"}:
        raw_path = tool_input.get(
            "file_path",
            tool_input.get(
                "filePath",
                tool_input.get("path", tool_input.get("filename")),
            ),
        )
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
        path = _repo_relative_path(repo_root, raw_path)
        return [path] if path is not None else None
    return []


def _is_task_card_bootstrap(
    repo_root: Path,
    tool_name: str,
    hook_input: Mapping[str, Any] | None,
) -> bool:
    if tool_name.strip().lower() not in FILE_MUTATION_TOOLS:
        return False
    paths = _mutation_paths(repo_root, tool_name, hook_input)
    if paths is None or len(paths) != 1 or not _is_task_card_path(paths[0]):
        return False
    if tool_name.strip().lower() != "apply_patch":
        return True
    patch = _hook_tool_input(hook_input).get("patch")
    if not isinstance(patch, str):
        return False
    matches = PATCH_FILE_RE.findall(patch)
    return len(matches) == 1 and matches[0][0] in {"Add", "Update"}


def _simple_shell_tokens(command: str) -> list[str] | None:
    if not command or "\n" in command:
        return None
    if re.search(r"&&|\|\||[;&|<>`]|\$\(", command):
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    return tokens or None


def _systemctl_action(tokens: list[str]) -> str | None:
    """Return a local systemctl action, rejecting alternate control targets."""

    if not tokens or tokens[0] != "systemctl":
        return None
    forbidden_exact = {
        "-H",
        "--host",
        "-M",
        "--machine",
        "--root",
        "--image",
        "--transport",
    }
    forbidden_prefixes = tuple(f"{option}=" for option in forbidden_exact if option.startswith("--"))
    if any(
        token in forbidden_exact
        or token.startswith(forbidden_prefixes)
        or token.startswith(("-H", "-M"))
        for token in tokens[1:]
    ):
        return None
    no_argument_options = {
        "--all",
        "--full",
        "--global",
        "--legend",
        "--no-ask-password",
        "--no-block",
        "--no-legend",
        "--no-pager",
        "--no-reload",
        "--no-wall",
        "--quiet",
        "--reverse",
        "--runtime",
        "--show-types",
        "--system",
        "--user",
        "-a",
        "-l",
        "-q",
        "-r",
    }
    argument_options = {
        "--job-mode",
        "--kill-who",
        "--output",
        "--property",
        "--signal",
        "--state",
        "--type",
        "-n",
        "-o",
        "-p",
        "-s",
        "-t",
    }
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in forbidden_exact or token.startswith(forbidden_prefixes):
            return None
        if token == "--":
            index += 1
            break
        if token in no_argument_options or token.startswith("--no-"):
            index += 1
            continue
        if token in argument_options:
            if index + 1 >= len(tokens):
                return None
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in argument_options if option.startswith("--")):
            index += 1
            continue
        if token.startswith("-"):
            return None
        return token
    return tokens[index] if index < len(tokens) else None


def _git_command(tokens: list[str]) -> tuple[str | None, list[str]]:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-C" and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, tokens[index + 1 :]
    return None, []


def _read_only_git(tokens: list[str]) -> bool:
    if any(
        token == "-c"
        or (token.startswith("-c") and token != "-C")
        or token in {"-p", "--paginate", "--exec-path", "--config-env"}
        or token.startswith(("--exec-path=", "--config-env="))
        for token in tokens[1:]
    ):
        return False
    subcommand, args = _git_command(tokens)
    if any(
        arg in {"--ext-diff", "--textconv", "--output"}
        or arg.startswith("--output=")
        for arg in args
    ):
        return False
    if subcommand in READ_ONLY_GIT_COMMANDS:
        return True
    if subcommand == "branch":
        flag_only = {
            "-a",
            "-r",
            "-v",
            "-vv",
            "--all",
            "--ignore-case",
            "--merged",
            "--no-color",
            "--no-contains",
            "--no-merged",
            "--points-at",
            "--remotes",
            "--show-current",
            "--verbose",
        }
        return all(
            arg in flag_only
            or arg.startswith(
                (
                    "--color=",
                    "--contains=",
                    "--format=",
                    "--no-contains=",
                    "--no-merged=",
                    "--points-at=",
                    "--sort=",
                )
            )
            for arg in args
        )
    if subcommand == "remote":
        return not args or args[0] in {"-v", "get-url", "show"}
    if subcommand == "worktree":
        return bool(args) and args[0] == "list"
    if subcommand == "config":
        read_modes = {"--get", "--get-all", "--get-regexp", "--list", "-l"}
        write_modes = {
            "--add",
            "--edit",
            "--global",
            "--local",
            "--remove-section",
            "--rename-section",
            "--replace-all",
            "--system",
            "--unset",
            "--unset-all",
            "--worktree",
        }
        return any(arg in read_modes for arg in args) and not any(
            arg in write_modes for arg in args
        )
    return False


def _command_path(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve(strict=False)


def _python_helper_command(
    tokens: list[str],
    *,
    repo_root: Path,
) -> tuple[Path, str, list[str]] | None:
    if len(tokens) < 3 or tokens[0] not in {"python", "python3"}:
        return None
    return _command_path(repo_root, tokens[1]), tokens[2], tokens[3:]


def _trusted_guard_paths(control_plane_root: Path, repo_root: Path) -> set[Path]:
    repo_relative = Path(".agents/skills/tenn-git-guard/scripts/tenn_git_guard.py")
    authoritative = (control_plane_root / repo_relative).resolve(strict=False)
    trusted = {authoritative}
    try:
        authoritative_digest = hashlib.sha256(authoritative.read_bytes()).digest()
    except OSError:
        return trusted
    candidates = {
        (repo_root / repo_relative).resolve(strict=False),
        (Path.home() / repo_relative).resolve(strict=False),
        (Path.home() / ".codex/skills/tenn-git-guard/scripts/tenn_git_guard.py").resolve(
            strict=False
        ),
    }
    for candidate in candidates - {authoritative}:
        try:
            if hashlib.sha256(candidate.read_bytes()).digest() == authoritative_digest:
                trusted.add(candidate)
        except OSError:
            continue
    return trusted


def _trusted_control_script_paths(
    control_plane_root: Path,
    repo_root: Path,
    relative: Path,
) -> set[Path]:
    authoritative = (control_plane_root / relative).resolve(strict=False)
    trusted = {authoritative}
    vendored = (repo_root / relative).resolve(strict=False)
    if vendored != authoritative:
        try:
            if hashlib.sha256(vendored.read_bytes()).digest() == hashlib.sha256(
                authoritative.read_bytes()
            ).digest():
                trusted.add(vendored)
        except OSError:
            pass
    return trusted


def _read_only_find(tokens: list[str]) -> bool:
    mutating_prefixes = (
        "-delete",
        "-exec",
        "-fls",
        "-fprint",
        "-fprintf",
        "-ok",
    )
    return not any(token.startswith(mutating_prefixes) for token in tokens[1:])


def _read_only_journalctl(tokens: list[str]) -> bool:
    mutating_prefixes = (
        "--flush",
        "--relinquish-var",
        "--rotate",
        "--setup-keys",
        "--sync",
        "--update-catalog",
        "--vacuum",
    )
    return not any(token.startswith(mutating_prefixes) for token in tokens[1:])


def _read_only_rg(tokens: list[str]) -> bool:
    return not any(
        token == "--pre"
        or token.startswith("--pre=")
        or token == "--search-zip"
        for token in tokens[1:]
    )


def _read_only_bash(
    command: str,
    *,
    control_plane_root: Path,
    repo_root: Path,
) -> bool:
    tokens = _simple_shell_tokens(command)
    if tokens is None:
        return False
    executable = tokens[0]
    if executable in READ_ONLY_COMMANDS:
        return executable != "rg" or _read_only_rg(tokens)
    if executable == "find":
        return _read_only_find(tokens)
    if executable == "journalctl":
        return _read_only_journalctl(tokens)
    if executable == "systemctl":
        return _systemctl_action(tokens) in READ_ONLY_SYSTEMCTL_COMMANDS
    if executable == "git":
        return _read_only_git(tokens)

    helper_admission = _trusted_helper_admission(
        control_plane_root, repo_root, tokens, metadata=None
    )
    return helper_admission == ToolAdmission(True, frozenset({"READ"}))


def _claim_bootstrap_card(
    control_plane_root: Path,
    repo_root: Path,
    command: str,
) -> ActiveTaskCard | None:
    tokens = _simple_shell_tokens(command)
    if tokens is None:
        return None
    helper = _python_helper_command(tokens, repo_root=repo_root)
    if helper is None:
        return None
    script, subcommand, args = helper
    if (
        script
        not in _trusted_control_script_paths(
            control_plane_root, repo_root, REGISTRY_SCRIPT
        )
        or subcommand != "claim"
    ):
        return None

    positionals: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"--repo-root", "--stale-after-seconds"}:
            if index + 1 >= len(args):
                return None
            if token == "--repo-root":
                requested_root = Path(args[index + 1]).expanduser()
                if not requested_root.is_absolute():
                    requested_root = repo_root / requested_root
                if requested_root.resolve(strict=False) != repo_root.resolve():
                    return None
            index += 2
            continue
        if token.startswith("--repo-root="):
            requested_root = Path(token.split("=", 1)[1]).expanduser()
            if not requested_root.is_absolute():
                requested_root = repo_root / requested_root
            if requested_root.resolve(strict=False) != repo_root.resolve():
                return None
            index += 1
            continue
        if token.startswith("-"):
            return None
        positionals.append(token)
        index += 1
    if len(positionals) != 1:
        return None
    path = _repo_relative_path(repo_root, positionals[0])
    if not _is_task_card_path(path):
        return None
    assert path is not None
    card = ActiveTaskCard(source="V2 claim bootstrap", display_path=path, path=repo_root / path)
    if not card.path.is_file():
        return None
    validate = _run_contract(
        control_plane_root, repo_root, "v2-claim-bootstrap", ["validate", path]
    )
    metadata = validate.parsed.get("metadata") if validate.parsed else None
    if (
        validate.returncode != 0
        or validate.parsed is None
        or validate.parsed.get("ok") is not True
        or not isinstance(metadata, Mapping)
        or metadata.get("control_contract_version") != 2
    ):
        return None
    return card


def _abandon_bootstrap_allowed(
    control_plane_root: Path,
    repo_root: Path,
    command: str,
    list_active: ContractRun,
) -> bool:
    """Admit one exact current-registry abandon command before selector checks."""

    tokens = _simple_shell_tokens(command)
    if tokens is None:
        return False
    helper = _python_helper_command(tokens, repo_root=repo_root)
    if helper is None:
        return False
    script, subcommand, args = helper
    if (
        script
        not in _trusted_control_script_paths(
            control_plane_root, repo_root, REGISTRY_SCRIPT
        )
        or subcommand != "release"
    ):
        return False

    positionals: list[str] = []
    reason: str | None = None
    requested_root = repo_root
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"--repo-root", "--abandon-reason"}:
            if index + 1 >= len(args):
                return False
            value = args[index + 1]
            if token == "--repo-root":
                requested_root = _command_path(repo_root, value)
            else:
                reason = value.strip()
            index += 2
            continue
        if token.startswith("--repo-root="):
            requested_root = _command_path(repo_root, token.split("=", 1)[1])
            index += 1
            continue
        if token.startswith("--abandon-reason="):
            reason = token.split("=", 1)[1].strip()
            index += 1
            continue
        if token.startswith("-"):
            return False
        positionals.append(token)
        index += 1
    if (
        len(positionals) != 1
        or not reason
        or requested_root.resolve(strict=False) != repo_root.resolve()
    ):
        return False
    job_id = positionals[0]
    if Path(job_id).name != job_id or job_id in {"", ".", ".."}:
        return False

    active_jobs = list_active.parsed.get("active_jobs") if list_active.parsed else None
    if isinstance(active_jobs, list):
        for active in active_jobs:
            if (
                isinstance(active, Mapping)
                and active.get("job_id") == job_id
                and _resolved_worktree_matches(repo_root, active.get("worktree")) is True
            ):
                if active.get("stale") is True:
                    return True
                raw_card = active.get("task_card")
                expected_hash = active.get("task_card_sha256")
                if not isinstance(raw_card, str) or not isinstance(
                    expected_hash, str
                ):
                    return True
                try:
                    observed_hash = hashlib.sha256(
                        _command_path(repo_root, raw_card).read_bytes()
                    ).hexdigest()
                except OSError:
                    return True
                if observed_hash != expected_hash:
                    return True
                claim_head_sha = active.get("claim_head_sha")
                if not isinstance(claim_head_sha, str) or re.fullmatch(
                    r"[0-9a-f]{40}(?:[0-9a-f]{24})?",
                    claim_head_sha,
                ) is None:
                    return True
                validation = _run_contract(
                    control_plane_root,
                    repo_root,
                    "v2-abandon-recovery-card",
                    ["validate", str(raw_card)],
                )
                metadata = validation.parsed.get("metadata") if validation.parsed else None
                if (
                    validation.returncode != 0
                    or validation.parsed is None
                    or validation.parsed.get("ok") is not True
                    or not isinstance(metadata, Mapping)
                    or metadata.get("control_contract_version") != 2
                ):
                    return True
                expected_identity = {
                    "job_id": metadata.get("job_id"),
                    "scope_fingerprint": metadata.get("computed_scope_fingerprint"),
                    **{
                        field: metadata.get(field)
                        for field in V2_SEMANTIC_IDENTITY_FIELDS
                    },
                }
                if any(
                    active.get(field) != value
                    for field, value in expected_identity.items()
                ):
                    return True
    return False


def _ledger_initialize_bootstrap_allowed(
    control_plane_root: Path,
    repo_root: Path,
    command: str,
) -> bool:
    """Admit only explicit initialization of this repo's live V2 ledger."""

    tokens = _simple_shell_tokens(command)
    if tokens is None:
        return False
    helper = _python_helper_command(tokens, repo_root=repo_root)
    if helper is None:
        return False
    script, subcommand, args = helper
    if (
        script
        not in _trusted_control_script_paths(
            control_plane_root, repo_root, DECISION_LEDGER_SCRIPT
        )
        or subcommand != "initialize"
    ):
        return False

    authorized = False
    requested_root = repo_root
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--authorize-create-empty-ledger":
            authorized = True
            index += 1
            continue
        if token == "--repo-root":
            if index + 1 >= len(args):
                return False
            requested_root = _command_path(repo_root, args[index + 1])
            index += 2
            continue
        if token.startswith("--repo-root="):
            requested_root = _command_path(repo_root, token.split("=", 1)[1])
            index += 1
            continue
        return False
    return authorized and requested_root.resolve(strict=False) == repo_root.resolve()


def _allowed_file_set(metadata: Mapping[str, Any]) -> set[str]:
    values = metadata.get("allowed_files")
    if not isinstance(values, list):
        return set()
    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        candidate = PurePosixPath(value.strip().replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts:
            continue
        normalized.add(candidate.as_posix())
    return normalized


def _path_capabilities(
    path: str,
    metadata: Mapping[str, Any],
) -> tuple[frozenset[str], str | None]:
    lowered = path.lower()
    suffix = Path(path).suffix.lower()
    if suffix in MODEL_SUFFIXES:
        return frozenset({"MODEL_PERSIST"}), None
    if suffix in DATABASE_SUFFIXES or lowered.endswith(DATABASE_SIDECAR_SUFFIXES):
        declared = {
            value
            for value in metadata.get("capabilities", [])
            if value in {"DB_COPY_WRITE", "CANONICAL_DB_WRITE"}
        }
        if len(declared) == 1:
            return frozenset(declared), None
        if not declared:
            return frozenset({"DB_COPY_WRITE", "CANONICAL_DB_WRITE"}), None
        return frozenset(), (
            f"database path {path} is ambiguous because both DB write capabilities are declared; "
            "use a dedicated path-classified database helper"
        )
    if suffix in DATASET_SUFFIXES and any(
        marker in lowered for marker in ("dataset", "materialized", "training")
    ):
        return frozenset({"DATASET_MATERIALIZE"}), None
    output_dir = str(metadata.get("output_dir", "")).rstrip("/")
    if output_dir and (path == output_dir or path.startswith(output_dir + "/")):
        return frozenset({"REPORT_WRITE"}), None
    return frozenset({"CODE_EDIT"}), None


def _paths_admission(
    paths: list[str] | None,
    metadata: Mapping[str, Any],
) -> ToolAdmission:
    if not paths:
        return ToolAdmission(False, issue="proposed mutation paths could not be parsed")
    allowed = _allowed_file_set(metadata)
    outside = sorted(set(paths) - allowed)
    if outside:
        return ToolAdmission(
            False,
            issue="proposed paths are outside task-card allowed_files: "
            + ", ".join(outside),
        )
    capabilities: set[str] = set()
    for path in paths:
        path_capabilities, issue = _path_capabilities(path, metadata)
        if issue is not None:
            return ToolAdmission(False, issue=issue)
        capabilities.update(path_capabilities)
    return ToolAdmission(True, capabilities=frozenset(capabilities))


def _unwrap_sudo(tokens: list[str]) -> list[str] | None:
    if not tokens or tokens[0] != "sudo":
        return tokens
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in {"--", "-n"}:
            index += 1
            if token == "--":
                break
            continue
        if token in {"-u", "--user"} and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith("-"):
            return None
        break
    return tokens[index:] or None


def _path_tokens(
    repo_root: Path,
    raw_paths: list[str],
) -> list[str] | None:
    paths: list[str] = []
    for raw_path in raw_paths:
        path = _repo_relative_path(repo_root, raw_path)
        if path is None:
            return None
        paths.append(path)
    return paths or None


def _python_script_capabilities(script: Path) -> frozenset[str]:
    name = script.stem.lower()
    capabilities: set[str] = set()
    if any(
        token in name
        for token in ("audit", "analyze", "check", "diagnose", "inventory", "review", "verify")
    ):
        capabilities.add("READ")
    if any(
        token in name
        for token in (
            "backtest",
            "calibrate",
            "challenger",
            "evaluate",
            "fit",
            "research",
            "retest",
            "train",
            "tune",
        )
    ):
        capabilities.add("RESEARCH_FIT")
    if any(token in name for token in ("materialize", "build_dataset", "prepare_dataset")):
        capabilities.add("DATASET_MATERIALIZE")
    if any(token in name for token in ("persist_model", "save_model", "export_model")):
        capabilities.add("MODEL_PERSIST")
    if any(token in name for token in ("canonical_db", "production_db", "live_db")):
        capabilities.add("CANONICAL_DB_WRITE")
    if any(token in name for token in ("copy_db", "db_copy", "repair_copy")):
        capabilities.add("DB_COPY_WRITE")
    if any(token in name for token in ("publish", "deploy", "release")):
        capabilities.add("PUBLISH")
    if any(token in name for token in ("packet", "report")):
        capabilities.add("REPORT_WRITE")
    if name.startswith("test_") or name.endswith("_test"):
        capabilities.add("CODE_EDIT")
    return frozenset(capabilities)


def _python_artifact_path_admission(
    tokens: list[str],
    *,
    repo_root: Path,
    metadata: Mapping[str, Any],
) -> ToolAdmission:
    """Path-classify explicit Python outputs without treating read inputs as writes."""

    exact_output_options = {
        "--artifact-out",
        "--artifact-output",
        "--database-out",
        "--database-output",
        "--dataset-out",
        "--dataset-output",
        "--db-out",
        "--db-output",
        "--dest",
        "--destination",
        "--export-file",
        "--export-path",
        "--export-to",
        "--materialize-path",
        "--materialize-to",
        "--model-out",
        "--model-output",
        "--model-output-path",
        "--out",
        "--out-dir",
        "--output",
        "--output-dir",
        "--output-file",
        "--output-path",
        "--persist-path",
        "--persist-to",
        "--save",
        "--save-dir",
        "--save-path",
        "--save-to",
        "--write-dir",
        "--write-file",
        "--write-path",
        "--write-to",
    }
    non_path_options = {
        "--no-write",
        "--output-format",
        "--output-mode",
        "--output-style",
        "--overwrite",
    }
    output_prefixes = (
        "--export-",
        "--materialize-",
        "--persist-",
        "--save-",
        "--write-",
    )
    output_markers = ("destination", "output")
    classified_paths: list[str] = []
    explicit_capabilities: set[str] = set()
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if not token.startswith("--"):
            index += 1
            continue
        option, separator, inline_value = token.partition("=")
        output_like = (
            option in exact_output_options
            or option.startswith(output_prefixes)
            or any(marker in option for marker in output_markers)
        )
        if option in non_path_options:
            index += 1
            continue
        if not output_like:
            index += 1
            continue
        if separator:
            raw = inline_value
            index += 1
        elif index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
            raw = tokens[index + 1]
            index += 2
        else:
            return ToolAdmission(
                False,
                issue=f"unclassified output-bearing Python option: {option}",
            )
        path = _repo_relative_path(repo_root, raw)
        if path is None:
            return ToolAdmission(
                False,
                issue="Python output paths must stay inside the current repository",
            )
        classified_paths.append(path)
        if "model" in option:
            explicit_capabilities.add("MODEL_PERSIST")
        if "dataset" in option or "materialize" in option:
            explicit_capabilities.add("DATASET_MATERIALIZE")
        if "database" in option or option.startswith("--db-"):
            lowered = path.lower()
            if not (
                Path(path).suffix.lower() in DATABASE_SUFFIXES
                or lowered.endswith(DATABASE_SIDECAR_SUFFIXES)
            ):
                return ToolAdmission(
                    False,
                    issue="database output options require a recognized database path suffix",
                )
    if not classified_paths:
        return ToolAdmission(True)
    path_admission = _paths_admission(classified_paths, metadata)
    if not path_admission.classified:
        return path_admission
    return ToolAdmission(
        True,
        frozenset({*path_admission.capabilities, *explicit_capabilities}),
    )


def _validation_environment(tokens: list[str]) -> tuple[list[str], bool]:
    """Unwrap only the two environment settings required for local pytest."""

    index = 1 if tokens and tokens[0] == "env" else 0
    required = {
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
    }
    present: set[str] = set()
    while index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("-"):
        assignment = tokens[index]
        if assignment not in required or assignment in present:
            return tokens, False
        present.add(assignment)
        index += 1
    if not present:
        return tokens, False
    if present != required or index >= len(tokens):
        return tokens, False
    return tokens[index:], True


def _staged_git_paths(repo_root: Path) -> list[str] | None:
    """Return all staged paths without invoking repository-configured hooks."""

    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "diff",
            "--cached",
            "--name-status",
            "-z",
            "--find-renames",
            "--no-ext-diff",
            "--",
        ],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return None
    fields = completed.stdout.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    paths: list[str] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        if not status or index + path_count > len(fields):
            return None
        paths.extend(fields[index : index + path_count])
        index += path_count
    return paths


def _configured_git_remotes(repo_root: Path) -> set[str] | None:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "remote",
        ],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return None
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def _strip_bound_repo_root(
    args: list[str],
    *,
    repo_root: Path,
) -> list[str] | None:
    """Remove only a current-worktree --repo-root option from helper args."""

    remaining: list[str] = []
    seen = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--repo-root":
            if seen or index + 1 >= len(args):
                return None
            requested = _command_path(repo_root, args[index + 1])
            if requested != repo_root.resolve():
                return None
            seen = True
            index += 2
            continue
        if token.startswith("--repo-root="):
            if seen:
                return None
            requested = _command_path(repo_root, token.split("=", 1)[1])
            if requested != repo_root.resolve():
                return None
            seen = True
            index += 1
            continue
        remaining.append(token)
        index += 1
    return remaining


def _one_repo_task_card(repo_root: Path, args: list[str]) -> bool:
    if len(args) != 1:
        return False
    relative = _repo_relative_path(repo_root, args[0])
    return _is_task_card_path(relative)


def _contract_helper_admission(
    repo_root: Path,
    subcommand: str,
    args: list[str],
) -> ToolAdmission:
    stripped = _strip_bound_repo_root(args, repo_root=repo_root)
    if stripped is None:
        return ToolAdmission(False, issue="contract helper must target the current worktree")
    if subcommand == "validate":
        if "--write-report" in stripped or not _one_repo_task_card(repo_root, stripped):
            return ToolAdmission(False, issue="V2 admits only read-only validation of one repo task card")
        return ToolAdmission(True, frozenset({"READ"}))
    if subcommand == "check-diff":
        if stripped.count("--no-write-report") != 1:
            return ToolAdmission(False, issue="manual V2 diff checks must use --no-write-report")
        stripped = [token for token in stripped if token != "--no-write-report"]
        if not _one_repo_task_card(repo_root, stripped):
            return ToolAdmission(False, issue="V2 diff check must select one repo task card")
        return ToolAdmission(True, frozenset({"READ"}))
    if subcommand in {"check-artifacts", "check-report-artifacts", "check-closeout"}:
        if not _one_repo_task_card(repo_root, stripped):
            return ToolAdmission(False, issue=f"V2 {subcommand} must select one repo task card")
        return ToolAdmission(True, frozenset({"READ"}))
    return ToolAdmission(False, issue=f"unclassified contract helper command: {subcommand}")


def _registry_helper_admission(
    repo_root: Path,
    subcommand: str,
    args: list[str],
    metadata: Mapping[str, Any] | None,
) -> ToolAdmission:
    stripped = _strip_bound_repo_root(args, repo_root=repo_root)
    if stripped is None:
        return ToolAdmission(False, issue="registry helper must target the current worktree")
    if subcommand == "list-active":
        index = 0
        seen_read_only = False
        while index < len(stripped):
            token = stripped[index]
            if token == "--read-only":
                seen_read_only = True
                index += 1
            elif token == "--stale-after-seconds" and index + 1 < len(stripped):
                index += 2
            elif token.startswith("--stale-after-seconds="):
                index += 1
            else:
                return ToolAdmission(False, issue="unclassified list-active option")
        if not seen_read_only:
            return ToolAdmission(False, issue="list-active must use --read-only")
        return ToolAdmission(True, frozenset({"READ"}))
    if subcommand == "check-overlap":
        positionals: list[str] = []
        index = 0
        while index < len(stripped):
            token = stripped[index]
            if token == "--stale-after-seconds" and index + 1 < len(stripped):
                index += 2
            elif token.startswith("--stale-after-seconds="):
                index += 1
            elif token.startswith("-"):
                return ToolAdmission(False, issue="unclassified check-overlap option")
            else:
                positionals.append(token)
                index += 1
        if not _one_repo_task_card(repo_root, positionals):
            return ToolAdmission(False, issue="check-overlap must select one repo task card")
        return ToolAdmission(True, frozenset({"READ"}))
    if metadata is None:
        return ToolAdmission(False, issue=f"registry {subcommand} requires an active V2 claim")
    job_id = metadata.get("job_id")
    if not isinstance(job_id, str):
        return ToolAdmission(False, issue="active V2 task has no job_id")
    if subcommand == "heartbeat" and stripped == [job_id]:
        return ToolAdmission(True, frozenset({"READ"}))
    if subcommand == "release" and stripped == [job_id]:
        return ToolAdmission(True, frozenset({"REPORT_WRITE"}))
    return ToolAdmission(False, issue=f"registry {subcommand} is not bound to the current V2 job")


def _ledger_helper_admission(
    repo_root: Path,
    subcommand: str,
    args: list[str],
) -> ToolAdmission:
    stripped = _strip_bound_repo_root(args, repo_root=repo_root)
    if stripped is None or any(
        token == "--ledger-path" or token.startswith("--ledger-path=")
        for token in stripped
    ):
        return ToolAdmission(False, issue="decision helper must use the current repo's live ledger")
    if subcommand in {"resolve-path", "validate"}:
        if stripped:
            return ToolAdmission(False, issue=f"decision {subcommand} does not admit entry or path overrides")
        return ToolAdmission(True, frozenset({"READ"}))
    if subcommand == "summarize":
        if stripped in ([], ["--format", "json"], ["--format=json"], ["--format", "markdown"], ["--format=markdown"]):
            return ToolAdmission(True, frozenset({"READ"}))
        return ToolAdmission(False, issue="unclassified decision summarize options")
    if subcommand == "search":
        value_options = {
            "--claim-id",
            "--dataset-version",
            "--decision",
            "--decision-id",
            "--evidence-hash",
            "--hypothesis-id",
            "--outcome-status",
            "--program-track",
            "--project-id",
            "--run-id",
            "--scope-fingerprint",
            "--source-class",
            "--target-transition",
            "--task-id",
            "--text",
        }
        index = 0
        while index < len(stripped):
            token = stripped[index]
            if token == "--no-delta-only":
                index += 1
            elif token in value_options and index + 1 < len(stripped):
                index += 2
            elif any(token.startswith(f"{option}=") for option in value_options):
                index += 1
            else:
                return ToolAdmission(False, issue="unclassified decision search option")
        return ToolAdmission(True, frozenset({"READ"}))
    return ToolAdmission(False, issue=f"decision {subcommand} is not admitted directly")


def _guard_helper_admission(repo_root: Path, subcommand: str, args: list[str]) -> ToolAdmission:
    if subcommand != "preflight":
        return ToolAdmission(False, issue="only guard preflight is admitted")
    stripped = _strip_bound_repo_root(args, repo_root=repo_root)
    if stripped is None or "--audit-path" in stripped or any(
        token.startswith("--audit-path=") for token in stripped
    ):
        return ToolAdmission(False, issue="guard preflight must be read-only and target the current worktree")
    value_options = {"--topic", "--task-card", "--fallback-detail", "--fallback-sample-limit"}
    index = 0
    while index < len(stripped):
        token = stripped[index]
        if token == "--json":
            index += 1
            continue
        if token in value_options and index + 1 < len(stripped):
            if token == "--task-card" and not _one_repo_task_card(repo_root, [stripped[index + 1]]):
                return ToolAdmission(False, issue="guard task card must be inside this repository")
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in value_options):
            if token.startswith("--task-card=") and not _one_repo_task_card(repo_root, [token.split("=", 1)[1]]):
                return ToolAdmission(False, issue="guard task card must be inside this repository")
            index += 1
            continue
        return ToolAdmission(False, issue="unclassified guard preflight option")
    return ToolAdmission(True, frozenset({"READ"}))


def _trusted_helper_admission(
    control_plane_root: Path,
    repo_root: Path,
    tokens: list[str],
    *,
    metadata: Mapping[str, Any] | None,
) -> ToolAdmission | None:
    helper = _python_helper_command(tokens, repo_root=repo_root)
    if helper is None:
        return None
    script, subcommand, args = helper
    if script in _trusted_control_script_paths(
        control_plane_root, repo_root, CONTRACT_SCRIPT
    ):
        return _contract_helper_admission(repo_root, subcommand, args)
    if script in _trusted_control_script_paths(
        control_plane_root, repo_root, REGISTRY_SCRIPT
    ):
        return _registry_helper_admission(repo_root, subcommand, args, metadata)
    if script in _trusted_control_script_paths(
        control_plane_root, repo_root, DECISION_LEDGER_SCRIPT
    ):
        return _ledger_helper_admission(repo_root, subcommand, args)
    if script in _trusted_guard_paths(control_plane_root, repo_root):
        return _guard_helper_admission(repo_root, subcommand, args)
    return None


def _git_publish_admission(
    tokens: list[str],
    *,
    repo_root: Path,
    metadata: Mapping[str, Any],
) -> ToolAdmission:
    hooks_disabled = tokens[1:5] == [
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
    ]
    if hooks_disabled:
        tokens = [tokens[0], *tokens[5:]]
    if any(
        token in {"-C", "-c"}
        or token.startswith(("--git-dir", "--work-tree", "--namespace"))
        for token in tokens[1:]
    ):
        return ToolAdmission(False, issue="publishing Git commands must target the current worktree")
    subcommand, args = _git_command(tokens)
    if subcommand not in PUBLISH_GIT_COMMANDS:
        return ToolAdmission(False, issue=f"Git {subcommand} is not in the V2 publish allowlist")
    if subcommand == "add":
        paths: list[str] = []
        after_separator = False
        for token in args:
            if token == "--" and not after_separator:
                after_separator = True
                continue
            if not after_separator and token in {"-f", "--force"}:
                continue
            if not after_separator and token.startswith("-"):
                return ToolAdmission(False, issue="V2 git add requires explicit paths and no mutation flags")
            if token in {".", ".."}:
                return ToolAdmission(False, issue="V2 git add requires exact task-card paths")
            paths.append(token)
        admission = _paths_admission(_path_tokens(repo_root, paths), metadata)
        if not admission.classified:
            return admission
        return ToolAdmission(
            True,
            capabilities=frozenset({*admission.capabilities, "PUBLISH"}),
        )
    if subcommand == "commit":
        index = 0
        no_verify = False
        no_gpg_sign = False
        has_message = False
        allow_empty = False
        while index < len(args):
            token = args[index]
            if token in {"-m", "--message"} and index + 1 < len(args):
                if not args[index + 1].strip():
                    return ToolAdmission(False, issue="V2 git commit requires a non-empty message")
                has_message = True
                index += 2
                continue
            if token.startswith("--message="):
                if not token.split("=", 1)[1].strip():
                    return ToolAdmission(False, issue="V2 git commit requires a non-empty message")
                has_message = True
                index += 1
                continue
            if token == "--no-verify":
                no_verify = True
                index += 1
                continue
            if token == "--no-gpg-sign":
                no_gpg_sign = True
                index += 1
                continue
            if token == "--allow-empty":
                allow_empty = True
                index += 1
                continue
            if token in {"--quiet", "-q", "--verbose", "-v"}:
                index += 1
                continue
            return ToolAdmission(False, issue="unclassified or unsafe V2 git commit option")
        if not hooks_disabled or not no_verify or not no_gpg_sign or not has_message:
            return ToolAdmission(
                False,
                issue=(
                    "V2 git commit requires `git -c core.hooksPath=/dev/null "
                    "-c core.fsmonitor=false commit --no-verify --no-gpg-sign "
                    "-m <message>`"
                ),
            )
        staged_paths = _staged_git_paths(repo_root)
        if staged_paths == [] and allow_empty:
            return ToolAdmission(True, frozenset({"PUBLISH"}))
        staged_admission = _paths_admission(staged_paths, metadata)
        if not staged_admission.classified:
            return staged_admission
        return ToolAdmission(
            True,
            frozenset({*staged_admission.capabilities, "PUBLISH"}),
        )
    safe_push_flags = {
        "--dry-run",
        "--no-verify",
        "--porcelain",
        "--quiet",
        "--set-upstream",
        "--verbose",
        "-q",
        "-u",
        "-v",
    }
    if any(
        (
            token.startswith("-")
            and token not in safe_push_flags
        )
        or token.startswith(("+", ":"))
        for token in args
    ):
        return ToolAdmission(False, issue="unclassified, destructive, or broad git push is not admitted")
    if "--no-verify" not in args:
        return ToolAdmission(
            False,
            issue="V2 git push requires --no-verify so repository hooks cannot execute unclassified actions",
        )
    positionals = [token for token in args if not token.startswith("-")]
    if len(positionals) != 2:
        return ToolAdmission(
            False,
            issue="V2 git push requires one configured remote followed by HEAD",
        )
    remotes = _configured_git_remotes(repo_root)
    if remotes is None or positionals[0] not in remotes:
        return ToolAdmission(
            False,
            issue="V2 git push destination must be a configured named remote",
        )
    if positionals[1] != "HEAD":
        return ToolAdmission(
            False,
            issue="V2 git push admits only the current HEAD",
        )
    return ToolAdmission(True, frozenset({"PUBLISH"}))


def _gh_admission(tokens: list[str]) -> ToolAdmission:
    if len(tokens) < 3 or any(
        token in {"-R", "--repo", "--hostname"}
        or token.startswith(("--repo=", "--hostname="))
        for token in tokens[1:]
    ):
        return ToolAdmission(False, issue="gh must target the current repository with an explicit subcommand")
    group, action = tokens[1:3]
    read_actions = {
        "issue": {"list", "status", "view"},
        "pr": {"checks", "diff", "list", "status", "view"},
        "repo": {"view"},
        "run": {"list", "view"},
    }
    publish_actions = {
        "issue": {"close", "comment", "create", "edit", "reopen"},
        "pr": {"close", "comment", "create", "edit", "merge", "ready", "reopen"},
    }
    if action in read_actions.get(group, set()):
        return ToolAdmission(True, frozenset({"READ"}))
    if action in publish_actions.get(group, set()):
        return ToolAdmission(True, frozenset({"PUBLISH"}))
    return ToolAdmission(False, issue=f"gh {group} {action} is not in the V2 allowlist")


def _ruff_admission(
    tokens: list[str],
    *,
    repo_root: Path,
    metadata: Mapping[str, Any],
) -> ToolAdmission:
    if len(tokens) < 2 or tokens[1] not in {"check", "format"}:
        return ToolAdmission(False, issue="V2 admits only ruff check or ruff format")
    if any(
        token in {"--cache-dir", "--config", "--output-file"}
        or token.startswith(("--cache-dir=", "--config=", "--output-file="))
        for token in tokens[2:]
    ):
        return ToolAdmission(False, issue="ruff path/config output overrides are not admitted")
    value_options = {
        "--extend-ignore",
        "--extend-select",
        "--ignore",
        "--line-length",
        "--select",
        "--target-version",
    }
    flag_options = {
        "--check",
        "--diff",
        "--exit-non-zero-on-fix",
        "--fix",
        "--fix-only",
        "--force-exclude",
        "--isolated",
        "--no-cache",
        "--no-fix",
        "--quiet",
        "--show-fixes",
        "--statistics",
        "--unsafe-fixes",
        "--verbose",
        "-q",
        "-v",
    }
    paths: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in value_options and index + 1 < len(tokens):
            index += 2
        elif any(token.startswith(f"{option}=") for option in value_options):
            index += 1
        elif token in flag_options:
            index += 1
        elif token.startswith("-"):
            return ToolAdmission(False, issue="unclassified ruff option")
        else:
            paths.append(token)
            index += 1
    mutating = (
        tokens[1] == "format" and "--check" not in tokens[2:]
    ) or any(token in {"--fix", "--fix-only"} for token in tokens[2:])
    if not mutating:
        return ToolAdmission(True, frozenset({"READ"}))
    return _paths_admission(_path_tokens(repo_root, paths), metadata)


def _pytest_admission(
    tokens: list[str],
    *,
    repo_root: Path,
    hardened_environment: bool,
) -> ToolAdmission:
    if not hardened_environment:
        return ToolAdmission(
            False,
            issue=(
                "V2 pytest requires PYTHONDONTWRITEBYTECODE=1 and "
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"
            ),
        )
    forbidden = {
        "--basetemp",
        "--cache-clear",
        "--confcutdir",
        "--junitxml",
        "--override-ini",
        "--pyargs",
        "--rootdir",
        "-o",
    }
    if any(
        token in forbidden
        or any(token.startswith(f"{option}=") for option in forbidden if option.startswith("--"))
        for token in tokens[1:]
    ):
        return ToolAdmission(False, issue="pytest plugin, external-root, cache, or output overrides are not admitted")
    value_options = {"--capture", "--maxfail", "--tb", "-k", "-m"}
    flag_options = {
        "--collect-only",
        "--disable-warnings",
        "--exitfirst",
        "--no-header",
        "--no-summary",
        "--quiet",
        "--strict-config",
        "--strict-markers",
        "-q",
        "-s",
        "-v",
        "-x",
    }
    targets: list[str] = []
    cacheprovider_disabled = False
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-p" and index + 1 < len(tokens):
            if tokens[index + 1] != "no:cacheprovider":
                return ToolAdmission(False, issue="V2 pytest admits only -p no:cacheprovider")
            cacheprovider_disabled = True
            index += 2
        elif token == "-pno:cacheprovider":
            cacheprovider_disabled = True
            index += 1
        elif token in value_options and index + 1 < len(tokens):
            index += 2
        elif any(token.startswith(f"{option}=") for option in value_options):
            index += 1
        elif token in flag_options or (token.startswith("-v") and set(token[1:]) == {"v"}):
            index += 1
        elif token.startswith("-"):
            return ToolAdmission(False, issue="unclassified pytest option")
        else:
            target = token.split("::", 1)[0]
            if _repo_relative_path(repo_root, target) is None:
                return ToolAdmission(False, issue="pytest targets must stay inside the current repository")
            targets.append(target)
            index += 1
    if not targets:
        return ToolAdmission(False, issue="V2 pytest requires at least one explicit repo-local target")
    if not cacheprovider_disabled:
        return ToolAdmission(False, issue="V2 pytest requires -p no:cacheprovider")
    return ToolAdmission(True, frozenset({"READ", "CODE_EDIT"}))


def _shell_admission(
    control_plane_root: Path,
    repo_root: Path,
    metadata: Mapping[str, Any],
    command: str,
) -> ToolAdmission:
    tokens = _simple_shell_tokens(command)
    if tokens is None:
        return ToolAdmission(
            False,
            issue="compound, redirected, multiline, or unparsable shell commands are not admitted by V2",
        )
    if _read_only_bash(
        command,
        control_plane_root=control_plane_root,
        repo_root=repo_root,
    ):
        return ToolAdmission(True, frozenset({"READ"}))

    unwrapped = _unwrap_sudo(tokens)
    if unwrapped is None:
        return ToolAdmission(False, issue="unsupported sudo wrapper")
    tokens = unwrapped
    tokens, hardened_validation_environment = _validation_environment(tokens)
    executable = tokens[0]
    if executable == "systemctl":
        if _systemctl_action(tokens) is None:
            return ToolAdmission(False, issue="remote, alternate-root, or malformed systemctl is not admitted")
        return ToolAdmission(True, frozenset({"RUNTIME_CHANGE"}))
    if executable == "service":
        return ToolAdmission(True, frozenset({"RUNTIME_CHANGE"}))
    if executable == "git":
        return _git_publish_admission(tokens, repo_root=repo_root, metadata=metadata)
    if executable == "gh":
        return _gh_admission(tokens)
    if executable == "sqlite3":
        return ToolAdmission(False, issue="sqlite3 shell execution is not admitted; use a path-classified database helper")
    if executable in {
        "chmod",
        "chown",
        "cp",
        "install",
        "ln",
        "mkdir",
        "mv",
        "rm",
        "touch",
        "truncate",
    }:
        return ToolAdmission(False, issue=f"shell filesystem mutation via {executable} is not admitted; use an exact-path file tool")
    if executable == "ruff":
        return _ruff_admission(tokens, repo_root=repo_root, metadata=metadata)
    if executable == "pytest":
        return _pytest_admission(
            tokens,
            repo_root=repo_root,
            hardened_environment=hardened_validation_environment,
        )
    if executable in {"mypy", "pyright"}:
        return ToolAdmission(False, issue=f"{executable} cache/output behavior is not path-classified")
    if executable == "uv":
        if (
            len(tokens) >= 5
            and tokens[1] == "run"
            and {"--no-sync", "--frozen"}.issubset(tokens[2:4])
        ):
            return _shell_admission(
                control_plane_root,
                repo_root,
                metadata,
                shlex.join(tokens[4:]),
            )
        return ToolAdmission(
            False,
            issue="V2 uv execution requires `uv run --no-sync --frozen` with no other uv options",
        )
    if executable in {"python", "python3"}:
        if len(tokens) >= 3 and tokens[1:3] == ["-m", "pytest"]:
            return _pytest_admission(
                ["pytest", *tokens[3:]],
                repo_root=repo_root,
                hardened_environment=hardened_validation_environment,
            )
        if len(tokens) >= 3 and tokens[1:3] in (
            ["-m", "py_compile"],
            ["-m", "compileall"],
        ):
            return ToolAdmission(False, issue="Python bytecode compilation writes unclassified cache paths")
        trusted = _trusted_helper_admission(
            control_plane_root, repo_root, tokens, metadata=metadata
        )
        if trusted is not None:
            return trusted
        if len(tokens) < 2 or tokens[1].startswith("-"):
            return ToolAdmission(False, issue="unclassified Python invocation")
        relative_script = _repo_relative_path(repo_root, tokens[1])
        if relative_script is None:
            return ToolAdmission(False, issue="Python scripts must stay inside the current repository")
        capabilities = _python_script_capabilities(_command_path(repo_root, tokens[1]))
        artifact_admission = _python_artifact_path_admission(
            tokens,
            repo_root=repo_root,
            metadata=metadata,
        )
        if not artifact_admission.classified:
            return artifact_admission
        if capabilities:
            return ToolAdmission(
                True,
                frozenset({*capabilities, *artifact_admission.capabilities}),
            )
        return ToolAdmission(False, issue="unclassified Python script")
    if executable == "curl":
        return ToolAdmission(False, issue="arbitrary HTTP requests are not admitted by V2")
    return ToolAdmission(False, issue=f"unclassified shell executable: {executable}")


def _tool_admission(
    control_plane_root: Path,
    repo_root: Path,
    metadata: Mapping[str, Any],
    hook_input: Mapping[str, Any] | None,
) -> ToolAdmission:
    tool_name = _hook_tool_name(hook_input)
    normalized_tool = tool_name.lower()
    if not normalized_tool:
        return ToolAdmission(True, frozenset({"READ"}))
    if normalized_tool in FILE_MUTATION_TOOLS:
        return _paths_admission(
            _mutation_paths(repo_root, tool_name, hook_input), metadata
        )
    if normalized_tool in SHELL_TOOL_NAMES:
        command = _bash_command(hook_input)
        if not command:
            return ToolAdmission(False, issue="V2 shell admission requires a command")
        return _shell_admission(
            control_plane_root, repo_root, metadata, command
        )
    return ToolAdmission(False, issue=f"unclassified tool: {tool_name}")


def _substantive_before_tool(
    control_plane_root: Path,
    repo_root: Path,
    hook_input: Mapping[str, Any] | None,
) -> bool:
    tool_name = _hook_tool_name(hook_input).lower()
    if tool_name in FILE_MUTATION_TOOLS:
        return not _is_task_card_bootstrap(repo_root, tool_name, hook_input)
    if tool_name in SHELL_TOOL_NAMES:
        return not _read_only_bash(
            _bash_command(hook_input),
            control_plane_root=control_plane_root,
            repo_root=repo_root,
        )
    return True


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


def _resolved_worktree_matches(repo_root: Path, raw_worktree: object) -> bool | None:
    if not isinstance(raw_worktree, str) or not raw_worktree.strip():
        return None
    try:
        candidate = Path(raw_worktree.strip()).expanduser()
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate.resolve(strict=False) == repo_root.resolve()
    except (OSError, ValueError):
        return None


def _v2_registry_warning_state(
    list_active: ContractRun,
) -> tuple[dict[str, list[str]], list[str]]:
    warnings_by_job: dict[str, list[str]] = {}
    unscoped_active_warnings: list[str] = []
    warnings = list_active.parsed.get("warnings") if list_active.parsed else None
    if not isinstance(warnings, list):
        return warnings_by_job, unscoped_active_warnings
    for warning in warnings:
        if not isinstance(warning, Mapping) or warning.get("field") != "active_jobs":
            continue
        job_id = warning.get("job_id")
        message = warning.get("message")
        if not isinstance(message, str) or not message.strip():
            continue
        normalized = message.strip()
        if isinstance(job_id, str) and job_id.strip():
            warnings_by_job.setdefault(job_id, []).append(normalized)
        else:
            unscoped_active_warnings.append(normalized)
    return warnings_by_job, unscoped_active_warnings


def _active_record_is_v2_like(
    active: Mapping[str, Any],
    warnings_by_job: Mapping[str, list[str]],
) -> bool:
    job_id = active.get("job_id")
    return (
        "control_contract_version" in active
        or "scope_fingerprint" in active
        or any(field in active for field in V2_SEMANTIC_IDENTITY_FIELDS)
        or (isinstance(job_id, str) and bool(warnings_by_job.get(job_id)))
    )


def _task_card_declares_v2(card_bytes: bytes) -> bool:
    """Read the top-level contract version without trusting registry identity."""

    try:
        lines = card_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"task card is not UTF-8: {exc}") from exc
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
            return value == "2"
    return False


def _select_active_v2_task_card(
    repo_root: Path,
    list_active: ContractRun,
) -> tuple[ActiveTaskCard | None, ContractRun | None]:
    """Select the sole current target-worktree V2 card."""

    if (
        list_active.returncode != 0
        or list_active.parsed is None
        or list_active.parsed.get("ok") is not True
    ):
        return None, _synthetic_run(
            "active-v2-task-selector",
            ok=False,
            issues=[
                {
                    "field": "active_jobs",
                    "message": "could not read the active registry while selecting a V2 task",
                }
            ],
        )

    active_jobs = list_active.parsed.get("active_jobs")
    if not isinstance(active_jobs, list):
        return None, _synthetic_run(
            "active-v2-task-selector",
            ok=False,
            issues=[{"field": "active_jobs", "message": "registry active_jobs must be a list"}],
        )

    warnings_by_job, unscoped_active_warnings = _v2_registry_warning_state(list_active)

    if unscoped_active_warnings:
        return None, _synthetic_run(
            "active-v2-task-selector",
            ok=False,
            issues=[
                {
                    "field": "active_jobs",
                    "message": "unscoped active registry parse/schema warning: " + message,
                }
                for message in unscoped_active_warnings
            ],
        )

    candidates: list[ActiveTaskCard] = []
    selector_issues: list[dict[str, str]] = []
    for active in active_jobs:
        if not isinstance(active, Mapping):
            continue
        if active.get("status", "active") != "active" or active.get("stale") is True:
            continue
        registry_v2_like = _active_record_is_v2_like(active, warnings_by_job)
        job_id = active.get("job_id")
        raw_task_card = active.get("task_card")
        card: ActiveTaskCard | None = None
        card_bytes: bytes | None = None
        card_declares_v2 = False
        if not isinstance(raw_task_card, str) or not raw_task_card.strip():
            card_error = "has no task card, so its contract version cannot be inspected"
        else:
            try:
                card = _resolve_card_path(
                    repo_root,
                    raw_task_card,
                    f"target-worktree active registry job {job_id}",
                )
                card_bytes = card.path.read_bytes()
                card_declares_v2 = _task_card_declares_v2(card_bytes)
                card_error = None
            except (OSError, ValueError) as exc:
                card_error = f"task card cannot be safely inspected: {exc}"

        expected_card_hash = active.get("task_card_sha256")
        observed_card_hash = (
            hashlib.sha256(card_bytes).hexdigest() if card_bytes is not None else None
        )
        card_hash_matches = (
            isinstance(expected_card_hash, str)
            and observed_card_hash is not None
            and expected_card_hash.strip().lower() == observed_card_hash
        )
        card_v2_authority = card_declares_v2
        worktree_matches = _resolved_worktree_matches(repo_root, active.get("worktree"))
        if worktree_matches is None:
            if registry_v2_like or card_v2_authority:
                selector_issues.append(
                    {
                        "field": "worktree",
                        "message": (
                            f"V2-like active selector {job_id or '<unknown>'} "
                            "has a missing or invalid worktree and cannot be safely scoped"
                        ),
                    }
                )
            continue
        if not worktree_matches:
            continue
        if card is None:
            if registry_v2_like:
                selector_issues.append(
                    {
                        "field": "task_card",
                        "message": (
                            f"target-worktree active selector {job_id or '<unknown>'} "
                            f"{card_error}"
                        ),
                    }
                )
            continue
        if not registry_v2_like and not card_declares_v2:
            continue
        if card_declares_v2 and not card_hash_matches:
            selector_issues.append(
                {
                    "field": "task_card_sha256",
                    "message": (
                        f"matching V2 selector task card changed after claim: "
                        f"{card.display_path}; abandon and reclaim the task before continuing"
                    ),
                }
            )
            continue

        invalid_fields = [
            field
            for field in V2_ACTIVE_SELECTOR_FIELDS
            if not isinstance(active.get(field), str) or not str(active.get(field)).strip()
        ]
        if active.get("control_contract_version") != 2:
            invalid_fields.append("control_contract_version")
        if isinstance(job_id, str) and warnings_by_job.get(job_id):
            invalid_fields.append("registry_validation")
        if invalid_fields:
            selector_issues.append(
                {
                    "field": "active_jobs",
                    "message": (
                        f"matching V2 selector {job_id or '<unknown>'} is invalid: "
                        + ", ".join(sorted(set(invalid_fields)))
                    ),
                }
            )
            continue
        if not card_hash_matches:
            selector_issues.append(
                {
                    "field": "task_card_sha256",
                    "message": (
                        f"matching V2 selector task card changed after claim: {card.display_path}; "
                        "abandon and reclaim the task before continuing"
                    ),
                }
            )
            continue
        candidates.append(card)

    if selector_issues:
        return None, _synthetic_run(
            "active-v2-task-selector",
            ok=False,
            issues=selector_issues,
        )
    if len(candidates) > 1:
        return None, _synthetic_run(
            "active-v2-task-selector",
            ok=False,
            issues=[
                {
                    "field": "active_jobs",
                    "message": "multiple non-stale V2 jobs select this worktree; resolve the ambiguity before continuing",
                }
            ],
        )
    return (candidates[0] if candidates else None), None


def _explicit_v2_claim_binding_run(
    repo_root: Path,
    *,
    card: ActiveTaskCard,
    metadata: Mapping[str, Any],
    list_active: ContractRun,
) -> ContractRun:
    """Bind an explicit V2 selector to one current claimed card."""

    if (
        list_active.returncode != 0
        or list_active.parsed is None
        or list_active.parsed.get("ok") is not True
        or not isinstance(list_active.parsed.get("active_jobs"), list)
    ):
        return _synthetic_run(
            "explicit-v2-claim-binding",
            ok=False,
            issues=[{"field": "active_jobs", "message": "active registry is unreadable"}],
        )

    try:
        observed_card_hash = hashlib.sha256(card.path.read_bytes()).hexdigest()
    except OSError as exc:
        return _synthetic_run(
            "explicit-v2-claim-binding",
            ok=False,
            issues=[{"field": "task_card", "message": f"cannot read selected card: {exc}"}],
        )

    warnings_by_job, unscoped_warnings = _v2_registry_warning_state(list_active)
    issues = [
        {
            "field": "active_jobs",
            "message": "unscoped active registry parse/schema warning: " + warning,
        }
        for warning in unscoped_warnings
    ]
    matches: list[str] = []
    for active in list_active.parsed["active_jobs"]:
        if not isinstance(active, Mapping):
            issues.append(
                {"field": "active_jobs", "message": "active registry entry must be an object"}
            )
            continue
        if active.get("status", "active") != "active" or active.get("stale") is True:
            continue
        if not _active_record_is_v2_like(active, warnings_by_job):
            continue
        worktree_matches = _resolved_worktree_matches(repo_root, active.get("worktree"))
        if worktree_matches is None:
            issues.append(
                {
                    "field": "worktree",
                    "message": (
                        f"V2-like active record {active.get('job_id') or '<unknown>'} "
                        "has a missing or invalid worktree and cannot be safely scoped"
                    ),
                }
            )
            continue
        if not worktree_matches:
            continue

        job_id = active.get("job_id")
        invalid_fields = [
            field
            for field in V2_ACTIVE_SELECTOR_FIELDS
            if not isinstance(active.get(field), str) or not str(active.get(field)).strip()
        ]
        if active.get("control_contract_version") != 2:
            invalid_fields.append("control_contract_version")
        if isinstance(job_id, str) and warnings_by_job.get(job_id):
            invalid_fields.append("registry_validation")
        if invalid_fields:
            issues.append(
                {
                    "field": "active_jobs",
                    "message": (
                        f"target-worktree V2-like claim {job_id or '<unknown>'} is invalid: "
                        + ", ".join(sorted(set(invalid_fields)))
                    ),
                }
            )
            continue

        raw_task_card = active.get("task_card")
        assert isinstance(raw_task_card, str)
        try:
            active_card = _resolve_card_path(
                repo_root,
                raw_task_card,
                f"active V2 registry job {active.get('job_id') or '<unknown>'}",
            )
        except ValueError as exc:
            issues.append({"field": "task_card", "message": str(exc)})
            continue
        if active_card.path != card.path:
            continue

        expected_job_id = metadata.get("job_id")
        expected_fingerprint = metadata.get("computed_scope_fingerprint")
        expected_card_hash = active.get("task_card_sha256")
        mismatch_fields: list[str] = []
        if active.get("job_id") != expected_job_id:
            mismatch_fields.append("job_id")
        if active.get("scope_fingerprint") != expected_fingerprint:
            mismatch_fields.append("scope_fingerprint")
        if expected_card_hash != observed_card_hash:
            mismatch_fields.append("task_card_sha256")
        if mismatch_fields:
            issues.append(
                {
                    "field": "active_jobs",
                    "message": (
                        "explicit V2 card does not match its active claim: "
                        + ", ".join(sorted(set(mismatch_fields)))
                        + "; abandon and reclaim the task"
                    ),
                }
            )
            continue
        matches.append(str(active.get("session_id") or active.get("job_id")))

    if len(matches) != 1:
        issues.append(
            {
                "field": "active_jobs",
                "message": (
                    "explicit V2 selection requires exactly one non-stale matching "
                    f"target-worktree claim; found {len(matches)}"
                ),
            }
        )
    return _synthetic_run("explicit-v2-claim-binding", ok=not issues, issues=issues)


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


def _warning_messages(payload: dict[str, Any] | None) -> list[str]:
    if not payload:
        return []
    messages: list[str] = []
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        return messages
    for warning in warnings:
        if not isinstance(warning, Mapping):
            continue
        field = warning.get("field", "warning")
        message = warning.get("message")
        if isinstance(message, str) and message.strip():
            messages.append(f"{field}: {message.strip()}")
    return messages


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


def _v2_semantic_scope_run(
    repo_root: Path,
    *,
    metadata: Mapping[str, Any],
    list_active: ContractRun,
) -> tuple[ContractRun, str | None]:
    """Classify an unclaimed V2 card without creating a report or claim."""

    try:
        ledger_path = decision_ledger_module.resolve_live_ledger_path(repo_root)
        if not ledger_path.is_file():
            raise decision_ledger_module.DecisionLedgerError(
                f"decision ledger is missing: {ledger_path}"
            )
        entries = decision_ledger_module.load_entries(ledger_path)
        issues = decision_ledger_module.validate_entries(
            entries, source=str(ledger_path)
        )
        if issues:
            raise decision_ledger_module.DecisionLedgerError("; ".join(issues))
    except (OSError, decision_ledger_module.DecisionLedgerError) as exc:
        return (
            _synthetic_run(
                "v2-semantic-scope",
                ok=False,
                issues=[{"field": "decision_ledger", "message": str(exc)}],
            ),
            None,
        )

    active_jobs = list_active.parsed.get("active_jobs") if list_active.parsed else None
    active = (
        [entry for entry in active_jobs if isinstance(entry, Mapping)]
        if isinstance(active_jobs, list)
        else []
    )
    result = decision_ledger_module.classify_v2_scope(
        metadata,
        active_jobs=active,
        decision_matches=entries,
    )
    status = result.get("status")
    if not isinstance(status, str):
        return (
            _synthetic_run(
                "v2-semantic-scope",
                ok=False,
                issues=[
                    {
                        "field": "semantic_status",
                        "message": "scope classifier returned no status",
                    }
                ],
            ),
            None,
        )
    payload = {"ok": True, **result}
    return (
        ContractRun(
            name="v2-semantic-scope",
            returncode=0,
            stdout=json.dumps(payload, sort_keys=True),
            stderr="",
            parsed=payload,
        ),
        status,
    )


def _released_v2_receipt_run(
    repo_root: Path,
    *,
    card: ActiveTaskCard,
    metadata: Mapping[str, Any],
) -> tuple[ContractRun, str | None, str | None]:
    """Validate the successful-release receipt used by a terminal hook."""

    output_dir = metadata.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir.strip():
        return (
            _synthetic_run(
                "released-v2-closeout-receipt",
                ok=False,
                issues=[{"field": "output_dir", "message": "missing V2 output_dir"}],
            ),
            None,
            None,
        )
    status_path = repo_root / output_dir / "status.json"
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        card_hash = hashlib.sha256(card.path.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError) as exc:
        return (
            _synthetic_run(
                "released-v2-closeout-receipt",
                ok=False,
                issues=[{"field": "status.json", "message": str(exc)}],
            ),
            None,
            None,
        )
    if not isinstance(payload, Mapping):
        return (
            _synthetic_run(
                "released-v2-closeout-receipt",
                ok=False,
                issues=[{"field": "status.json", "message": "must contain a JSON object"}],
            ),
            None,
            None,
        )

    expected = {
        "status": "released",
        "closeout_validated": True,
        "job_id": metadata.get("job_id"),
        "task_card": card.display_path,
        "task_card_sha256": card_hash,
        "scope_fingerprint": metadata.get("computed_scope_fingerprint"),
        **{field: metadata.get(field) for field in V2_SEMANTIC_IDENTITY_FIELDS},
    }
    mismatches = [
        field for field, expected_value in expected.items() if payload.get(field) != expected_value
    ]
    run_id = payload.get("session_id")
    decision_id = payload.get("decision_id")
    if not isinstance(run_id, str) or not run_id.strip():
        mismatches.append("session_id")
    if not isinstance(decision_id, str) or not decision_id.strip():
        mismatches.append("decision_id")
    if mismatches:
        return (
            _synthetic_run(
                "released-v2-closeout-receipt",
                ok=False,
                issues=[
                    {
                        "field": "status.json",
                        "message": (
                            "released V2 closeout receipt mismatch: "
                            + ", ".join(sorted(set(mismatches)))
                        ),
                    }
                ],
            ),
            None,
            None,
        )
    assert isinstance(run_id, str)
    assert isinstance(decision_id, str)
    return (
        _synthetic_run("released-v2-closeout-receipt", ok=True),
        run_id,
        decision_id,
    )


def _v2_decision_candidate_run(
    repo_root: Path,
    *,
    metadata: Mapping[str, Any],
    list_active: ContractRun,
) -> ContractRun:
    """Validate the unappended decision candidate for the current active run."""

    job_id = metadata.get("job_id")
    output_dir = metadata.get("output_dir")
    fingerprint = metadata.get("computed_scope_fingerprint")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (job_id, output_dir, fingerprint)
    ):
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[{"field": "task_card", "message": "missing V2 candidate identity fields"}],
        )

    active_jobs = list_active.parsed.get("active_jobs") if list_active.parsed else None
    current = next(
        (
            active
            for active in active_jobs
            if isinstance(active, Mapping)
            and active.get("job_id") == job_id
            and active.get("scope_fingerprint") == fingerprint
            and active.get("status", "active") == "active"
            and active.get("stale") is not True
        ),
        None,
    ) if isinstance(active_jobs, list) else None
    if not isinstance(current, Mapping):
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[{"field": "active_job", "message": "matching current V2 claim is required"}],
        )

    report_dir = repo_root / str(output_dir)
    outcome_path = report_dir / "RUN_OUTCOME.json"
    candidate_path = report_dir / "DECISION_ENTRY.json"
    try:
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        candidates = decision_ledger_module.load_entry_file(candidate_path)
    except (OSError, json.JSONDecodeError, decision_ledger_module.DecisionLedgerError) as exc:
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[{"field": "DECISION_ENTRY.json", "message": str(exc)}],
        )
    if not isinstance(outcome, Mapping) or len(candidates) != 1:
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[
                {
                    "field": "DECISION_ENTRY.json",
                    "message": "candidate and RUN_OUTCOME must each contain one JSON object",
                }
            ],
        )
    candidate = candidates[0]
    candidate_issues = decision_ledger_module.validate_entry(
        candidate,
        source=str(candidate_path),
    )
    if candidate_issues:
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[
                {"field": "DECISION_ENTRY.json", "message": issue}
                for issue in candidate_issues
            ],
        )

    expected = {
        "scope_fingerprint": fingerprint,
        "task_id": job_id,
        "run_id": current.get("session_id"),
        "outcome_status": outcome.get("status"),
        "phase_before": outcome.get("state_before"),
        "phase_after": outcome.get("state_after"),
        **{field: metadata.get(field) for field in V2_SEMANTIC_IDENTITY_FIELDS},
    }
    mismatches = [
        field for field, value in expected.items() if candidate.get(field) != value
    ]
    if json.dumps(candidate.get("decision_delta"), sort_keys=True) != json.dumps(
        outcome.get("decision_delta"), sort_keys=True
    ):
        mismatches.append("decision_delta")
    if mismatches:
        return _synthetic_run(
            "decision-candidate-closeout-match",
            ok=False,
            issues=[
                {
                    "field": "DECISION_ENTRY.json",
                    "message": "candidate identity does not match current card/outcome: "
                    + ", ".join(sorted(set(mismatches))),
                }
            ],
        )
    return _synthetic_run("decision-candidate-closeout-match", ok=True)


def _v2_decision_closeout_runs(
    control_plane_root: Path,
    repo_root: Path,
    *,
    metadata: Mapping[str, Any],
    list_active: ContractRun,
    run_id_override: str | None = None,
    decision_id_override: str | None = None,
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
    run_id = (
        run_id_override
        if run_id_override is not None
        else current_active.get("session_id")
        if isinstance(current_active, Mapping)
        else None
    )
    if (
        not isinstance(run_id, str)
        or not run_id.strip()
        or (
            run_id_override is None
            and current_active.get("scope_fingerprint") != fingerprint
        )
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
            *(
                ["--decision-id", decision_id_override]
                if decision_id_override is not None
                else []
            ),
        ],
    )
    if search.returncode != 0 or search.parsed is None or search.parsed.get("ok") is not True:
        return [search]

    matches = search.parsed.get("matches")
    matching_ids: list[str] = []
    matching_entries: list[Mapping[str, Any]] = []
    if isinstance(matches, list):
        for match in matches:
            entry = match.get("entry") if isinstance(match, Mapping) else None
            if not isinstance(entry, Mapping):
                continue
            if (
                entry.get("phase_before") == outcome.get("state_before")
                and entry.get("phase_after") == outcome.get("state_after")
                and json.dumps(
                    entry.get("decision_delta"),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                == json.dumps(
                    outcome.get("decision_delta"),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ):
                decision_id = entry.get("decision_id")
                if isinstance(decision_id, str):
                    matching_ids.append(decision_id)
                    matching_entries.append(entry)
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
    try:
        ledger_path = decision_ledger_module.resolve_live_ledger_path(repo_root)
        all_entries = decision_ledger_module.load_entries(ledger_path)
    except (OSError, decision_ledger_module.DecisionLedgerError) as exc:
        return [
            search,
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[{"field": "decision_ledger", "message": str(exc)}],
            ),
        ]
    latest_ids = [
        entry.get("decision_id")
        for entry in matching_entries
        if decision_ledger_module.is_latest_chain_head(all_entries, entry)
    ]
    if not latest_ids:
        return [
            search,
            _synthetic_run(
                "decision-ledger-closeout-match",
                ok=False,
                issues=[
                    {
                        "field": "decision_ledger",
                        "message": "release receipt references a superseded decision instead of the latest chain head",
                    }
                ],
            ),
        ]
    return [
        search,
        ContractRun(
            name="decision-ledger-closeout-match",
            returncode=0,
            stdout=json.dumps({"ok": True, "matching_decision_ids": latest_ids}, sort_keys=True),
            stderr="",
            parsed={"ok": True, "matching_decision_ids": latest_ids},
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
    hook_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    control_plane_root = _resolve_control_plane_root()
    values = env or os.environ
    v2_required = _env_flag(values, V2_REQUIRED_ENV)
    card = find_active_task_card(repo_root, env=values)
    explicitly_selected = card is not None
    tool_name = _hook_tool_name(hook_input)
    normalized_tool = tool_name.lower()
    list_active = _run_registry(
        control_plane_root,
        repo_root,
        "list-active",
        ["list-active", "--read-only", "--repo-root", str(repo_root)],
    )
    if (
        event == "BeforeTool"
        and normalized_tool in SHELL_TOOL_NAMES
        and _abandon_bootstrap_allowed(
            control_plane_root,
            repo_root,
            _bash_command(hook_input),
            list_active,
        )
    ):
        return _allow_payload(
            platform,
            "Tenn V2 recovery: exact current-registry abandonment admitted.",
        )
    active_v2_card, selector_failure = _select_active_v2_task_card(repo_root, list_active)
    if selector_failure is not None:
        selected_card = card or ActiveTaskCard(
            source="active V2 registry selector",
            display_path="<active-v2-registry-selector>",
            path=repo_root,
        )
        return _blocking_payload(
            _summarize_failure(selected_card, [list_active, selector_failure]),
            platform=platform,
        )

    active_v2_authority = active_v2_card is not None
    if event == "BeforeTool" and not active_v2_authority:
        if v2_required and _is_task_card_bootstrap(repo_root, tool_name, hook_input):
            return _allow_payload(
                platform,
                "Tenn V2 task-card bootstrap admitted; validate and claim it before substantive work.",
            )
        if normalized_tool in SHELL_TOOL_NAMES:
            if _ledger_initialize_bootstrap_allowed(
                control_plane_root, repo_root, _bash_command(hook_input)
            ):
                return _allow_payload(
                    platform,
                    "Tenn V2 decision-ledger initialization bootstrap admitted.",
                )
            claim_card = _claim_bootstrap_card(
                control_plane_root, repo_root, _bash_command(hook_input)
            )
            if claim_card is not None:
                return _allow_payload(
                    platform,
                    f"Tenn V2 claim bootstrap admitted: {claim_card.display_path}",
                )
    if explicitly_selected:
        assert card is not None
        if active_v2_card is not None and active_v2_card.path != card.path:
            path_mismatch = _synthetic_run(
                "explicit-v2-claim-binding",
                ok=False,
                issues=[
                    {
                        "field": "task_card",
                        "message": (
                            f"active V2 claim selects {active_v2_card.display_path}, but the "
                            f"explicit selector chooses {card.display_path}"
                        ),
                    }
                ],
            )
            return _blocking_payload(
                _summarize_failure(card, [list_active, path_mismatch]),
                platform=platform,
            )
    else:
        card = active_v2_card
        if card is None:
            if v2_required and event in {"Stop", "SessionEnd"}:
                return _allow_payload(
                    platform,
                    "Tenn V2 closeout: no active V2 claim; substantive tools would have required admission before use.",
                )
            if v2_required and event == "BeforeTool":
                if normalized_tool in SHELL_TOOL_NAMES and _read_only_bash(
                    _bash_command(hook_input),
                    control_plane_root=control_plane_root,
                    repo_root=repo_root,
                ):
                    return _allow_payload(
                        platform,
                        "Tenn V2 admission: read-only bootstrap command allowed before claim.",
                    )
                return _blocking_payload(
                    "Tenn V2 admission blocked substantive or unclassified tool use: "
                    "create, validate, and claim one V2 task card for this worktree first.",
                    platform=platform,
                )
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
    strict_contract = (
        v2_required
        or active_v2_authority
        or _task_card_requires_strict_closeout(card, validate)
    )
    runs = [validate, list_active]
    metadata = validate.parsed.get("metadata") if validate.parsed else None
    validated_v2 = (
        validate.returncode == 0
        and validate.parsed is not None
        and validate.parsed.get("ok") is True
        and isinstance(metadata, Mapping)
        and type(metadata.get("control_contract_version")) is int
        and metadata.get("control_contract_version") == 2
    )
    released_v2_receipt: ContractRun | None = None
    released_v2_run_id: str | None = None
    released_v2_decision_id: str | None = None
    terminal_no_run_status: str | None = None
    if (
        event in {"Stop", "SessionEnd"}
        and explicitly_selected
        and validated_v2
        and not active_v2_authority
    ):
        assert isinstance(metadata, Mapping)
        semantic_run, semantic_status = _v2_semantic_scope_run(
            repo_root,
            metadata=metadata,
            list_active=list_active,
        )
        runs.append(semantic_run)
        output_dir = metadata.get("output_dir")
        status_path = (
            repo_root / str(output_dir) / "status.json"
            if isinstance(output_dir, str)
            else None
        )
        release_receipt_candidate = False
        if status_path is not None and status_path.is_file():
            try:
                status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                status_payload = None
            release_receipt_candidate = (
                isinstance(status_payload, Mapping)
                and status_payload.get("status") == "released"
                and status_payload.get("closeout_validated") is True
                and status_payload.get("job_id") == metadata.get("job_id")
                and status_payload.get("scope_fingerprint")
                == metadata.get("computed_scope_fingerprint")
            )
        if release_receipt_candidate:
            (
                released_v2_receipt,
                released_v2_run_id,
                released_v2_decision_id,
            ) = _released_v2_receipt_run(repo_root, card=card, metadata=metadata)
            runs.append(released_v2_receipt)
        elif semantic_status in {
            "ACTIVE_DUPLICATE",
            "BLOCKED_BY_DECISION",
            "DATA_MISSING",
            "EVIDENCE_CONFLICT",
            "LOOP_GUARD_STOP",
            "REUSED_COMPLETE",
        }:
            terminal_no_run_status = semantic_status
        else:
            released_v2_receipt, _, _ = _released_v2_receipt_run(
                repo_root, card=card, metadata=metadata
            )
            runs.append(released_v2_receipt)
    if v2_required and not validated_v2 and (
        event in {"Stop", "SessionEnd"}
        or (
            event == "BeforeTool"
            and _substantive_before_tool(
                control_plane_root, repo_root, hook_input
            )
        )
    ):
        runs.append(
            _synthetic_run(
                "v2-required-admission",
                ok=False,
                issues=[
                    {
                        "field": "control_contract_version",
                        "message": (
                            "this repository requires control_contract_version: 2 "
                            "for non-trivial work and closeout"
                        ),
                    }
                ],
            )
        )
    if active_v2_authority and not validated_v2:
        runs.append(
            _synthetic_run(
                "active-v2-card-validation",
                ok=False,
                issues=[
                    {
                        "field": "control_contract_version",
                        "message": "the active V2 claim requires its selected task card to validate as V2",
                    }
                ],
            )
        )
    if (
        explicitly_selected
        and validated_v2
        and released_v2_receipt is None
        and terminal_no_run_status is None
    ):
        runs.append(
            _explicit_v2_claim_binding_run(
                repo_root,
                card=card,
                metadata=metadata,
                list_active=list_active,
            )
        )

    if event == "BeforeTool" and validated_v2:
        if normalized_tool in SHELL_TOOL_NAMES and not _bash_command(hook_input):
            runs.append(
                _synthetic_run(
                    "v2-tool-capability",
                    ok=False,
                    issues=[
                        {
                            "field": "tool_input.command",
                            "message": "V2 Bash admission requires the proposed command",
                        }
                    ],
                )
            )
        assert isinstance(metadata, Mapping)
        admission = _tool_admission(
            control_plane_root, repo_root, metadata, hook_input
        )
        if not admission.classified:
            runs.append(
                _synthetic_run(
                    "v2-tool-classification",
                    ok=False,
                    issues=[
                        {
                            "field": "tool_input",
                            "message": admission.issue
                            or "proposed V2 tool use is unclassified",
                        }
                    ],
                )
            )
        requested_capabilities = set(admission.capabilities)
        declared_capabilities = {
            capability
            for capability in metadata.get("capabilities", [])
            if isinstance(capability, str)
        }
        undeclared_capabilities = sorted(
            requested_capabilities - declared_capabilities
        )
        if undeclared_capabilities:
            runs.append(
                _synthetic_run(
                    "v2-tool-capability",
                    ok=False,
                    issues=[
                        {
                            "field": "capabilities",
                            "message": (
                                "proposed tool use requires undeclared capabilities: "
                                + ", ".join(undeclared_capabilities)
                            ),
                        }
                    ],
                )
            )

    if event == "BeforeTool":
        check_diff = _run_contract(
            control_plane_root,
            repo_root,
            "check-diff",
            ["check-diff", card.display_path, "--repo-root", str(repo_root), "--no-write-report"],
        )
        runs.append(check_diff)
    elif event in {"Stop", "SessionEnd"} and terminal_no_run_status is None:
        closeout = _run_contract(
            control_plane_root,
            repo_root,
            "check-closeout",
            ["check-closeout", card.display_path, "--repo-root", str(repo_root)],
        )
        runs.append(closeout)
        if validated_v2:
            assert isinstance(metadata, Mapping)
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
                if active_v2_authority:
                    runs.append(
                        _v2_decision_candidate_run(
                            repo_root,
                            metadata=metadata,
                            list_active=list_active,
                        )
                    )
                    runs.append(
                        _synthetic_run(
                            "v2-registry-release-required",
                            ok=False,
                            issues=[
                                {
                                    "field": "active_job",
                                    "message": (
                                        "validated registry release must publish the decision "
                                        "candidate and remove the active V2 claim before Stop"
                                    ),
                                }
                            ],
                        )
                    )
                else:
                    runs.extend(
                        _v2_decision_closeout_runs(
                            control_plane_root,
                            repo_root,
                            metadata=metadata,
                            list_active=list_active,
                            run_id_override=released_v2_run_id,
                            decision_id_override=released_v2_decision_id,
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
        if terminal_no_run_status is not None:
            return _allow_payload(
                platform,
                f"Tenn V2 semantic stop: {terminal_no_run_status}; no new report or continuation goal is permitted.",
            )
        return _allow_payload(platform)

    if platform == "codex" and event == "Stop":
        return _allow_payload(platform)

    warnings = _warning_messages(validate.parsed)
    message = f"Tenn agent-job contract passed: {card.display_path}"
    if warnings:
        message += "; warnings: " + "; ".join(warnings)
    return _allow_payload(platform, message)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("codex", "claude", "gemini"), default="codex")
    parser.add_argument("--event", choices=("Stop", "SessionEnd", "BeforeTool"), default="Stop")
    parser.add_argument("--repo-root", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        hook_input = _read_hook_stdin()
        repo_root = _resolve_repo_root(args.repo_root)
        payload = build_hook_payload(
            repo_root=repo_root,
            platform=args.platform,
            event=args.event,
            hook_input=hook_input,
        )
    except Exception as exc:
        payload = _blocking_payload(f"Tenn agent-job hook failed: {exc}", platform=args.platform)

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
