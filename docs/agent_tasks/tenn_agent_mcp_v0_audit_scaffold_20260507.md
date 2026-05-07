---
job_id: tenn_agent_mcp_v0_audit_scaffold_20260507
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/**
  - tools/tenn_agent_mcp/**
  - tests/tools/tenn_agent_mcp/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Build a local-first Tenn Agent MCP V0/V1 scaffold for audit-only Codex job orchestration.

# Scope

Allowed:
- Inspect repo docs for task-card, registry, hook, and agent-control conventions.
- Create a minimal MCP server scaffold under `tools/tenn_agent_mcp/`.
- Add tests under `tests/tools/tenn_agent_mcp/` or `tools/tenn_agent_mcp/tests/` if repo convention prefers.
- Add README/docs under `tools/tenn_agent_mcp/`.
- Write final report under `reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/`.

Not allowed:
- Do not touch Tenn production/runtime DBs.
- Do not access or mutate financial truth, Qdrant, news.sqlite, company memory, market memory, holdings, gold labels, source PDFs, extraction outputs, or live runtime services.
- Do not modify core backend/Cockpit/extraction/query/news/memory code.
- Do not add auto-merge behavior.
- Do not add recursive self-launching agent loops.
- Do not launch nested Codex jobs during tests unless explicitly dry-run/mocked.
- Do not add broad framework dependencies to root project files without stopping and reporting.
- Do not use unrestricted shell execution as an MCP tool.

# Required Preflight

Run and report:
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- recent commits relevant to task-card/agent tooling
- whether AGENTS.md, CLAUDE.md, docs/agent_tasks, registry scripts, hooks, or check-diff tooling exist
- whether scripts/agent_job_registry.py or similar exists
- whether task-card enforcement exists
- whether Python/Node project conventions suggest best MCP implementation location
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn` if available
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md --repo-root /mnt/sdb2/home/l4nd0/tenn` if available

Claim the registry job only if safe.

# Hard Stops

Stop and report only if:
- registry overlap is found
- dirty files overlap the allowed surfaces or agent-control surfaces in a way that makes safe extension risky
- task-card validation fails
- backend runtime edits appear necessary
- production data access would be required
- collision risk becomes HIGH

# MCP Tools

Implement or scaffold these tools with strict schemas and safety checks:
- `list_capabilities`
- `create_task_card`
- `list_active_jobs`
- `launch_codex_audit`
- `get_agent_status`
- `read_agent_report`

# Security Requirements

The scaffold must preserve:
- local-first operation
- default bind host `127.0.0.1`
- configurable port with default `8765`
- bearer token required for non-read tools through `TENN_AGENT_MCP_TOKEN`
- no arbitrary shell tool
- no unrestricted filesystem read/write
- no production DB access
- no Tenn runtime mutation
- no Qdrant/news/company-memory/financial-truth access
- no auto-merge
- no dependency upgrades outside isolated MCP scaffold
- no recursive self-running loops
- dry-run default for Codex launch
- real launch requires `TENN_AGENT_MCP_ENABLE_LAUNCH=1`

# Validation

Run the smallest safe validation available:
- task-card validation/check-diff hook if repo supports it
- targeted unit tests for the new MCP scaffold
- ruff/format/lint on changed Python files if applicable
- `git diff --check`

Do not run production extraction, ingestion, Qdrant/news sync, live Tenn runtime mutation, database migrations, or real nested Codex launches in tests.

# Final Report

Write final report to:

`reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/README.md`

Report:
- branch and HEAD
- git status --short before and after
- worktree list
- task-card path and validation status
- registry/list-active status if available
- files changed
- tests/checks run with exact results
- what tools the MCP server exposes
- security model and hard refusals
- DATA_MISSING
- remaining risks
- next safe step
- whether `/save` is recommended
