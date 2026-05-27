---
job_id: pr39_ci_split_audit_preservation_review_v1_20260527
lane: Reporting
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527
production_data_access: false
allow_audit_code_changes: true
github_mutation_allowed: false
issue_number: 105
pr_number: 39
allowed_files:
  - docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/README.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/status.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/dirty_work_matrix.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/child_task_priority.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/preservation_recommendation.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/diff-check.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/**
allowed_repo_files:
  - docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/**
read_only_inspection_allowed:
  - docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
  - current git status/diff metadata
  - registry/list-active/check-overlap outputs
  - "PR #39 and issue #105 GitHub state, if gh is available"
forbidden:
  - editing PR39 audit artifacts unless a later explicit preservation task allows it
  - implementing or fixing any of the 13 clusters
  - editing product/backend/frontend/runtime/test/dependency/workflow files
  - cleaning, stashing, resetting, deleting, restoring, or overwriting unrelated dirty work
  - committing, merging, rebasing, cherry-picking, force-pushing, or closing GitHub issues
  - production DB/Qdrant/news/memory access
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - runtime/model/GPU/service config
---

# PR #39 CI Split Audit Preservation Review

Mode detail: result review and audit-only preservation planning for the
completed `pr39_lint_and_test_failure_cluster_split_v1_20260526` job.

## Objective

Make the issue #105 audit result safely reviewable and durable without
implementing PR #39 child fixes, editing prior PR39 audit artifacts, or touching
unrelated dirty work.

## Scope

- Capture current branch, HEAD, worktree, git status, recent commits, worktree
  list, and registry state.
- Validate this task card, check registry overlap, claim only if safe, and
  release before closeout.
- Inspect the prior issue #105 task card and report bundle read-only.
- Parse prior JSON artifacts and generated JSON artifacts.
- Classify current dirty/untracked/ignored files by likely lane and ownership
  without opening or changing unrelated work more than needed.
- Write only this preservation-review task card and report bundle.

## Required Outputs

- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/README.md`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/status.json`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/dirty_work_matrix.json`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/child_task_priority.md`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/preservation_recommendation.md`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/diff-check.json`

## Forbidden

- Product, backend, frontend, runtime, test, dependency, workflow, package,
  lockfile, parser routing, extraction prompt, gold-label, canonical financial
  truth, runtime/model/GPU/service config, or child-fix changes.
- Production DB, Qdrant, news, memory, service, or GitHub mutation.
- Commit, merge, rebase, cherry-pick, force-push, close issue, create issue,
  label, milestone, project, or comment mutation.
- Cleaning, stashing, resetting, deleting, restoring, overwriting, or otherwise
  resolving unrelated dirty work.
- Editing the completed PR39 audit task card or its report artifacts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md --repo-root .`
- Registry claim only if safe and supported, release before closeout.
- JSON parse validation for generated JSON and prior issue #105 JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md --repo-root .`

## Hard Stops

- High registry/file collision on this task's allowed files.
- Prior issue #105 artifacts are missing and cannot be inspected.
- A forbidden surface becomes required.
- Any need to clean, stash, reset, delete, restore, or overwrite unrelated work.
- Any need to edit product/runtime/test/dependency/workflow files.
- Any need to mutate GitHub or close issues without explicit approval.
- Validation cannot run and cannot be honestly marked `DATA_MISSING`.
