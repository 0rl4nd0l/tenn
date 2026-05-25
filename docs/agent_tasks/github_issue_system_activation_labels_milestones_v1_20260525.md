---
job_id: github_issue_system_activation_labels_milestones_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/github_issue_system_activation_labels_milestones_v1_20260525.md
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/README.md
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/status.json
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/labels_before.json
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/labels_after.json
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/milestones_before.json
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/milestones_after.json
  - reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525/created_or_existing_matrix.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/github_issue_system_activation_labels_milestones_v1_20260525
mutation_mode: github_metadata_setup
allow_audit_code_changes: true
production_data_access: false
---

# GitHub Issue System Activation: Labels and Milestones

Mode detail: GitHub metadata setup safe_extension.

## Objective

Create or reconcile Tenn GitHub labels and milestones so issue-finder,
issue-closeout, and issue-resolution-reviewer can use GitHub Issues as Tenn's
live actionable backlog.

## Allowed GitHub Mutations

- Create missing labels.
- Update label descriptions or colors only when clearly safe and
  non-destructive.
- Create missing M0-M6 milestones.

## Forbidden

- Live issue closeout.
- Live issue creation.
- Issue body edits, comments, reopening, or closure.
- Pull request mutation.
- GitHub Project mutation.
- Product/backend/frontend/runtime code.
- Production DB, Qdrant, news, or memory store mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, or gold-label changes.
- Model/runtime/GPU/service config changes.
- Unrelated dirty files.
- Merge, cherry-pick, rebase, reset, stash, prune, delete, or cleanup.

## Required Outputs

- This task card.
- Before and after label snapshots.
- Before and after milestone snapshots.
- Created/existing reconciliation matrix.
- Status and validation report.

## Validation

- Confirm repository target before mutation.
- De-duplicate against existing labels and milestones before mutation.
- JSON parse all JSON artifacts.
- `git diff --check`.
- Task-card frontmatter parse.
- Confirm no issue bodies, comments, closures, PRs, or Projects were mutated by
  this task.

## Hard Stops

Stop if `gh` is unavailable, authentication is missing, the target repository is
not `0rl4nd0l/tenn`, or completing the task requires forbidden repo, runtime,
data, GitHub issue, PR, or Project mutations.
