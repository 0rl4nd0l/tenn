---
job_id: green_pr_status_comments_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/green_pr_status_comments_v1_20260602.md
  - reports/agent_jobs/green_pr_status_comments_v1_20260602/README.md
  - reports/agent_jobs/green_pr_status_comments_v1_20260602/status.json
  - reports/agent_jobs/green_pr_status_comments_v1_20260602/validation.json
  - reports/agent_jobs/green_pr_status_comments_v1_20260602/comment-log.json
  - reports/agent_jobs/green_pr_status_comments_v1_20260602/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/green_pr_status_comments_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_comment_targets:
  - 181
  - 101
  - 102
  - 90
  - 154
  - 72
  - 120
  - 121
---

# Green PR Status Comments

## Objective

Post only non-duplicate GitHub issue status comments that link currently green,
merge-clean PRs to their tracked issues while explicitly keeping the issues open
until merge/review close gates are satisfied.

## Scope

Primary lane: Reporting.

Mode: issue closeout/status only.

No product code, runtime, data, docs outside this task card/report bundle, labels,
issue bodies, or issue states may be changed.

## Candidate Issue Targets

- #181 with PR #190
- #101 with PR #191
- #102 with PR #192
- #90 with PR #197
- #154 with PR #198
- #72 with PR #200
- #120 with PR #203
- #121 with PR #202 only if the latest comments do not already carry equivalent
  green/clean audit-only status

## Hard Boundaries

- Do not close issues.
- Do not edit issue bodies.
- Do not add/remove labels.
- Do not create duplicate status comments when equivalent current evidence is
  already present.
- Do not claim product remediation is complete before the covering PR merges.
- Do not mutate runtime, services, DB, Qdrant, news, memory, financial truth,
  parser routing, extraction prompts, gold labels, model config, or GPU config.
- Do not touch shared-checkout dirty files.

## Required Preflight

1. Validate this task card.
2. Run registry list-active and check-overlap.
3. Claim this task only if there is no HIGH overlap.
4. Re-check each candidate issue's latest comments and covering PR state before
   posting.
5. Post comments only for `POST` candidates.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/green_pr_status_comments_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/green_pr_status_comments_v1_20260602.md`
- registry claim/release
- `gh pr view` / `gh pr checks` for covering PRs
- `gh issue view` for target issue comments before posting
- `jq empty reports/agent_jobs/green_pr_status_comments_v1_20260602/*.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/green_pr_status_comments_v1_20260602.md`

## Closeout Policy

This batch may only post status comments. All target issues must remain open
unless a separate future task proves a Tenn close gate after merge/review.
