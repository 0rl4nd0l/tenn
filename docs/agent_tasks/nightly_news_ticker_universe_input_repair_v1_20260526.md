---
job_id: nightly_news_ticker_universe_input_repair_v1_20260526
lane: Query Orchestration
requested_primary_lane: Runtime
supporting_lanes:
  - Reporting
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_REQUEST_FIX_ISSUE_114_20260526
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526
allowed_files:
  - docs/agent_tasks/nightly_news_ticker_universe_input_repair_v1_20260526.md
  - docs/agent_tasks/nightly_news_ingest_and_lockup_repair_v1_20260526.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - financial-engine_v2/scripts/nightly_news.sh
  - financial-engine_v2/data/raw/asx_ticker_universe.txt
  - reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526/**
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/**
---

# Nightly News Ticker Universe Input Repair

## Objective

Resolve #114 by restoring a deterministic ASX ticker universe input at the
canonical path used by `scripts/fetch_daily_news.py` and the scheduled nightly
news command.

## Scope

- Confirm the missing input from current repo state.
- Restore the canonical ticker file from an existing local Tenn runtime copy
  only after source hash and content checks.
- Make the nightly script pass the resolved ticker file explicitly.
- Validate with a no-write fetch dry-run.

## Forbidden

- No live news fetch.
- No Qdrant, SQLite news store, memo, or memory mutation.
- No scheduler or service mutation.
- No broad ticker regeneration from an external or unverified source.
