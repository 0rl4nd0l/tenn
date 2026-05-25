---
job_id: a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525
title: A2M news projection canonical integration and status reporting controller
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
mutation_mode: safe_extension
requested_mutation_mode: controller_safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525
allowed_files:
  - docs/agent_tasks/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525.md
  - docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md
  - docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md
  - docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md
  - docs/agent_tasks/a2m_news_projection_status_reporting_safe_extension_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/diff-check.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/a2m_evidence_route_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/diff-check.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/news_projection_path_map.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/projection_gap_register.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/recommended_child_task_card.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/diff-check.json
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_next_fix_decision.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_readonly_smoke_matrix.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status_reporting_gap_register.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/diff-check.json
---

# A2M News Projection Canonical Integration and Status Reporting Controller

## Objective

Integrate the parked A2M audit and read-only smoke controller commits into
canonical `/home/l4nd0/tenn` if current repo evidence proves exact-file safety,
then run only the smallest safe status/reporting follow-up.

## Source Commits

- `2d1e810bcb978cc062d5de81d2c6b6198a76b8a4`
- `b47d0497d24ec8dce5bf3e75c314b5c3a758ef7c`

## Boundaries

- Do not touch, move, clean, stash, reset, or commit the known foreign task
  cards:
  - `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
  - `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`
- Do not run ingestion, backfill, reindex, resync, projection rebuild, news
  refresh, database repair, Qdrant mutation, SQLite mutation, alias
  canonicalization, route data-flow changes, runtime restarts, Docker changes,
  systemd changes, cron changes, env changes, or model/GPU routing changes.
- Do not claim that A2M canonical SQLite projection is fixed.

## Validation

- Validate this task card.
- Run registry `list-active` and `check-overlap`.
- Inspect parked worktree state and exact commit file lists before integration.
- Cherry-pick with `-x` only if exact paths are disjoint from current canonical
  dirt.
- Validate integrated task cards and generated JSON artifacts.
- Run `git diff --check` and task-card `check-diff`; classify warnings for the
  two known foreign task cards as preserved external work, not owned changes.
- Write controller `README.md` and `status.json`.
