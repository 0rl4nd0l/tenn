#!/usr/bin/env python3
"""Read-only OpenCode worker bridge for Codex delegation."""

from __future__ import annotations

import argparse
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
)

DECISION_LIMITS = {"evidence_only", "recommendation_only", "bounded_implementation", "strategy_bid"}
TASK_TIERS = {"small", "medium", "large", "critical"}
MAX_TASK_BYTES = 12000
MAX_RESULT_BYTES = 32000
MAX_PROBE_ITEMS = 200
MAX_PROBE_TEXT_BYTES = 16000
MAX_PROBE_ITEM_CHARS = 180
WORKER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*)\s*:\s*(.*)$")
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


def run_command(args: Sequence[str], timeout_seconds: int) -> CommandResult:
    try:
        completed = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
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
    args = [opencode_path, "run"]
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
        """
    ).lstrip()


def parse_result_fields(text: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = FIELD_RE.match(line.strip())
        if match and match.group(1) in REQUIRED_RESULT_FIELDS:
            current = match.group(1)
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


def _evidence_paths_are_present(value: str | None) -> bool:
    if not _field_has_content(value):
        return False
    lines = [line.strip().lstrip("-").strip() for line in (value or "").splitlines()]
    concrete = [line for line in lines if line and line.lower() not in {"none", "data_missing", "[]"}]
    if not concrete:
        return False
    return any("/" in line or "." in Path(line).name for line in concrete)


def validate_result_text(text: str, *, max_bytes: int = MAX_RESULT_BYTES) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    encoded = text.encode("utf-8")
    if not text.strip():
        issues.append({"field": "result", "message": "result is empty"})
    if len(encoded) > max_bytes:
        issues.append({"field": "result", "message": f"result exceeds {max_bytes} bytes"})

    fields = parse_result_fields(text)
    for field in REQUIRED_RESULT_FIELDS:
        if not _field_has_content(fields.get(field)):
            issues.append({"field": field, "message": "required field is missing or empty"})

    if not _evidence_paths_are_present(fields.get("evidence_paths")):
        issues.append({"field": "evidence_paths", "message": "must include at least one concrete evidence path"})

    decision_limit = (fields.get("decision_limit") or "").strip().lower()
    if decision_limit == "evidence_only":
        lower = text.lower()
        authority_phrases = (
            "final decision",
            "final authority",
            "authoritative decision",
            "approved to merge",
            "ready to merge",
            "merge now",
            "ship it",
            "no further review needed",
            "codex can skip review",
            "this is fixed",
            "this is complete",
        )
        for phrase in authority_phrases:
            if phrase in lower:
                issues.append(
                    {
                        "field": "decision_limit",
                        "message": f"evidence_only result claims final authority: {phrase}",
                    }
                )
                break

    return {"ok": not issues, "fields": fields, "issues": issues}


def validate_result_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "fields": {}, "issues": [{"field": "result_path", "message": "file does not exist"}]}
    return validate_result_text(path.read_text(encoding="utf-8"))


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
        meta["result_validation"] = validate_result_file(result_path)
        write_json(meta_path, meta)
        print(json_dump(meta), end="")
        return 127

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
        server_url=os.environ.get("OPENCODE_SERVER_URL"),
    )
    meta["command"] = command[:-1] + ["<prompt>"]
    meta["status"] = "running"
    write_json(meta_path, meta)

    result = run_command(command, timeout_seconds=args.timeout_seconds)
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

    validation = validate_result_file(result_path)
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
    result = validate_result_file(Path(args.result_file))
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
    run.add_argument("--task-tier", default="small")
    run.add_argument("--timeout-seconds", type=int, default=600)
    run.add_argument("--opencode-command")
    run.set_defaults(func=command_run)

    validate = subparsers.add_parser("validate-result")
    validate.add_argument("result_file")
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
