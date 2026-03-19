from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, BinaryIO, Callable

from openclaw.codex_memory import CodexMemoryStore

SERVER_NAME = "tenn-mcp"
SERVER_VERSION = "0.1.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2024-11-05")
SERVER_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
RUN_ID_LENGTH = 16
MAX_SEARCH_RESULTS = 50
MAX_CODEX_MEMORY_RESULTS = 50
MAX_FETCH_LINES = 400
MAX_TEXT_FILE_BYTES = 512 * 1024
SEARCH_TIMEOUT_SECONDS = 20
BLOCKED_ROOT_NAMES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv-autodev",
    ".venv-docling-gpu",
    "backups",
    "failed",
    "inbox",
    "models",
    "node_modules",
    "processed",
    "tmp",
    "transcripts",
}
BLOCKED_DIR_NAMES = {"__pycache__", "data", "reports"}


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def default_command_runner(argv: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


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
        headers[name.strip().lower()] = value.strip()
    raw_length = headers.get("content-length")
    if raw_length is None:
        raise ValueError("missing Content-Length header")
    length = int(raw_length)
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("incomplete MCP message body")
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


class TennMCPServer:
    def __init__(
        self,
        repo_root: Path,
        command_runner: Callable[[list[str], Path, int], CommandResult] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.command_runner = command_runner or default_command_runner
        self.memory_store = CodexMemoryStore(self.repo_root)
        self._initialized = False
        self._tools = {
            "search": self._tool_search,
            "fetch": self._tool_fetch,
            "list_operations": self._tool_list_operations,
            "get_model_routing": self._tool_get_model_routing,
            "system_health_check": self._tool_system_health_check,
            "list_runs": self._tool_list_runs,
            "get_run_report": self._tool_get_run_report,
            "get_run_commands": self._tool_get_run_commands,
            "openclaw_run_operation": self._tool_openclaw_run_operation,
            "codex_memory_bootstrap": self._tool_codex_memory_bootstrap,
            "codex_memory_recall": self._tool_codex_memory_recall,
            "codex_memory_search": self._tool_codex_memory_search,
            "codex_memory_get_session": self._tool_codex_memory_get_session,
            "codex_memory_list_sessions": self._tool_codex_memory_list_sessions,
            "codex_memory_write_session": self._tool_codex_memory_write_session,
            "openclaw_analyze": self._tool_openclaw_analyze,
            "openclaw_verify": self._tool_openclaw_verify,
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
                requested_version = params.get("protocolVersion")
                if not isinstance(requested_version, str) or not requested_version.strip():
                    return self._error_response(request_id, -32602, "initialize requires protocolVersion")
                if requested_version not in SUPPORTED_PROTOCOL_VERSIONS:
                    supported = ", ".join(SUPPORTED_PROTOCOL_VERSIONS)
                    return self._error_response(
                        request_id,
                        -32602,
                        f"Unsupported protocolVersion {requested_version!r}. Supported versions: {supported}",
                    )
                self._initialized = True
                return self._result_response(request_id, self._initialize_result(requested_version))
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
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._error_response(request_id, -32603, f"Internal error: {exc}")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = self._tools.get(name)
        if handler is None:
            return self._tool_error(f"Unknown tool: {name}")
        try:
            return handler(arguments)
        except ValueError as exc:
            return self._tool_error(str(exc))
        except FileNotFoundError as exc:
            return self._tool_error(str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._tool_error(f"{name} failed: {exc}")

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search",
                "description": "Search Tenn repo text across code, docs, configs, and run artefacts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "scope": {
                            "type": "string",
                            "enum": ["repo", "docs", "openclaw", "reports", "config"],
                            "default": "repo",
                        },
                        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS, "default": 20},
                        "path_glob": {"type": "string"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "fetch",
                "description": "Fetch a numbered excerpt from a repo file or run artefact.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start_line": {"type": "integer", "minimum": 1, "default": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "list_operations",
                "description": "List Tenn OpenClaw operations from the checked-in manifest.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "get_model_routing",
                "description": "Read the active financial-engine model routing config.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "system_health_check",
                "description": "Run Tenn OpenClaw status and doctor checks and return both outputs.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "list_runs",
                "description": "List the latest Tenn OpenClaw run manifests on disk.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "get_run_report",
                "description": "Fetch a numbered excerpt from Tenn OpenClaw report.md by run id or latest.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string"},
                        "start_line": {"type": "integer", "minimum": 1, "default": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "get_run_commands",
                "description": "Fetch a numbered excerpt from Tenn OpenClaw commands.json by run id or latest.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string"},
                        "start_line": {"type": "integer", "minimum": 1, "default": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "openclaw_run_operation",
                "description": "Run an allowlisted Tenn operation via analyze or verify using its manifest goal/checks/constraints.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation_id": {"type": "string"},
                        "mode": {"type": "string", "enum": ["analyze", "verify"], "default": "analyze"},
                        "request": {"type": "string"},
                    },
                    "required": ["operation_id"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
            },
            {
                "name": "openclaw_analyze",
                "description": "Run scripts/openclaw-autodev analyze for a scoped Tenn request.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "string"},
                    },
                    "required": ["request"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
            },
            {
                "name": "openclaw_verify",
                "description": "Run scripts/openclaw-autodev verify for a scoped Tenn request.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "string"},
                    },
                    "required": ["request"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_bootstrap",
                "description": "Load durable Codex context from USER.md, MEMORY.md, daily notes, session summaries, and the digest.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recent_sessions": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                        "include_daily_notes": {"type": "boolean", "default": True},
                        "include_digest": {"type": "boolean", "default": True},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_recall",
                "description": "Build a compact cross-session recall pack from Codex memory files and session summaries.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                        "max_chars": {"type": "integer", "minimum": 500, "maximum": 8000, "default": 4000},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_search",
                "description": "Search Codex memory files and session summaries for cross-session recall.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CODEX_MEMORY_RESULTS, "default": 10},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_get_session",
                "description": "Fetch a stored Codex session summary by path, OpenViking path, filename, or latest.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_ref": {"type": "string"},
                    },
                    "required": ["session_ref"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_list_sessions",
                "description": "List recent Codex session summaries stored under memory/codex/sessions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "readOnlyHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "codex_memory_write_session",
                "description": "Write a compact Codex session summary in an OpenViking-aligned path shape.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "title": {"type": "string"},
                        "outcome": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "source_paths": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["summary"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
            },
        ]

    def _initialize_result(self, protocol_version: str) -> dict[str, Any]:
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "Tenn MCP exposes repo search/fetch, Codex cross-session memory bootstrap/recall/search/write, "
                "OpenClaw run inspection, model-routing inspection, and allowlisted analyze/verify commands."
            ),
        }

    def _tool_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = self._required_text(arguments, "query")
        scope = str(arguments.get("scope", "repo")).strip().lower() or "repo"
        if scope not in {"repo", "docs", "openclaw", "reports", "config"}:
            raise ValueError("scope must be one of repo, docs, openclaw, reports, config")
        limit = int(arguments.get("limit", 20))
        if limit < 1 or limit > MAX_SEARCH_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")
        path_glob = str(arguments.get("path_glob", "")).strip()
        matches, backend = self._search_matches(query=query, scope=scope, limit=limit, path_glob=path_glob)
        lines = [f"{item['path']}:{item['line']}: {item['text']}" for item in matches]
        text = "\n".join(lines) if lines else f"No matches for {query!r} in scope {scope!r}."
        return self._tool_success(
            text,
            {
                "scope": scope,
                "query": query,
                "matches": matches,
                "backend": backend,
                "path_glob": path_glob or None,
                "truncated": len(matches) >= limit,
            },
        )

    def _tool_fetch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_path = self._required_text(arguments, "path")
        path = self._resolve_repo_path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {raw_path}")
        if path.is_dir():
            raise ValueError(f"Path is a directory: {raw_path}")
        if path.stat().st_size > MAX_TEXT_FILE_BYTES:
            raise ValueError(f"Path exceeds {MAX_TEXT_FILE_BYTES} bytes: {raw_path}")
        start_line = int(arguments.get("start_line", 1))
        end_line = int(arguments.get("end_line", start_line + MAX_FETCH_LINES - 1))
        if start_line < 1 or end_line < start_line:
            raise ValueError("start_line must be >= 1 and end_line must be >= start_line")
        if end_line - start_line + 1 > MAX_FETCH_LINES:
            raise ValueError(f"Fetch range exceeds {MAX_FETCH_LINES} lines")
        collected: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number < start_line:
                    continue
                if line_number > end_line:
                    break
                collected.append({"line": line_number, "text": line.rstrip("\n")})
        relative = path.relative_to(self.repo_root).as_posix()
        excerpt = "\n".join(f"{item['line']}: {item['text']}" for item in collected)
        return self._tool_success(
            excerpt or f"No content in requested range for {relative}.",
            {"path": relative, "lines": collected},
        )

    def _tool_list_operations(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._reject_extra_arguments(arguments)
        manifest_path = self.repo_root / "openclaw" / "tenn_operations_manifest.json"
        payload = self._read_json_file(manifest_path)
        operations = payload.get("operations", []) if isinstance(payload, dict) else []
        if not isinstance(operations, list):
            raise ValueError("operations manifest is malformed")
        text = "\n".join(
            f"{item.get('id', '<missing-id>')}: {item.get('goal', '').strip()}"
            for item in operations
            if isinstance(item, dict)
        )
        return self._tool_success(text or "No operations found.", {"operations": operations})

    def _tool_get_model_routing(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._reject_extra_arguments(arguments)
        path = self.repo_root / "financial-engine_v2" / "backend" / "app" / "config" / "model_routing.yaml"
        payload = self._read_yaml_mapping(path)
        routing = self._flatten_mapping(payload)
        text = "\n".join(f"{key}: {value}" for key, value in routing.items())
        return self._tool_success(
            text,
            {
                "routing": routing,
                "raw_payload": payload,
                "path": path.relative_to(self.repo_root).as_posix(),
            },
        )

    def _tool_system_health_check(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._reject_extra_arguments(arguments)
        status = self._run_openclaw(["status"], timeout_seconds=60)
        doctor = self._run_openclaw(["doctor"], timeout_seconds=60)
        ok = status.exit_code == 0 and doctor.exit_code == 0
        text = (
            f"status exit={status.exit_code}\n{status.stdout.strip()}\n\n"
            f"doctor exit={doctor.exit_code}\n{doctor.stdout.strip()}"
        ).strip()
        return self._tool_success(
            text,
            {
                "ok": ok,
                "status": self._command_result_payload(status),
                "doctor": self._command_result_payload(doctor),
            },
        )

    def _tool_list_runs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit", 10))
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        runs = [self._summarize_run(run_dir) for run_dir in self._sorted_run_dirs()[:limit]]
        text = "\n".join(
            f"{item['run_id']} [{item['mode']}] {item['status']} - {item['request']}" for item in runs
        )
        return self._tool_success(text or "No runs found.", {"runs": runs})

    def _tool_get_run_report(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_dir = self._resolve_run_dir(arguments.get("run_id"))
        report_path = run_dir / "report.md"
        report_markdown = report_path.read_text(encoding="utf-8")
        excerpt = self._build_excerpt_payload(report_markdown, arguments)
        return self._tool_success(
            excerpt["text"],
            {
                "run_id": run_dir.name,
                "path": report_path.relative_to(self.repo_root).as_posix(),
                "report_markdown": excerpt["raw_excerpt"],
                "lines": excerpt["lines"],
                "start_line": excerpt["start_line"],
                "end_line": excerpt["end_line"],
                "total_lines": excerpt["total_lines"],
                "truncated": excerpt["truncated"],
            },
        )

    def _tool_get_run_commands(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_dir = self._resolve_run_dir(arguments.get("run_id"))
        commands_path = run_dir / "commands.json"
        commands = self._read_json_file(commands_path)
        pretty = json.dumps(commands, indent=2, sort_keys=True)
        excerpt = self._build_excerpt_payload(pretty, arguments)
        return self._tool_success(
            excerpt["text"],
            {
                "run_id": run_dir.name,
                "path": commands_path.relative_to(self.repo_root).as_posix(),
                "commands": commands,
                "lines": excerpt["lines"],
                "start_line": excerpt["start_line"],
                "end_line": excerpt["end_line"],
                "total_lines": excerpt["total_lines"],
                "truncated": excerpt["truncated"],
            },
        )

    def _tool_openclaw_run_operation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation_id = self._required_text(arguments, "operation_id")
        mode = str(arguments.get("mode", "analyze")).strip().lower() or "analyze"
        if mode not in {"analyze", "verify"}:
            raise ValueError("mode must be one of analyze or verify")
        operation = self._get_operation(operation_id)
        additional_request = str(arguments.get("request", "")).strip()
        request = self._render_operation_request(operation, additional_request)
        result = self._run_openclaw([mode, request], timeout_seconds=300)
        payload = self._command_result_tool_payload(result, mode, request)
        structured = dict(payload.get("structuredContent", {}))
        structured["operation_id"] = operation_id
        structured["operation"] = operation
        structured["resolved_request"] = request
        payload["structuredContent"] = structured
        return payload

    def _tool_codex_memory_bootstrap(self, arguments: dict[str, Any]) -> dict[str, Any]:
        recent_sessions = int(arguments.get("recent_sessions", 5))
        include_daily_notes = bool(arguments.get("include_daily_notes", True))
        include_digest = bool(arguments.get("include_digest", True))
        payload = self.memory_store.build_bootstrap(
            recent_sessions=recent_sessions,
            include_daily_notes=include_daily_notes,
            include_digest=include_digest,
        )
        return self._tool_success(payload["text"], payload["structured"])

    def _tool_codex_memory_recall(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = self._required_text(arguments, "query")
        limit = int(arguments.get("limit", 5))
        max_chars = int(arguments.get("max_chars", 4_000))
        payload = self.memory_store.build_recall(query, limit=limit, max_chars=max_chars)
        return self._tool_success(payload["text"], payload["structured"])

    def _tool_codex_memory_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = self._required_text(arguments, "query")
        limit = int(arguments.get("limit", 10))
        matches = self.memory_store.search(query, limit=limit)
        text = "\n".join(f"{item['path']}:{item['line']}: {item['text']}" for item in matches)
        if not text:
            text = f"No Codex memory matches for {query!r}."
        return self._tool_success(text, {"query": query, "matches": matches})

    def _tool_codex_memory_get_session(self, arguments: dict[str, Any]) -> dict[str, Any]:
        session_ref = self._required_text(arguments, "session_ref")
        payload = self.memory_store.get_session(session_ref)
        text = payload["markdown"]
        return self._tool_success(text, payload)

    def _tool_codex_memory_list_sessions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit", 10))
        sessions = self.memory_store.list_sessions(limit=limit)
        text = "\n".join(
            f"{item['created_at'] or 'unknown'} {item['title']} [{item['path']}]"
            for item in sessions
        )
        return self._tool_success(text or "No Codex session summaries found.", {"sessions": sessions})

    def _tool_codex_memory_write_session(self, arguments: dict[str, Any]) -> dict[str, Any]:
        summary = self._required_text(arguments, "summary")
        title = str(arguments.get("title", "")).strip()
        outcome = str(arguments.get("outcome", "")).strip()
        tags = self._string_list(arguments.get("tags"))
        source_paths = self._string_list(arguments.get("source_paths"))
        payload = self.memory_store.write_session_summary(
            summary=summary,
            title=title,
            outcome=outcome,
            tags=tags,
            source_paths=source_paths,
        )
        text = f"Wrote Codex session summary to {payload['path']}"
        return self._tool_success(text, payload)

    def _tool_openclaw_analyze(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = self._required_text(arguments, "request")
        result = self._run_openclaw(["analyze", request], timeout_seconds=300)
        return self._command_result_tool_payload(result, "analyze", request)

    def _tool_openclaw_verify(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = self._required_text(arguments, "request")
        result = self._run_openclaw(["verify", request], timeout_seconds=300)
        return self._command_result_tool_payload(result, "verify", request)

    def _command_result_tool_payload(self, result: CommandResult, command: str, request: str) -> dict[str, Any]:
        text = result.stdout.strip() or result.stderr.strip() or f"openclaw {command} finished with exit {result.exit_code}"
        if result.exit_code != 0:
            return self._tool_error(text, {"command": command, "request": request, **self._command_result_payload(result)})
        return self._tool_success(text, {"command": command, "request": request, **self._command_result_payload(result)})

    def _run_openclaw(self, argv: list[str], timeout_seconds: int) -> CommandResult:
        script = self.repo_root / "scripts" / "openclaw-autodev"
        if not script.exists():
            raise FileNotFoundError(f"OpenClaw bridge missing: {script}")
        return self.command_runner([str(script), *argv], self.repo_root, timeout_seconds)

    def _sorted_run_dirs(self) -> list[Path]:
        runs_root = self.repo_root / "autodev" / "reports" / "runs"
        if not runs_root.exists():
            return []
        run_dirs = [path for path in runs_root.iterdir() if path.is_dir() and self._looks_like_run_id(path.name)]
        run_dirs.sort(key=lambda path: path.name, reverse=True)
        return run_dirs

    def _resolve_run_dir(self, run_id: Any) -> Path:
        if run_id is None:
            run_dirs = self._sorted_run_dirs()
            if not run_dirs:
                raise FileNotFoundError("No Tenn run directories found.")
            return run_dirs[0]
        run_id_text = str(run_id).strip()
        if not self._looks_like_run_id(run_id_text):
            raise ValueError("run_id must match YYYYMMDDTHHMMSSZ")
        run_dir = self.repo_root / "autodev" / "reports" / "runs" / run_id_text
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run not found: {run_id_text}")
        return run_dir

    def _summarize_run(self, run_dir: Path) -> dict[str, Any]:
        request = self._read_json_file(run_dir / "request.json")
        manager = self._read_json_file(run_dir / "manager.json")
        return {
            "run_id": run_dir.name,
            "mode": request.get("mode", ""),
            "request": request.get("request", ""),
            "status": manager.get("status", ""),
            "planner_mode": manager.get("planner_mode", ""),
            "report_path": (run_dir / "report.md").relative_to(self.repo_root).as_posix(),
            "commands_path": (run_dir / "commands.json").relative_to(self.repo_root).as_posix(),
        }

    def _search_matches(
        self,
        *,
        query: str,
        scope: str,
        limit: int,
        path_glob: str,
    ) -> tuple[list[dict[str, Any]], str]:
        matches = self._search_with_ripgrep(query=query, scope=scope, limit=limit, path_glob=path_glob)
        if matches is not None:
            return matches, "ripgrep"
        return self._search_with_python(query=query, scope=scope, limit=limit, path_glob=path_glob), "python-fallback"

    def _search_with_ripgrep(
        self,
        *,
        query: str,
        scope: str,
        limit: int,
        path_glob: str,
    ) -> list[dict[str, Any]] | None:
        if shutil.which("rg") is None:
            return None
        targets = [self._ripgrep_target(target) for target in self._scope_targets(scope) if target.exists()]
        if not targets:
            return []
        argv = [
            "rg",
            "--json",
            "--fixed-strings",
            "--ignore-case",
            "--line-number",
            "--hidden",
            "--no-ignore",
            "--color",
            "never",
        ]
        if path_glob:
            argv.extend(["-g", path_glob])
        for glob in self._ripgrep_exclude_globs(scope):
            argv.extend(["-g", glob])
        argv.extend([query, *targets])
        try:
            completed = subprocess.run(
                argv,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=SEARCH_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode not in {0, 1}:
            return None

        matches: list[dict[str, Any]] = []
        for raw_line in completed.stdout.splitlines():
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "match":
                continue
            data = payload.get("data", {})
            path_payload = data.get("path", {})
            line_payload = data.get("lines", {})
            path_text = str(path_payload.get("text", "")).strip()
            if not path_text:
                continue
            relative_path = self._normalize_repo_relative_path(path_text)
            if path_glob and not fnmatch(relative_path, path_glob):
                continue
            text = str(line_payload.get("text", "")).rstrip("\n")
            matches.append(
                {
                    "path": relative_path,
                    "line": int(data.get("line_number", 0) or 0),
                    "text": text,
                }
            )
            if len(matches) >= limit:
                break
        return matches

    def _search_with_python(
        self,
        *,
        query: str,
        scope: str,
        limit: int,
        path_glob: str,
    ) -> list[dict[str, Any]]:
        lowered = query.casefold()
        matches: list[dict[str, Any]] = []
        for path in self._iter_scope_files(scope):
            relative = path.relative_to(self.repo_root).as_posix()
            if path_glob and not fnmatch(relative, path_glob):
                continue
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line_number, line in enumerate(handle, start=1):
                    text = line.rstrip("\n")
                    if lowered in text.casefold():
                        matches.append({"path": relative, "line": line_number, "text": text})
                        if len(matches) >= limit:
                            return matches
        return matches

    def _ripgrep_target(self, target: Path) -> str:
        if target == self.repo_root:
            return "."
        return target.relative_to(self.repo_root).as_posix()

    def _ripgrep_exclude_globs(self, scope: str) -> list[str]:
        globs = [f"!{name}/**" for name in sorted(BLOCKED_ROOT_NAMES)]
        blocked_dir_names = set(BLOCKED_DIR_NAMES)
        if scope == "reports":
            blocked_dir_names.discard("reports")
        globs.extend(f"!**/{name}/**" for name in sorted(blocked_dir_names))
        return globs

    def _normalize_repo_relative_path(self, path_text: str) -> str:
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = (self.repo_root / candidate).resolve()
        try:
            return candidate.relative_to(self.repo_root).as_posix()
        except ValueError:
            return path_text

    def _build_excerpt_payload(self, text: str, arguments: dict[str, Any]) -> dict[str, Any]:
        lines = text.splitlines()
        total_lines = len(lines)
        start_line = int(arguments.get("start_line", 1))
        default_end_line = min(total_lines or 1, start_line + MAX_FETCH_LINES - 1)
        end_line = int(arguments.get("end_line", default_end_line))
        if start_line < 1 or end_line < start_line:
            raise ValueError("start_line must be >= 1 and end_line must be >= start_line")
        if end_line - start_line + 1 > MAX_FETCH_LINES:
            raise ValueError(f"Fetch range exceeds {MAX_FETCH_LINES} lines")
        collected: list[dict[str, Any]] = []
        for line_number in range(start_line, min(end_line, total_lines) + 1):
            collected.append({"line": line_number, "text": lines[line_number - 1]})
        numbered_excerpt = "\n".join(f"{item['line']}: {item['text']}" for item in collected)
        raw_excerpt = "\n".join(item["text"] for item in collected)
        return {
            "text": numbered_excerpt or "No content in requested range.",
            "raw_excerpt": raw_excerpt,
            "lines": collected,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "truncated": end_line < total_lines,
        }

    def _get_operation(self, operation_id: str) -> dict[str, Any]:
        manifest_path = self.repo_root / "openclaw" / "tenn_operations_manifest.json"
        payload = self._read_json_file(manifest_path)
        operations = payload.get("operations", [])
        if not isinstance(operations, list):
            raise ValueError("operations manifest is malformed")
        for operation in operations:
            if isinstance(operation, dict) and str(operation.get("id", "")).strip() == operation_id:
                return operation
        raise ValueError(f"Unknown operation_id: {operation_id}")

    def _render_operation_request(self, operation: dict[str, Any], additional_request: str) -> str:
        parts = [
            f"Operation: {operation.get('id', '')}",
            f"Goal: {str(operation.get('goal', '')).strip()}",
        ]
        for label, key in (("Checks", "checks"), ("Outputs", "outputs"), ("Constraints", "constraints")):
            values = operation.get(key, [])
            if not isinstance(values, list) or not values:
                continue
            parts.append(f"{label}:")
            parts.extend(f"- {str(value).strip()}" for value in values if str(value).strip())
        if additional_request:
            parts.extend(["Additional request:", additional_request])
        return "\n".join(parts).strip()

    def _iter_scope_files(self, scope: str) -> list[Path]:
        targets = self._scope_targets(scope)
        files: list[Path] = []
        for target in targets:
            if not target.exists():
                continue
            if target.is_file():
                if self._is_readable_text_file(target):
                    files.append(target)
                continue
            for root, dirnames, filenames in os.walk(target):
                current_root = Path(root)
                dirnames[:] = [name for name in dirnames if self._allow_descend(current_root, name)]
                for filename in filenames:
                    candidate = current_root / filename
                    if self._is_readable_text_file(candidate):
                        files.append(candidate)
        files.sort()
        return files

    def _scope_targets(self, scope: str) -> list[Path]:
        if scope == "docs":
            return [
                self.repo_root / "README.md",
                self.repo_root / "docs",
                self.repo_root / "news_pipeline.md",
                self.repo_root / "financial_intelligence_pipeline.md",
                self.repo_root / "system_architecture.md",
            ]
        if scope == "openclaw":
            return [
                self.repo_root / "openclaw",
                self.repo_root / "scripts" / "openclaw-autodev",
                self.repo_root / "docs" / "ops" / "openclaw_ops_loop.md",
            ]
        if scope == "reports":
            return [self.repo_root / "autodev" / "reports" / "runs"]
        if scope == "config":
            return [
                self.repo_root / ".mcp.json",
                self.repo_root / "docs" / "mcp_servers.md",
                self.repo_root / "openclaw" / "tenn_operations_manifest.json",
                self.repo_root / "financial-engine_v2" / "backend" / "app" / "config",
            ]
        return [self.repo_root]

    def _allow_descend(self, current_root: Path, dirname: str) -> bool:
        if dirname in BLOCKED_DIR_NAMES:
            return False
        if dirname.startswith(".") and dirname not in {".github"}:
            return False
        if current_root == self.repo_root and dirname in BLOCKED_ROOT_NAMES:
            return False
        return True

    def _is_readable_text_file(self, path: Path) -> bool:
        try:
            if not path.is_file():
                return False
            relative = path.relative_to(self.repo_root)
        except ValueError:
            return False
        if relative.parts and relative.parts[0] in BLOCKED_ROOT_NAMES:
            return False
        size = path.stat().st_size
        if size > MAX_TEXT_FILE_BYTES:
            return False
        try:
            with path.open("rb") as handle:
                prefix = handle.read(1024)
        except OSError:
            return False
        return b"\x00" not in prefix

    def _resolve_repo_path(self, raw_path: str) -> Path:
        candidate = (self.repo_root / raw_path).resolve()
        try:
            relative = candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("Requested path is outside the Tenn repository.") from exc
        if not relative.parts:
            raise ValueError("Requested path must point to a file inside the Tenn repository.")
        first_part = relative.parts[0]
        if first_part in BLOCKED_ROOT_NAMES:
            raise ValueError(f"Requested path is blocked: {raw_path}")
        return candidate

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path.relative_to(self.repo_root).as_posix()}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {path.relative_to(self.repo_root).as_posix()}")
        return data

    def _read_yaml_mapping(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path.relative_to(self.repo_root).as_posix()}")
        try:
            import yaml  # type: ignore
        except Exception:
            payload: dict[str, Any] = {}
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#") or ":" not in stripped:
                    continue
                key, value = stripped.split(":", 1)
                parsed_value = value.strip().strip('"').strip("'")
                lowered = parsed_value.lower()
                if lowered in {"true", "false"}:
                    payload[key.strip()] = lowered == "true"
                    continue
                try:
                    payload[key.strip()] = int(parsed_value)
                    continue
                except ValueError:
                    pass
                try:
                    payload[key.strip()] = float(parsed_value)
                    continue
                except ValueError:
                    pass
                payload[key.strip()] = parsed_value
            return payload
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected YAML object in {path.relative_to(self.repo_root).as_posix()}")
        return loaded

    def _flatten_mapping(self, payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key, value in payload.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                flattened.update(self._flatten_mapping(value, prefix=full_key))
                continue
            flattened[full_key] = value
        return flattened

    def _required_text(self, arguments: dict[str, Any], key: str) -> str:
        value = str(arguments.get(key, "")).strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Expected a list of strings.")
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items

    def _reject_extra_arguments(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ValueError(f"This tool does not accept arguments: {sorted(arguments)}")

    def _looks_like_run_id(self, run_id: str) -> bool:
        return len(run_id) == RUN_ID_LENGTH and run_id.endswith("Z") and "T" in run_id

    def _command_result_payload(self, result: CommandResult) -> dict[str, Any]:
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def _result_response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _tool_success(self, text: str, structured_content: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": structured_content,
            "isError": False,
        }

    def _tool_error(self, text: str, structured_content: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "content": [{"type": "text", "text": text}],
            "isError": True,
        }
        if structured_content is not None:
            payload["structuredContent"] = structured_content
        return payload


def serve_stdio(repo_root: Path) -> int:
    server = TennMCPServer(repo_root=repo_root)
    while True:
        try:
            message = read_message(sys.stdin.buffer)
        except ValueError as exc:
            print(f"{SERVER_NAME}: invalid message: {exc}", file=sys.stderr)
            return 1
        if message is None:
            return 0
        response = server.handle_message(message)
        if response is not None:
            write_message(sys.stdout.buffer, response)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tenn stdio MCP server")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    return serve_stdio(Path(args.repo_root))


if __name__ == "__main__":
    raise SystemExit(main())
