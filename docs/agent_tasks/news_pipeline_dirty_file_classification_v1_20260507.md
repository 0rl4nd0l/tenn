---
job_id: news_pipeline_dirty_file_classification_v1_20260507
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md
  - reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/**
  - reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/README.md
  - reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/diff-check.json
  - reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/status.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify unrelated dirty news-pipeline files currently present in the preserve worktree.

This is an audit-only repo hygiene task. Do not edit, format, stage, commit, revert, delete, or move dirty news-pipeline files. The only permitted writes are this task card and report artifacts under the approved output directory.

# Context

The previous Cockpit Home Portfolio Aggregation / Day Change v1 task reportedly landed at HEAD `93c1191a8e479cb564f1cd8c8f8989776186a245`, but reported that task-card check-diff was blocked by unrelated dirty news-pipeline files that appeared during the live-repo window. Codex did not touch or stage them.

Before any market movers/news/Home endpoint work, classify those files.

# Required Preflight

1. Print branch and HEAD.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Run recent log around Cockpit Home and news commits.
5. Validate this task card if repo tooling supports it.
6. Run registry/list-active if available.
7. Run registry/check-overlap if available.
8. Do not claim implementation. If registry supports audit-only claim, claim only this audit and release at the end.
9. Stop and report if another active job owns the same dirty news files.

# Audit Scope

Inspect dirty/untracked news-pipeline files read-only. For each dirty or untracked file, classify:

- path
- git status code
- likely lane
- likely owner/workstream
- whether it is staged or unstaged
- whether it appears intentional, generated, stale, accidental, or DATA_MISSING
- whether it belongs to news ingestion, news retrieval, Qdrant projection, entity linking, commentary, tests, runtime logs, reports, or unrelated surfaces
- whether it blocks market movers/Home news endpoint work
- whether it should be preserved, isolated, reviewed, reverted, archived, or left untouched
- whether it overlaps current Cockpit Home files

# Boundaries

Do not touch:

- news-pipeline dirty files
- Qdrant
- news.sqlite
- embeddings
- ingestion/backfill scripts
- entity linker code
- query orchestrator
- Cockpit Home implementation
- financial truth
- company memory
- market memory
- thesis memory
- parser/gold labels

Do not run:

- news ingestion
- Qdrant sync/reindex
- database migrations
- production data mutation
- formatting commands over dirty files
- `git add` for dirty news files
- `git checkout` or `git restore` on dirty news files
- `git commit` containing dirty news files

# Required Report

Write `reports/agent_jobs/news_pipeline_dirty_file_classification_v1_20260507/README.md` with:

1. Branch / HEAD
2. Task card path
3. Registry / lock status
4. Preflight summary
5. Dirty file table
6. Per-file classification
7. Which files are unrelated to Cockpit Home
8. Which files block future Home market movers/news work
9. Which files should be preserved/reviewed/reverted/isolated, with no action taken
10. DATA_MISSING
11. Recommended next safe step
12. Final git status
13. Project Memory save recommendation

# Validation

Run:

- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`

If check-diff reports dirty files outside this audit card, record that as the expected audit finding. Do not fix it.

# Definition Of Done

- No code files changed by this task.
- Dirty news files remain untouched.
- Report classifies every dirty/untracked file.
- Registry claim is released if one was created.
- Final status is recorded.
