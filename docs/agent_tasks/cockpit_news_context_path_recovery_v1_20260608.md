---
job_id: cockpit_news_context_path_recovery_v1_20260608
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_news_context_path_recovery_v1_20260608.md
  - financial-engine_v2/cockpit/core/config.py
  - financial-engine_v2/cockpit/core/tools.py
  - financial-engine_v2/cockpit/ui/app.py
  - financial-engine_v2/backend/app/services/cockpit_service.py
  - financial-engine_v2/cockpit/tests/test_config_router_mode.py
  - financial-engine_v2/scripts/test_cockpit_tools_additional_context.py
  - reports/agent_jobs/cockpit_news_context_path_recovery_v1_20260608/README.md
  - reports/agent_jobs/cockpit_news_context_path_recovery_v1_20260608/status.json
  - reports/agent_jobs/cockpit_news_context_path_recovery_v1_20260608/validation.json
  - reports/agent_jobs/cockpit_news_context_path_recovery_v1_20260608/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_news_context_path_recovery_v1_20260608
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
github_mutation_allowed: false
---

# Cockpit News Context Path Recovery

## Objective

Recover the useful portion of the preserved `COCKPIT_NEWS_CONTEXT_CANDIDATE`
stash without applying the stale branch wholesale. Make Cockpit's effective
news-context path follow the current nightly news artifact environment and make
the existing SQLite fallback reachable when backend RAG is unavailable.

## Scope

Mode: SAFE_EXTENSION.

Allowed runtime surfaces are limited to Cockpit config path resolution, ToolRouter
news-context fallback wiring, and focused tests. The current architecture keeps
Qdrant/backend RAG as the preferred news route; this task must not weaken
local-news honesty guards or relabel unverified context as `claim_verified`.

## Hard Stops

- Do not apply `stash@{0}` wholesale.
- Do not modify `cockpit-ui`, dependencies, package locks, loose root notes, or
  unrelated task cards.
- Do not mutate DB, Qdrant, Redis, news stores, source PDFs, prompts, gold labels,
  model/GPU config, or production data.
- Do not run broad extraction, broad backfill, random samples, or ticker-universe
  extraction.
- Do not create, edit, label, comment on, close, or reopen GitHub issues.
- Do not clean, drop, pop, or overwrite stashes.
- Treat task-card validation, focused tests, JSON parse, `git diff --check`, and
  task-card `check-diff` failures as blockers.

## Required Output

- Effective config support for `COCKPIT_NEWS_DB_PATH`, `TENN_NEWS_CONTEXT_DB`,
  and `TENN_NEWS_ARTIFACT_ROOT` for `rag.news_context.db_path`.
- ToolRouter construction that receives `rag.news_context.db_path` and
  `corpus_filter` in both Cockpit UI and backend service paths.
- Direct news-context fallback to existing SQLite context when backend RAG is
  unavailable and a configured path/ticker is present.
- Focused tests for path override precedence and SQLite fallback behavior.
- Report with validation results and explicit statement that the preserved stash
  remains untouched.
