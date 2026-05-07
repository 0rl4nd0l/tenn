---
job_id: query_legacy_chat_envelope_preserve_merge_back_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/query_legacy_chat_envelope_preserve_merge_back_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_merge_from_integration_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_integration_v1.md
  - financial-engine_v2/backend/app/routes/chat.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_chat_route.py
  - reports/agent_jobs/query_legacy_chat_envelope_integration_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_merge_from_integration_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_preserve_merge_back_v1/**
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/query_legacy_chat_envelope_preserve_merge_back_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Merge `integrate/query-legacy-chat-envelope-merge-into-preserve-v1` into the preserve branch/worktree only if fresh preflight proves it is safe.

# Hard boundaries

Do not touch:
- Cockpit UI
- source drawer UI
- marketplace files
- ingestion
- Qdrant
- `news.sqlite`
- memory DBs
- financial truth / extraction
- deep research
- retrieval ranking
- unrelated dirty/untracked files

Do not stage or commit unrelated task-card files, reports, prompt zips, Cockpit UI/design/export files, marketplace files, or backend import-validity task files.

If any dirty/untracked/deleted file overlaps this task's allowed files or would be swept into the merge commit, STOP and report only.

# Required preflight

From the preserve worktree, report:
- repo path
- branch
- HEAD
- `git status --short --untracked-files=all`
- `git worktree list`
- recent commits
- active task card state
- registry/list-active state if supported
- whether active registry locks overlap Query Orchestration / Provenance / Reporting or touched files
- whether `920a001`, `d86321f`, `bcdb57d`, or `ad1caa2` are already contained in preserve HEAD
- dirty/untracked/deleted files classified by lane
- overlap between dirty files and this task's allowed files

# Required hard stops

STOP and write report only if:
- preserve is not on the expected preserve branch/worktree
- registry shows active overlapping work
- dirty/untracked/deleted files overlap allowed files
- merge would modify files outside allowed_files
- merge conflicts occur
- task-card validation fails
- check-diff fails
- validation cannot run for environment reasons
- any Cockpit UI/design/marketplace/news/extraction/memory files would be staged

# Allowed work

If and only if preflight is safe:
1. merge `integrate/query-legacy-chat-envelope-merge-into-preserve-v1` into preserve
2. preserve the merge/report artifacts
3. run focused validation
4. commit only the allowed files produced by this merge-back task
5. write final report under `reports/agent_jobs/query_legacy_chat_envelope_preserve_merge_back_v1/`

# Validation

Run:
- task-card validation
- registry list-active / claim / release if supported
- `git diff --check`
- `python -m pytest financial-engine_v2/backend/tests/test_chat_route.py -q`
- `python -m pytest financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`
- `python -m pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`
- `ruff check financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_chat_route.py`
- task-card check-diff

Do not attempt to fix the known broader `app.models.companies` collection blocker.

# Final report

Write:
`reports/agent_jobs/query_legacy_chat_envelope_preserve_merge_back_v1/README.md`

Include:
- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- branch / HEAD before and after
- merge command used
- files changed
- files intentionally not touched
- dirty/untracked/deleted file classification
- registry status
- validation commands and exact results
- final git status
- final commit hash if merge succeeded
- whether preserve now contains `920a001` / equivalent merge
- remaining blockers
- Project Memory save recommendation
