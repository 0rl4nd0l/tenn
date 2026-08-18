---
job_id: pr39_ci_audit_artifact_preservation_v1_20260527
lane: Evaluation
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md
  - docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md
  - docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/README.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/status.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/failure_clusters.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/child_task_proposals.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/pr39_merge_readiness.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/diff-check.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/README.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/status.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/dirty_work_matrix.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/child_task_priority.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/preservation_recommendation.md
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/diff-check.json
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/**
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/README.md
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/status.json
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/artifact_inventory.json
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/parking_recommendation.md
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/next_child_task_queue.md
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/diff-check.json
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/**
allowed_repo_files:
  - docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md
  - docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md
  - docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
  - reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/**
  - reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527
mutation_mode: safe_extension
requested_mutation_mode: audit_first_safe_preservation_only
production_data_access: false
github_mutation_allowed: false
issue_number: 105
pr_number: 39
---

# PR #39 CI Audit Artifact Preservation

Mode detail: AUDIT_FIRST / SAFE PRESERVATION ONLY.

## Objective

Make the completed issue #105 PR #39 CI failure-cluster audit evidence and the
follow-up preservation-review evidence durable, visible, and reviewable without
mixing unrelated dirty work.

## Lane

- Requested primary lane: Repo Hygiene.
- Validator lane: Evaluation, because the current task-card validator accepts
  only Financial Truth, Evaluation, Provenance, Query Orchestration, Memory,
  and Reporting.
- Supporting lanes: Evaluation and Reporting.

## Allowed Scope

- Create this task card and report bundle.
- Inspect the prior PR #39 / issue #105 task card and report bundle.
- Inspect the preservation-review task card and report bundle.
- Parse required JSON artifacts and record artifact visibility.
- Read-only inspect current GitHub PR #39, run state, and issue #105 if `gh`
  is available.
- Stage and commit only the allowed preservation task cards and report
  artifacts if validation, registry checks, and exact staged-file checks pass.
- Use `git add -f` only for ignored report artifacts explicitly listed in this
  task card.

## Forbidden

- Product, backend, frontend, runtime, test, dependency, workflow, package,
  lockfile, parser routing, extraction prompt, gold-label, canonical financial
  truth, runtime/model/GPU/service config, or PR39 cluster remediation changes.
- Production DB, Qdrant, news, memory, service, runtime, model, GPU, or parser
  mutation.
- Cleaning, stashing, resetting, deleting, restoring, overwriting, moving, or
  committing unrelated dirty work.
- Merge, rebase, cherry-pick, force-push, branch cleanup, PR update, PR merge,
  CI rerun, or GitHub issue/PR mutation.
- Creating child task cards or implementing C01 or any other failure cluster.

## Required Outputs

Write under
`reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/`:

- `README.md`
- `status.json`
- `artifact_inventory.json`
- `parking_recommendation.md`
- `next_child_task_queue.md`
- `diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md --repo-root .` only if safe.
- JSON parse validation for existing and generated JSON artifacts.
- `git diff --check`
- `git diff --cached --check` if staging.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md --repo-root .`
- Exact staged-file verification before any commit.
- Registry release if claimed.
- Final git status with ignored report paths visible.

## Hard Stops

- HIGH registry or file collision on this task's allowed files.
- Any need to edit product/runtime/test/dependency/workflow files.
- Any need to clean, stash, reset, delete, restore, overwrite, or move
  unrelated dirty work.
- Forbidden surfaces become required.
- Production data access becomes required.
- Committing ignored report artifacts would require bypassing current
  task-card or check-diff rules.
- Merge-parking path creation is needed but not allowed.
- Validation cannot run and cannot be honestly marked `DATA_MISSING`.
