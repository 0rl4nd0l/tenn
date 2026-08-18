---
job_id: github_issue_backlog_audit_v1_20260526
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
  - Financial Truth
  - Provenance
  - Query Orchestration
  - Memory
  - Runtime
  - Cockpit
owner: Codex
allowed_files:
  - docs/agent_tasks/github_issue_backlog_audit_v1_20260526.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/README.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/status.json
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/open_issue_matrix.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/closed_issue_safety_review.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/pr_alignment.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/milestone_health.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/label_hygiene.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/recommended_next_queue.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/data_missing.md
allowed_repo_files:
  - docs/agent_tasks/github_issue_backlog_audit_v1_20260526.md
  - reports/agent_jobs/github_issue_backlog_audit_v1_20260526/**
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/github_issue_backlog_audit_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# GitHub Issue Backlog Audit

## Objective

Audit the current GitHub issue and pull request backlog for `0rl4nd0l/tenn`
without mutating repo product code, runtime state, data stores, branches, or
GitHub state. Produce a prioritized issue-state report and a safe next
execution queue.

## Lane

- Primary lane: Reporting.
- Supporting lanes: Repo Hygiene, Evaluation, Financial Truth, Provenance,
  Query Orchestration, Memory, Runtime, and Cockpit.
- Mode: audit_only / issue_inventory.

## Allowed Scope

- Create this task card.
- Create the report bundle under
  `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/`.
- Inspect local repo state, task-card protocol files, registry state, issue
  templates, skill mirrors, worktree inventory, GitHub issues, GitHub pull
  requests, labels, and milestones.
- Classify open issues, recent closed issues, open PRs, recent closed PRs,
  milestones, labels, duplicates, parked work, blockers, and recommended next
  queue.

## Forbidden

- Product/backend/frontend/runtime code changes.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service
  config mutation.
- Branch cleanup, merge, rebase, reset, stash, prune, delete, or cherry-pick.
- Live GitHub issue, pull request, label, milestone, project, comment, or close
  mutation.
- Issue creation or issue closure.
- Unrelated dirty-file cleanup.

## Required Outputs

- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/README.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/status.json`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/open_issue_matrix.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/closed_issue_safety_review.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/pr_alignment.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/milestone_health.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/label_hygiene.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/recommended_next_queue.md`
- `reports/agent_jobs/github_issue_backlog_audit_v1_20260526/data_missing.md`

## Acceptance Criteria

- All open issues are classified.
- At least the last 50 closed issues and last 20 closed PRs are reviewed.
- Open PRs are aligned to linked or obvious issue coverage where possible.
- Closed audit issues are checked for buried unresolved findings, follow-up
  linkage, `NO_FOLLOWUP`, or `DATA_MISSING`.
- Milestone and label hygiene issues are reported without mutation.
- Parked or branch-referenced work is flagged when visible issue, PR, task,
  report, or parking coverage is missing.
- Top 10 next issues are recommended by value, unblocker value, risk,
  readiness, and validation clarity.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/github_issue_backlog_audit_v1_20260526.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/github_issue_backlog_audit_v1_20260526.md`
- `jq empty reports/agent_jobs/github_issue_backlog_audit_v1_20260526/status.json`
- `git diff --check`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Final `git status --short --untracked-files=all`

## Hard Stops

- GitHub read-only queries cannot establish issue or PR inventory.
- Required evidence would require GitHub mutation.
- Required evidence would require forbidden repo, runtime, data, branch, or
  service mutation.
- Active registry conflict creates unresolved high collision risk.
