---
job_id: marketplace_recency_promote_to_target_v1
lane: Reporting
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 3600
stale_after_seconds: 3600
output_dir: reports/agent_jobs/marketplace_recency_promote_to_target_v1
allowed_files:
  - docs/agent_tasks/marketplace_recency_promote_to_target_v1.md
  - reports/agent_jobs/marketplace_recency_promote_to_target_v1/README.md
  - reports/agent_jobs/marketplace_recency_promote_to_target_v1/status.json
  - reports/agent_jobs/marketplace_recency_promote_to_target_v1/diff-check.json
---

# Marketplace Recency Promote To Target V1

## Task

Promote the already validated `integrate/marketplace-recency-integration-v1` branch into `preserve/dirty-work-20260430T065748Z`.

## Mode

Safe extension / promotion only.

## Boundaries

Do not implement new Marketplace features.
Do not edit marketplace implementation files manually.
Do not overwrite, stash, delete, clean, or otherwise disturb unrelated dirty files in the target worktree.
Do not touch Cockpit Home, MCP, metric coverage, scanner/discovery, scraping adapters, memory, RAG, financial truth, extraction, or query orchestration.

## Required Checks

- Confirm branch, HEAD, target dirty status, worktrees, recent log, active registry jobs, and task-card validation.
- Compare `preserve/dirty-work-20260430T065748Z` with `integrate/marketplace-recency-integration-v1`.
- Proceed only if the target branch can fast-forward safely and dirty target files do not overlap marketplace recency files.
- Stop if the target branch advanced since `c22a6c06a999a33933906d3d262382d30706c197`.

## Validation

- After promotion, record recent log, status, registry state, and focused Marketplace validation when dependencies are available.
- Run `git diff --check` against the previous target HEAD when useful.
- Run task-card `check-diff`; if unrelated dirty files block it, preserve that evidence in the final report without changing those files.

## Final Report

Write `reports/agent_jobs/marketplace_recency_promote_to_target_v1/README.md`.

Include starting and final target HEAD, fast-forward result, dirty files left untouched, validation run/results, registry claim/release status, and whether Task C scanner instrumentation is safe to start.
