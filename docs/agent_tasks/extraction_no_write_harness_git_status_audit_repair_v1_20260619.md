---
job_id: extraction_no_write_harness_git_status_audit_repair_v1_20260619
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_git_status_audit_repair_v1_20260619.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619/README.md
  - reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619/status.json
  - reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619/validation.json
  - reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619/diff-check.json
  - reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619/PR_REVIEW.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_no_write_harness_git_status_audit_repair_v1_20260619
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_git_status_audit_repair_v1_20260619.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_git_status_audit_repair_v1_20260619.md
docs_followup: NONE
reason: "The task card documents the side-effect audit behavior repair for PR #379."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Small code-review repair touching one runner, focused tests, and report artifacts."
worker_model_allowed: false
worker_decision_limit: "No workers used for this focused review repair."
escalation_needed: false
---

# No-Write Harness Git Status Audit Repair

## Objective

Repair the PR #379 code-review finding that repo worktree changes recorded in
`git_status_after` do not currently fail the no-write side-effect contract.

## Scope

- Treat new non-report-local git status changes after replay as forbidden
  `repo_worktree_write` side effects.
- Preserve report-local artifact writes under the selected report directory.
- Add focused regression tests for non-report git changes and report-local
  artifact changes.
- Add a report-local validation and review bundle for this repair.

## Hard Stops

- Do not change extraction prompts, source PDFs, gold labels, DB, Qdrant, Redis,
  news, memory, runtime/model/GPU config, venvs, dependency files, or
  production data.
- Do not run broad extraction, count samples, backfills, dependency installs, or
  service starts.
- Do not merge, rebase, reset, stash, clean, delete branches/worktrees, or touch
  unrelated PR state.
- GitHub mutation is limited to pushing this repair commit to the existing PR
  #379 branch.

## Validation

- Task-card validate.
- Focused no-write replay unit tests.
- `py_compile`.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.
- Repeat read-only PR review.
