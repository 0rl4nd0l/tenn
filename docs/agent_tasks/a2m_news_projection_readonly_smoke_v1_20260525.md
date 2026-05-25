---
job_id: a2m_news_projection_readonly_smoke_v1_20260525
title: A2M news projection read-only smoke
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525
allowed_files:
  - docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_readonly_smoke_matrix.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_next_fix_decision.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/diff-check.json
---

# A2M News Projection Read-Only Smoke

## Objective

Prove the current user-visible A2M route state across Qdrant, canonical NVMe projection paths, legacy `/mnt/sdb2` projection paths, and Cockpit/query routes without data mutation.

## Required Distinctions

- Qdrant retrieval availability.
- Canonical SQLite projection availability.
- Legacy SQLite A2M evidence.
- Cockpit/query route reachability.
- Whether the current user-facing path can access A2M evidence.
- Whether the next fix is data repair, path repair, route/reporting change, projection rebuild planning, or no-op/defer.

## Allowed Read-Only Surfaces

- Existing A2M audit report artifacts.
- News/query retrieval code paths.
- Cockpit news/status/query BFF routes if present.
- SQLite path config and docs.
- Qdrant collection references.
- Local SQLite files with read-only inspection only.
- Qdrant read-only query only if an existing local service is already available.
- Curl only to already-running local endpoints when safe and non-mutating.

## Forbidden

- No ingestion, backfill, reindex, resync, projection rebuild, or news refresh.
- No Qdrant writes.
- No SQLite, Postgres, DB, news store, memory, company memory, market memory, thesis memory, or production-data writes.
- No copying or symlinking legacy DBs into canonical paths.
- No alias/entity-linking hacks or source-label trust changes.
- No Cockpit behavior changes.
- No service starts, stops, restarts, reloads, Docker, systemd, cron, env, model runtime, or GPU-routing changes.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`
- JSON validation for generated smoke artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`

## Done Criteria

- Smoke report and matrix clearly classify Confirmed, Inferred, Speculative, and DATA_MISSING evidence.
- Exactly one next task recommendation is selected.
- No forbidden mutation occurred.
