---
job_id: tenn_agent_mcp_v0_merge_readiness_audit_20260507
lane: Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/tenn_agent_mcp_v0_merge_readiness_audit_20260507
allowed_files:
  - docs/agent_tasks/tenn_agent_mcp_v0_merge_readiness_audit_20260507.md
  - reports/agent_jobs/tenn_agent_mcp_v0_merge_readiness_audit_20260507/**
---

# Task

Audit merge-readiness for isolated Tenn Agent MCP V0 scaffold commit `9911b9d0835d`.

# Allowed writes

- This task card.
- Final report under `reports/agent_jobs/tenn_agent_mcp_v0_merge_readiness_audit_20260507/`.

# Allowed reads

- Git status/log/worktree/branch information.
- Commit `9911b9d0835d`.
- Branch `safe/tenn-agent-mcp-v0-audit-scaffold-20260507`.
- Existing task-card, registry, hook, tools, tests, and report paths relevant to the MCP scaffold.
- Dirty/untracked file list in the target preserve worktree.

# Not allowed

- Do not merge.
- Do not cherry-pick.
- Do not commit.
- Do not move/delete/archive dirty files.
- Do not edit existing task cards except this audit card.
- Do not modify MCP scaffold code.
- Do not create HTTP/Tailscale adapter.
- Do not touch backend/Cockpit/runtime/financial truth/Qdrant/news/company memory/market memory/extraction/gold labels.
- Do not access production data.

# Final report

Write:

`reports/agent_jobs/tenn_agent_mcp_v0_merge_readiness_audit_20260507/README.md`

If the repo requires additional task-card fields, adapt minimally and report the adaptation.
