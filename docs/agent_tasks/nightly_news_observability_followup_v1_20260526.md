---
job_id: nightly_news_observability_followup_v1_20260526
lane: Reporting
requested_primary_lane: Runtime
supporting_lanes:
  - Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_REQUEST_FIX_ISSUE_112_20260526
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/nightly_news_observability_followup_v1_20260526
allowed_files:
  - docs/agent_tasks/nightly_news_observability_followup_v1_20260526.md
  - docs/agent_tasks/nightly_news_ingest_and_lockup_repair_v1_20260526.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - financial-engine_v2/scripts/nightly_news.sh
  - reports/agent_jobs/nightly_news_observability_followup_v1_20260526/**
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/**
---

# Nightly News Observability Follow-Up

## Objective

Resolve #112 by making `financial-engine_v2/scripts/nightly_news.sh` leave a
durable final-status artifact and capture stderr into the nightly log when the
job succeeds or fails.

## Scope

- Add bounded final-status reporting around the existing nightly phases.
- Preserve the existing fetch, sync, SQLite fallback refresh, and optional memo
  backfill behavior.
- Add no-mutation smoke controls for validation without running a live fetch or
  sync.

## Forbidden

- No cron or systemd mutation.
- No live backend restart.
- No production DB, Qdrant, news, memo, or memory mutation.
- No broad news repair or reindex.
