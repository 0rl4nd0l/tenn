---
job_id: marketindex_headed_recovery_reporting_current_base_v2_20260627
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md
  - financial-engine_v2/scripts/full_history_ticker_sync.py
  - financial-engine_v2/scripts/marketindex_recovery_reporting.py
  - financial-engine_v2/scripts/resume_pending_downloads.py
  - financial-engine_v2/scripts/test_full_history_ticker_sync_env.py
  - financial-engine_v2/scripts/test_marketindex_recovery_reporting.py
  - financial-engine_v2/scripts/test_resume_pending_extraction_failures.py
  - scripts/backfill_missing_universe_announcements.py
  - scripts/test_backfill_missing_universe_announcements.py
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/README.md
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/STATE.md
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/VALIDATION.md
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/REVIEW.md
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/PR_BODY.md
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/status.json
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/validation.json
  - reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/marketindex_headed_recovery_reporting_current_base_v2_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NONE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/entrypoints.md
docs_changed: []
docs_followup: NONE
reason: "Issue #279 asks for clearer operator-facing reports for MarketIndex headed recovery blockers without changing the blocking behavior or starting runtime services."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused script/reporting contract change with current-base port of preserved stale work and unit tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; scope is narrow and source-local."
escalation_needed: false
---

# MarketIndex Headed Recovery Reporting

## Objective

Close issue #279 by making normal operator-facing reports explicit when
MarketIndex documents are blocked pending headed recovery.

## Scope

- Port the useful prior work from the stale
  `/home/l4nd0/tenn-issue279-marketindex-headed-recovery-reporting-v1-20260626`
  worktree onto current canonical.
- Add deterministic MarketIndex headed-recovery report metadata.
- Add `requires_headed_recovery_count` and recommended command fields to the
  resume and full-history report surfaces.
- Surface child-report metadata in the missing-universe wrapper when it embeds a
  fresh full-history report.
- Add focused unit tests for the helper and report contracts.

## Hard Stops

- Do not run live document backfills, recovery commands, service starts, browser
  automation, or full runtime smoke tests.
- Do not mutate DB, source PDFs, Qdrant, Redis, news stores, memory, gold
  labels, extraction prompts, model/GPU config, service config, or production
  data.
- Do not change MarketIndex blocking policy or introduce a headless bypass.
- Do not merge, rebase, reset, stash, clean, delete branches, or close issues
  except through the final reviewed PR/issue closeout path.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Focused unit tests for the MarketIndex report helper.
- Focused resume/full-history/wrapper unit tests.
- Targeted Ruff check when available through `uv`.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
