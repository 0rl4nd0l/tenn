# Tenn Agent MCP

Local-first MCP scaffold for audit-only Tenn/Codex job orchestration.

Run over stdio:

```bash
python3 -m tools.tenn_agent_mcp --repo-root /path/to/tenn
```

The scaffold exposes only bounded task-card, registry, status, and report operations. It does not expose arbitrary shell execution and does not access Tenn runtime databases, Qdrant, news stores, memory stores, holdings, gold labels, source PDFs, extraction outputs, or live services.

## Tools

- `list_capabilities`: read-only server capability and security summary.
- `create_task_card`: token-gated creation of validated non-production task cards under `docs/agent_tasks/`.
- `list_active_jobs`: read-only wrapper around the shared Tenn agent-job registry.
- `launch_codex_audit`: token-gated, dry-run by default Codex audit launch planner for `audit_only` task cards.
- `get_agent_status`: read-only status lookup from `reports/agent_jobs/<job_id>/status.json` plus active registry records.
- `read_agent_report`: read-only bounded `README.md` fetch from `reports/agent_jobs/<job_id>/`.

## Security Defaults

- Local-first only.
- Stdio transport in this scaffold; future HTTP/SSE binding defaults are recorded as `127.0.0.1:8765`.
- Non-read tools require `TENN_AGENT_MCP_TOKEN`.
- `launch_codex_audit` is dry-run unless `dry_run=false` and `TENN_AGENT_MCP_ENABLE_LAUNCH=1`.
- Real launch uses a fixed Codex argv, not a caller-provided shell command.
- The launch tool only accepts `audit_only` task cards under `docs/agent_tasks/`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `TENN_AGENT_MCP_TOKEN` | unset | Required bearer token for non-read tools. |
| `TENN_AGENT_MCP_ENABLE_LAUNCH` | unset | Set to `1` to allow real Codex launch attempts. |
| `TENN_AGENT_MCP_HOST` | `127.0.0.1` | Reserved future local HTTP/SSE bind host. |
| `TENN_AGENT_MCP_PORT` | `8765` | Reserved future local HTTP/SSE port. |
