---
job_id: cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609
lane: Reporting
supporting_lanes:
  - Query Orchestration
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
  - docs/agent_tasks/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609/README.md
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609/status.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609/validation.json
  - reports/agent_jobs/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609/diff-check.json
approval_required: true
approval_reference: "User said proceed after PR #337 merged and next step was preserving local merge-gate / merge-execution packets."
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_news_context_date_filter_merge_packets_preserve_v1_20260609
mutation_mode: safe_extension
requested_mutation_mode: report_artifact_preservation_and_pr_publish
production_data_access: false
github_mutation_allowed: push_branch_and_open_draft_pr_only
---

# Cockpit News Context Date Filter Merge Packets Preserve

## Objective

Preserve the local PR #337 merge-gate and merge-execution packets in a narrow
report-only follow-up PR from the current
`migration/clean-runtime-baseline-reconstruct-v1` target head.

## Scope

Mode: SAFE_EXTENSION.

Allowed changes are limited to task-card/report artifacts. Allowed GitHub
mutations are limited to pushing this preservation branch and opening one draft
PR.

## Hard Stops

- Do not modify runtime code, tests, product surfaces, data stores, prompts,
  gold labels, model/GPU config, or extraction behavior.
- Do not merge the preservation PR.
- Do not mark the preservation PR ready for review.
- Do not delete branches, refs, worktrees, or stashes.
- Do not create, edit, label, comment on, close, or reopen GitHub issues.
- Stop if the diff includes files outside this card's allowlist.

## Required Output

- Preserve PR #337 merge-gate and merge-execution task cards/reports.
- Push a narrow preservation branch.
- Open one draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
- Record validation and GitHub readback in the preservation report.
