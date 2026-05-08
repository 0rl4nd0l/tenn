---
job_id: news_memo_qdrant_dirty_diff_classification_v1_20260508
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/news_memo_qdrant_dirty_diff_classification_v1_20260508.md
  - reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508/**
  - reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508/README.md
  - reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508/diff-check.json
  - reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508/status.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit and classify the dirty news memo / Qdrant loader diffs that blocked Cockpit Home Market Movers / News Snapshot v1.

No product/code mutation is allowed. Do not edit, stage, commit, revert, format, or run the dirty files.

# Known dirty paths

- financial-engine_v2/backend/app/services/news_memo_extractor.py
- scripts/load_news_to_qdrant.py

# Required preflight

Run read-only:

- git branch --show-current
- git rev-parse HEAD
- git status --short --untracked-files=all
- git diff --name-status
- git diff --stat
- git diff -- financial-engine_v2/backend/app/services/news_memo_extractor.py
- git diff -- scripts/load_news_to_qdrant.py
- git log --oneline --decorate -12
- git log --oneline --decorate -- financial-engine_v2/backend/app/services/news_memo_extractor.py scripts/load_news_to_qdrant.py
- git show --name-status --oneline HEAD
- git show --name-status --oneline c4ab78d
- git show --name-status --oneline 4ea8bfa
- git show --name-status --oneline 9aae854
- python3 scripts/agent_job_registry.py list-active, if available
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_memo_qdrant_dirty_diff_classification_v1_20260508.md, if available

If claim fails because dirty product/code files are outside this audit card, continue report-only and record the exact failure. Do not fix it.

# Read-only inspection allowed

You may inspect diffs, git history, and surrounding code. Do not run:

- news ingestion
- Qdrant sync/reindex
- memo extraction
- backfills
- embeddings jobs
- database migrations
- tests that mutate news/Qdrant state
- formatters/autofixers
- git add/commit/restore/checkout

# Classification required

For each dirty file, report:

- path
- exact diff summary
- changed lines and purpose
- likely lane
- likely owner/workstream
- whether it relates to:
  - memo extraction quality
  - Qdrant projection/loading
  - local news context
  - retrieval source labels
  - backfill batching
  - runtime diagnostics
  - accidental debug code
- whether it is safe to preserve
- whether it affects future Home News Snapshot work
- whether it changes ingestion/retrieval semantics
- whether it could affect source provenance or trusted labels
- recommended treatment:
  - preserve in dedicated commit
  - revert with approval
  - isolate in a worktree
  - leave blocked
  - DATA_MISSING
- confidence level

# Hard boundaries

Do not touch:

- financial-engine_v2/backend/app/services/news_memo_extractor.py
- scripts/load_news_to_qdrant.py
- Qdrant
- news.sqlite or news_articles.sqlite
- embeddings
- ingestion/backfill runtime
- query orchestrator
- Cockpit Home implementation
- financial truth
- company/market/thesis memory
- parser/gold labels

# Required report

Write:

reports/agent_jobs/news_memo_qdrant_dirty_diff_classification_v1_20260508/README.md

Include:

1. Branch / HEAD
2. Registry / lock status
3. Preflight summary
4. Dirty file table
5. Detailed diff classification: news_memo_extractor.py
6. Detailed diff classification: load_news_to_qdrant.py
7. Whether these changes block Market Movers / News Snapshot v1
8. Whether they should be preserved, reverted, isolated, or left blocked
9. What requires user approval
10. DATA_MISSING
11. Recommended next safe step
12. Final git status

# Validation

Run:

git diff --check

Run task-card check-diff if available. If it fails due existing dirty files, record exact output and do not fix it.

Definition of done:

- No product/code files changed.
- Dirty files remain untouched.
- Report written.
- Registry claim released if one was created.
- Final status recorded.
