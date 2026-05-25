---
job_id: repo_native_goal_schema_slice_review_integration_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/repo_native_goal_schema_slice_review_integration_v1_20260525.md
  - docs/agent_tasks/task_card_schema_notes_v1.md
  - docs/goals/README.md
  - docs/goals/_template.md
  - docs/goals/goal_schema_v1.json
  - reports/agent_jobs/status_schema_v1.json
  - scripts/agent_goal_contract.py
  - scripts/test_agent_goal_contract.py
  - reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/README.md
  - reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/status.json
  - reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/validation.json
  - reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/integration_readiness.json
  - reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement GitHub #69: review and integrate the repo-native goal schema slice
into the current safe audit branch.

# Scope

Review commit `cf825692cc8448820b6b493ad4baeeebabfcf9eb`, adopt only its
repo-native goal schema docs, status schema, changed-file-scoped validation
helper, and focused tests, then report the integration-readiness decision for
the live migration branch.

# Hard Boundaries

- Do not merge, cherry-pick, rebase, reset, stash, clean, or mutate the live
  migration branch.
- Do not touch product, backend, frontend, runtime, financial-truth, memory,
  Qdrant, DB, news, parser-routing, extraction, Docker, cron, systemd, model, or
  GPU files.
- Do not implement merge parking beyond the already separate merge parking
  validation slice.
- Do not implement Git-ref claims, auto-merge, auto-cherry-pick, auto-rebase,
  branch mutation, or broad CI enforcement.
- Keep validation explicit-file or changed-file scoped.
- Mutate only this task card, listed goal/status schema docs/helper/test files,
  and listed report artifacts.

# Required Outputs

- Current evidence that the referenced branch/commit exists locally or
  remotely.
- Changed-file scope compared against the original allowed files.
- Focused validation of helper/test behavior where feasible.
- Integration readiness decision for the live migration branch.
- Report artifacts under
  `reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/`.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
branch/commit existence checks, JSON checks, goal-contract explicit and
changed-file validation, focused tests, ruff where available, `git diff --check`,
and task-card check-diff.
