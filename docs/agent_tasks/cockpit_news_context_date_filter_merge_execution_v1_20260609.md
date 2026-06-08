---
job_id: cockpit_news_context_date_filter_merge_execution_v1_20260609
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_news_context_date_filter_merge_gate_v1_20260609.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_gate_v1_20260609/README.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_gate_v1_20260609/status.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_gate_v1_20260609/validation.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_gate_v1_20260609/diff-check.json
  - docs/agent_tasks/cockpit_news_context_date_filter_merge_execution_v1_20260609.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_execution_v1_20260609/README.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_execution_v1_20260609/status.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_execution_v1_20260609/validation.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_execution_v1_20260609/diff-check.json
approval_required: true
approval_reference: "User said proceed after PR #337 merge-readiness gate reported CLEAN/MERGEABLE with green checks."
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_news_context_date_filter_merge_execution_v1_20260609
mutation_mode: safe_extension
requested_mutation_mode: mark_ready_and_merge_pr_only
production_data_access: false
github_mutation_allowed: mark_ready_and_merge_pr_337_only
---

# Cockpit News Context Date Filter Merge Execution

## Objective

Mark draft PR #337 ready for review and merge it into
`migration/clean-runtime-baseline-reconstruct-v1` after a fresh clean readback.

## Scope

Mode: SAFE_EXTENSION.

Allowed GitHub mutations are limited to:

- Mark PR #337 ready for review.
- Merge PR #337 with a normal merge commit.

## Hard Stops

- Do not merge any PR other than #337.
- Do not delete the source branch.
- Do not create, edit, label, comment on, close, or reopen issues.
- Do not push commits.
- Do not delete branches, refs, worktrees, or stashes.
- Do not mutate DB, Qdrant, Redis, news stores, source PDFs, prompts, gold
  labels, model/GPU config, or production data.
- Stop if #337 is not `OPEN`, is not clean/mergeable, has failing or pending
  checks, or no longer targets `migration/clean-runtime-baseline-reconstruct-v1`.

## Required Output

- Fresh pre-mutation readback for PR #337.
- Ready-for-review mutation readback.
- Merge mutation readback with merge commit.
- Report artifacts with validation and explicit forbidden-actions avoided.
