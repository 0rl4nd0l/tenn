---
job_id: query_legacy_chat_envelope_refresh_preserve_merge_back_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/query_legacy_chat_envelope_refresh_preserve_merge_back_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_refresh_candidate_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_integration_v1.md
  - docs/agent_tasks/query_legacy_chat_envelope_merge_from_integration_v1.md
  - financial-engine_v2/backend/app/routes/chat.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_chat_route.py
  - reports/agent_jobs/query_legacy_chat_envelope_integration_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_integration_v1/README.md
  - reports/agent_jobs/query_legacy_chat_envelope_integration_v1/diff-check.json
  - reports/agent_jobs/query_legacy_chat_envelope_integration_v1/status.json
  - reports/agent_jobs/query_legacy_chat_envelope_merge_from_integration_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_merge_from_integration_v1/README.md
  - reports/agent_jobs/query_legacy_chat_envelope_merge_from_integration_v1/diff-check.json
  - reports/agent_jobs/query_legacy_chat_envelope_merge_from_integration_v1/status.json
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_candidate_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_candidate_v1/README.md
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_candidate_v1/diff-check.json
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_candidate_v1/status.json
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/**
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/README.md
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/diff-check.json
  - reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/status.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Merge `integrate/query-legacy-chat-envelope-refresh-candidate-v1` into preserve only if registry and worktree checks are clean.

# Hard boundaries

Do not touch:
- cockpit-ui/**
- marketplace files
- source drawer UI
- ingestion
- Qdrant
- news.sqlite
- memory DBs
- financial truth / extraction
- deep research
- retrieval ranking
- unrelated task cards
- dirty-preserve classification artifacts
- docs/claude/STATE.md unless already required by repo hook and explicitly within allowed diff

Do not stage or commit unrelated untracked task cards.

# Required preflight

From the preserve worktree, report:
- repo path
- branch
- HEAD
- git status --short --untracked-files=all
- git worktree list
- recent commits
- active task card state
- registry/list-active state
- whether active registry locks remain for:
  - cockpit_home_live_wiring_v1
  - dirty_task_card_classification_for_mcp_unblock_20260507
- whether any active lock overlaps Query Orchestration / Provenance / Reporting or touched files
- whether commit 487edc1a9873923428f11536f19c6212546487c0 is already contained in preserve
- dirty/untracked/deleted files classified by lane
- overlap between dirty files and this task's allowed files
- preview of merge diff from refreshed candidate into preserve

# Hard stops

STOP and report only if:
- active overlapping registry locks remain
- preserve worktree dirty files overlap allowed files
- merge preview includes cockpit-ui/**
- merge preview includes marketplace/source drawer/ingestion/Qdrant/news/memory/extraction/deep research/retrieval ranking
- merge preview deletes dirty-preserve classification artifacts
- task-card validation fails
- merge conflicts occur
- check-diff fails
- validation cannot run

# Allowed work

If and only if preflight is safe:
1. merge `integrate/query-legacy-chat-envelope-refresh-candidate-v1` into preserve
2. stage only allowed files
3. commit the merge-back
4. write final report under reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/
5. run validation

# Validation

Run:
- task-card validation
- registry list-active / check-overlap / claim / release if supported
- git diff --check
- python -m pytest financial-engine_v2/backend/tests/test_chat_route.py -q
- python -m pytest financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q
- python -m pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q
- ruff check financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_chat_route.py
- task-card check-diff

Do not fix the known broader app.models.companies collection blocker.

# Final report

Write:
reports/agent_jobs/query_legacy_chat_envelope_refresh_preserve_merge_back_v1/README.md

Include:
- Confirmed facts
- Inferred facts
- DATA_MISSING
- branch / HEAD before and after
- merge command used
- final commit hash if merge succeeded
- files changed
- proof no cockpit-ui files were touched
- proof dirty-preserve classification artifacts were not deleted
- files intentionally not touched
- registry status before/after
- validation commands and exact results
- final git status
- whether preserve now contains the refreshed candidate
- remaining blockers
- Project Memory save recommendation
