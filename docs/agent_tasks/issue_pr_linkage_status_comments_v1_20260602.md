---
job_id: issue_pr_linkage_status_comments_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602
allowed_files:
  - docs/agent_tasks/issue_pr_linkage_status_comments_v1_20260602.md
  - reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602/README.md
  - reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602/issue_pr_linkage_matrix.md
  - reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602/status.json
  - reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602/validation.json
  - reports/agent_jobs/issue_pr_linkage_status_comments_v1_20260602/diff-check.json
github_comment_targets:
  - 138
  - 140
  - 146
  - 148
---

# Task

Post status-only GitHub issue comments for open issues that already have visible green PR coverage but no issue-side comment.

Targets:

- #138 -> PR #172
- #140 -> PR #173
- #146 -> PR #164
- #148 -> PR #166

# Boundaries

- Do not close issues.
- Do not edit labels, milestones, assignees, projects, or PR state.
- Do not mutate product/backend/frontend/runtime/data files.
- Do not run cleanup, prune worktrees, start services, call live chat, or access production data.
- For report-only PRs, make clear the issue remains open until review/merge and any implementation/cleanup gate is satisfied.

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue_pr_linkage_status_comments_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/issue_pr_linkage_status_comments_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue_pr_linkage_status_comments_v1_20260602.md`
- fresh `gh issue view` for targets
- fresh `gh pr view` for covering PRs
- JSON parse checks
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue_pr_linkage_status_comments_v1_20260602.md`
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_registry.py release issue_pr_linkage_status_comments_v1_20260602`

# Definition Of Done

- Each target issue has one current status comment linking the covering PR.
- The report records comment URLs and confirms issues were not closed.
- No forbidden surfaces are changed.
