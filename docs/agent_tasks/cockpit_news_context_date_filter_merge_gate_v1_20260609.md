---
job_id: cockpit_news_context_date_filter_merge_gate_v1_20260609
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
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_news_context_date_filter_merge_gate_v1_20260609
mutation_mode: audit_only
requested_mutation_mode: merge_readiness_review
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# Cockpit News Context Date Filter Merge Gate

## Objective

Perform a read-only merge-readiness gate for draft PR #337.

## Scope

Mode: AUDIT_ONLY.

Review the current GitHub PR state, checks, changed files, target-base merge
state, task-card/report contracts, focused local validation, and a non-mutating
merge probe. This task records whether PR #337 is ready for an operator-approved
ready/merge mutation.

## Hard Stops

- Do not merge the PR.
- Do not mark the PR ready for review.
- Do not create, edit, label, comment on, close, or reopen GitHub issues or PRs.
- Do not push commits.
- Do not delete branches, refs, worktrees, or stashes.
- Do not mutate DB, Qdrant, Redis, news stores, source PDFs, prompts, gold
  labels, model/GPU config, or production data.
- Stop on failed checks, merge conflicts, disallowed files, or task-card
  validation failures.

## Required Output

- Fresh GitHub readback for PR #337.
- Non-mutating merge probe result.
- Focused validation results.
- Clear decision: ready for explicit operator-approved ready/merge mutation, or
  blocked with reason.
