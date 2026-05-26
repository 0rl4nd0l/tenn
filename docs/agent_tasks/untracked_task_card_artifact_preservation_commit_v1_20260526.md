---
job_id: untracked_task_card_artifact_preservation_commit_v1_20260526
lane: Evaluation
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md
  - docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md
  - docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md
  - docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/runtime_reload_trace.json
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/diff-check.json
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/README.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/status.json
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/issue_drafts.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/duplicate_check.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/data_missing.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/diff-check.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/README.md
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/status.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/classification_matrix.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/duplicate_search_matrix.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/artifact_inventory.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/validation_results.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/diff-check.json
  - reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/README.md
  - reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/status.json
  - reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/committed_files.json
  - reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/validation_results.json
  - reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: artifact_preservation_commit
production_data_access: false
---

# Untracked Task-Card Artifact Preservation Commit

Mode detail: scoped repo-hygiene artifact preservation commit.

## Objective

Commit the two issue #94 target task cards and their matching report bundles,
plus the issue #94 classification task card and report bundle that proves the
preservation path.

## Lane

- Requested primary lane: Repo Hygiene.
- Validator lane: Evaluation, because the current task-card validator accepts
  only Financial Truth, Evaluation, Provenance, Query Orchestration, Memory,
  and Reporting.
- Supporting lanes: Reporting, Evaluation.

## Commit Scope

Commit these task-card/report artifact groups only:

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/`
- `docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md`
- `reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/`
- this task card and its report bundle

## Dirty Context Only

`docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md` is included
in `allowed_files` only because it is pre-existing dirty context visible in the
shared checkout. It is not part of this preservation commit and must not be
staged, edited, moved, deleted, reset, stashed, or cleaned by this task.

## Allowed Scope

- Create this task card and report bundle.
- Stage and commit only the exact preservation artifact set listed above.
- Use `git add -f` for ignored `reports/` paths that are part of the exact
  preservation artifact set.
- Read-only inspect GitHub issue #94 and adjacent issue coverage if needed.

## Forbidden

- Product/backend/frontend/runtime code changes.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label changes.
- Runtime, model, GPU, or service config edits.
- GitHub issue edits, comments, closure, or PR creation.
- Branch delete, prune, reset, stash, rebase, or merge.
- Deleting, cleaning, stashing, resetting, or moving any untracked task card.
- Staging or committing `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`.
- Unrelated dirty work.

## Required Output

Write report artifacts under:

`reports/agent_jobs/untracked_task_card_artifact_preservation_commit_v1_20260526/`

Required artifacts:

- `README.md`
- `status.json`
- `committed_files.json`
- `validation_results.json`
- `diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md`
- JSON validation for report artifacts
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md`
- Verify staged file list exactly matches this preservation task, excluding the dirty-context-only GitHub issue-creation card
- Commit with milestone protocol
- `python3 scripts/agent_job_contract.py check-diff --no-write-report docs/agent_tasks/untracked_task_card_artifact_preservation_commit_v1_20260526.md`
- Release registry claim
- Final git status

## Acceptance Criteria

- The two issue #94 target task cards are durably committed with matching report bundles.
- The issue #94 classification card and report bundle are durably committed.
- This preservation task card and report bundle are committed.
- The pre-existing GitHub issue-creation task card remains untouched and uncommitted.
- No destructive git action is performed.
- No product, runtime, data, or unrelated source file is touched.

## Hard Stops

- Any need to delete, stash, reset, clean, move, or commit the dirty-context-only GitHub issue-creation task card.
- Active registry conflict that cannot be handled safely.
- Staged files include any file outside the exact preservation artifact set.
- Any product, runtime, or data mutation requirement.
