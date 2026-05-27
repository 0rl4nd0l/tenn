---
job_id: pr39_lint_and_test_failure_cluster_split_v1_20260526
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526
production_data_access: false
allow_audit_code_changes: true
github_mutation_allowed: false
issue_number: 105
pr_number: 39
allowed_files:
  - docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/README.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/status.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/failure_clusters.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/child_task_proposals.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/pr39_merge_readiness.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/diff-check.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
allowed_repo_files:
  - docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
forbidden:
  - product/backend/frontend/runtime code changes
  - dependency/workflow/package/lockfile changes
  - test rewrites or test fixes
  - production DB/Qdrant/news/memory
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - runtime/model/GPU/service config
  - merging, rebasing, cherry-picking, or updating PR #39
  - closing/opening/updating GitHub issues unless explicitly approved later
  - broad local runtime/data suites that mutate state
  - unrelated dirty work
---

# PR #39 Lint And Test Failure Cluster Split

## Objective

Produce a current, evidence-backed failure-cluster map and remediation or
parking plan for issue #105 and PR #39 without fixing product code, tests,
dependencies, workflows, runtime state, or GitHub state.

## Scope

- Validate current repo/worktree state before writing reports.
- Inspect PR #39 metadata, status checks, failing GitHub Actions logs, relevant
  CI workflow configuration, local reports, and duplicate GitHub trackers.
- Split current failures into actionable clusters with owner lane, likely file
  surfaces, classification, baseline-vs-PR status where evidence allows, and
  next safe action.
- Draft child task proposals only; do not create GitHub issues unless separately
  approved.
- Reference #66 only as the closed audit precursor, not as completion of #105.
- Note #55 as closed/remediated and removed from this queue if mentioned.

## Allowed Writes

- This task card.
- Report artifacts under
  `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/`.

## Forbidden

- Product, backend, frontend, runtime, dependency, workflow, package, lockfile,
  parser routing, extraction prompt, gold-label, canonical financial truth,
  runtime/model/GPU/service config, test-fix, or test-rewrite changes.
- Production DB, Qdrant, news, memory, or service mutation.
- Broad local runtime/data suites that mutate state.
- Merge, rebase, cherry-pick, update, or rerun PR #39.
- GitHub issue, PR, label, milestone, comment, or project mutation.
- Unrelated dirty-work cleanup.

## Required Outputs

- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/README.md`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/status.json`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/failure_clusters.json`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/child_task_proposals.md`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/pr39_merge_readiness.md`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md --repo-root .`
- Registry claim only if safe and supported.
- GitHub PR/check/run inspection for PR #39.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`

## Hard Stops

- High active registry or file collision that cannot be isolated.
- Required evidence or validation needs forbidden product/runtime/data/GitHub
  mutation.
- PR merge, rebase, cherry-pick, update, or CI rerun becomes necessary.
- Report generation cannot be performed or safely approximated.
- Out-of-scope dirty work cannot be avoided.
