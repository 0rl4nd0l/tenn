---
job_id: legacy_worker_tasks_quarantine_rebase_review_v1_20260608
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md
  - financial-engine_v2/worker/app/tasks.py
  - financial-engine_v2/backend/tests/test_architecture_invariants.py
  - reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/README.md
  - reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/status.json
  - reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/validation.json
  - reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/diff-check.json
  - reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/code_review.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608
mutation_mode: safe_extension
production_data_access: false
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Provenance
  - Reporting
github_tracking:
  source_issue: 267
  branch_review_issue: 327
---

# Legacy Worker Task Quarantine Rebase Review

## Summary

Replay the parked local legacy worker quarantine branch onto current `origin/migration/clean-runtime-baseline-reconstruct-v1`, validate the exact repo-control surface, and publish a draft PR for review.

## Scope

- Keep `financial-engine_v2/worker/app/tasks.py` fail-closed.
- Preserve/add architecture invariant coverage proving the deprecated module is not a runnable Celery task surface.
- Link the PR back to #327 as the visible branch-review path for the parked #267 remediation.

## Forbidden surfaces

- Production DB, Qdrant, news, memory, or canonical financial truth stores.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime/model/GPU/service config.
- Live worker start, stop, restart, or task execution.
- Branch delete, prune, reset, stash, merge, rebase, or cherry-pick outside this clean worktree.
- Unrelated dirty work in `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.

## Validation

- Task-card validate.
- Safe registry read-only probe or `DATA_MISSING` if unavailable.
- Focused py_compile.
- Static legacy-worker quarantine probe.
- Focused architecture invariant pytest.
- Celery task-registration smoke.
- Focused ruff if available.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff --no-write-report`.

## Hard Stops

- Replay requires changing surfaces outside `allowed_files`.
- Validation would require live worker execution or production data access.
- The deprecated worker module remains importable as runnable task code.
- GitHub remote/auth points to the wrong repository.
