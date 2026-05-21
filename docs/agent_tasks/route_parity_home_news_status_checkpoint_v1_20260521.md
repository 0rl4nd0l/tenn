---
job_id: route_parity_home_news_status_checkpoint_v1_20260521
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521
allowed_files:
  - docs/agent_tasks/route_parity_home_news_status_checkpoint_v1_20260521.md
  - docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/README.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/diff-check.json
  - reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/
  - reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/README.md
  - reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/diff-check.json
  - reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/status.json
---

# Route Parity Home/News Status Checkpoint v1 20260521

## Objective

Checkpoint the completed Route Parity Home/News Status Audit v1 20260521 task card and report artifacts so the active runtime worktree returns to a clean coordination state.

## Scope

- Preserve the existing route-parity audit task card.
- Preserve the existing route-parity audit report artifacts.
- Write a checkpoint report for this preservation action.
- Commit only the allowed task cards and report artifacts after validation passes.

## Explicit Non-Scope

- No backend source changes.
- No frontend source changes.
- No Cockpit UI source changes.
- No runtime config, Docker Compose, script, systemd, `.env`, data, database, Qdrant, news store, memory store, source registry, model, parser, extraction, Evaluation Spine, DuckDB, A2M, news retrieval, ASX classifier, sidecar, or dirty HDD preserve worktree changes.
- No route tests, live smoke, frontend Vitest, runtime service start, or backend service start as part of this checkpoint.

## Stop Conditions

- Stop if the active registry is not empty or overlapping.
- Stop if a staged file is outside the allowed task/report artifacts.
- Stop if any report artifact contains secrets or broad personal data dumps.
- Stop if the commit would include source, runtime, data, or config files.
- Stop if task-card validation fails.
- Stop if `check-diff` cannot be made clean without broadening beyond the route-parity task/report artifacts.
