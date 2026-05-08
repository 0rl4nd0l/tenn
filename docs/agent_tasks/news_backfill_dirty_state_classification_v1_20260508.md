---
job_id: news_backfill_dirty_state_classification_v1_20260508
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md
  - reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/**
  - reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md
  - reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/diff-check.json
  - reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/status.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify the dirty news/backfill state that blocked Cockpit Home Market Movers / News Snapshot v1.

This is audit-only. Do not edit, stage, commit, restore, delete, move, format, or run the dirty script.

# Known dirty/blocking paths from previous closeout

- docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md
- docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md
- scripts/backfill_missing_news_memos.py
- ignored reports under reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/
- ignored reports under reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/

# Required preflight

Run read-only:

- git branch --show-current
- git rev-parse HEAD
- git status --short --untracked-files=all
- git status --ignored --short --untracked-files=all -- reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507 reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507
- git worktree list
- python3 scripts/agent_job_registry.py list-active, if available
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_backfill_dirty_state_classification_v1_20260508.md, if available

Claim this audit only if safe. If claim fails because of dirty files, continue report-only and record the exact failure.

# Read-only inspection allowed

Use read-only commands only:

- git diff -- scripts/backfill_missing_news_memos.py
- git diff --stat -- scripts/backfill_missing_news_memos.py
- git log --oneline --decorate -- scripts/backfill_missing_news_memos.py
- git blame -- scripts/backfill_missing_news_memos.py
- git show --name-status --oneline HEAD
- git show --name-status --oneline 4ea8bfa
- git show --name-status --oneline 9aae854
- git diff --name-status HEAD
- git status --short --untracked-files=all

Do not run:

- scripts/backfill_missing_news_memos.py
- news ingestion
- memo extraction
- Qdrant sync/reindex
- database migrations
- embeddings jobs
- formatting/lint autofix
- tests that mutate local news state
- git add/commit/restore/checkout for dirty files

# Classification required

For each dirty/untracked/ignored artifact, classify:

- path
- git status
- likely lane
- likely owner/workstream
- staged/unstaged/untracked/ignored
- intentional/generated/stale/accidental/DATA_MISSING
- subsystem
- whether it blocks Cockpit Home Market Movers / News Snapshot v1
- whether it is safe to preserve
- whether it needs user approval before commit/revert/delete
- recommended next action

Special focus:

scripts/backfill_missing_news_memos.py

Classify whether the diff appears to belong to:
- 4ea8bfa milestone(news): constrain memo extraction output quality
- 9aae854 milestone(news): decouple memo enrichment from nightly ingest
- another active/unknown job
- local uncommitted operator work
- generated/accidental edit
- DATA_MISSING

# Hard boundaries

Do not touch:

- scripts/backfill_missing_news_memos.py
- news stores
- Qdrant
- embeddings
- ingestion scripts
- memo extraction runtime
- query orchestrator
- Cockpit Home implementation
- financial truth
- company/market/thesis memory
- parser/gold labels

# Required report

Write:

reports/agent_jobs/news_backfill_dirty_state_classification_v1_20260508/README.md

Include:

1. Branch / HEAD
2. Registry / lock status
3. Preflight summary
4. Dirty file table
5. Detailed classification of scripts/backfill_missing_news_memos.py
6. Classification of uncommitted task cards and ignored reports
7. What blocks Market Movers / News Snapshot v1
8. Safe cleanup/preservation options
9. What requires user approval
10. DATA_MISSING
11. Recommended next safe step
12. Final git status

# Validation

Run:

git diff --check

Run task-card check-diff if available, but if it fails due existing dirty files, record the exact output and do not fix it.

Definition of done:
- No product/code files changed.
- Dirty news script untouched.
- Report written.
- Registry claim released if one was created.
- Final status recorded.
