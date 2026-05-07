---
job_id: tenn_agent_mcp_v0_clean_integration_20260507
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507
allowed_files:
  - docs/agent_tasks/tenn_agent_mcp_v0_clean_integration_20260507.md
  - docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/**
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/README.md
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/diff-check.json
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/status.json
  - reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/validation.json
  - reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507/**
  - reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507/README.md
  - reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507/diff-check.json
  - reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507/status.json
  - tools/tenn_agent_mcp/**
  - tools/tenn_agent_mcp/README.md
  - tools/tenn_agent_mcp/__init__.py
  - tools/tenn_agent_mcp/__main__.py
  - tools/tenn_agent_mcp/server.py
  - tests/tools/tenn_agent_mcp/**
  - tests/tools/tenn_agent_mcp/test_server.py
---

# Task

Integrate the existing Tenn Agent MCP V0 scaffold commit `9911b9d0835d` into a fresh integration worktree from the preserve branch.

# Allowed work

- Apply/cherry-pick the single MCP scaffold commit.
- Preserve the force-added ignored scaffold/report/tool/test files intentionally.
- Run targeted MCP scaffold validation.
- Write final integration report.

# Not allowed

- Do not modify dirty preserve worktree files.
- Do not touch backend/Cockpit/runtime/financial truth/Qdrant/news/memory/extraction/gold labels.
- Do not create HTTP/Tailscale adapter.
- Do not add production data access.
- Do not run real nested Codex launch.
- Do not auto-merge to preserve/main.

# Validation

Run targeted MCP scaffold validation and task-card check-diff.

# Final report

Write final report under:
`reports/agent_jobs/tenn_agent_mcp_v0_clean_integration_20260507/README.md`

If repo validator requires additional fields or formatting, adapt minimally and report the adaptation.
