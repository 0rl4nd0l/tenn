---
job_id: untracked_task_card_preservation_classification_v1_20260526
lane: Evaluation
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md
  - docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md
  - docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/README.md
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/status.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/classification_matrix.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/duplicate_search_matrix.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/artifact_inventory.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/validation_results.json
  - reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: audit_first_preservation_classification
production_data_access: false
---

# Untracked Task-Card Preservation Classification

Mode detail: audit-first / preservation classification.

## Objective

Classify the two persistent unrelated untracked task cards identified by
GitHub issue #94 and recommend one exact preservation next action for each.
Also record any other current untracked task-card dirt discovered during
preflight as out-of-scope context.

## Lane

- Requested primary lane: Repo Hygiene.
- Validator lane: Evaluation, because the current task-card validator accepts
  only Financial Truth, Evaluation, Provenance, Query Orchestration, Memory,
  and Reporting.
- Supporting lanes: Reporting, Evaluation.

## Target Files

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

## Current Out-of-Scope Dirty Context

- `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`

This file is included in `allowed_files` only so registry and diff checks can
represent current dirty state without forcing cleanup. It is not one of the two
issue #94 target files and must not be edited except by a separately authorized
task.

## Allowed Scope

- Create this task card and the report bundle.
- Read-only inspect the target task-card files.
- Read-only inspect matching report bundles, task cards, GitHub issues, PRs,
  and local git history.
- Produce a classification and one recommended next action for each target file.
- Record out-of-scope dirty task-card context if it affects validation.

## Forbidden

- Product/backend/frontend/runtime file changes.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime, model, GPU, or service config edits.
- Deleting, cleaning, stashing, resetting, or moving any untracked task card.
- Editing the two target task cards.
- Committing the two target task cards before this audit proves the correct
  preservation path and the user separately authorizes it.
- Pull request creation.
- Branch delete, prune, reset, stash, rebase, or merge.
- Unrelated dirty work.

## Classification Choices

Each target task card must be classified as one of:

- valid uncommitted artifact to commit;
- already represented by committed report/issue/memory;
- stale but needs preservation elsewhere;
- foreign work to leave untouched;
- DATA_MISSING.

## Required Output

Write report artifacts under:

`reports/agent_jobs/untracked_task_card_preservation_classification_v1_20260526/`

Required artifacts:

- `README.md`
- `status.json`
- `classification_matrix.json`
- `duplicate_search_matrix.json`
- `artifact_inventory.json`
- `validation_results.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md` if safe
- duplicate GitHub issue/PR search
- JSON validation for report artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/untracked_task_card_preservation_classification_v1_20260526.md`
- release registry claim if one is created

## Acceptance Criteria

- Each target untracked task card is classified with evidence.
- Matching report bundles and GitHub issue coverage are checked.
- The report recommends one exact next action for each target file.
- No destructive git action is performed.
- No product, runtime, data, or unrelated source file is touched.

## Hard Stops

- Any need to delete, stash, reset, clean, move, or commit files.
- Active registry conflict that cannot be handled safely.
- Inability to prove whether a target task card is represented elsewhere.
- Any product, runtime, or data mutation requirement.
