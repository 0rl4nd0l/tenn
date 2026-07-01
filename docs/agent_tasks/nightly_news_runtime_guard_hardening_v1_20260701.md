---
job_id: nightly_news_runtime_guard_hardening_v1_20260701
lane: Query Orchestration
requested_primary_lane: Runtime
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_REQUEST_ENSURE_NEWS_AUTOMATION_DOES_NOT_REPEAT_20260701
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/nightly_news_runtime_guard_hardening_v1_20260701
allowed_files:
  - docs/agent_tasks/nightly_news_runtime_guard_hardening_v1_20260701.md
  - financial-engine_v2/scripts/nightly_news.sh
  - scripts/test_nightly_news_runtime_guard.py
  - docs/ops/news_baseline_policy.md
  - reports/agent_jobs/nightly_news_runtime_guard_hardening_v1_20260701/STATE.md
  - reports/agent_jobs/nightly_news_runtime_guard_hardening_v1_20260701/VALIDATION.md
  - reports/agent_jobs/nightly_news_runtime_guard_hardening_v1_20260701/diff-check.json
  - reports/agent_jobs/nightly_news_runtime_guard_hardening_v1_20260701/validation.json
---

# Nightly News Runtime Guard Hardening

## Objective

Prevent a repeat of the 2026-07-01 nightly news failure class where fetch could
run but downstream news sync stayed stale because required runtime prerequisites
were missing or stopped.

## Scope

- Make `financial-engine_v2/scripts/nightly_news.sh` fail closed when backend
  sync prerequisites are absent.
- Add a bounded Qdrant endpoint readiness check before live sync.
- Allow only one narrow self-heal path: start the existing configured Qdrant
  container if the endpoint is unavailable.
- Preserve the bounded `newspaper4k` daily RSS-only fetch defaults.

## Forbidden

- No Qdrant delete, wipe, collection recreation, broad reindex, or cleanup.
- No DB reset or schema migration.
- No cron, systemd, Docker compose env, or service config mutation.
- No provider switch, broad Playwright crawl, GitHub write, push, merge, rebase,
  reset, or stash.

## Validation

- Validate this task card.
- `bash -n financial-engine_v2/scripts/nightly_news.sh`
- Focused unit/static tests for the runtime guard.
- Existing news/Qdrant loader focused tests where practical.
- `git diff --check`
- Task-card `check-diff`.
