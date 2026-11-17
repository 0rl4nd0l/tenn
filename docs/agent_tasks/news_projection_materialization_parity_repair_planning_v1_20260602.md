---
job_id: news_projection_materialization_parity_repair_planning_v1_20260602
title: News projection materialization parity repair planning
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Runtime
  - Reporting
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602
allowed_files:
  - docs/agent_tasks/news_projection_materialization_parity_repair_planning_v1_20260602.md
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/README.md
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/status.json
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/parity_matrix.json
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/next_repair_decision.md
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/validation.json
  - reports/agent_jobs/news_projection_materialization_parity_repair_planning_v1_20260602/diff-check.json
---

# News Projection Materialization Parity Repair Planning

## Objective

Resolve the audit/planning deliverable for GitHub issue #83 without mutating
news stores, Qdrant, memory, canonical financial truth, runtime config, or live
services.

## Required Distinctions

- Qdrant-backed news retrieval state.
- Canonical SQLite projection file state.
- Legacy SQLite evidence state.
- Current news status route and reporting state, if already-running services
  expose it.
- Whether the next safe step is no-op, docs/status only, projection
  materialization, Qdrant repair, or a separate scheduler fix.

## Allowed Read-Only Surfaces

- Existing reports and task cards related to A2M/news projection parity.
- Existing docs/config describing the canonical news substrate.
- Local canonical and legacy SQLite files with read-only inspection only.
- Already-running local HTTP status/query endpoints, using safe read-only
  methods and short timeouts.
- Qdrant read-only collection/count/scroll probes only with vectors disabled,
  if an existing local service is already available.

## Forbidden

- No ingestion, backfill, resync, refresh, reindex, projection rebuild, DB copy,
  symlink workaround, or data repair.
- No Qdrant writes.
- No SQLite, Postgres, DB, news store, memory, company memory, market memory,
  thesis memory, or production-data writes.
- No source-label relaxation, ticker alias workaround, retrieval ranking change,
  backend route implementation, UI implementation, runtime/model/GPU/service
  config change, service start, stop, restart, reload, Docker, systemd, cron, or
  environment mutation.
- No claim that canonical SQLite projection is fixed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_projection_materialization_parity_repair_planning_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_projection_materialization_parity_repair_planning_v1_20260602.md`
- Claim and release the task card for implementation.
- JSON validation for generated artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_projection_materialization_parity_repair_planning_v1_20260602.md`

## Done Criteria

- The report identifies the current canonical projection source/target state or
  marks it `DATA_MISSING` with exact missing evidence.
- The report compares at least one affected ticker/article route across Qdrant,
  canonical projection paths, and legacy SQLite candidates where available.
- The report selects exactly one next safe step and splits any mutation into a
  separate approval-gated task.
- No forbidden mutation occurred.
