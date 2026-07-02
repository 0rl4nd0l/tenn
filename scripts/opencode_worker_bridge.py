#!/usr/bin/env python3
"""Read-only OpenCode worker bridge for Codex delegation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REQUIRED_RESULT_FIELDS = (
    "worker_id",
    "task_tier",
    "model",
    "decision_limit",
    "summary",
    "findings",
    "evidence_paths",
    "confidence",
    "risks",
    "recommended_next_action",
    "stop_condition_hit",
)

DECISION_LIMITS = {"evidence_only", "recommendation_only", "bounded_implementation", "strategy_bid"}
TASK_TIERS = {"small", "medium", "large", "critical"}
STOP_CONDITION_HIT_VALUES = {"yes", "no", "DATA_MISSING"}
PERMISSION_PROFILES = {"readonly", "none"}
MAX_TASK_BYTES = 12000
MAX_RESULT_BYTES = 32000
MAX_PROBE_ITEMS = 200
MAX_PROBE_TEXT_BYTES = 16000
MAX_PROBE_ITEM_CHARS = 180
WORKER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*)\s*:\s*(.*)$")
MARKDOWN_FENCE_RE = re.compile(r"^`{3,}\s*[A-Za-z0-9_-]*\s*$")
PATHISH_RE = re.compile(
    r"(?:(?:\.\.?/|/)?[A-Za-z0-9._~+-]+(?:/[A-Za-z0-9._~+-]+)+"
    r"|\.env(?:\.[A-Za-z0-9_-]+)?"
    r"|[A-Za-z0-9._-]+\.(?:sqlite3?|db|pem|key|p12|pfx))"
)
DANGEROUS_FLAGS = {
    "--dangerously-skip-permissions",
    "--permission-mode",
    "--allow-all",
    "--unsafe",
    "--yolo",
}


class BridgeError(RuntimeError):
    """User-facing bridge error."""


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dump(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def readonly_permission_rules() -> dict[str, Any]:
    """Return restrictive OpenCode permissions for evidence-only workers."""
    denied_read_patterns = {
        "*.env": "deny",
        "*.env.*": "deny",
        "**/.env": "deny",
        "**/.env.*": "deny",
        "**/credentials*": "deny",
        "**/*credential*": "deny",
        "**/*token*": "deny",
        "**/*api_key*": "deny",
        "**/*apikey*": "deny",
        "**/*.pem": "deny",
        "**/*.key": "deny",
        "**/*.p12": "deny",
        "**/*.pfx": "deny",
        "**/*.db": "deny",
        "**/*.sqlite": "deny",
        "**/*.sqlite3": "deny",
    }
    safe_bash_rules = {
        "*": "deny",
        "pwd": "allow",
        "git diff": "deny",
        "git diff *": "deny",
        "git log": "deny",
        "git log *": "deny",
        "git show *": "deny",
        "git blame *": "deny",
        "git status": "allow",
        "git status *": "allow",
        "git diff --stat": "allow",
        "git diff --stat *": "allow",
        "git rev-parse": "allow",
        "git rev-parse *": "allow",
        "git commit*": "deny",
        "git push*": "deny",
        "git merge*": "deny",
        "git reset*": "deny",
        "git clean*": "deny",
        "git stash*": "deny",
        "git rebase*": "deny",
        "git checkout*": "deny",
        "git switch*": "deny",
        "git cherry-pick*": "deny",
        "cat": "deny",
        "cat *": "deny",
        "ls": "deny",
        "ls *": "deny",
        "find *": "deny",
        "rg *": "deny",
        "grep *": "deny",
        "head *": "deny",
        "tail *": "deny",
        "wc *": "deny",
        "echo *": "deny",
        "rm *": "deny",
        "mv *": "deny",
        "cp *": "deny",
        "chmod *": "deny",
        "chown *": "deny",
        "tee *": "deny",
        "sed -i *": "deny",
        "perl -pi *": "deny",
        "python *": "deny",
        "python3 *": "deny",
        "node *": "deny",
        "bash *": "deny",
        "sh *": "deny",
        "curl *": "deny",
        "wget *": "deny",
    }
    return {
        "*": "deny",
        "read": {"*": "allow", **denied_read_patterns},
        "list": "allow",
        "glob": "allow",
        "grep": "allow",
        "edit": "deny",
        "bash": safe_bash_rules,
        "external_directory": "deny",
        "task": "deny",
        "todowrite": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "lsp": "deny",
        "skill": "deny",
        "question": "deny",
        "doom_loop": "ask",
    }


def build_readonly_opencode_config(agent: str) -> dict[str, Any]:
    permissions = readonly_permission_rules()
    return {
        "$schema": "https://opencode.ai/config.json",
        "permission": permissions,
        "agent": {
            agent: {
                "description": "Read-only evidence scout enforced by Codex worker bridge.",
                "mode": "primary",
                "permission": permissions,
                "tools": {
                    "write": False,
                    "edit": False,
                    "bash": True,
                },
            }
        },
    }


def _nested_get(data: dict[str, Any], keys: Sequence[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _validate_readonly_permission_block(permission: Any, issues: list[str], prefix: str) -> None:
    if not isinstance(permission, dict):
        issues.append(f"{prefix} must be an object")
        return

    if permission.get("edit") != "deny":
        issues.append(f"{prefix}.edit must deny edits")
    if permission.get("external_directory") != "deny":
        issues.append(f"{prefix}.external_directory must deny external paths")
    if permission.get("task") != "deny":
        issues.append(f"{prefix}.task must deny subagents")

    read = permission.get("read")
    if not isinstance(read, dict):
        issues.append(f"{prefix}.read must be granular")
    else:
        if read.get("*") != "allow":
            issues.append(f"{prefix}.read.* must allow normal repo reads")
        for pattern in ("*.env", "*.env.*", "**/.env", "**/.env.*", "**/*.db", "**/*.sqlite", "**/*.sqlite3"):
            if read.get(pattern) != "deny":
                issues.append(f"{prefix}.read.{pattern} must deny sensitive files")

    bash = permission.get("bash")
    if not isinstance(bash, dict):
        issues.append(f"{prefix}.bash must be granular")
    else:
        if bash.get("*") != "deny":
            issues.append(f"{prefix}.bash.* must deny by default")
        allowed_bash = {"pwd", "git status", "git status *", "git diff --stat", "git diff --stat *", "git rev-parse", "git rev-parse *"}
        unexpected_allows = sorted(key for key, value in bash.items() if value == "allow" and key not in allowed_bash)
        for key in unexpected_allows:
            issues.append(f"{prefix}.bash.{key} must not remain allowed in readonly profile")
        for allowed in ("git status", "git status *", "git diff --stat", "git diff --stat *", "git rev-parse", "git rev-parse *"):
            if bash.get(allowed) != "allow":
                issues.append(f"{prefix}.bash.{allowed} must allow only safe git inspection")
        for denied in ("git commit*", "git push*", "git merge*", "git reset*", "git clean*", "git stash*", "rm *"):
            if bash.get(denied) != "deny":
                issues.append(f"{prefix}.bash.{denied} must deny mutation/destruction")


def validate_readonly_permission_config(config: dict[str, Any], agent: str) -> list[str]:
    issues: list[str] = []
    permission = config.get("permission")
    _validate_readonly_permission_block(permission, issues, "permission")

    agent_permission = _nested_get(config, ("agent", agent, "permission"))
    _validate_readonly_permission_block(agent_permission, issues, f"agent.{agent}.permission")

    agent_tools = _nested_get(config, ("agent", agent, "tools"))
    if isinstance(agent_tools, dict):
        if agent_tools.get("write") is not False or agent_tools.get("edit") is not False:
            issues.append("selected agent legacy write/edit tools must be disabled")
    else:
        issues.append("selected agent legacy tools guard must be present")
    return issues


def resolve_opencode_command(command: str | None = None) -> str | None:
    candidates = [command] if command else ["opencode", "/home/l4nd0/.opencode/bin/opencode", "open-code"]
    for candidate in candidates:
        if not candidate:
            continue
        found = shutil.which(candidate)
        if found:
            return found
        path = Path(candidate)
        if path.is_absolute() and path.exists() and os.access(path, os.X_OK):
            return str(path)
    return None


def run_command(args: Sequence[str], timeout_seconds: int, env: dict[str, str] | None = None) -> CommandResult:
    try:
        completed = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
        return CommandResult(
            command=list(args),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except FileNotFoundError as exc:
        return CommandResult(command=list(args), exit_code=127, stdout="", stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=list(args),
            exit_code=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"timed out after {timeout_seconds}s",
            timed_out=True,
        )


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def build_opencode_env(base_env: dict[str, str] | None, config_content: str | None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    if config_content is not None:
        env["OPENCODE_CONFIG_CONTENT"] = config_content
    return env


def _safe_config_summary(config: dict[str, Any], agent: str) -> dict[str, Any]:
    permission = config.get("permission") if isinstance(config.get("permission"), dict) else {}
    agent_permission = _nested_get(config, ("agent", agent, "permission"))
    return {
        "global_edit": permission.get("edit") if isinstance(permission, dict) else None,
        "global_bash_default": _nested_get(permission, ("bash", "*")) if isinstance(permission, dict) else None,
        "global_external_directory": permission.get("external_directory") if isinstance(permission, dict) else None,
        "agent_edit": agent_permission.get("edit") if isinstance(agent_permission, dict) else None,
        "agent_bash_default": _nested_get(agent_permission, ("bash", "*")) if isinstance(agent_permission, dict) else None,
        "agent_external_directory": agent_permission.get("external_directory") if isinstance(agent_permission, dict) else None,
    }


def verify_readonly_permission_enforcement(
    opencode_path: str,
    *,
    agent: str,
    config_content: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    env = build_opencode_env(os.environ, config_content)
    result = run_command([opencode_path, "debug", "config", "--pure"], timeout_seconds=timeout_seconds, env=env)
    if not result.ok:
        return {
            "ok": False,
            "method": "opencode_config_content_debug_config",
            "reason": "debug_config_failed",
            "exit_code": result.exit_code,
            "stderr": _first_nonempty_line(result.stderr),
        }
    try:
        resolved = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "method": "opencode_config_content_debug_config",
            "reason": "debug_config_not_json",
        }

    issues = validate_readonly_permission_config(resolved, agent)
    return {
        "ok": not issues,
        "method": "opencode_config_content_debug_config",
        "reason": None if not issues else "resolved_config_not_readonly",
        "issues": issues,
        "summary": _safe_config_summary(resolved, agent),
    }


def build_permission_enforcement(
    *,
    decision_limit: str,
    permission_profile: str,
    agent: str,
    opencode_path: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    if permission_profile not in PERMISSION_PROFILES:
        raise BridgeError(f"permission-profile must be one of: {', '.join(sorted(PERMISSION_PROFILES))}")

    if decision_limit != "evidence_only":
        if permission_profile == "readonly":
            config = build_readonly_opencode_config(agent)
            issues = validate_readonly_permission_config(config, agent)
            if issues:
                raise BridgeError(f"readonly permission config is invalid: {'; '.join(issues)}")
            config_content = json.dumps(config, separators=(",", ":"))
            verification = verify_readonly_permission_enforcement(
                opencode_path,
                agent=agent,
                config_content=config_content,
                timeout_seconds=min(timeout_seconds, 10),
            )
            if not verification.get("ok"):
                raise BridgeError(
                    "UNSUPPORTED_PERMISSION_ENFORCEMENT: OpenCode readonly permissions could not be proven"
                )
            return (
                {
                    "profile": "readonly",
                    "method": "OPENCODE_CONFIG_CONTENT",
                    "config_sha256": hashlib.sha256(config_content.encode("utf-8")).hexdigest(),
                    "verified": True,
                    "verification": verification,
                },
                build_opencode_env(os.environ, config_content),
            )
        return ({"profile": "none", "method": "none", "verified": False}, dict(os.environ))

    if permission_profile != "readonly":
        raise BridgeError("evidence_only workers require --permission-profile readonly")

    config = build_readonly_opencode_config(agent)
    issues = validate_readonly_permission_config(config, agent)
    if issues:
        raise BridgeError(f"readonly permission config is invalid: {'; '.join(issues)}")
    config_content = json.dumps(config, separators=(",", ":"))
    verification = verify_readonly_permission_enforcement(
        opencode_path,
        agent=agent,
        config_content=config_content,
        timeout_seconds=min(timeout_seconds, 10),
    )
    if not verification.get("ok"):
        raise BridgeError("UNSUPPORTED_PERMISSION_ENFORCEMENT: OpenCode readonly permissions could not be proven")
    return (
        {
            "profile": "readonly",
            "method": "OPENCODE_CONFIG_CONTENT",
            "config_sha256": hashlib.sha256(config_content.encode("utf-8")).hexdigest(),
            "verified": True,
            "verification": verification,
        },
        build_opencode_env(os.environ, config_content),
    )


def attach_mode_state(
    *,
    decision_limit: str,
    server_url: str | None,
    remote_permission_verified: bool = False,
) -> dict[str, Any]:
    requested = bool(server_url)
    state: dict[str, Any] = {
        "attach_mode_requested": requested,
        "attach_mode_allowed": False,
        "remote_permission_verified": bool(remote_permission_verified),
    }
    if not requested:
        return state

    if decision_limit == "evidence_only" and not remote_permission_verified:
        state["blocked"] = True
        state["reason"] = "evidence_only_attach_requires_remote_readonly_proof"
        return state

    state["attach_mode_allowed"] = True
    return state


def resolve_attach_mode(
    *,
    decision_limit: str,
    server_url: str | None,
    remote_permission_verified: bool = False,
) -> tuple[str | None, dict[str, Any]]:
    state = attach_mode_state(
        decision_limit=decision_limit,
        server_url=server_url,
        remote_permission_verified=remote_permission_verified,
    )
    if state.get("blocked"):
        raise BridgeError(
            "UNSUPPORTED_REMOTE_PERMISSION_ENFORCEMENT: evidence_only workers cannot use "
            "OPENCODE_SERVER_URL/--attach without proven remote readonly enforcement"
        )
    return (server_url if state["attach_mode_allowed"] else None, state)


def _parse_json_or_lines(text: str) -> list[str]:
    stripped = text[:MAX_PROBE_TEXT_BYTES].strip()
    if not stripped:
        return []
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        values = []
        for line in stripped.splitlines():
            candidate = line.strip().strip(",")
            if not candidate or candidate in {"[", "]", "{", "}"}:
                continue
            if candidate.startswith('"'):
                continue
            values.append(candidate[:MAX_PROBE_ITEM_CHARS])
            if len(values) >= MAX_PROBE_ITEMS:
                break
        return values
    if isinstance(loaded, list):
        values = []
        for item in loaded:
            if isinstance(item, str):
                values.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("id") or item.get("model")
                if name:
                    values.append(str(name))
        return values[:MAX_PROBE_ITEMS]
    if isinstance(loaded, dict):
        for key in ("agents", "models", "data", "items"):
            value = loaded.get(key)
            if isinstance(value, list):
                return _parse_json_or_lines(json.dumps(value))
    return [str(loaded)[:MAX_PROBE_ITEM_CHARS]]


def _probe_list(command: str, attempts: Iterable[Sequence[str]], timeout_seconds: int) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    for attempt in attempts:
        result = run_command([command, *attempt], timeout_seconds=timeout_seconds)
        probes.append(
            {
                "args": list(attempt),
                "exit_code": result.exit_code,
                "ok": result.ok,
                "stderr": _first_nonempty_line(result.stderr),
            }
        )
        if result.ok:
            return {"supported": True, "items": _parse_json_or_lines(result.stdout), "probes": probes}
    return {"supported": False, "items": [], "probes": probes}


def probe_opencode(command: str | None = None, timeout_seconds: int = 5) -> dict[str, Any]:
    resolved = resolve_opencode_command(command)
    probe: dict[str, Any] = {
        "available": bool(resolved),
        "command": resolved or command or "opencode",
        "version": None,
        "agents": [],
        "models": [],
        "deepseek_available": False,
        "checks": {},
    }
    if not resolved:
        probe["checks"]["version"] = {"ok": False, "exit_code": 127, "stderr": "opencode not found"}
        return probe

    version = run_command([resolved, "--version"], timeout_seconds=timeout_seconds)
    probe["version"] = _first_nonempty_line(version.stdout) or _first_nonempty_line(version.stderr)
    probe["checks"]["version"] = version.to_dict()

    agents = _probe_list(
        resolved,
        attempts=(("agent", "list", "--json"), ("agent", "list"), ("agents",)),
        timeout_seconds=timeout_seconds,
    )
    models = _probe_list(
        resolved,
        attempts=(("models", "--json"), ("models",), ("model", "list", "--json"), ("model", "list")),
        timeout_seconds=timeout_seconds,
    )
    probe["agents"] = agents["items"]
    probe["models"] = models["items"]
    probe["checks"]["agents"] = agents
    probe["checks"]["models"] = models
    joined = "\n".join([probe["version"] or "", *probe["agents"], *probe["models"]]).lower()
    probe["deepseek_available"] = "deepseek" in joined
    return probe


def is_denied_path(value: str | Path) -> bool:
    normalized = str(value).replace("\\", "/")
    lower = normalized.lower()
    parts = [part for part in lower.split("/") if part]
    basename = parts[-1] if parts else lower
    if basename == ".env" or basename.startswith(".env."):
        return True
    if any(part in {"secret", "secrets", "credential", "credentials", ".ssh"} for part in parts):
        return True
    if any(token in basename for token in ("api_key", "apikey", "private_key", "credential", "token")):
        return True
    if lower.endswith((".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db")):
        return True
    if "raw" in parts and any(part in {"db", "database", "dump", "dumps"} for part in parts):
        return True
    return False


def find_denied_references(text: str) -> list[str]:
    denied: list[str] = []
    for match in PATHISH_RE.finditer(text):
        token = match.group(0).strip("`'\"()[]{}<>.,;:")
        if token and is_denied_path(token):
            denied.append(token)
    return sorted(set(denied))


def read_safe_task_file(task_file: Path) -> str:
    if is_denied_path(task_file):
        raise BridgeError(f"task file path is denied: {task_file}")
    data = task_file.read_bytes()
    if len(data) > MAX_TASK_BYTES:
        raise BridgeError(f"task file exceeds {MAX_TASK_BYTES} bytes")
    text = data.decode("utf-8")
    denied_refs = find_denied_references(text)
    if denied_refs:
        joined = ", ".join(denied_refs[:5])
        raise BridgeError(f"task file references denied path(s): {joined}")
    return text


def validate_worker_id(worker_id: str) -> None:
    if not WORKER_ID_RE.fullmatch(worker_id):
        raise BridgeError("worker-id must contain only letters, numbers, dot, underscore, or dash")


def build_opencode_command(
    opencode_path: str,
    *,
    agent: str,
    model: str,
    workdir: Path,
    prompt: str,
    server_url: str | None = None,
) -> list[str]:
    args = [opencode_path, "run", "--pure"]
    if server_url:
        args.extend(["--attach", server_url])
    if agent:
        args.extend(["--agent", agent])
    if model:
        args.extend(["--model", model])
    args.extend(["--dir", str(workdir)])
    args.append(prompt)
    unexpected = sorted(DANGEROUS_FLAGS.intersection(args))
    if unexpected:
        raise BridgeError(f"dangerous OpenCode flag refused: {', '.join(unexpected)}")
    return args


def build_worker_prompt(
    *,
    worker_id: str,
    task_tier: str,
    model: str,
    decision_limit: str,
    task_text: str,
    workdir: Path,
) -> str:
    return textwrap.dedent(
        f"""
        You are a read-only Codex worker delegated through OpenCode.

        Policy:
        - Read, grep, glob, and summarize only.
        - Do not edit repo source, docs, templates, config, data, or host-global files.
        - Do not run git mutation commands: commit, push, merge, rebase, reset, stash, clean, delete, prune, checkout, or cherry-pick.
        - Do not touch product/runtime/data/extraction/count-24 surfaces.
        - Do not read secrets, credentials, API keys, .env files, private tokens, or raw DB dumps.
        - Do not make final decisions for critical work. Provide evidence for Codex to decide.
        - If evidence is missing, write DATA_MISSING.

        Workdir: {workdir}
        worker_id: {worker_id}
        task_tier: {task_tier}
        model: {model}
        decision_limit: {decision_limit}

        Return only a WORKER_RESULT.md body using exactly these fields:
        worker_id: {worker_id}
        task_tier: {task_tier}
        model: {model}
        decision_limit: {decision_limit}
        summary:
        findings:
        evidence_paths:
        confidence:
        risks:
        recommended_next_action:
        stop_condition_hit:

        Task:
        {task_text}
        """
    ).strip()


def write_worker_task(path: Path, *, worker_id: str, task_file: Path, task_text: str) -> None:
    path.write_text(
        textwrap.dedent(
            f"""
            # Worker Task

            worker_id: {worker_id}
            source_task_file: {task_file}

            ## Task

            {task_text}
            """
        ).lstrip(),
        encoding="utf-8",
    )


def failure_result(
    *,
    worker_id: str,
    task_tier: str,
    model: str,
    decision_limit: str,
    summary: str,
    evidence_paths: Sequence[str],
) -> str:
    evidence = "\n".join(f"- {path}" for path in evidence_paths) or "- DATA_MISSING"
    return textwrap.dedent(
        f"""
        worker_id: {worker_id}
        task_tier: {task_tier}
        model: {model}
        decision_limit: {decision_limit}
        summary: {summary}
        findings:
        - DATA_MISSING: OpenCode worker did not produce a usable result.
        evidence_paths:
        {evidence}
        confidence: low
        risks:
        - Worker output may be incomplete; Codex must inspect raw_output.txt and WORKER_META.json.
        recommended_next_action: revise
        stop_condition_hit: yes
        """
    ).lstrip()


def _strip_outer_markdown_fence(lines: list[str]) -> list[str]:
    nonblank = [idx for idx, line in enumerate(lines) if line.strip()]
    if len(nonblank) < 2:
        return lines
    first = nonblank[0]
    last = nonblank[-1]
    if MARKDOWN_FENCE_RE.match(lines[first].strip()) and MARKDOWN_FENCE_RE.match(lines[last].strip()):
        return lines[:first] + lines[first + 1 : last] + lines[last + 1 :]
    return lines


def parse_result_fields(text: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    in_markdown_fence = False
    for raw_line in _strip_outer_markdown_fence(text.splitlines()):
        line = raw_line.rstrip()
        stripped = line.strip()
        if MARKDOWN_FENCE_RE.match(stripped):
            in_markdown_fence = not in_markdown_fence
            if current:
                fields[current].append(stripped)
            continue
        if in_markdown_fence:
            if current and line.strip():
                fields[current].append(line.strip())
            continue
        match = FIELD_RE.match(stripped)
        if match:
            field = match.group(1)
            if field not in REQUIRED_RESULT_FIELDS:
                current = None
                continue
            current = field
            fields.setdefault(current, [])
            value = match.group(2).strip()
            if value:
                fields[current].append(value)
            continue
        if current and line.strip():
            fields[current].append(line.strip())
    return {key: "\n".join(value).strip() for key, value in fields.items()}


def _field_has_content(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().strip("[]").strip()
    return bool(normalized) and normalized.lower() not in {"none", "null", "n/a", "data_missing"}


def _stop_condition_hit_has_content(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    return bool(normalized) and normalized.lower() not in {"none", "null", "n/a"}


def _evidence_paths_are_present(value: str | None) -> bool:
    if not _field_has_content(value):
        return False
    lines = [line.strip().lstrip("-").strip() for line in (value or "").splitlines()]
    concrete = [line for line in lines if line and line.lower() not in {"none", "data_missing", "[]"}]
    if not concrete:
        return False
    return any("/" in line or "." in Path(line).name for line in concrete)


def _worker_id_unsafe_owner_re(worker_id: str | None) -> re.Pattern[str] | None:
    normalized = (worker_id or "").strip().lower()
    if not normalized or not WORKER_ID_RE.fullmatch(normalized):
        return None
    escaped = re.escape(normalized)
    return re.compile(rf"(?<![A-Za-z0-9_.-]){escaped}(?:'s)?(?![A-Za-z0-9_.-])")


def _final_authority_boundary_spans(line: str, *, worker_id: str | None = None) -> list[tuple[int, int]]:
    parent_authority_owner = r"(?:codex|parent(?: session)?|main[- ]agent|orchestrator)"
    authority_phrase = r"(?:final decisions?|final authorit(?:y|ies)|authoritative decisions?)"
    spans: list[tuple[int, int]] = []
    parent_owns_authority = re.search(
        rf"\b{parent_authority_owner}\b"
        rf"\s+(?:(?:must|should|still|explicitly)\s+)*"
        rf"(?:own|owns|owned|retain|retains|retained|hold|holds|held|make|makes|made|is responsible for)\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    parent_is_authority = re.search(
        rf"\b{parent_authority_owner}\b"
        rf"\s+(?:(?:still|explicitly)\s+)*"
        rf"(?:is|has|remain|remains)\b"
        rf"\s+(?:the\s+)?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    authority_remains_with_parent = re.search(
        rf"\b{authority_phrase}\b"
        rf"[^.\n;:]*?\b(?:remain|remains|rest|rests|belong|belongs|owned|held|retained|responsibility)\b"
        rf"[^.\n;:]*?\b{parent_authority_owner}\b[^.\n;:]*",
        line,
    )
    parent_not_worker_appositive = re.search(
        rf"\b{parent_authority_owner}\b"
        rf"\s*,\s*(?:not|never)\s+workers?\s*,\s*"
        rf"(?:is|has|remain|remains)\b"
        rf"\s+(?:the\s+)?\b{authority_phrase}\b(?P<trailing>[^.\n;:]*)",
        line,
    )
    parent_boundary_unsafe = re.compile(
        r"\b(?:workers?|opencode|models?'?s?|(?<!main-)(?<!main )agents?'?s?|"
        r"(?:evidence\s+)?scouts?'?s?|"
        r"i|me|my|mine|we|us|our|ours|no|not|never|cannot|can not|can't|"
        r"do not|does not|don't|doesn't|must not|should not|outside|without|away from)\b"
    )
    worker_id_unsafe = _worker_id_unsafe_owner_re(worker_id)
    trailing_worker_denial = re.compile(r"\s*,\s*(?:not|never)\s+workers?\s*$")

    def parent_boundary_is_safe(text: str) -> bool:
        safety_text = trailing_worker_denial.sub("", text)
        if parent_boundary_unsafe.search(safety_text):
            return False
        return not (worker_id_unsafe and worker_id_unsafe.search(safety_text))

    if parent_owns_authority and parent_boundary_is_safe(parent_owns_authority.group(0)):
        spans.append(parent_owns_authority.span())
    if parent_is_authority and parent_boundary_is_safe(parent_is_authority.group(0)):
        spans.append(parent_is_authority.span())
    if authority_remains_with_parent and parent_boundary_is_safe(authority_remains_with_parent.group(0)):
        spans.append(authority_remains_with_parent.span())
    if parent_not_worker_appositive and parent_boundary_is_safe(parent_not_worker_appositive.group("trailing")):
        spans.append(parent_not_worker_appositive.span())

    authority_action = r"(?:make|makes|made|own|owns|hold|holds|retain|retains|have|has|claim|claims|exercise|exercises)"
    parent_denies_worker_authority = re.search(
        rf"\b{parent_authority_owner}\b"
        rf"[^.\n;:]*\b(?:cannot|can not|can't|must not|should not|do not|does not|don't|doesn't|never)\b"
        rf"\s+allow(?:s|ed)?\b"
        rf"[^.\n;:]*?\bworkers?\b"
        rf"[^.\n;:]*?\b{authority_action}\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    worker_not_allowed_authority = re.search(
        rf"\bworkers?\b"
        rf"[^.\n;:]*?\b(?:are|is|be)\b"
        rf"\s+(?:not|never)\s+allowed\s+to\s+{authority_action}\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    worker_denies_authority = re.search(
        rf"\bworkers?\b"
        rf"[^.\n;:]*\b(?:cannot|can not|can't|must not|should not|do not|does not|don't|doesn't|never)\b"
        rf"\s+{authority_action}\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    worker_has_no_authority = re.search(
        rf"\bworkers?\b"
        rf"[^.\n;:]*\b{authority_action}\b"
        rf"[^.\n;:]*?\bno\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b[^.\n;:]*",
        line,
    )
    worker_denial_unsafe = re.compile(
        r"\b(?:(?:anything\s+)?less than|apart\s+from|other\s+than|except|unless|alongside|"
        r"but|however|opencode|models?'?s?|(?<!main-)(?<!main )agents?'?s?|"
        r"(?:evidence\s+)?scouts?'?s?|"
        r"i|me|my|mine|we|us|our|ours)\b"
    )

    def worker_denial_is_safe(text: str) -> bool:
        if worker_denial_unsafe.search(text):
            return False
        return not (worker_id_unsafe and worker_id_unsafe.search(text))

    authority_denied_to_workers = re.search(
        rf"\b(?:no|never)\b"
        rf"[^.\n;:]*?\b{authority_phrase}\b"
        rf"[^.\n;:]*?\b(?:by|from|for)\b"
        rf"[^.\n;:]*?\bworkers?\b[^.\n;:]*",
        line,
    )
    if parent_denies_worker_authority and worker_denial_is_safe(parent_denies_worker_authority.group(0)):
        spans.append(parent_denies_worker_authority.span())
    if worker_not_allowed_authority and worker_denial_is_safe(worker_not_allowed_authority.group(0)):
        spans.append(worker_not_allowed_authority.span())
    if worker_denies_authority and worker_denial_is_safe(worker_denies_authority.group(0)):
        spans.append(worker_denies_authority.span())
    if worker_has_no_authority and worker_denial_is_safe(worker_has_no_authority.group(0)):
        spans.append(worker_has_no_authority.span())
    if authority_denied_to_workers and worker_denial_is_safe(authority_denied_to_workers.group(0)):
        spans.append(authority_denied_to_workers.span())
    return spans


def _final_authority_boundary_statement(line: str) -> bool:
    return bool(_final_authority_boundary_spans(line))


def _terminal_claim_is_negated(line: str, claim_start: int) -> bool:
    prefix = line[:claim_start].rstrip()
    return bool(
        re.search(
            r"\b(?:not(?:\s+(?:yet|currently|be\s+considered|mark\s+this(?:\s+as)?))?|"
            r"no\s+longer|never|cannot|can not|can't|isn't|is\s+not|aren't|are\s+not)\s*$",
            prefix,
        )
    )


def _evidence_only_final_authority_claim(text: str, *, worker_id: str | None = None) -> str | None:
    terminal_claims = (
        "approved to merge",
        "approved-to-merge",
        "approved for merge",
        "approved-for-merge",
        "merge approved",
        "merge-approved",
        "ready for merge",
        "ready-for-merge",
        "ready to merge",
        "merge-ready",
        "merge now",
        "ship it",
        "no further review needed",
        "codex can skip review",
        "this is fixed",
        "this is complete",
    )
    authority_claims = (
        "final decision",
        "final authority",
        "authoritative decision",
    )
    for raw_line in text.splitlines():
        line = raw_line.strip().lower()
        for phrase in terminal_claims:
            if any(not _terminal_claim_is_negated(line, match.start()) for match in re.finditer(re.escape(phrase), line)):
                return phrase
        for phrase in authority_claims:
            if phrase not in line:
                continue
            for clause in re.split(r"[.;:]", line):
                stripped_clause = clause.strip()
                safe_spans = _final_authority_boundary_spans(stripped_clause, worker_id=worker_id)
                for match in re.finditer(re.escape(phrase), stripped_clause):
                    in_safe_span = any(
                        start <= match.start() and match.end() <= end for start, end in safe_spans
                    )
                    if not in_safe_span:
                        return phrase
    return None


def validate_result_text(
    text: str,
    *,
    max_bytes: int = MAX_RESULT_BYTES,
    expected_decision_limit: str | None = None,
    trusted_worker_id: str | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    encoded = text.encode("utf-8")
    if not text.strip():
        issues.append({"field": "result", "message": "result is empty"})
    if len(encoded) > max_bytes:
        issues.append({"field": "result", "message": f"result exceeds {max_bytes} bytes"})

    fields = parse_result_fields(text)
    for field in REQUIRED_RESULT_FIELDS:
        if field == "stop_condition_hit":
            has_content = _stop_condition_hit_has_content(fields.get(field))
        else:
            has_content = _field_has_content(fields.get(field))
        if not has_content:
            issues.append({"field": field, "message": "required field is missing or empty"})

    if not _evidence_paths_are_present(fields.get("evidence_paths")):
        issues.append({"field": "evidence_paths", "message": "must include at least one concrete evidence path"})

    stop_condition_hit = (fields.get("stop_condition_hit") or "").strip()
    if _stop_condition_hit_has_content(stop_condition_hit) and stop_condition_hit not in STOP_CONDITION_HIT_VALUES:
        allowed = ", ".join(sorted(STOP_CONDITION_HIT_VALUES))
        issues.append(
            {
                "field": "stop_condition_hit",
                "message": f"must be exactly one of: {allowed}",
            }
        )

    reported_decision_limit = (fields.get("decision_limit") or "").strip().lower()
    requested_decision_limit = (expected_decision_limit or "").strip().lower()
    trusted_worker_id = (trusted_worker_id or "").strip()
    if trusted_worker_id:
        reported_worker_id = (fields.get("worker_id") or "").strip()
        if reported_worker_id and reported_worker_id != trusted_worker_id:
            issues.append(
                {
                    "field": "worker_id",
                    "message": f"worker_id {reported_worker_id} does not match trusted worker_id {trusted_worker_id}",
                }
            )
    if requested_decision_limit:
        if requested_decision_limit not in DECISION_LIMITS:
            issues.append(
                {
                    "field": "decision_limit",
                    "message": f"requested decision_limit is invalid: {requested_decision_limit}",
                }
            )
        elif reported_decision_limit != requested_decision_limit:
            issues.append(
                {
                    "field": "decision_limit",
                    "message": (
                        "worker decision_limit "
                        f"{reported_decision_limit or 'DATA_MISSING'} does not match requested "
                        f"{requested_decision_limit}"
                    ),
                }
            )

    effective_decision_limit = requested_decision_limit or reported_decision_limit
    if effective_decision_limit == "evidence_only":
        authority_claim = _evidence_only_final_authority_claim(
            text,
            worker_id=trusted_worker_id or fields.get("worker_id"),
        )
        if authority_claim:
            issues.append(
                {
                    "field": "decision_limit",
                    "message": f"evidence_only result claims final authority: {authority_claim}",
                }
            )

    return {"ok": not issues, "fields": fields, "issues": issues}


def validate_result_file(path: Path, *, expected_decision_limit: str | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "fields": {}, "issues": [{"field": "result_path", "message": "file does not exist"}]}
    meta_path = path.with_name("WORKER_META.json")
    meta: dict[str, Any] | None = None
    meta_read_error: str | None = None
    if meta_path.exists():
        try:
            loaded_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta_read_error = "WORKER_META.json must be valid JSON"
        else:
            if isinstance(loaded_meta, dict):
                meta = loaded_meta
            else:
                meta_read_error = "WORKER_META.json must be a JSON object"

    requested_decision_limit = expected_decision_limit
    trusted_worker_id = None
    if requested_decision_limit is None and meta is not None:
        meta_decision_limit = meta.get("decision_limit")
        if isinstance(meta_decision_limit, str) and meta_decision_limit.strip():
            requested_decision_limit = meta_decision_limit
    if meta is not None:
        meta_worker_id = meta.get("worker_id")
        if isinstance(meta_worker_id, str) and meta_worker_id.strip():
            trusted_worker_id = meta_worker_id.strip()

    result = validate_result_text(
        path.read_text(encoding="utf-8"),
        expected_decision_limit=requested_decision_limit,
        trusted_worker_id=trusted_worker_id,
    )
    fields = result.get("fields", {})
    effective_decision_limit = (
        (requested_decision_limit or fields.get("decision_limit") or "")
        .strip()
        .lower()
    )
    if effective_decision_limit == "evidence_only":
        if not meta_path.exists():
            result["ok"] = False
            result["issues"].append(
                {"field": "permission_enforcement", "message": "WORKER_META.json is required for evidence_only"}
            )
        elif meta_read_error:
            result["ok"] = False
            result["issues"].append(
                {"field": "permission_enforcement", "message": meta_read_error}
            )
        else:
            enforcement = meta.get("permission_enforcement") if meta else None
            if not isinstance(enforcement, dict) or enforcement.get("profile") != "readonly":
                result["ok"] = False
                result["issues"].append(
                    {
                        "field": "permission_enforcement",
                        "message": "evidence_only requires readonly permission metadata",
                    }
                )
            elif enforcement.get("verified") is not True:
                result["ok"] = False
                result["issues"].append(
                    {
                        "field": "permission_enforcement",
                        "message": "evidence_only readonly permission enforcement must be verified",
                    }
                )
            elif enforcement.get("method") != "OPENCODE_CONFIG_CONTENT":
                result["ok"] = False
                result["issues"].append(
                    {
                        "field": "permission_enforcement",
                        "message": "evidence_only requires OPENCODE_CONFIG_CONTENT enforcement",
                    }
                )
    return result


def write_json(path: Path, data: Any) -> None:
    path.write_text(json_dump(data), encoding="utf-8")


def command_run(args: argparse.Namespace) -> int:
    validate_worker_id(args.worker_id)
    if args.task_tier not in TASK_TIERS:
        raise BridgeError(f"task-tier must be one of: {', '.join(sorted(TASK_TIERS))}")
    if args.decision_limit not in DECISION_LIMITS:
        raise BridgeError(f"decision-limit must be one of: {', '.join(sorted(DECISION_LIMITS))}")

    job_dir = Path(args.job_dir)
    worker_dir = job_dir / args.worker_id
    task_file = Path(args.task_file)
    workdir = Path(args.workdir)
    if not task_file.is_file():
        raise BridgeError(f"task file not found: {task_file}")
    if not workdir.is_dir():
        raise BridgeError(f"workdir not found: {workdir}")

    task_text = read_safe_task_file(task_file)
    worker_dir.mkdir(parents=True, exist_ok=True)
    task_path = worker_dir / "WORKER_TASK.md"
    result_path = worker_dir / "WORKER_RESULT.md"
    meta_path = worker_dir / "WORKER_META.json"
    raw_path = worker_dir / "raw_output.txt"

    write_worker_task(task_path, worker_id=args.worker_id, task_file=task_file, task_text=task_text)

    started_at = utc_now()
    meta: dict[str, Any] = {
        "schema_version": 1,
        "worker_id": args.worker_id,
        "runtime": "opencode",
        "agent": args.agent,
        "model": args.model,
        "task_tier": args.task_tier,
        "decision_limit": args.decision_limit,
        "task_file": str(task_file),
        "workdir": str(workdir),
        "worker_dir": str(worker_dir),
        "task_path": str(task_path),
        "result_path": str(result_path),
        "raw_output_path": str(raw_path),
        "status": "starting",
        "started_at": started_at,
        "session_id": os.environ.get("OPENCODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or "DATA_MISSING",
    }
    server_url = os.environ.get("OPENCODE_SERVER_URL")
    attach_state = attach_mode_state(decision_limit=args.decision_limit, server_url=server_url)
    meta.update(attach_state)
    if attach_state.get("blocked"):
        message = (
            "UNSUPPORTED_REMOTE_PERMISSION_ENFORCEMENT: evidence_only workers cannot use "
            "OPENCODE_SERVER_URL/--attach without proven remote readonly enforcement"
        )
        raw_path.write_text(f"{message}\n", encoding="utf-8")
        meta.update(
            {
                "status": "failed",
                "failure": "remote_permission_enforcement_failed",
                "ended_at": utc_now(),
            }
        )
        write_json(meta_path, meta)
        result_path.write_text(
            failure_result(
                worker_id=args.worker_id,
                task_tier=args.task_tier,
                model=args.model,
                decision_limit=args.decision_limit,
                summary="OpenCode remote readonly permission enforcement could not be proven.",
                evidence_paths=[str(meta_path), str(raw_path)],
            ),
            encoding="utf-8",
        )
        print(json_dump(meta), end="")
        return 2

    opencode_path = resolve_opencode_command(args.opencode_command)
    if not opencode_path:
        raw_path.write_text("OpenCode command not found.\n", encoding="utf-8")
        result_path.write_text(
            failure_result(
                worker_id=args.worker_id,
                task_tier=args.task_tier,
                model=args.model,
                decision_limit=args.decision_limit,
                summary="OpenCode command not found.",
                evidence_paths=[str(task_path), str(raw_path)],
            ),
            encoding="utf-8",
        )
        meta.update({"status": "failed", "failure": "opencode_not_found", "ended_at": utc_now()})
        meta["result_validation"] = validate_result_file(result_path, expected_decision_limit=args.decision_limit)
        write_json(meta_path, meta)
        print(json_dump(meta), end="")
        return 127

    try:
        permission_enforcement, opencode_env = build_permission_enforcement(
            decision_limit=args.decision_limit,
            permission_profile=args.permission_profile,
            agent=args.agent,
            opencode_path=opencode_path,
            timeout_seconds=args.timeout_seconds,
        )
    except BridgeError as exc:
        raw_path.write_text(f"{exc}\n", encoding="utf-8")
        meta.update(
            {
                "status": "failed",
                "failure": "permission_enforcement_failed",
                "permission_enforcement": {
                    "profile": args.permission_profile,
                    "method": "DATA_MISSING",
                    "verified": False,
                    "reason": str(exc),
                },
                "ended_at": utc_now(),
            }
        )
        write_json(meta_path, meta)
        result_path.write_text(
            failure_result(
                worker_id=args.worker_id,
                task_tier=args.task_tier,
                model=args.model,
                decision_limit=args.decision_limit,
                summary="OpenCode readonly permission enforcement could not be proven.",
                evidence_paths=[str(meta_path), str(raw_path)],
            ),
            encoding="utf-8",
        )
        print(json_dump(meta), end="")
        return 2
    meta["permission_enforcement"] = permission_enforcement

    prompt = build_worker_prompt(
        worker_id=args.worker_id,
        task_tier=args.task_tier,
        model=args.model,
        decision_limit=args.decision_limit,
        task_text=task_text,
        workdir=workdir,
    )
    command = build_opencode_command(
        opencode_path,
        agent=args.agent,
        model=args.model,
        workdir=workdir,
        prompt=prompt,
        server_url=server_url if meta["attach_mode_allowed"] else None,
    )
    meta["command"] = command[:-1] + ["<prompt>"]
    meta["status"] = "running"
    write_json(meta_path, meta)

    result = run_command(command, timeout_seconds=args.timeout_seconds, env=opencode_env)
    raw_path.write_text(
        textwrap.dedent(
            f"""
            command: {json.dumps(meta["command"])}
            exit_code: {result.exit_code}
            timed_out: {str(result.timed_out).lower()}

            ## stdout
            {result.stdout}

            ## stderr
            {result.stderr}
            """
        ).lstrip(),
        encoding="utf-8",
    )

    if result.ok and result.stdout.strip():
        result_path.write_text(result.stdout.strip() + "\n", encoding="utf-8")
    else:
        result_path.write_text(
            failure_result(
                worker_id=args.worker_id,
                task_tier=args.task_tier,
                model=args.model,
                decision_limit=args.decision_limit,
                summary="OpenCode worker failed before producing a result.",
                evidence_paths=[str(task_path), str(raw_path)],
            ),
            encoding="utf-8",
        )

    validation = validate_result_file(result_path, expected_decision_limit=args.decision_limit)
    status = "completed" if result.ok and validation["ok"] else "result_invalid"
    if not result.ok:
        status = "failed"
    meta.update(
        {
            "status": status,
            "ended_at": utc_now(),
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "result_validation": validation,
        }
    )
    if not result.ok:
        meta["failure"] = "opencode_failed"
    write_json(meta_path, meta)
    print(json_dump(meta), end="")
    return 0 if status == "completed" else 1


def command_probe(args: argparse.Namespace) -> int:
    print(json_dump(probe_opencode(command=args.opencode_command, timeout_seconds=args.timeout_seconds)), end="")
    return 0


def command_validate_result(args: argparse.Namespace) -> int:
    result = validate_result_file(Path(args.result_file), expected_decision_limit=args.decision_limit)
    print(json_dump(result), end="")
    return 0 if result["ok"] else 1


def _compact_value(value: str, limit: int = 220) -> str:
    flattened = " ".join(line.strip().lstrip("-").strip() for line in value.splitlines() if line.strip())
    if len(flattened) <= limit:
        return flattened
    return flattened[: limit - 3].rstrip() + "..."


def command_summarize(args: argparse.Namespace) -> int:
    job_dir = Path(args.job_dir)
    result_paths = sorted(job_dir.rglob("WORKER_RESULT.md"))
    lines = ["# Worker Result Summary", ""]
    if not result_paths:
        lines.append("DATA_MISSING: no WORKER_RESULT.md files found.")
    for result_path in result_paths:
        validation = validate_result_file(result_path)
        fields = validation.get("fields", {})
        worker_id = fields.get("worker_id") or result_path.parent.name
        lines.append(f"## {worker_id}")
        lines.append(f"- result_path: {result_path}")
        lines.append(f"- status: {'valid' if validation['ok'] else 'invalid'}")
        lines.append(f"- task_tier: {fields.get('task_tier', 'DATA_MISSING')}")
        lines.append(f"- model: {fields.get('model', 'DATA_MISSING')}")
        lines.append(f"- decision_limit: {fields.get('decision_limit', 'DATA_MISSING')}")
        lines.append(f"- summary: {_compact_value(fields.get('summary', 'DATA_MISSING'))}")
        lines.append(f"- evidence_paths: {_compact_value(fields.get('evidence_paths', 'DATA_MISSING'))}")
        if not validation["ok"]:
            issue_text = "; ".join(f"{i['field']}: {i['message']}" for i in validation["issues"])
            lines.append(f"- validation_issues: {issue_text}")
        lines.append("")
    print("\n".join(lines).rstrip() + "\n")
    return 0


def command_ledger_entry(args: argparse.Namespace) -> int:
    meta: dict[str, Any] = {}
    worker_dir: Path | None = None
    if args.job_dir and args.worker_id:
        worker_dir = Path(args.job_dir) / args.worker_id
        meta_path = worker_dir / "WORKER_META.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

    result_path = args.result_path or meta.get("result_path")
    if not result_path and worker_dir:
        result_path = str(worker_dir / "WORKER_RESULT.md")

    entry = {
        "schema_version": 1,
        "worker_id": args.worker_id or meta.get("worker_id") or "DATA_MISSING",
        "runtime": "opencode",
        "model": args.model or meta.get("model") or "DATA_MISSING",
        "agent": args.agent or meta.get("agent") or "DATA_MISSING",
        "task_tier": args.task_tier or meta.get("task_tier") or "DATA_MISSING",
        "decision_limit": args.decision_limit or meta.get("decision_limit") or "DATA_MISSING",
        "worktree": args.worktree or meta.get("workdir") or "DATA_MISSING",
        "session_id": os.environ.get("OPENCODE_SESSION_ID")
        or os.environ.get("CODEX_THREAD_ID")
        or meta.get("session_id")
        or "DATA_MISSING",
        "result_path": result_path or "DATA_MISSING",
        "status": args.status or meta.get("status") or "DATA_MISSING",
        "agent_task_ledger_available": Path("scripts/agent_task_ledger.py").exists(),
    }
    print(json_dump(entry), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe")
    probe.add_argument("--opencode-command")
    probe.add_argument("--timeout-seconds", type=int, default=5)
    probe.set_defaults(func=command_probe)

    run = subparsers.add_parser("run")
    run.add_argument("--job-dir", required=True)
    run.add_argument("--worker-id", required=True)
    run.add_argument("--agent", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--task-file", required=True)
    run.add_argument("--workdir", required=True)
    run.add_argument("--decision-limit", default="evidence_only")
    run.add_argument("--permission-profile", default="readonly")
    run.add_argument("--task-tier", default="small")
    run.add_argument("--timeout-seconds", type=int, default=600)
    run.add_argument("--opencode-command")
    run.set_defaults(func=command_run)

    validate = subparsers.add_parser("validate-result")
    validate.add_argument("result_file")
    validate.add_argument("--decision-limit")
    validate.set_defaults(func=command_validate_result)

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--job-dir", required=True)
    summarize.set_defaults(func=command_summarize)

    ledger = subparsers.add_parser("ledger-entry")
    ledger.add_argument("--job-dir")
    ledger.add_argument("--worker-id")
    ledger.add_argument("--agent")
    ledger.add_argument("--model")
    ledger.add_argument("--task-tier")
    ledger.add_argument("--decision-limit")
    ledger.add_argument("--worktree")
    ledger.add_argument("--result-path")
    ledger.add_argument("--status")
    ledger.set_defaults(func=command_ledger_entry)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BridgeError as exc:
        print(json_dump({"ok": False, "error": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
