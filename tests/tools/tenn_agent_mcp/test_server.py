from __future__ import annotations

import subprocess
from pathlib import Path

from tools.tenn_agent_mcp.server import SERVER_PROTOCOL_VERSION, TennAgentMCPServer


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "tenn-agent-mcp@example.invalid")
    run_git(repo, "config", "user.name", "Tenn Agent MCP Tests")
    (repo / ".gitignore").write_text("reports/agent_jobs/\n", encoding="utf-8")
    (repo / "docs" / "agent_tasks").mkdir(parents=True)
    run_git(repo, "add", ".gitignore")
    run_git(repo, "commit", "-m", "init")
    return repo


def write_task_card(repo: Path, job_id: str, *, mutation_mode: str = "audit_only") -> Path:
    card = repo / "docs" / "agent_tasks" / f"{job_id}.md"
    card.write_text(
        "\n".join(
            [
                "---",
                f"job_id: {job_id}",
                "lane: Evaluation",
                "owner: Codex",
                "allowed_files:",
                f"  - docs/agent_tasks/{job_id}.md",
                f"  - reports/agent_jobs/{job_id}/README.md",
                "approval_required: false",
                "timeout_seconds: 300",
                f"output_dir: reports/agent_jobs/{job_id}",
                f"mutation_mode: {mutation_mode}",
                "production_data_access: false",
                "---",
                "",
                "# Task",
                "",
                "Audit only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return card


def initialized_server(repo: Path, env: dict[str, str] | None = None) -> TennAgentMCPServer:
    server = TennAgentMCPServer(repo, env=env or {})
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": SERVER_PROTOCOL_VERSION},
        }
    )
    assert response is not None
    assert response["result"]["serverInfo"]["name"] == "tenn-agent-mcp"
    return server


def test_tools_list_exposes_requested_surface(tmp_path: Path) -> None:
    server = initialized_server(make_repo(tmp_path))

    response = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {
        "list_capabilities",
        "create_task_card",
        "list_active_jobs",
        "launch_codex_audit",
        "get_agent_status",
        "read_agent_report",
    }
    create_tool = next(tool for tool in response["result"]["tools"] if tool["name"] == "create_task_card")
    assert create_tool["annotations"]["readOnlyHint"] is False


def test_list_capabilities_reports_local_security_defaults(tmp_path: Path) -> None:
    server = initialized_server(make_repo(tmp_path), env={"TENN_AGENT_MCP_PORT": "9000"})

    result = server.call_tool("list_capabilities", {})

    structured = result["structuredContent"]
    assert structured["ok"] is True
    assert structured["local_defaults"] == {"bind_host": "127.0.0.1", "port": 9000}
    assert "arbitrary_shell" in structured["hard_refusals"]


def test_non_read_tools_require_token(tmp_path: Path) -> None:
    server = initialized_server(make_repo(tmp_path))

    result = server.call_tool(
        "create_task_card",
        {"job_id": "audit_card", "lane": "Evaluation", "allowed_files": ["docs/agent_tasks/audit_card.md"], "body": "# Task"},
    )

    assert result["isError"] is True
    assert "TENN_AGENT_MCP_TOKEN" in result["structuredContent"]["error"]


def test_create_task_card_writes_valid_card_with_token(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    server = initialized_server(repo, env={"TENN_AGENT_MCP_TOKEN": "secret"})

    result = server.call_tool(
        "create_task_card",
        {
            "token": "secret",
            "job_id": "new_audit",
            "lane": "Evaluation",
            "allowed_files": ["docs/agent_tasks/new_audit.md", "reports/agent_jobs/new_audit/README.md"],
            "body": "# Task\n\nAudit the thing.",
        },
    )

    assert result["structuredContent"]["ok"] is True
    card = repo / "docs" / "agent_tasks" / "new_audit.md"
    assert card.exists()
    assert "production_data_access: false" in card.read_text(encoding="utf-8")
    assert result["structuredContent"]["validation"]["ok"] is True


def test_create_task_card_rejects_path_escape(tmp_path: Path) -> None:
    server = initialized_server(make_repo(tmp_path), env={"TENN_AGENT_MCP_TOKEN": "secret"})

    result = server.call_tool(
        "create_task_card",
        {
            "token": "secret",
            "job_id": "bad_path",
            "lane": "Evaluation",
            "allowed_files": ["../outside.md"],
            "body": "# Task",
        },
    )

    assert result["isError"] is True
    assert "repo-relative" in result["structuredContent"]["error"]


def test_launch_codex_audit_is_dry_run_and_audit_only(tmp_path: Path, monkeypatch) -> None:
    repo = make_repo(tmp_path)
    monkeypatch.setenv("TENN_AGENT_REGISTRY_ROOT", str(tmp_path / "registry"))
    write_task_card(repo, "audit_launch")
    server = initialized_server(repo, env={"TENN_AGENT_MCP_TOKEN": "secret"})

    result = server.call_tool(
        "launch_codex_audit",
        {"token": "secret", "task_card": "docs/agent_tasks/audit_launch.md"},
    )

    structured = result["structuredContent"]
    assert structured["ok"] is True
    assert structured["dry_run"] is True
    assert structured["argv"][:3] == ["codex", "exec", "--cd"]


def test_launch_codex_audit_refuses_safe_extension_card(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    write_task_card(repo, "safe_job", mutation_mode="safe_extension")
    server = initialized_server(repo, env={"TENN_AGENT_MCP_TOKEN": "secret"})

    result = server.call_tool(
        "launch_codex_audit",
        {"token": "secret", "task_card": "docs/agent_tasks/safe_job.md"},
    )

    assert result["isError"] is True
    assert "failed validation" in result["structuredContent"]["error"] or "audit_only" in result["structuredContent"]["error"]


def test_status_and_report_reads_are_job_id_scoped(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    report_dir = repo / "reports" / "agent_jobs" / "job_status"
    report_dir.mkdir(parents=True)
    (report_dir / "status.json").write_text('{"status": "active"}\n', encoding="utf-8")
    (report_dir / "README.md").write_text("# Report\n\nDone.\n", encoding="utf-8")
    server = initialized_server(repo)

    status = server.call_tool("get_agent_status", {"job_id": "job_status"})["structuredContent"]
    report = server.call_tool("read_agent_report", {"job_id": "job_status"})["structuredContent"]
    invalid = server.call_tool("read_agent_report", {"job_id": "../escape"})["structuredContent"]

    assert status["ok"] is True
    assert status["status"] == {"status": "active"}
    assert report["ok"] is True
    assert report["text"].startswith("# Report")
    assert invalid["ok"] is False
