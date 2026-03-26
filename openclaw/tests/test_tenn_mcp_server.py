from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from openclaw.tenn_mcp_server import (
    CommandResult,
    HttpResult,
    SERVER_PROTOCOL_VERSION,
    TennMCPServer,
    read_message,
    write_message,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    _write(
        tmp_path / "openclaw" / "tenn_operations_manifest.json",
        json.dumps(
            {
                "operations": [
                    {
                        "id": "system_health_check",
                        "goal": "Run health checks and report failures.",
                        "checks": ["status succeeds"],
                        "outputs": ["health snapshots"],
                        "constraints": ["do not restart services"],
                        "triggers": ["system health check"],
                    }
                ]
            }
        ),
    )
    _write(
        tmp_path / "financial-engine_v2" / "backend" / "app" / "config" / "model_routing.yaml",
        "\n".join(
            (
                "router_model: phi3:mini",
                "router_provider: ollama",
                "coding_model: qwen2.5-coder-14b",
                "coding_provider: llamacpp",
                "queue_backlog_threshold: 50",
            )
        ),
    )
    _write(tmp_path / "docs" / "guide.md", "Alpha\nPipeline health\n")
    _write(tmp_path / "README.md", "TENN\n")
    _write(tmp_path / "USER.md", "# USER\n- Name: Lando\n")
    _write(tmp_path / "MEMORY.md", "# MEMORY\n- Prefers concise help\n")
    _write(tmp_path / "memory" / "2026-03-16.md", "# 2026-03-16\n- Investigated Codex context\n")
    _write(tmp_path / "reports" / "agent_context_digest.md", "# Agent Context Digest\n- Branch: main\n")
    _write(tmp_path / "scripts" / "openclaw-autodev", "#!/usr/bin/env bash\n")
    latest_run = tmp_path / "autodev" / "reports" / "runs" / "20260313T120000Z"
    older_run = tmp_path / "autodev" / "reports" / "runs" / "20260313T110000Z"
    _write(
        latest_run / "request.json",
        json.dumps(
            {
                "mode": "analyze",
                "request": "inspect pipeline",
                "run_id": "20260313T120000Z",
            }
        ),
    )
    _write(
        latest_run / "manager.json",
        json.dumps({"status": "completed", "planner_mode": "openai"}),
    )
    _write(latest_run / "report.md", "# Latest report\nAll good.\nNext step.\n")
    _write(latest_run / "commands.json", json.dumps({"commands": [{"name": "git_status"}]}))
    _write(
        older_run / "request.json",
        json.dumps(
            {
                "mode": "verify",
                "request": "retest pipeline",
                "run_id": "20260313T110000Z",
            }
        ),
    )
    _write(older_run / "manager.json", json.dumps({"status": "worker_error"}))
    _write(older_run / "report.md", "# Older report\n")
    _write(tmp_path / "node_modules" / "ignored.js", "pipeline\n")
    return tmp_path


def _default_http_stub(
    url: str, timeout_seconds: float = 3, headers: dict[str, str] | None = None,
) -> HttpResult:
    return HttpResult(status=0, body="connection refused")


def _server(
    repo_root: Path,
    calls: list[tuple[list[str], Path, int]] | None = None,
    http_requester=None,
) -> TennMCPServer:
    def runner(argv: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
        if calls is not None:
            calls.append((argv, cwd, timeout_seconds))
        return CommandResult(exit_code=0, stdout="ok\n", stderr="")

    return TennMCPServer(
        repo_root=repo_root,
        command_runner=runner,
        http_requester=http_requester or _default_http_stub,
    )


def test_initialize_advertises_tenn_tools(repo_root: Path) -> None:
    server = _server(repo_root)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": SERVER_PROTOCOL_VERSION},
        }
    )

    assert response["result"]["protocolVersion"] == SERVER_PROTOCOL_VERSION
    assert response["result"]["serverInfo"]["name"] == "tenn-mcp"
    assert response["result"]["capabilities"] == {"tools": {"listChanged": False}}


def test_initialize_accepts_supported_legacy_protocol_version(repo_root: Path) -> None:
    server = _server(repo_root)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )

    assert response["result"]["protocolVersion"] == "2025-06-18"


def test_tools_list_requires_initialize_first(repo_root: Path) -> None:
    server = _server(repo_root)

    response = server.handle_message({"jsonrpc": "2.0", "id": 99, "method": "tools/list"})

    assert response["error"]["code"] == -32002
    assert "initialize" in response["error"]["message"]


def test_tools_list_contains_expected_safe_surface(repo_root: Path) -> None:
    server = _server(repo_root)
    server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": SERVER_PROTOCOL_VERSION},
        }
    )

    response = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    tools = response["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert {
        "search",
        "fetch",
        "list_operations",
        "get_model_routing",
        "system_health_check",
        "list_runs",
        "get_run_report",
        "get_run_commands",
        "openclaw_run_operation",
        "codex_memory_bootstrap",
        "codex_memory_recall",
        "codex_memory_search",
        "codex_memory_get_session",
        "codex_memory_list_sessions",
        "codex_memory_write_session",
        "openclaw_analyze",
        "openclaw_verify",
    } <= names
    search_tool = next(tool for tool in tools if tool["name"] == "search")
    analyze_tool = next(tool for tool in tools if tool["name"] == "openclaw_analyze")
    assert search_tool["annotations"]["readOnlyHint"] is True
    assert analyze_tool["annotations"]["destructiveHint"] is False


def test_search_returns_matches_and_skips_excluded_directories(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("search", {"query": "pipeline"})

    matches = result["structuredContent"]["matches"]
    assert matches
    assert matches[0]["path"] == "docs/guide.md"
    assert all(match["path"] != "node_modules/ignored.js" for match in matches)


def test_search_honors_path_glob(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("search", {"query": "pipeline", "path_glob": "docs/*.md"})

    matches = result["structuredContent"]["matches"]
    assert matches
    assert all(match["path"].startswith("docs/") for match in matches)


def test_fetch_returns_line_numbered_excerpt(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("fetch", {"path": "docs/guide.md", "start_line": 2, "end_line": 2})

    assert result["structuredContent"]["path"] == "docs/guide.md"
    assert result["structuredContent"]["lines"] == [{"line": 2, "text": "Pipeline health"}]
    assert "2: Pipeline health" in result["content"][0]["text"]


def test_fetch_rejects_paths_outside_repo(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("fetch", {"path": "../secret.txt"})

    assert result["isError"] is True
    assert "outside the Tenn repository" in result["content"][0]["text"]


def test_list_operations_reads_manifest(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("list_operations", {})

    operations = result["structuredContent"]["operations"]
    assert operations == [
        {
            "checks": ["status succeeds"],
            "constraints": ["do not restart services"],
            "goal": "Run health checks and report failures.",
            "id": "system_health_check",
            "outputs": ["health snapshots"],
            "triggers": ["system health check"],
        }
    ]


def test_get_model_routing_parses_flat_yaml(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("get_model_routing", {})

    assert result["structuredContent"]["routing"]["coding_model"] == "qwen2.5-coder-14b"
    assert result["structuredContent"]["routing"]["router_provider"] == "ollama"
    assert result["structuredContent"]["routing"]["queue_backlog_threshold"] == 50


def test_list_runs_returns_latest_first(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("list_runs", {})

    runs = result["structuredContent"]["runs"]
    assert [run["run_id"] for run in runs] == ["20260313T120000Z", "20260313T110000Z"]
    assert runs[0]["status"] == "completed"
    assert runs[0]["request"] == "inspect pipeline"


def test_get_run_report_uses_latest_run_by_default(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("get_run_report", {})

    assert result["structuredContent"]["run_id"] == "20260313T120000Z"
    assert "# Latest report" in result["structuredContent"]["report_markdown"]


def test_get_run_report_returns_line_numbered_excerpt(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("get_run_report", {"run_id": "20260313T120000Z", "start_line": 2, "end_line": 3})

    assert result["structuredContent"]["lines"] == [
        {"line": 2, "text": "All good."},
        {"line": 3, "text": "Next step."},
    ]
    assert result["structuredContent"]["truncated"] is False
    assert "2: All good." in result["content"][0]["text"]


def test_get_run_commands_reads_commands_json(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("get_run_commands", {"run_id": "20260313T120000Z"})

    assert result["structuredContent"]["run_id"] == "20260313T120000Z"
    assert result["structuredContent"]["commands"]["commands"][0]["name"] == "git_status"


def test_get_run_commands_returns_line_numbered_excerpt(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("get_run_commands", {"run_id": "20260313T120000Z", "start_line": 2, "end_line": 3})

    assert result["structuredContent"]["lines"] == [
        {"line": 2, "text": '  "commands": ['},
        {"line": 3, "text": "    {"},
    ]
    assert result["structuredContent"]["truncated"] is True
    assert '2:   "commands": [' in result["content"][0]["text"]


def test_system_health_check_runs_status_and_doctor(repo_root: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []
    server = _server(repo_root, calls=calls)

    result = server.call_tool("system_health_check", {})

    assert [call[0][-1] for call in calls] == ["status", "doctor"]
    assert result["structuredContent"]["ok"] is True


def test_openclaw_analyze_runs_bridge_command(repo_root: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []
    server = _server(repo_root, calls=calls)

    result = server.call_tool("openclaw_analyze", {"request": "inspect the ingestion pipeline"})

    assert calls == [
        (
            [str(repo_root / "scripts" / "openclaw-autodev"), "analyze", "inspect the ingestion pipeline"],
            repo_root,
            300,
        )
    ]
    assert result["structuredContent"]["exit_code"] == 0


def test_openclaw_run_operation_builds_manifest_scoped_request(repo_root: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []
    server = _server(repo_root, calls=calls)

    result = server.call_tool(
        "openclaw_run_operation",
        {
            "operation_id": "system_health_check",
            "mode": "analyze",
            "request": "Focus on llama.cpp readiness.",
        },
    )

    assert result["isError"] is False
    assert calls == [
        (
            [
                str(repo_root / "scripts" / "openclaw-autodev"),
                "analyze",
                "Operation: system_health_check\nGoal: Run health checks and report failures.\nChecks:\n- status succeeds\nOutputs:\n- health snapshots\nConstraints:\n- do not restart services\nAdditional request:\nFocus on llama.cpp readiness.",
            ],
            repo_root,
            300,
        )
    ]
    assert result["structuredContent"]["operation"]["id"] == "system_health_check"


def test_openclaw_run_operation_rejects_unknown_operation(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("openclaw_run_operation", {"operation_id": "not-real", "mode": "analyze"})

    assert result["isError"] is True
    assert "Unknown operation_id" in result["content"][0]["text"]


def test_openclaw_verify_requires_non_empty_request(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("openclaw_verify", {"request": "  "})

    assert result["isError"] is True
    assert "request is required" in result["content"][0]["text"]


def test_codex_memory_bootstrap_includes_canonical_memory(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("codex_memory_bootstrap", {"recent_sessions": 3})

    assert result["isError"] is False
    assert "USER.md" in result["content"][0]["text"]
    assert "MEMORY.md" in result["content"][0]["text"]
    assert result["structuredContent"]["user_path"] == "USER.md"
    assert result["structuredContent"]["memory_path"] == "MEMORY.md"
    assert result["structuredContent"]["digest_path"] == "reports/agent_context_digest.md"


def test_codex_memory_write_session_creates_openviking_aligned_summary(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool(
        "codex_memory_write_session",
        {
            "title": "Add Codex memory tools",
            "summary": "Implemented bootstrap, search, and session memory tools.",
            "tags": ["codex", "memory"],
            "source_paths": ["openclaw/tenn_mcp_server.py"],
            "outcome": "implemented",
        },
    )

    assert result["isError"] is False
    path = repo_root / result["structuredContent"]["path"]
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "- openviking_path: viking://tenn/codex/sessions/" in content
    assert "Implemented bootstrap, search, and session memory tools." in content


def test_codex_memory_search_finds_written_session(repo_root: Path) -> None:
    server = _server(repo_root)
    server.call_tool(
        "codex_memory_write_session",
        {
            "title": "Track repo context refresh",
            "summary": "Reviewed the Codex bootstrap digest and repo memory layout.",
        },
    )

    result = server.call_tool("codex_memory_search", {"query": "bootstrap digest", "limit": 5})

    assert result["isError"] is False
    matches = result["structuredContent"]["matches"]
    assert matches
    assert any(match["path"].startswith("memory/codex/sessions/") for match in matches)


def test_codex_memory_get_session_supports_latest_alias(repo_root: Path) -> None:
    server = _server(repo_root)
    server.call_tool(
        "codex_memory_write_session",
        {
            "title": "Fresh memory entry",
            "summary": "Captured the latest MCP context.",
        },
    )

    result = server.call_tool("codex_memory_get_session", {"session_ref": "latest"})

    assert result["isError"] is False
    assert result["structuredContent"]["session"]["title"] == "Fresh memory entry"
    assert "Captured the latest MCP context." in result["structuredContent"]["markdown"]


def test_codex_memory_get_session_rejects_paths_outside_repo(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("codex_memory_get_session", {"session_ref": "../secret.md"})

    assert result["isError"] is True
    assert "outside the Tenn repository" in result["content"][0]["text"]


def test_codex_memory_recall_returns_context_blocks(repo_root: Path) -> None:
    server = _server(repo_root)
    server.call_tool(
        "codex_memory_write_session",
        {
            "title": "MCP improvements",
            "summary": "Reviewed Tenn MCP improvements and cross-session memory design.",
        },
    )

    result = server.call_tool("codex_memory_recall", {"query": "cross-session memory", "limit": 3})

    assert result["isError"] is False
    assert result["structuredContent"]["query"] == "cross-session memory"
    assert result["structuredContent"]["entries"]
    assert "cross-session memory design" in result["content"][0]["text"]


def test_codex_memory_list_sessions_returns_recent_entries(repo_root: Path) -> None:
    server = _server(repo_root)
    server.call_tool(
        "codex_memory_write_session",
        {
            "title": "First memory entry",
            "summary": "Captured the first Codex memory item.",
        },
    )
    server.call_tool(
        "codex_memory_write_session",
        {
            "title": "Second memory entry",
            "summary": "Captured the second Codex memory item.",
        },
    )

    result = server.call_tool("codex_memory_list_sessions", {"limit": 5})

    assert result["isError"] is False
    sessions = result["structuredContent"]["sessions"]
    assert len(sessions) >= 2
    assert sessions[0]["path"].startswith("memory/codex/sessions/")
    assert sessions[0]["title"] in {"First memory entry", "Second memory entry"}


def test_unknown_tool_returns_tool_error(repo_root: Path) -> None:
    server = _server(repo_root)

    result = server.call_tool("not_a_tool", {})

    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_message_roundtrip_uses_content_length_frames() -> None:
    stream = BytesIO()
    payload = {"jsonrpc": "2.0", "id": 7, "result": {"ok": True}}

    write_message(stream, payload)
    stream.seek(0)

    assert read_message(stream) == payload


# ------------------------------------------------------------------
# Orchestrator introspection tools
# ------------------------------------------------------------------


def _make_http_responder(responses: dict[str, tuple[int, str]]):
    """Build an http_requester stub that returns pre-configured responses by URL substring."""

    def requester(url: str, timeout_seconds: float = 3, headers: dict[str, str] | None = None) -> HttpResult:
        for pattern, (status, body) in responses.items():
            if pattern in url:
                return HttpResult(status=status, body=body)
        return HttpResult(status=0, body="no stub matched")

    return requester


def test_tenn_health_all_services_up(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/health": (200, '{"status":"ok"}'),
        "/api/system/status": (200, '{"redis_connected":true,"qdrant_connected":true,"collections_present":["asx_docs"]}'),
        "/api/tags": (200, '{"models":[]}'),
        "/health": (200, '{"status":"ok"}'),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_health", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "healthy"
    assert sc["timestamp_utc"]
    assert sc["services"]["backend_api"] == "ok"
    assert sc["services"]["redis"] == "ok"
    assert sc["services"]["qdrant"] == "ok"
    assert sc["services"]["ollama"] == "ok"
    assert sc["services"]["llamacpp"] == "ok"


def test_tenn_health_all_services_down(repo_root: Path) -> None:
    server = _server(repo_root)  # default stub returns status=0 (unreachable)
    result = server.call_tool("tenn_health", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "unhealthy"
    for svc in ("backend_api", "redis", "qdrant", "ollama", "llamacpp"):
        assert sc["services"][svc] == "unreachable"


def test_tenn_health_degraded(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/health": (200, '{"status":"ok"}'),
        "/api/system/status": (200, '{"redis_connected":true,"qdrant_connected":false}'),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_health", {})

    sc = result["structuredContent"]
    assert sc["status"] == "degraded"
    assert sc["services"]["backend_api"] == "ok"
    assert sc["services"]["redis"] == "ok"
    assert sc["services"]["qdrant"] == "unreachable"


def test_tenn_eval_baseline_returns_latest(repo_root: Path) -> None:
    eval_dir = repo_root / "financial-engine_v2" / "backend" / "tests" / "eval_results"
    eval_dir.mkdir(parents=True)
    older = {
        "timestamp": "2026-03-25T100000Z",
        "overall_accuracy": 0.85,
        "per_fixture": {"BHP": {"accuracy": 1.0, "metric_count": 10}},
        "per_metric": {"revenue": 1.0},
        "thresholds": {"min_accuracy_overall": 0.85},
    }
    latest = {
        "timestamp": "2026-03-26T120000Z",
        "overall_accuracy": 0.9828,
        "per_fixture": {
            "BHP": {"accuracy": 1.0, "metric_count": 11},
            "MIN": {"accuracy": 0.8571, "metric_count": 7},
        },
        "per_metric": {"revenue": 1.0, "net_debt": 0.8333},
        "thresholds": {"min_accuracy_overall": 0.85},
    }
    _write(eval_dir / "eval_2026-03-25T100000Z.json", json.dumps(older))
    _write(eval_dir / "eval_2026-03-26T120000Z.json", json.dumps(latest))

    server = _server(repo_root)
    result = server.call_tool("tenn_eval_baseline", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "ok"
    assert sc["latest_run"]["score_pct"] == 98.28
    assert sc["latest_run"]["meets_baseline"] is True
    assert sc["latest_run"]["fixtures_passed"] == 2  # BHP=1.0 and MIN=0.8571 both >= 0.85
    assert sc["latest_run"]["fixtures_total"] == 2
    assert sc["eval_file"] == "eval_2026-03-26T120000Z.json"


def test_tenn_eval_baseline_no_results(repo_root: Path) -> None:
    server = _server(repo_root)
    result = server.call_tool("tenn_eval_baseline", {})

    sc = result["structuredContent"]
    assert sc["status"] == "no_results"


def test_tenn_eval_baseline_stale_detection(repo_root: Path) -> None:
    eval_dir = repo_root / "financial-engine_v2" / "backend" / "tests" / "eval_results"
    eval_dir.mkdir(parents=True)
    old_data = {
        "timestamp": "2020-01-01T000000Z",
        "overall_accuracy": 0.95,
        "per_fixture": {},
        "per_metric": {},
        "thresholds": {"min_accuracy_overall": 0.85},
    }
    _write(eval_dir / "eval_2020-01-01T000000Z.json", json.dumps(old_data))

    server = _server(repo_root)
    result = server.call_tool("tenn_eval_baseline", {})

    sc = result["structuredContent"]
    assert sc["stale"] is True
    assert sc["age_seconds"] > 86400


def test_tenn_queue_status_returns_queues(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/queue/status": (200, json.dumps({
            "redis_connected": True,
            "queues": {"ingest": 3, "embed": 0, "score": 0, "llm_gpu": 1, "llm_cpu": 0},
            "total_queued": 4,
        })),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_queue_status", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "ok"
    assert sc["total_queued"] == 4
    assert sc["queues"]["ingest"] == 3


def test_tenn_queue_status_unreachable(repo_root: Path) -> None:
    server = _server(repo_root)  # default stub = unreachable
    result = server.call_tool("tenn_queue_status", {})

    sc = result["structuredContent"]
    assert sc["status"] == "unreachable"


def test_tenn_collections_returns_collection_list(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/system/status": (200, json.dumps({
            "redis_connected": True,
            "qdrant_connected": True,
            "collections_present": ["asx_docs", "commentary_chunks"],
            "document_count_estimate": 150,
            "last_ingestion_activity": "2026-03-26T12:00:00",
        })),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_collections", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "ok"
    assert sc["collections"] == ["asx_docs", "commentary_chunks"]
    assert sc["document_count_estimate"] == 150


def test_tenn_collections_qdrant_down(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/system/status": (200, '{"redis_connected":true,"qdrant_connected":false,"collections_present":[]}'),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_collections", {})

    sc = result["structuredContent"]
    assert sc["status"] == "unreachable"
    assert sc["collections"] == []


def test_tenn_pipeline_status_returns_last_ingestion(repo_root: Path) -> None:
    http = _make_http_responder({
        "/api/system/status": (200, json.dumps({
            "redis_connected": True,
            "qdrant_connected": True,
            "collections_present": ["asx_docs"],
            "document_count_estimate": 42,
            "last_ingestion_activity": "2026-03-26T10:30:00",
        })),
    })
    server = _server(repo_root, http_requester=http)
    result = server.call_tool("tenn_pipeline_status", {})

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["status"] == "ok"
    assert sc["last_ingestion_at"] == "2026-03-26T10:30:00"
    assert sc["document_count"] == 42


def test_tenn_pipeline_status_unreachable(repo_root: Path) -> None:
    server = _server(repo_root)
    result = server.call_tool("tenn_pipeline_status", {})

    sc = result["structuredContent"]
    assert sc["status"] == "unreachable"


def test_orchestrator_tools_listed(repo_root: Path) -> None:
    server = _server(repo_root)
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    for expected in ("tenn_health", "tenn_eval_baseline", "tenn_queue_status", "tenn_collections", "tenn_pipeline_status"):
        assert expected in names, f"{expected} not in tool list"
    # Network-calling tools should have openWorldHint: True
    for tool in tools:
        if tool["name"] in ("tenn_health", "tenn_queue_status", "tenn_collections", "tenn_pipeline_status"):
            assert tool["annotations"]["openWorldHint"] is True
    # File-reading eval tool should have openWorldHint: False
    eval_tool = next(t for t in tools if t["name"] == "tenn_eval_baseline")
    assert eval_tool["annotations"]["openWorldHint"] is False
