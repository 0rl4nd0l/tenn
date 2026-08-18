---
job_id: nightly_news_ingest_and_lockup_repair_v1_20260526
lane: Query Orchestration
requested_primary_lane: Runtime
supporting_lanes:
  - Reporting
  - Evaluation
  - Memory
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_REQUEST_FIX_ISSUES_112_114_115_20260526
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526
allowed_files:
  - docs/agent_tasks/nightly_news_ingest_and_lockup_repair_v1_20260526.md
  - docs/agent_tasks/nightly_news_ticker_universe_input_repair_v1_20260526.md
  - docs/agent_tasks/nightly_news_observability_followup_v1_20260526.md
  - docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - financial-engine_v2/scripts/nightly_news.sh
  - financial-engine_v2/data/raw/asx_ticker_universe.txt
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/README.md
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/status.json
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/validation.json
  - reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/diff-check.json
  - reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526/README.md
  - reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526/status.json
  - reports/agent_jobs/nightly_news_observability_followup_v1_20260526/README.md
  - reports/agent_jobs/nightly_news_observability_followup_v1_20260526/status.json
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/README.md
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/status.json
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/branch_matrix.json
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/github_activity.json
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/memory_candidates.md
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/next_day_handoff.md
  - docs/claude/STATE.md
---

# Nightly News Ingest And Lock-Up Repair

## Objective

Fix the user-approved batch:

- #114: restore deterministic ASX ticker universe availability for the nightly
  news fetch path.
- #112: add durable final-status observability and stderr capture for nightly
  news scheduling.
- #115: run the first report-only Codex nightly lock-up audit and produce the
  declared artifacts.

## Contract Boundary

- Target layer: Ingestion and operational observability for the news pipeline.
- Backend financial truth, extraction, canonical metrics, embeddings, vector
  dimensions, Qdrant contents, and Cockpit contested surfaces must not change.
- No live news fetch, Qdrant sync, DB reset, reindex, broad backfill, scheduler
  mutation, memory write, merge, rebase, reset, or stash is allowed.
- Validation must use no-write dry-run or temp-output smoke checks.

## Preserved Pre-Existing Dirt

`docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md` was
untracked before this batch. It is listed in `allowed_files` only so repo diff
gates can see and preserve it without blocking the approved batch. It must not
be edited, staged, or committed by this task.

## Required Outputs

- `reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/README.md`
- `reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/status.json`
- `reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/validation.json`
- `reports/agent_jobs/nightly_news_ingest_and_lockup_repair_v1_20260526/diff-check.json`
- The issue-specific report bundles for #112, #114, and #115.

## Validation

- Validate this task card and issue-specific task cards.
- Registry list-active, check-overlap, claim, and release.
- `bash -n financial-engine_v2/scripts/nightly_news.sh`.
- No-write fetch dry-run with the restored ticker universe.
- Temp-log nightly dry-run success smoke.
- Temp-log nightly failure smoke with a deliberately missing ticker file.
- JSON validation for generated status/report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
