---
job_id: github_issue_templates_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - .github/ISSUE_TEMPLATE/tenn_task.yml
  - .github/ISSUE_TEMPLATE/tenn_bug_regression_seed.yml
  - .github/ISSUE_TEMPLATE/tenn_audit_finding.yml
  - .github/ISSUE_TEMPLATE/tenn_followup_remediation.yml
  - .github/ISSUE_TEMPLATE/tenn_branch_merge_review.yml
  - .github/ISSUE_TEMPLATE/config.yml
  - docs/agent_tasks/github_issue_templates_v1_20260525.md
  - docs/process/github_issue_system_protocol.md
  - reports/agent_jobs/github_issue_templates_v1_20260525/README.md
  - reports/agent_jobs/github_issue_templates_v1_20260525/validation.md
  - reports/agent_jobs/github_issue_templates_v1_20260525/status.json
  - reports/agent_jobs/github_issue_templates_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/github_issue_templates_v1_20260525
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# GitHub Issue Templates

Mode: repo/process safe_extension.

## Objective

Add repo-native GitHub Issue Forms for the activated Tenn issue-system protocol
so future issue-finder, closeout, and branch-review agents create consistent,
lane-scoped, validation-ready issues.

## Scope

Create forms for:

- planned Tenn task-card-ready work;
- confirmed bugs or seed regressions;
- audit-only findings;
- follow-up remediation from closed or completed audits; and
- branch, worktree, merge, or PR visibility review.

## Allowed

- Add `.github/ISSUE_TEMPLATE/` form files and template config.
- Add this task card.
- Add report artifacts under
  `reports/agent_jobs/github_issue_templates_v1_20260525/`.
- Update `docs/process/github_issue_system_protocol.md` only to reference the
  repo-native templates.

## Forbidden

- Live GitHub issue, PR, comment, label, milestone, or Project mutation.
- Product/backend/frontend/runtime code.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompt, gold-label, model/runtime/GPU/service
  config mutation.
- Unrelated dirty files.
- Branch cleanup, merge, cherry-pick, rebase, reset, stash, prune, or delete.

## Validation

- YAML parse every issue template.
- Confirm required fields exist in each template.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/github_issue_templates_v1_20260525.md`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/github_issue_templates_v1_20260525.md`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/github_issue_templates_v1_20260525.md --repo-root .`.
- Confirm no live GitHub mutation occurred.
- Final `git status --short`.

## Hard Stops

Stop if the templates require new live labels or milestones, if validation
requires forbidden GitHub mutation, if task-card gates show unrelated dirt in
the active worktree, or if implementation requires product/runtime/data changes.
