from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable

from scripts import agent_job_contract, agent_job_registry

SERVER_NAME = "tenn-agent-mcp"
SERVER_VERSION = "0.1.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2024-11-05")
SERVER_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_REPORT_BYTES = 128 * 1024
MAX_TASK_BODY_BYTES = 64 * 1024
MAX_LAUNCH_TIMEOUT_SECONDS = 3600
VALID_LAUNCH_TASK_RE = re.compile(r"^docs/agent_tasks/[A-Za-z0-9_.-]+\.md$")


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def default_command_runner(argv: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8").strip()
        name, sep, value = decoded.partition(":")
        if not sep:
            raise ValueError(f"invalid header line: {decoded}")
        headers[name.lower()] = value.strip()
    length_text = headers.get("content-length")
    if length_text is None:
        raise ValueError("missing Content-Length header")
    body = stream.read(int(length_text))
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    stream.write(body)
    stream.flush()


class TennAgentMCPServer:
    def __init__(
        self,
        repo_root: Path,
        *,
        command_runner: Callable[[list[str], Path, int], CommandResult] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.command_runner = command_runner or default_command_runner
        self.env = env if env is not None else os.environ
        self._initialized = False
        self._tools = {
            "list_capabilities": self._tool_list_capabilities,
            "create_task_card": self._tool_create_task_card,
            "list_active_jobs": self._tool_list_active_jobs,
            "launch_codex_audit": self._tool_launch_codex_audit,
            "get_agent_status": self._tool_get_agent_status,
            "read_agent_report": self._tool_read_agent_report,
        }

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return self._error_response(request_id, -32600, "Invalid request: missing method")
        try:
            if method == "initialize":
                params = message.get("params", {})
                if not isinstance(params, dict):
                    return self._error_response(request_id, -32602, "Invalid params for initialize")
                requested = params.get("protocolVersion")
                if not isinstance(requested, str) or requested not in SUPPORTED_PROTOCOL_VERSIONS:
                    return self._error_response(request_id, -32602, "Unsupported protocolVersion")
                self._initialized = True
                return self._result_response(request_id, self._initialize_result(requested))
            if method == "ping":
                return self._result_response(request_id, {})
            if method.startswith("notifications/"):
                if method == "notifications/initialized":
                    self._initialized = True
                return None
            if method == "tools/list":
                if not self._initialized:
                    return self._error_response(request_id, -32002, "Server not initialized. Call initialize first.")
                return self._result_response(request_id, {"tools": self.list_tools()})
            if method == "tools/call":
                if not self._initialized:
                    return self._error_response(request_id, -32002, "Server not initialized. Call initialize first.")
                params = message.get("params", {})
                if not isinstance(params, dict):
                    return self._error_response(request_id, -32602, "Invalid params for tools/call")
                name = params.get("name")
                arguments = params.get("arguments", {})
                if not isinstance(name, str):
                    return self._error_response(request_id, -32602, "Tool name must be a string")
                if not isinstance(arguments, dict):
                    return self._error_response(request_id, -32602, "Tool arguments must be an object")
                return self._result_response(request_id, self.call_tool(name, arguments))
            return self._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # pragma: no cover - defensive JSON-RPC guard
            return self._error_response(request_id, -32603, f"Internal error: {exc}")

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "list_capabilities",
                "description": "List the Tenn Agent MCP safe local tool surface and security posture.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            },
            {
                "name": "create_task_card",
                "description": "Create a validated non-production Tenn agent task card under docs/agent_tasks.",
                "inputSchema": {
                    "type": "object",
                    "required": ["token", "job_id", "lane", "allowed_files", "body"],
                    "properties": {
                        "token": {"type": "string"},
                        "job_id": {"type": "string"},
                        "lane": {"type": "string"},
                        "allowed_files": {"type": "array", "items": {"type": "string"}},
                        "body": {"type": "string"},
                        "mutation_mode": {"type": "string", "default": "audit_only"},
                        "approval_required": {"type": "boolean", "default": False},
                        "overwrite": {"type": "boolean", "default": False},
                    },
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": False, "destructiveHint": False},
            },
            {
                "name": "list_active_jobs",
                "description": "Read active Tenn dev-agent registry jobs.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            },
            {
                "name": "launch_codex_audit",
                "description": "Dry-run by default: validate an audit-only task card and return a fixed Codex launch plan.",
                "inputSchema": {
                    "type": "object",
                    "required": ["token", "task_card"],
                    "properties": {
                        "token": {"type": "string"},
                        "task_card": {"type": "string"},
                        "dry_run": {"type": "boolean", "default": True},
                        "timeout_seconds": {"type": "integer", "default": 300},
                    },
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": False, "destructiveHint": False},
            },
            {
                "name": "get_agent_status",
                "description": "Read one agent job status.json and matching active registry record if present.",
                "inputSchema": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {"job_id": {"type": "string"}},
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            },
            {
                "name": "read_agent_report",
                "description": "Read a bounded README.md from reports/agent_jobs/<job_id>.",
                "inputSchema": {
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {"job_id": {"type": "string"}},
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = self._tools.get(name)
        if handler is None:
            return self._tool_result({"ok": False, "error": f"Unknown tool: {name}"})
        return handler(arguments)

    def _tool_list_capabilities(self, _: dict[str, Any]) -> dict[str, Any]:
        structured = {
            "ok": True,
            "server": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "transport": {"stdio": True, "http": False},
            "local_defaults": {
                "bind_host": self.env.get("TENN_AGENT_MCP_HOST", DEFAULT_BIND_HOST),
                "port": _parse_port(self.env.get("TENN_AGENT_MCP_PORT")),
            },
            "tools": sorted(self._tools),
            "hard_refusals": [
                "production_data_access",
                "arbitrary_shell",
                "unrestricted_filesystem",
                "runtime_db_mutation",
                "qdrant_news_memory_financial_truth_access",
                "auto_merge",
                "recursive_self_launch",
            ],
            "launch": {
                "dry_run_default": True,
                "real_launch_env": "TENN_AGENT_MCP_ENABLE_LAUNCH=1",
                "non_read_token_env": "TENN_AGENT_MCP_TOKEN",
            },
        }
        return self._tool_result(structured)

    def _tool_create_task_card(self, arguments: dict[str, Any]) -> dict[str, Any]:
        token_error = self._require_token(arguments)
        if token_error:
            return self._tool_result(token_error)

        job_id = _require_job_id(arguments.get("job_id"))
        if job_id is None:
            return self._tool_result({"ok": False, "error": "job_id is invalid"})
        lane = arguments.get("lane")
        if lane not in agent_job_contract.VALID_LANES:
            return self._tool_result({"ok": False, "error": "lane is invalid"})
        mutation_mode = arguments.get("mutation_mode", "audit_only")
        if mutation_mode not in agent_job_contract.VALID_MUTATION_MODES:
            return self._tool_result({"ok": False, "error": "mutation_mode is invalid"})
        allowed_files = arguments.get("allowed_files")
        if not isinstance(allowed_files, list) or not all(isinstance(item, str) for item in allowed_files):
            return self._tool_result({"ok": False, "error": "allowed_files must be a string array"})
        body = arguments.get("body")
        if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_TASK_BODY_BYTES:
            return self._tool_result({"ok": False, "error": "body is required and must stay within size limit"})

        approval_required = bool(arguments.get("approval_required", False))
        card_path = self.repo_root / "docs" / "agent_tasks" / f"{job_id}.md"
        if card_path.exists() and not bool(arguments.get("overwrite", False)):
            return self._tool_result({"ok": False, "error": f"task card already exists: {card_path.relative_to(self.repo_root)}"})

        try:
            normalized_allowed = [_normalize_allowed_path(path) for path in allowed_files]
        except ValueError as exc:
            return self._tool_result({"ok": False, "error": str(exc)})

        metadata_lines = [
            "---",
            f"job_id: {job_id}",
            f"lane: {lane}",
            "owner: Codex",
            "allowed_files:",
            *[f"  - {path}" for path in normalized_allowed],
            f"approval_required: {'true' if approval_required else 'false'}",
        ]
        if not approval_required and mutation_mode == "safe_extension":
            metadata_lines.append("allow_unapproved_safe_extension: true")
        metadata_lines.extend(
            [
                "timeout_seconds: 1800",
                f"output_dir: reports/agent_jobs/{job_id}",
                f"mutation_mode: {mutation_mode}",
                "production_data_access: false",
                "---",
                "",
                body.rstrip(),
                "",
            ]
        )
        markdown = "\n".join(metadata_lines)
        validation = agent_job_contract.validate_task_card_markdown(markdown).to_dict()
        if not validation["ok"]:
            return self._tool_result({"ok": False, "error": "generated task card failed validation", "validation": validation})
        card_path.parent.mkdir(parents=True, exist_ok=True)
        card_path.write_text(markdown, encoding="utf-8")
        return self._tool_result({"ok": True, "path": card_path.relative_to(self.repo_root).as_posix(), "validation": validation})

    def _tool_list_active_jobs(self, _: dict[str, Any]) -> dict[str, Any]:
        return self._tool_result(agent_job_registry.list_active_jobs(repo_root=self.repo_root))

    def _tool_launch_codex_audit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        token_error = self._require_token(arguments)
        if token_error:
            return self._tool_result(token_error)
        task_card_text = arguments.get("task_card")
        if not isinstance(task_card_text, str) or not VALID_LAUNCH_TASK_RE.fullmatch(task_card_text):
            return self._tool_result({"ok": False, "error": "task_card must be docs/agent_tasks/<job_id>.md"})
        task_card = self.repo_root / task_card_text
        if not task_card.exists():
            return self._tool_result({"ok": False, "error": f"task card not found: {task_card_text}"})
        validation = agent_job_contract.validate_task_card_markdown(task_card.read_text(encoding="utf-8")).to_dict()
        if not validation["ok"]:
            return self._tool_result({"ok": False, "error": "task card failed validation", "validation": validation})
        metadata = validation["metadata"]
        if metadata.get("mutation_mode") != "audit_only":
            return self._tool_result({"ok": False, "error": "launch_codex_audit only launches audit_only task cards"})
        overlap = agent_job_registry.check_overlap_for_task_card(task_card, repo_root=self.repo_root)
        if not overlap.get("ok"):
            return self._tool_result({"ok": False, "error": "registry overlap check failed", "overlap": overlap})

        timeout_seconds = _bounded_timeout(arguments.get("timeout_seconds", 300))
        argv = [
            "codex",
            "exec",
            "--cd",
            str(self.repo_root),
            f"Execute audit-only Tenn task card: {task_card_text}",
        ]
        dry_run = arguments.get("dry_run", True) is not False
        if dry_run:
            return self._tool_result({"ok": True, "dry_run": True, "argv": argv, "overlap": overlap, "validation": validation})
        if self.env.get("TENN_AGENT_MCP_ENABLE_LAUNCH") != "1":
            return self._tool_result({"ok": False, "error": "real launch requires TENN_AGENT_MCP_ENABLE_LAUNCH=1", "argv": argv})
        result = self.command_runner(argv, self.repo_root, timeout_seconds)
        return self._tool_result(
            {
                "ok": result.exit_code == 0,
                "dry_run": False,
                "exit_code": result.exit_code,
                "stdout": result.stdout[-8192:],
                "stderr": result.stderr[-8192:],
            }
        )

    def _tool_get_agent_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        job_id = _require_job_id(arguments.get("job_id"))
        if job_id is None:
            return self._tool_result({"ok": False, "error": "job_id is invalid"})
        status_path = self.repo_root / "reports" / "agent_jobs" / job_id / "status.json"
        status = None
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
        active_payload = agent_job_registry.list_active_jobs(repo_root=self.repo_root)
        active = [
            job for job in active_payload.get("active_jobs", [])
            if isinstance(job, dict) and job.get("job_id") == job_id
        ]
        return self._tool_result(
            {
                "ok": True,
                "job_id": job_id,
                "status_path": status_path.relative_to(self.repo_root).as_posix(),
                "status": status,
                "active_jobs": active,
            }
        )

    def _tool_read_agent_report(self, arguments: dict[str, Any]) -> dict[str, Any]:
        job_id = _require_job_id(arguments.get("job_id"))
        if job_id is None:
            return self._tool_result({"ok": False, "error": "job_id is invalid"})
        report_path = self.repo_root / "reports" / "agent_jobs" / job_id / "README.md"
        if not report_path.exists():
            return self._tool_result({"ok": False, "error": "report not found", "path": report_path.relative_to(self.repo_root).as_posix()})
        raw = report_path.read_bytes()
        truncated = len(raw) > MAX_REPORT_BYTES
        text = raw[:MAX_REPORT_BYTES].decode("utf-8", errors="replace")
        return self._tool_result(
            {
                "ok": True,
                "job_id": job_id,
                "path": report_path.relative_to(self.repo_root).as_posix(),
                "text": text,
                "truncated": truncated,
            }
        )

    def _require_token(self, arguments: dict[str, Any]) -> dict[str, Any] | None:
        expected = self.env.get("TENN_AGENT_MCP_TOKEN", "")
        if not expected:
            return {"ok": False, "error": "TENN_AGENT_MCP_TOKEN is required for non-read tools"}
        supplied = arguments.get("token")
        if supplied != expected:
            return {"ok": False, "error": "invalid TENN_AGENT_MCP_TOKEN"}
        return None

    def _initialize_result(self, protocol_version: str) -> dict[str, Any]:
        return {
            "protocolVersion": protocol_version,
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "capabilities": {"tools": {"listChanged": False}},
        }

    def _tool_result(self, structured: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": json.dumps(structured, indent=2, sort_keys=True)}],
            "structuredContent": structured,
            "isError": structured.get("ok") is False,
        }

    def _result_response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _parse_port(value: str | None) -> int:
    if value is None or not value.strip():
        return DEFAULT_PORT
    try:
        parsed = int(value)
    except ValueError:
        return DEFAULT_PORT
    if parsed <= 0 or parsed > 65535:
        return DEFAULT_PORT
    return parsed


def _require_job_id(value: Any) -> str | None:
    if not isinstance(value, str) or not agent_job_contract.JOB_ID_RE.fullmatch(value):
        return None
    return value


def _normalize_allowed_path(path_text: str) -> str:
    path = PurePosixPath(path_text.strip().replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"allowed path must be repo-relative: {path_text}")
    return path.as_posix()


def _bounded_timeout(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 300
    return max(1, min(value, MAX_LAUNCH_TIMEOUT_SECONDS))


def run_stdio(server: TennAgentMCPServer, *, input_stream: BinaryIO, output_stream: BinaryIO) -> int:
    while True:
        message = read_message(input_stream)
        if message is None:
            return 0
        response = server.handle_message(message)
        if response is not None:
            write_message(output_stream, response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local-first Tenn Agent MCP stdio server.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    server = TennAgentMCPServer(args.repo_root)
    return run_stdio(server, input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)
