---
job_id: reporting_audit_closeout_batch_v1_20260531
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531
production_data_access: false
allow_audit_code_changes: true
github_mutation_allowed: true
issue_numbers:
  - 95
  - 105
  - 116
  - 117
  - 118
allowed_files:
  - docs/agent_tasks/reporting_audit_closeout_batch_v1_20260531.md
  - docs/agent_tasks/cockpit_source_drawer_semantics_audit_v1_20260526.md
  - docs/agent_tasks/news_empty_state_value_audit_v1_20260526.md
  - docs/agent_tasks/marketplace_home_location_setup_audit_v1_20260526.md
  - docs/agent_tasks/thesis_audit_first_run_workflow_audit_v1_20260526.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/**
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/**
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/**
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/**
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/**
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/README.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/status.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/issue_closeout_matrix.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/followup_issue_map.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/data_missing.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/validation.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/diff-check.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/code_review.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/resolution_review.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/current_green_closeout_20260531.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/current_green_closeout_20260531.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/README.md
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/status.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/source_state_matrix.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/validation.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/README.md
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/status.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/workflow_matrix.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/validation.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/README.md
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/status.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/location_contract_matrix.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/validation.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/README.md
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/status.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/first_run_matrix.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/validation.json
allowed_repo_files:
  - docs/agent_tasks/reporting_audit_closeout_batch_v1_20260531.md
  - docs/agent_tasks/cockpit_source_drawer_semantics_audit_v1_20260526.md
  - docs/agent_tasks/news_empty_state_value_audit_v1_20260526.md
  - docs/agent_tasks/marketplace_home_location_setup_audit_v1_20260526.md
  - docs/agent_tasks/thesis_audit_first_run_workflow_audit_v1_20260526.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/**
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/**
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/**
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/**
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/**
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/README.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/status.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/issue_closeout_matrix.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/followup_issue_map.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/data_missing.md
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/validation.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/diff-check.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/code_review.json
  - reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/resolution_review.json
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/current_green_closeout_20260531.md
  - reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/current_green_closeout_20260531.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/README.md
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/status.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/source_state_matrix.json
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/validation.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/README.md
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/status.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/workflow_matrix.json
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/validation.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/README.md
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/status.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/location_contract_matrix.json
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/validation.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/README.md
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/status.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/first_run_matrix.json
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/validation.json
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
  - merge, rebase, cherry-pick, force-push, reset, stash, or branch cleanup
  - broad local runtime/data suites that mutate state
  - unrelated dirty work
---

# Reporting Audit Closeout Batch

## Objective

Close out issues #95, #105, #116, #117, and #118 only when a Tenn issue-closeout
gate is satisfied by current evidence. Produce durable report artifacts and
GitHub closeout comments without changing product code, runtime state, data
stores, financial truth, parser routing, prompts, gold labels, workflows, or
dependencies.

## Scope

- Re-check issue, PR, check, and repo evidence before every closeout decision.
- Use existing source, test, and prior browser-audit evidence for report-only
  decisions.
- Create the missing issue-specific task cards and report bundles for #95,
  #116, #117, and #118.
- Add a current PR #39 supersession addendum for #105 if current GitHub CI makes
  the original red-CI cluster split obsolete.
- Comment on and close GitHub issues only when a close gate is satisfied.

## Allowed Writes

- This controller task card.
- The issue-specific task cards listed in `allowed_files`.
- Report artifacts under the listed `reports/agent_jobs/` directories.
- GitHub issue comments and close actions for #95, #105, #116, #117, and #118
  after a close gate is met.

## Forbidden

- Product/backend/frontend/runtime code changes.
- Dependency, workflow, package, or lockfile changes.
- Test rewrites or product test fixes.
- Production DB, Qdrant, news, or memory mutation.
- Canonical financial truth, parser routing, extraction prompt, or gold-label
  mutation.
- Runtime, model, GPU, or service configuration changes.
- Branch cleanup, merge, rebase, cherry-pick, force-push, reset, or stash.
- Unrelated dirty-work cleanup.

## Required Outputs

- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/README.md`
- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/status.json`
- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/issue_closeout_matrix.md`
- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/followup_issue_map.md`
- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/data_missing.md`
- `reports/agent_jobs/reporting_audit_closeout_batch_v1_20260531/validation.json`
- Issue-specific report bundles for #95, #105, #116, #117, and #118.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_audit_closeout_batch_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_audit_closeout_batch_v1_20260531.md --repo-root .`
- Registry claim before report writes and release before final report.
- GitHub issue/PR/check inspection.
- JSON validation for generated status and validation artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_audit_closeout_batch_v1_20260531.md`

## Hard Stops

- HIGH active collision risk on any allowed file.
- Product/runtime/data mutation becomes necessary for a closeout claim.
- Any unresolved `FOLLOWUP_REQUIRED` item cannot be linked, created, parked, or
  marked `DATA_MISSING`.
- GitHub authentication or repository identity cannot be verified before issue
  mutation.
- Task-card validation or check-diff cannot be made clean without touching
  forbidden files.
