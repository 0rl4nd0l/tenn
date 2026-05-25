---
job_id: a2m_news_projection_status_reporting_safe_extension_v1_20260525
title: A2M news projection status reporting safe extension
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525
allowed_files:
  - docs/agent_tasks/a2m_news_projection_status_reporting_safe_extension_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status_reporting_gap_register.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/diff-check.json
---

# A2M News Projection Status Reporting Safe Extension

## Objective

Publish a bounded status/report artifact that makes A2M route health honest:
Qdrant-backed retrieval can be OK while canonical NVMe SQLite projection is
missing and legacy `/mnt/sdb2` SQLite remains provenance only.

## Candidate Files

No backend, Cockpit, route, test, parser, extraction, DB, Qdrant, Docker,
systemd, cron, env, runtime, model, GPU, or UI implementation files are
candidate files in this run. The implementation is restricted to this task card
and report artifacts under this job's output directory.

## Required Health Labels

- `qdrant_retrieval: ok`
- `canonical_sqlite_projection: missing`
- `legacy_sqlite_projection: evidence_present_not_current_consumer`
- `cockpit_query_route: ok_via_rag_query`
- `cockpit_status_routes: missing_404`
- `chat_synthesis: DATA_MISSING`
- `projection_repair: not_run`

## Boundaries

- Do not run ingestion, backfill, reindex, resync, projection rebuild, news
  refresh, or route behavior changes.
- Do not mutate Qdrant, SQLite, Postgres, Tenn memory, company memory, market
  memory, thesis memory, or production data.
- Do not copy, symlink, or alias legacy DBs into canonical paths.
- Do not canonicalize ticker/company aliases or change source-label semantics.
- Do not start, stop, restart, rebuild, reload, or reconfigure services.

## Validation

- Validate this task card.
- Run registry `list-active` and `check-overlap`.
- Validate generated JSON artifacts.
- Run `git diff --check`.
- Run task-card `check-diff`; if it reports only parent-controller or known
  foreign task-card dirt outside this child allowlist, classify that as
  preserved external work rather than child implementation scope.
