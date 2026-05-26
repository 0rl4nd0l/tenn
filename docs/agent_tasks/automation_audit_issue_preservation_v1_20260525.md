---
job_id: automation_audit_issue_preservation_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Ops
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/**
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/README.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/status.json
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/issue_drafts.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/duplicate_check.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/data_missing.md
  - reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/automation_audit_issue_preservation_v1_20260525
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Automation Audit Issue Preservation

Preserve the recent Tenn issue-skill and automation-audit findings as
report-only GitHub issue drafts. Do not create GitHub issues in this task.

Mode detail: issue_logging_only / audit_preservation_only.
Audit-only writes are limited to this task card and its report bundle.

Primary lane: Reporting.

Supporting lanes:

- Repo Hygiene
- Ops
- Evaluation

## Objective

Record issue-ready drafts for confirmed automation audit findings before any
GitHub Issue System Protocol implementation begins.

## Allowed Writes

- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/**`

## Forbidden

- Product/backend/frontend/runtime code changes.
- Production DB, Qdrant, news, or memory store mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompt, or gold-label changes.
- Model/runtime/GPU/service config changes.
- GitHub issue creation, comments, labels, or closures.
- Branch/worktree cleanup, prune, stash, reset, rebase, cherry-pick, or merge.
- Touching unrelated dirty files or unrelated task cards.

## Required Evidence

- Current Tenn branch, HEAD, and git status.
- Skill-file location and git status.
- Read-only GitHub duplicate searches.
- Source evidence from local automation audit reports and command evidence.

## Required Outputs

- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/README.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/status.json`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/issue_drafts.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/duplicate_check.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/data_missing.md`
- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md --repo-root .`
- `python3 -m json.tool reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- Final `git status --short --untracked-files=all`

## Hard Stops

Stop if preserving the findings requires live GitHub mutation, product/runtime
code mutation, production data access, service changes, or touching unrelated
dirty files.
