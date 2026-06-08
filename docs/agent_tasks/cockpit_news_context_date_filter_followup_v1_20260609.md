---
job_id: cockpit_news_context_date_filter_followup_v1_20260609
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_news_context_date_filter_followup_v1_20260609.md
  - financial-engine_v2/cockpit/core/tools.py
  - financial-engine_v2/cockpit/ui/app.py
  - financial-engine_v2/scripts/test_cockpit_tools_additional_context.py
  - financial-engine_v2/scripts/test_cockpit_chat_status_widgets.py
  - reports/agent_jobs/cockpit_news_context_date_filter_followup_v1_20260609/README.md
  - reports/agent_jobs/cockpit_news_context_date_filter_followup_v1_20260609/status.json
  - reports/agent_jobs/cockpit_news_context_date_filter_followup_v1_20260609/validation.json
  - reports/agent_jobs/cockpit_news_context_date_filter_followup_v1_20260609/diff-check.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_news_context_date_filter_followup_v1_20260609
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
github_mutation_allowed: false
---

# Cockpit News Context Date Filter Follow-Up

## Objective

Fix the two review warnings from the Cockpit news-context path recovery merge:
preserve `date_from` / `date_to` filtering in the direct SQLite fallback and
avoid misleading startup text when SQLite news fallback remains available
without a backend client.

## Scope

Mode: SAFE_EXTENSION.

Allowed runtime surfaces are limited to `ToolRouter.get_news_context()` /
SQLite news-context filtering and the Cockpit UI startup warning. This task
must not change Qdrant preference, news ingest behavior, local-news honesty
guards, data stores, prompts, labels, or extraction behavior.

## Hard Stops

- Do not mutate DB, Qdrant, Redis, news stores, source PDFs, prompts, gold
  labels, model/GPU config, or production data.
- Do not run broad extraction, broad backfill, random samples, ticker-universe
  extraction, or news ingest.
- Do not create, edit, label, comment on, close, reopen, or merge GitHub items.
- Do not clean, drop, pop, or overwrite stashes.
- Do not modify dependencies, package locks, `cockpit-ui`, unrelated task
  cards, or unrelated reports.
- Treat task-card validation, focused tests, JSON parse, `git diff --check`,
  and task-card `check-diff` failures as blockers.

## Required Output

- Direct SQLite news-context fallback honors `date_from` and `date_to` like the
  backend and reader fallback paths.
- Cockpit UI startup warning distinguishes backend-disabled behavior from
  SQLite news fallback availability.
- Focused tests cover date filtering and warning text.
- Report with validation results and explicit note that no data or GitHub
  mutations were performed.
